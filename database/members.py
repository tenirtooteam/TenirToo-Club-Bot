# Файл: database/members.py
import sqlite3
import logging
from .connection import get_conn

logger = logging.getLogger(__name__)


def user_exists(user_id: int) -> bool:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        return c.fetchone() is not None


def add_user(user_id: int, first_name: str, last_name: str) -> bool:
    try:
        with get_conn() as conn:
            with conn:
                conn.execute(
                    "INSERT INTO users (user_id, first_name, last_name) VALUES (?, ?, ?)",
                    (user_id, first_name, last_name)
                )
        logger.info(f"👤 Добавлен пользователь: {first_name} {last_name} (ID: {user_id})")
        return True
    except sqlite3.IntegrityError:
        return False
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка при добавлении пользователя: {e}")
        return False


def delete_user(user_id: int):
    """Удаляет пользователя. Каскадное удаление (роли, группы) выполняется на уровне БД."""
    try:
        with get_conn() as conn:
            with conn:
                conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        logger.warning(f"🗑 Удален пользователь ID: {user_id}. Все связанные данные удалены БД каскадно.")
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка при удалении пользователя {user_id}: {e}")


def update_user_name(user_id: int, first_name: str, last_name: str):
    try:
        with get_conn() as conn:
            with conn:
                conn.execute(
                    "UPDATE users SET first_name = ?, last_name = ? WHERE user_id = ?",
                    (first_name, last_name, user_id)
                )
        logger.info(f"🔄 Данные пользователя {user_id} обновлены: {first_name} {last_name}")
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка при обновлении данных пользователя: {e}")


def get_all_users() -> list:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, first_name, last_name FROM users")
        users = c.fetchall()
        users.sort(key=lambda x: (
            x[1].lower() if x[1] else "",
            x[2].lower() if x[2] else ""
        ))
        return users


def get_user_name(user_id: int) -> str:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT first_name, last_name FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
    if row:
        return f"{row[0]} {row[1]}".strip()
    return "Неизвестный юзер"


def find_users_by_query(query: str) -> list:
    parts = [p.lower().strip() for p in query.split() if p.strip()]
    if not parts:
        return []
    
    # SQLite's LOWER() only works for ASCII, failing on Cyrillic. 
    # Fetch all users and filter in Python.
    all_users = get_all_users()
    matched = []

    if len(parts) == 1:
        w = parts[0]
        for user_id, fname, lname in all_users:
            f = fname.lower() if fname else ""
            l = lname.lower() if lname else ""
            if f == w or l == w:
                matched.append((user_id, fname, lname))
    else:
        w1, w2 = parts[0], parts[1]
        for user_id, fname, lname in all_users:
            f = fname.lower() if fname else ""
            l = lname.lower() if lname else ""
            if (f == w1 and l == w2) or (f == w2 and l == w1):
                matched.append((user_id, fname, lname))
                
    return matched
