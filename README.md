Проект: Telegram-бот для информирования сообщества
!
Краткое описание:
Этот Telegram-бот был создан для быстрого информирования жителей Белгорода-Днестровского. Он предоставляет актуальную информацию в реальном времени: уведомления о воздушных тревогах, местные новости, курс валют и удобный справочник. Проект изначально был "монолитным" и был полностью переработан для демонстрации принципов чистого кода, безопасности и модульной архитектуры.
🚀 Основные функции
Система оповещений: Мгновенные уведомления о начале и отбое воздушных тревог в указанном регионе.
Локальная информация: Публикация событий и новостей, собранных из местных источников, с функцией рассылки по расписанию.
Актуальный курс валют: Предоставление текущих курсов валют через API Monobank.
Интерактивный справочник: Структурированный каталог с полезными контактами (транспорт, услуги, досуг и т. д.).
Встроенный переводчик: Возможность переводить любой текст с помощью команды /translator или кнопки "🗣️ Перекладач". Эта функция использует несколько API для надежной работы.
Безопасность: Использование переменных окружения (.env) для защиты конфиденциальных данных.
Рефакторинг и модульность: Проект переработан из одного большого файла в набор логически организованных модулей.
Администрирование: Специальные команды для администраторов, позволяющие принудительно запускать фоновые задачи.
📚 Используемые технологии
Язык: Python
Библиотеки:
python-telegram-bot — для создания Telegram-бота
aiohttp — для асинхронных HTTP-запросов к API
aiosqlite — для асинхронной работы с базой данных SQLite
python-dotenv — для загрузки переменных окружения
alerts-in-ua — для получения данных о воздушных тревогах
deep-translator — для перевода текста
APScheduler — для планирования фоновых задач
💡 История проекта: от "монолита" до модульной архитектуры
Этот проект является наглядной демонстрацией эволюции кода. Изначально вся логика и все API-ключи были расположены в одном файле, что делало код сложным, небезопасным и трудным для поддержки.
❌ Было: "Монолитный" подход (файл test BOT.py)
Все функции и хэндлеры собраны в одном файле.
Секретные API-ключи жестко прописаны в коде.
<!-- end list -->



# ===== Налаштування =====
TELEGRAM_BOT_TOKEN="ваш токен бота"
ALERTS_API_TOKEN="ключ API alerts"
XYA_CHANNEL_ID="id вашого каналу"
WELCOME_PHOTO_ID="Ваше id фото бота"
DB_NAME="database.db"
TARGET_REGION="Одеська область" # ЗМІНА: додано новий параметр
ADMIN_IDS="ваш id"
...
def main():
    ...
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('currency', currency))
    ...
    application.add_handler(feedback_conv_handler)
    ...






✅ Стало: Модульная архитектура (текущая версия)
Вся логика была разделена на отдельные, независимые модули. Это делает код чистым, масштабируемым и понятным.
main.py: Точка входа, которая регистрирует хэндлеры из других файлов.
api.py: Содержит все функции для работы с внешними API (тревоги, валюты).
db.py: Управляет базой данных.
jobs.py: Содержит фоновые задачи (проверка тревог, рассылка новостей).
general_handlers.py: Содержит основные обработчики команд.
admin_handlers.py: Содержит команды для администраторов.
conversation_handlers.py: Управляет всеми диалогами (/feedback, /add_post, /translator).
<!-- end list -->




# main.py
...
# Імпортуємо ваші нові модулі
import config
import db
import jobs
from general_handlers import (
    start_command,
    help_command,
    ...
)
from conversation_handlers import (
    feedback_conversation_handler,
    add_post_conversation_handler,
    translator_conversation_handler, # <-- Теперь и переводчик!
    ...
)
...
def main() -> None:
    ...
    application.add_handler(translator_conversation_handler) # <-- И его хэндлер
    application.add_handler(feedback_conversation_handler)
    application.add_handler(add_post_conversation_handler)
    application.add_handler(CommandHandler("start", start_command))
    ...



⚙️ Установка и запуск

1.Клонируйте репозиторий:

git clone https://github.com/ваш_логин/название_проекта.git
cd название_проекта


2.Установите зависимости:

pip install -r requirements.txt


3.Настройте переменные окружения:
Создайте файл .env в корневой директории вашего проекта и добавьте в него свои ключи и ID:


TELEGRAM_BOT_TOKEN="ВАШ_ТОКЕН_БОТА"
ALERTS_API_TOKEN="ВАШ_ТОКЕН_API_ТРЕВОГ"
XYA_CHANNEL_ID="ВАШ_ID_КАНАЛА"
WELCOME_PHOTO_ID="ID_ФОТО_ПРИВЕТСТВИЯ"
DB_NAME="database.db"
TARGET_REGION="Одеська область"


4.Запустите бота:

python main.py


Запуск как сервис (опционально)
Чтобы бот работал круглосуточно и перезапускался автоматически в случае сбоев, вы можете запустить его как системный сервис systemd на сервере Linux (например, Ubuntu).

1.Создайте сервисный файл:
Сохраните следующий код в файле /etc/systemd/system/my_telegram_bot.service.

[Unit]
Description=My Telegram Bot
After=network.target

[Service]
User=sergiy # Укажите ваше имя пользователя
WorkingDirectory=/home/sergiy/telegram_bot_project # Укажите полный путь
ExecStart=/usr/bin/python3 /home/sergiy/telegram_bot_project/main.py # Укажите полный путь
Restart=on-failure
RestartSec=5s
Type=notify
WatchdogSec=30s
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target

2.Перезагрузите systemd и включите сервис:

sudo systemctl daemon-reload
sudo systemctl enable my_telegram_bot.service


3.Запустите сервис:

sudo systemctl start my_telegram_bot.service

(Вы можете проверить статус командой sudo systemctl status my_telegram_bot.service).

Автор
Сергей - https://github.com/SHVED-lab
