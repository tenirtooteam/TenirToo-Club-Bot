# Файл: database/groups.py
import sqlite3
import logging
from .connection import get_conn

logger = logging.getLogger(__name__)

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
        c.execute("SELECT id, name FROM groups")
        groups = c.fetchall()
        groups.sort(key=lambda x: x[1].lower() if x[1] else "")
        return groups

def get_group_name(group_id: int) -> str:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM groups WHERE id = ?", (group_id,))
        row = c.fetchone()
    return row[0] if row else "Неизвестная группа"

def delete_group(group_id: int):
    """Удаляет группу. Каскадное удаление (топики, юзеры) выполняется на уровне БД."""
    try:
        with get_conn() as conn:
            with conn:
                conn.execute("DELETE FROM groups WHERE id = ?", (group_id,))
        logger.warning(f"🗑 Удалена группа ID: {group_id}. Все связи очищены БД каскадно.")
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка при удалении группы {group_id}: {e}")

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

def get_groups_by_topic(topic_id: int) -> list:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT g.name FROM groups g
            JOIN group_topics gt ON g.id = gt.group_id
            WHERE gt.topic_id = ?
        """, (topic_id,))
        return [row[0] for row in c.fetchall()]

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
    """Возвращает список ID топиков, к которым у пользователя есть доступ (группы + прямой доступ)."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT DISTINCT gt.topic_id
            FROM user_groups ug
            JOIN group_topics gt ON ug.group_id = gt.group_id
            WHERE ug.user_id = ?
            UNION
            SELECT topic_id FROM direct_topic_access WHERE user_id = ?
        """, (user_id, user_id))
        return [row[0] for row in c.fetchall()]


def find_groups_by_query(query: str) -> list:
    """Поиск групп по вхождению строки в название (регистронезависимо)."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, name FROM groups")
        rows = c.fetchall()
        query = query.lower()
        # Возвращаем список (id, name)
        return [(r[0], r[1]) for r in rows if query in r[1].lower()]
