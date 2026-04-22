# Файл: database/topics.py
import sqlite3
import logging
from .connection import get_conn

logger = logging.getLogger(__name__)

def get_all_unique_topics() -> list:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT topic_id, name FROM topic_names")
        topics = c.fetchall()
        topics.sort(key=lambda x: x[1].lower() if x[1] else "")
        return [row[0] for row in topics]

def update_topic_name(topic_id: int, name: str):
    try:
        with get_conn() as conn:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO topic_names (topic_id, name) VALUES (?, ?)",
                    (topic_id, name)
                )
        logger.info(f"📝 Имя топика {topic_id} обновлено: {name}")
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка при обновлении имени топика: {e}")

def get_topic_name(topic_id: int) -> str:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM topic_names WHERE topic_id = ?", (topic_id,))
        row = c.fetchone()
    return row[0] if row else f"Топик {topic_id}"

def delete_topic(topic_id: int):
    """Удаляет топик. Каскадное удаление (роли, доступы) выполняется на уровне БД."""
    try:
        with get_conn() as conn:
            with conn:
                conn.execute("DELETE FROM topic_names WHERE topic_id = ?", (topic_id,))
        logger.warning(f"🗑 Топик ID: {topic_id} и все его связи полностью удалены БД каскадно.")
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка при удалении топика {topic_id}: {e}")

def register_topic_if_not_exists(topic_id: int):
    try:
        with get_conn() as conn:
            with conn:
                c = conn.cursor()
                c.execute("SELECT 1 FROM topic_names WHERE topic_id = ?", (topic_id,))
                if not c.fetchone():
                    name = "General" if topic_id == -1 else f"Топик {topic_id}"
                    c.execute(
                        "INSERT INTO topic_names (topic_id, name) VALUES (?, ?)",
                        (topic_id, name)
                    )
                    logger.info(f"🔍 Зарегистрирован новый топик ID: {topic_id}")
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка при авторегистрации топика: {e}")
