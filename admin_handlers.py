import logging
from telegram import Update
from telegram.ext import ContextTypes
import db
import config
from utils import send_alert_message
from jobs import check_for_alerts, send_events_today, send_events_tomorrow
async def force_check_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник команди /force_check_alerts, перевіряє тривоги негайно."""
    if not update.effective_user or update.effective_user.id not in config.ADMIN_IDS:
        return
    logging.info("Отримана команда /force_check_alerts. Запускаю негайну перевірку...")
    await update.message.reply_text("Запускаю негайну перевірку повітряних тривог...")
    await check_for_alerts(context)
async def force_send_events_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник команди /force_send_events_today, надсилає події на сьогодні."""
    if not update.effective_user or update.effective_user.id not in config.ADMIN_IDS:
        return
    logging.info("Отримана команда /force_send_events_today. Запускаю надсилання подій на сьогодні...")
    await update.message.reply_text("Запускаю надсилання подій на сьогодні...")
    await send_events_today(context)
async def force_send_events_tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник команди /force_send_events_tomorrow, надсилає події на завтра."""
    if not update.effective_user or update.effective_user.id not in config.ADMIN_IDS:
        return
    logging.info("Отримана команда /force_send_events_tomorrow. Запускаю надсилання подій на завтра...")
    await update.message.reply_text("Запускаю надсилання подій на завтра...")
    await send_events_tomorrow(context)
