from conversation_handlers import translator_start
from directory_handlers import directory_menu
import logging
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CommandHandler, CallbackQueryHandler
from typing import List, Dict, Any, Optional
from utils import split_text, format_post_message, format_currency_message, is_admin
from aiosqlite import Connection
import config
import db
import api
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник команди /start."""
    keyboard = ReplyKeyboardMarkup(
    [['📢 Тривоги', '💰 Курс валют'],
     ['📝 Переглянути оголошення', '📝 Додати оголошення'],
     ["✍️ Зворотний зв'язок", "🗣️ Перекладач", "🗺️ Довідник"]],
    resize_keyboard=True
)
    # 1. Відправляємо вітальне повідомлення з фото та клавіатурою
    await update.message.reply_photo(
        photo=config.WELCOME_PHOTO_ID,
        caption="Привіт! Я ваш бот, що інформує про повітряні тривоги, новини та події у Білгород-Дністровському.",
        reply_markup=keyboard
    )
    # 2. Відправляємо презентацію другим повідомленням
    presentation_text = """
🇺🇦 Привіт! Знайомтесь з вашим персональним ботом для Білгород-Дністровського!
Я допоможу вам залишатись в курсі подій та отримувати важливу інформацію.
📢 **Головні функції:**
⚡ ️ Оперативні сповіщення про повітряні тривоги та відбої.
💰 Актуальний курс валют.
📝 Дошка оголошень для вашої спільноти.
🗺️ Зручний довідник корисних закладів та послуг.
✍️ Зворотний зв'язок з розробником.
Запускайте і користуйтесь!
➡️ t.me/XuBotAkkerman\_bot
"""
    await update.message.reply_text(presentation_text, parse_mode=ParseMode.MARKDOWN)
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник команди /help."""
    text = (
        "Я можу інформувати вас про повітряні тривоги та події в Білгород-Дністровському, показувати актуальний курс...\""
    )
    await update.message.reply_text(text)
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Відправляє статус бота."""
    db_session = context.bot_data['db_session']
    try:
        current_alerts = await db.get_last_alerts_state(db_session)
        if current_alerts:
            message = f"🔴 **Активні повітряні тривоги в регіонах:**\n\n" + "\n".join(f"- {region}" for region in current_alerts)
        else:
            message = "🟢 **Наразі немає активних повітряних тривог.**"
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logging.error(f"Помилка при отриманні статусу тривог: {e}", exc_info=True)
        await update.message.reply_text("Не вдалося отримати статус повітряних тривог. Спробуйте пізніше.")
async def currency_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Відправляє актуальний курс валют."""
    logging.info("Отримую курси валют...")
    aiohttp_session = context.bot_data.get('aiohttp_session')
    if not aiohttp_session:
        await update.message.reply_text("Виникла помилка. Спробуйте пізніше.")
        return
    data = await api.get_currency_rates(aiohttp_session)
    if data:
        message = format_currency_message(data)
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("Не вдалося отримати курси валют. Спробуйте пізніше.")
async def announcements_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Відправляє список всіх оголошень."""
    logging.info("Початок виконання команди 'announcements_command'")
    db_session = context.bot_data.get('db_session')
    if not db_session:
        logging.error("Немає доступу до db_session.")
        await update.message.reply_text("Виникла помилка. Спробуйте пізніше.")
        return
    try:
        posts = await db.get_posts(db_session)
        logging.info(f"Отримано оголошень: {len(posts) if posts else 0}")
        if not posts:
            await update.message.reply_text("Наразі немає активних оголошень.")
            return
        messages = []
        for post in posts:
            message = format_post_message(post)
            keyboard = None
            if is_admin(update.effective_user.id):
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Видалити", callback_data=f"delete_post_{post['id']}") ]])
            messages.append((message, keyboard))
        for msg, kb in messages:
            for part in split_text(msg):
                await update.message.reply_text(part, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        logging.info("Успішно відправлено оголошення.")
    except Exception as e:
        logging.error(f"Помилка в announcements_command: {e}", exc_info=True)
        await update.message.reply_text("Виникла помилка при завантаженні оголошень. Спробуйте пізніше.")
async def delete_post_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник кнопки 'Видалити оголошення'."""
    query = update.callback_query
    post_id = int(query.data.split('_')[-1])
    db_session = context.bot_data.get('db_session')
    if not db_session:
        await query.answer("Виникла помилка.")
        return
    if not is_admin(query.from_user.id):
        await query.answer("Ви не адміністратор.")
        return
    await db.delete_post(db_session, post_id)
    await query.answer("Оголошення видалено.")
    await query.edit_message_text(f"Оголошення #{post_id} успішно видалено.")
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник текстових повідомлень, що не є командами."""
    if update.message.chat.type != 'private':
        return
    if update.message.text == '📢 Тривоги':
        await status_command(update, context)
    elif update.message.text == '💰 Курс валют':
        await currency_command(update, context)
    elif update.message.text == '📝 Переглянути оголошення':
        await announcements_command(update, context)
    elif update.message.text == '🗺️ Довідник':
        await directory_menu(update, context)
    elif update.message.text == '🗣️ Перекладач':
        await translator_start(update, context)
    else:
        await update.message.reply_text("Вибачте, я не знаю такої команди. Скористайтеся меню або командою /help.")
