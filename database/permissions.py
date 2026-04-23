# Файл: database/permissions.py
import sqlite3
import logging
from .connection import get_conn

logger = logging.getLogger(__name__)

def grant_direct_access(user_id: int, topic_id: int) -> bool:
    try:
        with get_conn() as conn:
            with conn:
                conn.execute(
                    "INSERT INTO direct_topic_access (user_id, topic_id) VALUES (?, ?)",
                    (user_id, topic_id)
                )
        logger.info(f"🔐 Пользователю {user_id} выдан прямой доступ к топику {topic_id}")
        return True
    except sqlite3.IntegrityError:
        return False
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка выдачи прямого доступа: {e}")
        return False

def revoke_direct_access(user_id: int, topic_id: int):
    try:
        with get_conn() as conn:
            with conn:
                conn.execute(
                    "DELETE FROM direct_topic_access WHERE user_id = ? AND topic_id = ?",
                    (user_id, topic_id)
                )
        logger.info(f"🔓 У пользователя {user_id} отозван прямой доступ к топику {topic_id}")
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка при отзыве прямого доступа: {e}")

def get_direct_access_users(topic_id: int) -> list:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT u.user_id, u.first_name, u.last_name
            FROM users u
            JOIN direct_topic_access dta ON u.user_id = dta.user_id
            WHERE dta.topic_id = ?
        """, (topic_id,))
        return c.fetchall()

def has_direct_access(user_id: int, topic_id: int) -> bool:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM direct_topic_access WHERE user_id = ? AND topic_id = ? LIMIT 1", (user_id, topic_id))
        return c.fetchone() is not None

def can_write(user_id: int, topic_id: int) -> bool:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT 1 FROM user_groups ug
            JOIN group_topics gt ON ug.group_id = gt.group_id
            WHERE ug.user_id = ? AND gt.topic_id = ? 
            UNION
            SELECT 1 FROM direct_topic_access
            WHERE user_id = ? AND topic_id = ?
            LIMIT 1
        """, (user_id, topic_id, user_id, topic_id))
        return c.fetchone() is not None

def is_topic_restricted(topic_id: int) -> bool:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT 1 FROM group_topics WHERE topic_id = ?
            UNION
            SELECT 1 FROM direct_topic_access WHERE topic_id = ?
            LIMIT 1
        """, (topic_id, topic_id))
        return c.fetchone() is not None

def get_topic_authorized_users(topic_id: int) -> list:
    """
    Универсальная функция: возвращает (id, first_name, last_name) всех пользователей,
    имеющих доступ к топику (по глобальным группам или прямому доступу).
    Если топик публичный — возвращает всех юзеров системы.
    """
    with get_conn() as conn:
        c = conn.cursor()

        # Проверяем, ограничен ли топик
        c.execute("""
            SELECT 1 FROM group_topics WHERE topic_id = ?
            UNION
            SELECT 1 FROM direct_topic_access WHERE topic_id = ?
            LIMIT 1
        """, (topic_id, topic_id))
        is_restricted = c.fetchone() is not None

        if is_restricted:
            # Выборка через пересечение групп и прямой доступ
            c.execute("""
                SELECT u.user_id, u.first_name, u.last_name
                FROM users u
                WHERE u.user_id IN (
                    SELECT ug.user_id 
                    FROM user_groups ug
                    JOIN group_topics gt ON ug.group_id = gt.group_id
                    WHERE gt.topic_id = ?
                    UNION
                    SELECT dta.user_id 
                    FROM direct_topic_access dta
                    WHERE dta.topic_id = ?
                )
                ORDER BY u.last_name, u.first_name
            """, (topic_id, topic_id))
        else:
            # Для публичного топика возвращаем всех
            c.execute("SELECT user_id, first_name, last_name FROM users ORDER BY last_name")

        return c.fetchall()
