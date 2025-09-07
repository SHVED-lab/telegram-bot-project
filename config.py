import os
from dotenv import load_dotenv
import datetime
# Завантажуємо змінні оточення з файлу .env
load_dotenv()
# ===== Змінні оточення та API-ключі =====
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ALERTS_API_TOKEN = os.getenv('ALERTS_API_TOKEN')
TARGET_REGION = os.getenv('TARGET_REGION')
DB_NAME = os.getenv('DB_NAME')
XYA_CHANNEL_ID = os.getenv('XYA_CHANNEL_ID')
WELCOME_PHOTO_ID = os.getenv('WELCOME_PHOTO_ID')
# =========================================
# Перевірка наявності необхідних ключів
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не був знайдений в змінних оточення. Перевірте файл .env")
if not ALERTS_API_TOKEN:
    print("WARNING: ALERTS_API_TOKEN не знайдено. Функціонал тривог буде вимкнено.")
# URL для отримання курсів валют
CURRENCY_API_URL = "https://api.monobank.ua/bank/currency"
# Джерела подій для парсингу (залишені лише ті, що працюють)
EVENTS_SOURCES = {
    "internet-bilet.ua": "https://www.internet-bilet.ua/events",
    "karabas.com": "https://karabas.com/events/",
    "kino-teatr.ua": "https://kino-teatr.ua/movies/cinema"
}
# Стан діалогів
FEEDBACK = 0
POST_TITLE, POST_CONTENT, POST_CONTACT, POST_CONFIRM = range(4)
# Стан діалогу для перекладача
TRANSLATOR = 4
# Ідентифікатори стікерів
STICKER_ALERT_ID = "CAACAgIAAxkBAAERtj9orLytPDjfsqmwzT1EW9KJ5wIK8gACfIYAAldXaElGJIq9peSKpjYE"
STICKER_ALL_CLEAR_ID = "CAACAgIAAxkBAAERtjJorLtblGjBbtREQeYP31RfgVoDQwACSIkAAsSAYUnxGAxeP4qvPjYE"

EVENTS_CHECK_TIME = datetime.time(hour=21, minute=0)
