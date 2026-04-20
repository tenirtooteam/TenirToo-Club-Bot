# Файл: database/roles.py
import sqlite3
import logging
from .connection import get_conn

logger = logging.getLogger(__name__)

def add_role(name: str) -> int:
    try:
        with get_conn() as conn:
            with conn:
                c = conn.cursor()
                c.execute("INSERT INTO roles (name) VALUES (?)", (name,))
                return c.lastrowid
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка при добавлении роли: {e}")
        return 0

def get_role_id(name: str) -> int:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM roles WHERE name = ?", (name,))
        row = c.fetchone()
        return row[0] if row else 0

def grant_role(user_id: int, role_id: int, topic_id: int = None) -> bool:
    try:
        with get_conn() as conn:
            with conn:
                conn.execute(
                    "INSERT INTO user_roles (user_id, role_id, topic_id) VALUES (?, ?, ?)",
                    (user_id, role_id, topic_id)
                )
        logger.info(f"🔐 Пользователю {user_id} выдана роль {role_id} (topic_id={topic_id})")
        return True
    except sqlite3.IntegrityError:
        return False
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка при выдаче роли: {e}")
        return False

def revoke_role(user_id: int, role_id: int, topic_id: int = None) -> bool:
    try:
        with get_conn() as conn:
            with conn:
                c = conn.cursor()
                c.execute(
                    "DELETE FROM user_roles WHERE user_id = ? AND role_id = ? AND (topic_id IS ? OR topic_id = ?)",
                    (user_id, role_id, topic_id, topic_id)
                )
                return c.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка при отзыве роли: {e}")
        return False

def get_user_roles(user_id: int) -> list:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT r.name, ur.topic_id
            FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE ur.user_id = ?
        """, (user_id,))
        return c.fetchall()

def get_moderators_of_topic(topic_id: int) -> list:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT u.user_id, u.first_name, u.last_name
            FROM user_roles ur
            JOIN users u ON ur.user_id = u.user_id
            JOIN roles r ON ur.role_id = r.id
            WHERE r.name = 'moderator' AND ur.topic_id = ?
            ORDER BY u.last_name, u.first_name
        """, (topic_id,))
        return c.fetchall()

def is_global_admin(user_id: int) -> bool:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT 1 FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE ur.user_id = ? AND r.name IN ('superadmin', 'admin') AND ur.topic_id IS NULL
            LIMIT 1
        """, (user_id,))
        return c.fetchone() is not None

def is_moderator_of_topic(user_id: int, topic_id: int) -> bool:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT 1 FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE ur.user_id = ? AND r.name = 'moderator' AND ur.topic_id = ?
            LIMIT 1
        """, (user_id, topic_id))
        return c.fetchone() is not None

def get_all_roles() -> list:
    """Возвращает список всех ролей: (id, name)."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, name FROM roles ORDER BY id")
        return c.fetchall()
