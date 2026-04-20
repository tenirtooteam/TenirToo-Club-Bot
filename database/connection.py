# Файл: database/connection.py
import sqlite3
import os
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "bot.db")


@contextmanager
def get_conn():
    """
    Контекстный менеджер соединения.
    Гарантирует закрытие соединения ВСЕГДА — даже при ошибке.
    Использование: with get_conn() as conn:
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Creates all tables if they do not exist using a transaction."""
    try:
        with get_conn() as conn:
            with conn:
                c = conn.cursor()
                # Существующие таблицы
                c.execute("CREATE TABLE IF NOT EXISTS groups (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)")
                c.execute("""CREATE TABLE IF NOT EXISTS group_topics (
                    group_id INTEGER,
                    topic_id INTEGER,
                    PRIMARY KEY (group_id, topic_id),
                    FOREIGN KEY (group_id) REFERENCES groups(id))""")
                c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT)")
                c.execute("""CREATE TABLE IF NOT EXISTS user_groups (
                    user_id INTEGER, group_id INTEGER,
                    PRIMARY KEY (user_id, group_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (group_id) REFERENCES groups(id))""")
                c.execute("CREATE TABLE IF NOT EXISTS topic_names (topic_id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_user_groups_user_id ON user_groups(user_id)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_group_topics_topic_id ON group_topics(topic_id)")

                # Новый прямой доступ
                c.execute("""CREATE TABLE IF NOT EXISTS direct_topic_access (
                    user_id INTEGER,
                    topic_id INTEGER,
                    PRIMARY KEY (user_id, topic_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )""")

                # Новые таблицы для ролей
                c.execute("""CREATE TABLE IF NOT EXISTS roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )""")
                c.execute("""CREATE TABLE IF NOT EXISTS user_roles (
                    user_id INTEGER,
                    role_id INTEGER,
                    topic_id INTEGER,
                    PRIMARY KEY (user_id, role_id, topic_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (role_id) REFERENCES roles(id)
                )""")

                # Предзаполнение ролей
                c.execute("INSERT OR IGNORE INTO roles (name) VALUES ('superadmin')")
                c.execute("INSERT OR IGNORE INTO roles (name) VALUES ('admin')")
                c.execute("INSERT OR IGNORE INTO roles (name) VALUES ('moderator')")

        logger.info("🗄 База данных успешно инициализирована с индексами и WAL")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при инициализации БД: {e}")
        raise