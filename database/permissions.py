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

def grant_direct_access_bulk(user_ids: list, topic_id: int) -> bool:
    """Массовая выдача прямого доступа к топику."""
    if not user_ids:
        return True
    try:
        with get_conn() as conn:
            with conn:
                conn.executemany(
                    "INSERT OR IGNORE INTO direct_topic_access (user_id, topic_id) VALUES (?, ?)",
                    [(uid, topic_id) for uid in user_ids]
                )
        logger.info(f"🔐 Выдан массовый доступ к топику {topic_id} для {len(user_ids)} пользователей.")
        return True
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка массовой выдачи прямого доступа: {e}")
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

def revoke_all_direct_access(topic_id: int):
    """Удаляет всех пользователей из прямого доступа к топику."""
    try:
        with get_conn() as conn:
            with conn:
                conn.execute("DELETE FROM direct_topic_access WHERE topic_id = ?", (topic_id,))
        logger.warning(f"🚫 Очищен весь прямой доступ к топику {topic_id}")
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка при полной очистке доступа: {e}")

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
            SELECT 1 FROM direct_topic_access
            WHERE user_id = ? AND topic_id = ?
            LIMIT 1
        """, (user_id, topic_id))
        return c.fetchone() is not None

def is_topic_restricted(topic_id: int) -> bool:
    """
    Проверяет, есть ли для топика настройки доступа.
    Если записей нет — топик считается 'не настроенным' (Default Deny).
    """
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT 1 FROM direct_topic_access WHERE topic_id = ?
            LIMIT 1
        """, (topic_id,))
        return c.fetchone() is not None

def get_topic_authorized_users(topic_id: int) -> list:
    """
    Универсальная функция: возвращает (id, first_name, last_name) всех пользователей,
    имеющих доступ к топику (ТОЛЬКО через прямой доступ).
    Если топик публичный — возвращает всех юзеров системы.
    """
    with get_conn() as conn:
        c = conn.cursor()

        # Проверяем, ограничен ли топик
        c.execute("SELECT 1 FROM direct_topic_access WHERE topic_id = ? LIMIT 1", (topic_id,))
        is_restricted = c.fetchone() is not None

        if is_restricted:
            # Выборка ТОЛЬКО через прямой доступ
            c.execute("""
                SELECT u.user_id, u.first_name, u.last_name
                FROM users u
                JOIN direct_topic_access dta ON u.user_id = dta.user_id
                WHERE dta.topic_id = ?
                ORDER BY u.last_name, u.first_name
            """, (topic_id,))
        else:
            # Для публичного топика возвращаем всех
            c.execute("SELECT user_id, first_name, last_name FROM users ORDER BY last_name")

        return c.fetchall()

def get_user_available_topics(user_id: int) -> list:
    """Возвращает список (id, name) топиков, к которым у пользователя есть прямой доступ."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT tn.topic_id, tn.name FROM direct_topic_access dta
            JOIN topic_names tn ON dta.topic_id = tn.topic_id
            WHERE dta.user_id = ?
        """, (user_id,))
        return c.fetchall()

def get_direct_access_user_ids(topic_id: int) -> list:
    """Возвращает только список ID пользователей с прямым доступом к топику."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM direct_topic_access WHERE topic_id = ?", (topic_id,))
        return [row[0] for row in c.fetchall()]

def get_topic_authorized_user_ids(topic_id: int) -> list:
    """Возвращает только список ID пользователей, имеющих доступ к топику."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM direct_topic_access WHERE topic_id = ? LIMIT 1", (topic_id,))
        is_restricted = c.fetchone() is not None

        if is_restricted:
            c.execute("SELECT user_id FROM direct_topic_access WHERE topic_id = ?", (topic_id,))
            return [row[0] for row in c.fetchall()]
        else:
            c.execute("SELECT user_id FROM users")
            return [row[0] for row in c.fetchall()]
