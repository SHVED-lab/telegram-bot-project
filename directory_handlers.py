from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext
from utils import load_directory_data
async def directory_menu(update: Update, context: CallbackContext) -> None:
    """Показує головне меню довідника."""
    if update.callback_query:
        await update.callback_query.answer()
    data = await load_directory_data()
    if not data:
        if update.message:
            await update.message.reply_text("Помилка: Не вдалося завантажити дані довідника.")
        return
    keyboard = []
    for category_name in data.keys():
        keyboard.append([InlineKeyboardButton(category_name, callback_data=f"dir_cat:{category_name}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад до головного меню", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("Оберіть категорію:", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text("Оберіть категорію:", reply_markup=reply_markup)
async def directory_show_items(update: Update, context: CallbackContext) -> None:
    """Показує список елементів у вибраній категорії."""
    query = update.callback_query
    await query.answer()
    _, category_name = query.data.split(':')
    data = await load_directory_data()
    items = data.get(category_name, {})
    if not items:
        await query.edit_message_text("В цій категорії немає даних.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="dir_menu")]]))
        return
    keyboard = []
    for item_id, item_data in items.items():
        button_text = item_data.get("назва", "Без назви")
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"dir_item:{category_name}:{item_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="dir_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"--- **{category_name}** ---", reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
async def directory_show_item_details(update: Update, context: CallbackContext) -> None:
    """Показує деталі вибраного елемента."""
    query = update.callback_query
    await query.answer()
    _, category_name, item_id = query.data.split(':')
    data = await load_directory_data()
    item_data = data.get(category_name, {}).get(item_id, {})
    if not item_data:
        await query.edit_message_text("Помилка: Дані не знайдено.")
        return
    text = f"**{item_data.get('назва', 'Невідомо')}**\n\n"
    if item_data.get("адреса"):
        text += f"📍 **Адреса:** {item_data['адреса']}\n"
    if item_data.get("години роботи"):
        text += f"⏰    **Години роботи:** {item_data['години роботи']}\n"
    if item_data.get("телефон"):
        text += f"📞 **Телефон:** {item_data['телефон']}\n"
    keyboard_rows = []
    if item_data.get("map_url"):
        keyboard_rows.append([InlineKeyboardButton("📍 Показати на карті", url=item_data["map_url"])])
    keyboard_rows.append([InlineKeyboardButton("🔙 Назад", callback_data=f"dir_cat:{category_name}")])
    reply_markup = InlineKeyboardMarkup(keyboard_rows)
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
async def main_menu_from_callback(update: Update, context: CallbackContext) -> None:
    """Обробник для повернення в головне меню."""
    query = update.callback_query
    await query.answer()
    keyboard = ReplyKeyboardMarkup(
        [['📢 Тривоги', '💰 Курс валют'],
         ['📝 Переглянути оголошення', '📝 Додати оголошення'],
         ["✍️ Зворотний зв'язок", "🗺️ Довідник"]],
        resize_keyboard=True
    )
    await query.edit_message_text("Ви повернулись до головного меню")
