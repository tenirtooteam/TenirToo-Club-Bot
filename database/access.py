# Файл: database/access.py
import sqlite3
import logging
from .connection import get_conn

logger = logging.getLogger(__name__)


# --- ГРУППЫ ---

def create_group(name: str) -> int:
    try:
        with get_conn() as conn:
            with conn:
                c = conn.cursor()
                c.execute("INSERT INTO groups (name) VALUES (?)", (name,))
                group_id = c.lastrowid
        logger.info(f"🆕 Создана новая группа: {name} (ID: {group_id})")
        return group_id
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка при создании группы: {e}")
        return 0


def get_all_groups() -> list:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, name FROM groups ORDER BY id")
        return c.fetchall()


def get_group_name(group_id: int) -> str:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM groups WHERE id = ?", (group_id,))
        row = c.fetchone()
    return row[0] if row else "Неизвестная группа"


def delete_group(group_id: int):
    try:
        with get_conn() as conn:
            with conn:
                c = conn.cursor()
                c.execute("DELETE FROM group_topics WHERE group_id = ?", (group_id,))
                c.execute("DELETE FROM user_groups WHERE group_id = ?", (group_id,))
                c.execute("DELETE FROM groups WHERE id = ?", (group_id,))
        logger.warning(f"🗑 Удалена группа ID: {group_id} и все её связи")
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка при удалении группы {group_id}: {e}")


# --- ТОПИКИ ---

def get_all_unique_topics() -> list:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT topic_id FROM topic_names ORDER BY topic_id ASC")
        return [row[0] for row in c.fetchall()]


def get_topics_of_group(group_id: int) -> list:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT topic_id FROM group_topics WHERE group_id = ?", (group_id,))
        return [row[0] for row in c.fetchall()]


def add_topic_to_group(group_id: int, topic_id: int) -> bool:
    try:
        with get_conn() as conn:
            with conn:
                conn.execute(
                    "INSERT INTO group_topics (group_id, topic_id) VALUES (?, ?)",
                    (group_id, topic_id)
                )
        logger.info(f"🔗 Топик {topic_id} привязан к группе {group_id}")
        return True
    except sqlite3.IntegrityError:
        return False
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка при добавлении топика в группу: {e}")
        return False


def remove_topic_from_group(group_id: int, topic_id: int):
    try:
        with get_conn() as conn:
            with conn:
                conn.execute(
                    "DELETE FROM group_topics WHERE group_id = ? AND topic_id = ?",
                    (group_id, topic_id)
                )
        logger.info(f"✂️ Топик {topic_id} отвязан от группы {group_id}")
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка при отвязке топика: {e}")


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


def get_groups_by_topic(topic_id: int) -> list:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT g.name FROM groups g
            JOIN group_topics gt ON g.id = gt.group_id
            WHERE gt.topic_id = ?
        """, (topic_id,))
        return [row[0] for row in c.fetchall()]


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


# --- ПРАВА (СВЯЗИ) ---

def get_user_groups(user_id: int) -> list:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT g.id, g.name FROM user_groups ug
            JOIN groups g ON ug.group_id = g.id
            WHERE ug.user_id = ?
        """, (user_id,))
        return c.fetchall()


def grant_group(user_id: int, group_id: int) -> bool:
    try:
        with get_conn() as conn:
            with conn:
                conn.execute(
                    "INSERT INTO user_groups (user_id, group_id) VALUES (?, ?)",
                    (user_id, group_id)
                )
        logger.info(f"🔐 Пользователю {user_id} выдана группа {group_id}")
        return True
    except sqlite3.IntegrityError:
        return False
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка при выдаче группы: {e}")
        return False


def revoke_group(user_id: int, group_id: int):
    try:
        with get_conn() as conn:
            with conn:
                conn.execute(
                    "DELETE FROM user_groups WHERE user_id = ? AND group_id = ?",
                    (user_id, group_id)
                )
        logger.info(f"🔓 У пользователя {user_id} отозвана группа {group_id}")
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка при отзыве группы: {e}")


def get_user_available_topics(user_id: int) -> list:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT DISTINCT gt.topic_id
            FROM user_groups ug
            JOIN group_topics gt ON ug.group_id = gt.group_id
            WHERE ug.user_id = ?
        """, (user_id,))
        return [row[0] for row in c.fetchall()]


# --- МОДЕРАЦИЯ ---

def can_write(user_id: int, topic_id: int) -> bool:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT 1 FROM user_groups ug
            JOIN group_topics gt ON ug.group_id = gt.group_id
            WHERE ug.user_id = ? AND gt.topic_id = ? LIMIT 1
        """, (user_id, topic_id))
        return c.fetchone() is not None


def is_topic_restricted(topic_id: int) -> bool:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM group_topics WHERE topic_id = ? LIMIT 1", (topic_id,))
        return c.fetchone() is not None