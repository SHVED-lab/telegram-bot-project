import os
import logging
import asyncio
import aiohttp
import aiosqlite
import telegram
import portalocker
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram import BotCommand, ReplyKeyboardMarkup, Update
from dotenv import load_dotenv
import datetime
# Імпортуємо ваші нові модулі
import config
import db
import jobs
from general_handlers import (
    start_command,
    help_command,
    status_command,
    currency_command,
    announcements_command,
    text_handler,
)
from directory_handlers import (
    directory_menu,
    directory_show_items,
    directory_show_item_details,
    main_menu_from_callback,
)
from conversation_handlers import (
    feedback_conversation_handler,
    add_post_conversation_handler,
    translator_conversation_handler,
)
from admin_handlers import (
    force_check_alerts,
    force_send_events_today,
    force_send_events_tomorrow,
)
from general_handlers import delete_post_callback
# Налаштування логування
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# === НОВА ФУНКЦІЯ: для ініціалізації сесій та ресурсів асинхронно ===
async def post_init_setup(application: Application) -> None:
    """Ініціалізує асинхронні сесії для бази даних та HTTP-запитів."""
    application.bot_data['aiohttp_session'] = aiohttp.ClientSession()
    db_session = await aiosqlite.connect(config.DB_NAME)
    application.bot_data['db_session'] = db_session
    application.bot_data['target_region'] = config.TARGET_REGION
    logger.info("Асинхронні сесії успішно ініціалізовані.")
    
    # === НОВИЙ КОД: Очищення стану тривог при запуску ===
    await db.clear_alerts_state(db_session)
    
    # === НОВИЙ КОД: ВСТАНОВЛЕННЯ КОМАНД МЕНЮ ДЛЯ БОТА ===
    bot_commands = [
        BotCommand("start", "Почати роботу з ботом"),
        BotCommand("help", "Показати список команд"),
        BotCommand("status", "Дізнатися про статус бота"),
        BotCommand("currency", "Показати курс валют"),
        BotCommand("announcements", "Переглянути оголошення"),
        BotCommand("add_post", "Додати оголошення"),
        BotCommand("feedback", "Залишити зворотний зв'язок"),
        BotCommand("directory", "Довідник"),
        BotCommand("force_check_alerts", "Примусова перевірка тривог (для адміна)"),
        BotCommand("force_send_events_today", "Примусове відправлення подій на сьогодні (для адміна)"),
        BotCommand("force_send_events_tomorrow", "Примусове відправлення подій на завтра (для адміна)")
    ]
    await application.bot.set_my_commands(bot_commands)
    logger.info("Команди меню бота успішно встановлені.")

# === НОВА ФУНКЦІЯ: для завершення роботи асинхронних сесій ===
async def shutdown(application: Application) -> None:
    """Закриває асинхронні сесії для бази даних та HTTP-запитів."""
    await application.bot_data['aiohttp_session'].close()
    await application.bot_data['db_session'].close()
    logger.info("Асинхронні сесії успішно закриті.")

def main() -> None:
    """Запускає бота."""
    load_dotenv()
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).post_init(post_init_setup).post_shutdown(shutdown).build()
    # Реєстрація діалогів першими
    application.add_handler(feedback_conversation_handler)
    application.add_handler(add_post_conversation_handler)
    application.add_handler(translator_conversation_handler)
    # Реєстрація інших обробників
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("currency", currency_command))
    application.add_handler(CommandHandler("announcements", announcements_command))
    application.add_handler(CommandHandler("directory", directory_menu))
    application.add_handler(CommandHandler("force_check_alerts", force_check_alerts))
    application.add_handler(CommandHandler("force_send_events_today", force_send_events_today))
    application.add_handler(CommandHandler("force_send_events_tomorrow", force_send_events_tomorrow))
    application.add_handler(CallbackQueryHandler(delete_post_callback, pattern=r'^delete_post_'))
    application.add_handler(CallbackQueryHandler(directory_show_items, pattern=r'^dir_cat:'))
    application.add_handler(CallbackQueryHandler(directory_show_item_details, pattern=r'^dir_item:'))
    application.add_handler(CallbackQueryHandler(main_menu_from_callback, pattern=r'^main_menu'))
    application.add_handler(CallbackQueryHandler(directory_menu, pattern=r'^dir_menu'))
    # Обробник текстових повідомлень, який повинен бути в кінці
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    # Реєстрація фонових завдань
    job_queue = application.job_queue
    job_queue.run_repeating(jobs.check_for_alerts, interval=60, first=5)  # Перевіряти кожну хвилину
    job_queue.run_daily(jobs.send_events_today, time=config.EVENTS_CHECK_TIME, days=(0, 1, 2, 3, 4, 5, 6))
    job_queue.run_daily(jobs.send_events_tomorrow, time=config.EVENTS_CHECK_TIME, days=(0, 1, 2, 3, 4, 5, 6))
    logger.info("Бот запущений. Відстежуємо регіон: %s", config.TARGET_REGION)
    # Запускаємо бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
