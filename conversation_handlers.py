import translator_api
import json
import logging
import re
import asyncio
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CommandHandler, CallbackQueryHandler
from typing import List, Dict, Any, Optional
from datetime import datetime
from utils import format_event_message, format_post_message
from aiosqlite import Connection
import config
import db
import api
TRANSLATOR = 1
# --- Обробники для діалогу зворотного зв'язку (Feedback Conversation) ---
async def feedback_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Початок діалогу зворотного зв'язку."""
    await update.message.reply_text("Напишіть ваше повідомлення для зворотного зв'язку. Щоб скасувати, надішліть /cancel.")
    return config.FEEDBACK
async def feedback_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробляє отримане повідомлення зворотного зв'язку."""
    feedback_text = update.message.text
    user = update.effective_user
    logging.info(f"Отримано зворотний зв'язок від @{user.username} ({user.id}): {feedback_text}")
    await update.message.reply_text("Дякую! Ваш відгук отримано. Я передав його розробнику. Можете надіслати новий або продовжити роботу з ботом.")
    return ConversationHandler.END
async def feedback_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Скасовує діалог зворотного зв'язку."""
    await update.message.reply_text("Відправлення відгуку скасовано.")
    return ConversationHandler.END
# --- Обробники для діалогу додавання оголошення (Add Post Conversation) ---
async def add_post_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Початок діалогу додавання оголошення."""
    await update.message.reply_text("Введіть заголовок для вашого оголошення. Щоб скасувати, надішліть /cancel.")
    return config.POST_TITLE
async def add_post_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробляє заголовок оголошення."""
    context.user_data['post_title'] = update.message.text
    await update.message.reply_text("Введіть повний текст оголошення:")
    return config.POST_CONTENT
async def add_post_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробляє вміст оголошення."""
    context.user_data['post_content'] = update.message.text
    await update.message.reply_text("Введіть контактну інформацію (телефон, нікнейм, посилання):")
    return config.POST_CONTACT
async def add_post_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробляє контактну інформацію та пропонує підтвердити."""
    context.user_data['post_contact'] = update.message.text
    post_title = context.user_data['post_title']
    post_content = context.user_data['post_content']
    post_contact = context.user_data['post_contact']
    preview_message = (
        f"**Заголовок:** {post_title}\n"
        f"**Опис:** {post_content}\n"
        f"**Контакти:** {post_contact}\n\n"
        f"**Чи правильно все вказано?**\n"
        f"Надішліть 'Так' для підтвердження або 'Ні' для скасування."
    )
    await update.message.reply_text(preview_message, parse_mode=ParseMode.MARKDOWN)
    return config.POST_CONFIRM
async def add_post_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Підтверджує та зберігає оголошення."""
    response = update.message.text.lower()
    if response == 'так':
        db_session = context.bot_data['db_session']
        author_id = update.effective_user.id
        title = context.user_data['post_title']
        content = context.user_data['post_content']
        contact_info = context.user_data['post_contact']
        await db.save_post(db_session, author_id, title, content, contact_info)
        await update.message.reply_text("Ваше оголошення успішно додано!")
        logging.info(f"Нове оголошення додано: {title}")
        context.user_data.clear()
        return ConversationHandler.END
    elif response == 'ні':
        await update.message.reply_text("Додавання оголошення скасовано.")
        context.user_data.clear()
        return ConversationHandler.END
    else:
        await update.message.reply_text("Будь ласка, надішліть 'Так' або 'Ні'.")
        return config.POST_CONFIRM
async def add_post_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Скасовує діалог додавання оголошення."""
    await update.message.reply_text("Додавання оголошення скасовано.")
    context.user_data.clear()
    return ConversationHandler.END
feedback_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("feedback", feedback_start), MessageHandler(filters.Regex(r'^✍️ Зворотний зв\'язок$'), feedback_start)],
    states={
        config.FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_received)],
    },
    fallbacks=[CommandHandler("cancel", feedback_cancel)]
)
add_post_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("add_post", add_post_start), MessageHandler(filters.Regex('^📝 Додати оголошення$'), add_post_start)],
    states={
        config.POST_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_post_title)],
        config.POST_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_post_content)],
        config.POST_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_post_contact)],
        config.POST_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_post_confirm)],
    },
    fallbacks=[CommandHandler("cancel", add_post_cancel)]
)
# --- Обробники для діалогу перекладача (Translator Conversation) ---
TRANSLATOR_LANG, TRANSLATOR_TEXT = range(2)

async def translator_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Початок діалогу перекладача."""
    try:
        with open('languages.json', 'r', encoding='utf-8') as f:
            languages_data = json.load(f)
            available_langs = languages_data.get('available_languages', {})
        keyboard = []
        for code, name in available_langs.items():
            keyboard.append([InlineKeyboardButton(f"{name} ({code.upper()})", callback_data=f"translate_lang:{code}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Оберіть мову, на яку потрібно перекласти текст:", reply_markup=reply_markup)
        return TRANSLATOR_LANG
    except FileNotFoundError:
        await update.message.reply_text("Вибачте, файл зі списком мов не знайдено. Зверніться до адміністратора.")
        return ConversationHandler.END
    except json.JSONDecodeError:
        await update.message.reply_text("Виникла помилка при читанні файлу мов. Зверніться до адміністратора.")
        return ConversationHandler.END

async def translator_lang_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробляє вибір мови та запитує текст для перекладу."""
    query = update.callback_query
    await query.answer()
    _, target_lang = query.data.split(':')
    context.user_data['target_lang'] = target_lang
    await query.edit_message_text(f"Оберіть мову, на яку потрібно перекласти текст: **{target_lang.upper()}**\n\nТепер надішліть текст, який потрібно перекласти. Щоб скасувати, надішліть /cancel.", parse_mode=ParseMode.MARKDOWN)
    return TRANSLATOR_TEXT

async def translator_text_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Перекладає отриманий текст і відправляє результат."""
    text_to_translate = update.message.text
    target_lang = context.user_data.get('target_lang', 'en')
    if not text_to_translate:
        await update.message.reply_text("Будь ласка, надішліть текст для перекладу.")
        return TRANSLATOR_TEXT
    try:
        translated_text = await translator_api.translate_text(text=text_to_translate, source_lang='auto', target_lang=target_lang)
        if translated_text:
            await update.message.reply_text(f"**Переклад:**\n\n`{translated_text}`", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("Не вдалося перекласти текст. Спробуйте пізніше.")
    except Exception as e:
        await update.message.reply_text("Виникла помилка під час перекладу. Спробуйте пізніше.")
    return ConversationHandler.END

async def translator_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Скасовує діалог перекладача."""
    await update.message.reply_text("Переклад скасовано.")
    return ConversationHandler.END

translator_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("translator", translator_start), MessageHandler(filters.Regex('^🗣️ Перекладач$'), translator_start)],
    states={
        TRANSLATOR_LANG: [CallbackQueryHandler(translator_lang_selected, pattern=r'^translate_lang:')],
        TRANSLATOR_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, translator_text_received)],
    },
    fallbacks=[CommandHandler("cancel", translator_cancel)]
)
