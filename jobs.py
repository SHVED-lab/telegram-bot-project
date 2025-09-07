import logging
from api import get_all_alerts, get_all_events
import db
import config
from utils import send_alert_message, format_event_message, split_text
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from datetime import date, timedelta
from typing import List, Dict, Any
# --- Функції для фонових завдань ---
async def check_for_alerts(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Перевіряє наявність повітряних тривог та надсилає сповіщення."""
    try:
        logging.info("Перевіряю повітряні тривоги...")
        db_session = context.bot_data['db_session']
        aiohttp_session = context.bot_data['aiohttp_session']
        alerts = await get_all_alerts(aiohttp_session)
        # Перевірка на випадок, якщо API не повернуло даних
        if alerts is None:
            logging.error("Не вдалося отримати дані про тривоги. Пропускаю перевірку.")
            return
        # Логуємо всі активні тривоги по всій Україні
        all_active_alerts = [alert.location_title for alert in alerts if alert.alert_type == 'air_raid']
        logging.info(f"Активні тривоги по Україні: {all_active_alerts}")
        current_alerts = await db.get_last_alerts_state(db_session)
        # Перевірка на відбій тривоги ТІЛЬКИ для Одеської області
        if config.TARGET_REGION in current_alerts and config.TARGET_REGION not in all_active_alerts:
            logging.info(f"Відбій у регіоні: {config.TARGET_REGION}")
            await send_alert_message(context, config.XYA_CHANNEL_ID, {'location_title': config.TARGET_REGION}, is_start=False, sticker_id='CAACAgIAAxkBAAERtjJorLtblGjBbtREQeYP31RfgVoDQwACSIkAAsSAYUnxGAxeP4qvPjYE')
        # Перевірка на нову тривогу ТІЛЬКИ для Одеської області
        elif config.TARGET_REGION not in current_alerts and config.TARGET_REGION in all_active_alerts:
            logging.info(f"Нова тривога у регіоні: {config.TARGET_REGION}")
            await send_alert_message(context, config.XYA_CHANNEL_ID, {'location_title': config.TARGET_REGION}, is_start=True, sticker_id='CAACAgIAAxkBAAERtj9orLytPDjfsqmwzT1EW9KJ5wIK8gACfIYAAldXaElGJIq9peSKpjYE')
        # Завжди зберігаємо актуальний стан тривог після перевірки
        await db.save_alerts_state(db_session, all_active_alerts)
    except Exception as e:
        logging.error(f"Помилка в завданні check_for_alerts: {e}", exc_info=True)
async def send_events_today(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Відправляє в канал події на сьогоднішній день."""
    try:
        db_session = context.bot_data['db_session']
        aiohttp_session = context.bot_data['aiohttp_session']
        all_events = await get_all_events(aiohttp_session)
        today = date.today().strftime("%d.%m.%Y")
        today_events = [e for e in all_events if e.get('date') == today]
        if not today_events:
            logging.warning("Події на сьогодні не знайдені.")
            return
        for event in today_events:
            is_sent = await db.is_event_sent(db_session, event['url'])
            if not is_sent:
                logging.info(f"Публікую подію: {event['title']} у канал.")
                await db.add_sent_event(db_session, event['url'])
                message_text = format_event_message(event, is_today=True)
                messages_to_send = split_text(message_text, max_length=4000)
                for part in messages_to_send:
                    try:
                        await context.bot.send_message(chat_id=config.XYA_CHANNEL_ID, text=part, parse_mode=ParseMode.MARKDOWN)
                    except Exception as e:
                        logging.error(f"Не вдалося опублікувати подію в канал {config.XYA_CHANNEL_ID}: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"Помилка в завданні send_events_today: {e}", exc_info=True)
async def send_events_tomorrow(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Відправляє в канал події на завтрашній день."""
    try:
        db_session = context.bot_data['db_session']
        aiohttp_session = context.bot_data['aiohttp_session']
        all_events = await get_all_events(aiohttp_session)
        tomorrow = (date.today() + timedelta(days=1)).strftime("%d.%m.%Y")
        tomorrow_events = [e for e in all_events if e.get('date') == tomorrow]
        if not tomorrow_events:
            logging.warning("Події на завтра не знайдені.")
            return
        for event in tomorrow_events:
            is_sent = await db.is_event_sent(db_session, event['url'])
            if not is_sent:
                logging.info(f"Публікую подію: {event['title']} у канал.")
                await db.add_sent_event(db_session, event['url'])
                message_text = format_event_message(event, is_today=False)
                messages_to_send = split_text(message_text, max_length=4000)
                for part in messages_to_send:
                    try:
                        await context.bot.send_message(chat_id=config.XYA_CHANNEL_ID, text=part, parse_mode=ParseMode.MARKDOWN)
                    except Exception as e:
                        logging.error(f"Не вдалося опублікувати подію в канал {config.XYA_CHANNEL_ID}: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"Помилка в завданні send_events_tomorrow: {e}", exc_info=True)
