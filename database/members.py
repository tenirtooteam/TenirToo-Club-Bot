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
    try:
        with get_conn() as conn:
            with conn:
                c = conn.cursor()
                c.execute("DELETE FROM user_groups WHERE user_id = ?", (user_id,))
                c.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        logger.warning(f"🗑 Удален пользователь ID: {user_id} и все его доступы")
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
        c.execute("SELECT user_id, first_name, last_name FROM users ORDER BY last_name")
        return c.fetchall()


def get_user_name(user_id: int) -> str:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT first_name, last_name FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
    if row:
        return f"{row[0]} {row[1]}".strip()
    return "Неизвестный юзер"
