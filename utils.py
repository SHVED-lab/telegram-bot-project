import logging
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from typing import List, Dict, Any, Optional
import re
from datetime import datetime
# Список ID адміністраторів
ADMIN_IDS = [1077089506]
def is_admin(user_id: int) -> bool:
    """Перевіряє, чи є користувач адміністратором."""
    return user_id in ADMIN_IDS
def split_text(text: str, max_length: int = 4000) -> List[str]:
    """
    Розбиває довгий текст на повідомлення, що не перевищують максимальну довжину
    для Telegram, зберігаючи цілісність абзаців.
    """
    messages = []
    current_message = ""
    for paragraph in text.split('\n\n'):
        if len(current_message) + len(paragraph) + 2 > max_length:
            if current_message:
                messages.append(current_message)
            current_message = paragraph
        else:
            if current_message:
                current_message += '\n\n' + paragraph
            else:
                current_message = paragraph
    if current_message:
        messages.append(current_message)
    return messages
def format_event_message(item: Dict[str, Any], is_today: bool) -> str:
    """Форматує об'єкт події для відправки у вигляді повідомлення."""
    if is_today:
        header = "✨     **Події на сьогодні:**\n\n"
    else:
        header = "📆 **Афіша на завтра:**\n\n"
    text = f"{header}"
    text += f"**{item.get('title', 'Без назви')}**\n"
    text += f"📅 Дата: {item.get('date', 'Невідомо')}\n"
    text += f"Джерело: *{item.get('source', 'Невідомо')}*\n\n"
    text += f"[Детальніше]({item.get('url', '#')})"
    return text
def format_post_message(post: Dict[str, Any]) -> str:
    """Форматує об'єкт оголошення для відправки у вигляді повідомлення."""
    message = (
        f"**📢 Оголошення: {post.get('title', 'Без назви')}**\n\n"
        f"{post.get('content', 'Без змісту')}\n\n"
        f"**Контакти:** {post.get('contact_info', 'Не вказано')}\n"
    )
    return message
def format_currency_message(data: list) -> str:
    """Форматує дані курсу валют для відправки у вигляді повідомлення."""
    message = "💰 **Актуальний курс валют (Monobank)**\n\n"
    for rate in data:
        if rate.get('currencyCodeA') == 840 and rate.get('currencyCodeB') == 980: # USD
            message += f"🇺🇸 Долар США (USD)\n"
            message += f"   Купівля: {rate.get('rateBuy'):.2f} грн\n"
            message += f"   Продаж: {rate.get('rateSell'):.2f} грн\n\n"
        elif rate.get('currencyCodeA') == 978 and rate.get('currencyCodeB') == 980: # EUR
            message += f"🇪🇺 Євро (EUR)\n"
            message += f"   Купівля: {rate.get('rateBuy'):.2f} грн\n"
            message += f"   Продаж: {rate.get('rateSell'):.2f} грн\n\n"
    return message
def get_region_name(location_title: str) -> str:
    """Повертає ім'я регіону з повної назви, або саму назву, якщо регіон не знайдено."""
    match = re.search(r'\((\w+)\s+область\)', location_title)
    if match:
        return f"{match.group(1).capitalize()} область"
    return location_title
# === НОВА ФУНКЦІЯ: для завантаження даних довідника ===
import json
import logging
import os
# Використовуємо глобальну змінну для кешування даних довідника
_DIRECTORY_CACHE = None
async def load_directory_data() -> dict:
    """
    Завантажує дані довідника з файлу directory.json з кешуванням.
    Дані завантажуються з диска лише один раз, при першому запиті.
    """
    global _DIRECTORY_CACHE
    if _DIRECTORY_CACHE is not None:
        logging.info("Дані довідника завантажено з кешу.")
        return _DIRECTORY_CACHE
    file_path = os.path.join(os.path.dirname(__file__), 'directory.json')
    if not os.path.exists(file_path):
        logging.error(f"Файл довідника не знайдено за шляхом: {file_path}")
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            _DIRECTORY_CACHE = data
            logging.info("Дані довідника успішно завантажено з файлу.")
            return data
    except json.JSONDecodeError as e:
        logging.error(f"Помилка при читанні файлу directory.json. Перевірте формат JSON: {e}")
        return {}
    except Exception as e:
        logging.error(f"Невідома помилка при завантаженні файлу довідника: {e}")
        return {}
# =======================================================
async def send_alert_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, alert: Dict[str, Any], is_start: bool, sticker_id: Optional[str] = None) -> None:
    """Надсилає сповіщення про тривогу в зазначений чат."""
    region = alert.get('location_title')
    if is_start:
        message = f"🔴 **Повітряна тривога!**\n\n**{region}**"
    else:
        message = f"🟢 **Відбій повітряної тривоги!**\n\n**{region}**"
    try:
        if sticker_id:
            await context.bot.send_sticker(chat_id=chat_id, sticker=sticker_id)
        await context.bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logging.error(f"Не вдалося опублікувати сповіщення про тривогу в канал {chat_id}: {e}", exc_info=True)
