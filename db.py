import aiosqlite
import datetime
import logging
import json
from typing import AsyncGenerator, Dict, List, Optional, Union, Any

async def init_db(db_session: aiosqlite.Connection) -> None:
    """Ініціалізує всі таблиці в базі даних."""
    await db_session.execute('''
        CREATE TABLE IF NOT EXISTS alarms (
            id INTEGER PRIMARY KEY, start_time TEXT NOT NULL, end_time TEXT, duration_minutes REAL, region TEXT
        )
    ''')
    await db_session.execute('''
        CREATE TABLE IF NOT EXISTS sent_events (
            url TEXT PRIMARY KEY
        )
    ''')
    await db_session.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_id INTEGER,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            contact_info TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    # === ЗМІНА: Додано створення таблиці для зберігання стану тривог ===
    await db_session.execute('''
        CREATE TABLE IF NOT EXISTS alerts_state (
            id INTEGER PRIMARY KEY,
            regions TEXT NOT NULL
        )
    ''')
    # =================================================================
    await db_session.commit()
    logging.info("Таблиці БД успішно ініціалізовано.")

# === НОВА ФУНКЦІЯ: Очищення таблиці alerts_state ===
async def clear_alerts_state(db_session: aiosqlite.Connection) -> None:
    """Очищує таблицю alerts_state. Використовується при запуску бота, щоб уникнути помилкових сповіщень."""
    await db_session.execute("DELETE FROM alerts_state")
    await db_session.commit()
    logging.info("Таблицю alerts_state успішно очищено.")
# =================================================================

async def record_start_time(db_session: aiosqlite.Connection, region: str) -> None:
    """Записує час початку повітряної тривоги для регіону."""
    now = datetime.datetime.now().isoformat()
    await db_session.execute("INSERT INTO alarms (region, start_time) VALUES (?, ?)", (region, now))
    await db_session.commit()

async def record_end_time(db_session: aiosqlite.Connection, region: str) -> None:
    """Оновлює запис, додаючи час відбою тривоги та розраховуючи тривалість."""
    now = datetime.datetime.now()
    cursor = await db_session.execute("SELECT start_time FROM alarms WHERE region = ? AND end_time IS NULL ORDER BY start_time DESC LIMIT 1", (region,))
    result = await cursor.fetchone()
    if result:
        start_time_str = result[0]
        start_time = datetime.datetime.fromisoformat(start_time_str)
        duration = (now - start_time).total_seconds() / 60
        await db_session.execute(
            "UPDATE alarms SET end_time = ?, duration_minutes = ? WHERE region = ? AND end_time IS NULL",
            (now.isoformat(), duration, region)
        )
        await db_session.commit()

async def add_sent_event(db_session: aiosqlite.Connection, url: str) -> None:
    """Додає URL події в базу даних, щоб уникнути повторної відправки."""
    await db_session.execute("INSERT OR IGNORE INTO sent_events (url) VALUES (?)", (url,))
    await db_session.commit()

async def is_event_sent(db_session: aiosqlite.Connection, url: str) -> bool:
    """Перевіряє, чи була подія вже відправлена."""
    cursor = await db_session.execute("SELECT 1 FROM sent_events WHERE url = ?", (url,))
    result = await cursor.fetchone()
    return result is not None

async def save_post(db_session: aiosqlite.Connection, author_id: int, title: str, content: str, contact_info: str) -> None:
    """Зберігає нове оголошення в базі даних."""
    now = datetime.datetime.now().isoformat()
    await db_session.execute(
        "INSERT INTO posts (author_id, title, content, contact_info, created_at) VALUES (?, ?, ?, ?, ?)",
        (author_id, title, content, contact_info, now)
    )
    await db_session.commit()

async def get_posts(db_session: aiosqlite.Connection) -> List[Dict[str, Any]]:
    """Отримує останні оголошення з бази даних."""
    db_session.row_factory = aiosqlite.Row
    cursor = await db_session.execute("SELECT * FROM posts ORDER BY created_at DESC LIMIT 10")
    posts = await cursor.fetchall()
    return [dict(post) for post in posts]

async def get_post_by_id(db_session: aiosqlite.Connection, post_id: int) -> Optional[Dict[str, Any]]:
    """Отримує оголошення за його ID."""
    db_session.row_factory = aiosqlite.Row
    cursor = await db_session.execute("SELECT * FROM posts WHERE id =?", (post_id,))
    post = await cursor.fetchone()
    return dict(post) if post else None

async def delete_post(db_session: aiosqlite.Connection, post_id: int) -> None:
    """Видаляє оголошення з бази даних за його ID."""
    await db_session.execute("DELETE FROM posts WHERE id =?", (post_id,))
    await db_session.commit()

async def get_last_alerts_state(db_session: aiosqlite.Connection) -> List[str]:
    """Отримує останній стан повітряних тривог із бази даних."""
    db_session.row_factory = aiosqlite.Row
    cursor = await db_session.execute("SELECT regions FROM alerts_state ORDER BY id DESC LIMIT 1")
    result = await cursor.fetchone()
    if result and result['regions']:
        return json.loads(result['regions'])
    return []

async def save_alerts_state(db_session: aiosqlite.Connection, regions: List[str]) -> None:
    """Зберігає поточний стан повітряних тривог у базу даних."""
    # Очищуємо таблицю, щоб вона містила лише останній запис
    await db_session.execute("DELETE FROM alerts_state")
    await db_session.execute(
        "INSERT INTO alerts_state (regions) VALUES (?)",
        (json.dumps(regions),)
    )
    await db_session.commit()
