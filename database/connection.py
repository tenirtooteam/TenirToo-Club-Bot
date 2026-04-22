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
    Гарантирует закрытие соединения и ВКЛЮЧАЕТ поддержку Foreign Keys.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    # Включаем WAL для производительности и FK для целостности данных
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Создает таблицы и проверяет поддержку Foreign Keys."""
    try:
        with get_conn() as conn:
            # Строгая проверка поддержки FK
            fk_check = conn.execute("PRAGMA foreign_keys;").fetchone()
            if not fk_check or fk_check[0] != 1:
                error_msg = "❌ КРИТИЧЕСКАЯ ОШИБКА: SQLite не поддерживает Foreign Keys или PRAGMA не сработала. Запуск невозможен."
                logger.critical(error_msg)
                raise RuntimeError(error_msg)

            with conn:
                c = conn.cursor()
                
                # Таблица групп
                c.execute("CREATE TABLE IF NOT EXISTS groups (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)")
                
                # Таблица связи топиков с группами
                c.execute("""CREATE TABLE IF NOT EXISTS group_topics (
                    group_id INTEGER,
                    topic_id INTEGER,
                    PRIMARY KEY (group_id, topic_id),
                    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE)""")
                
                # Таблица пользователей
                c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT)")
                
                # Таблица связи пользователей с группами
                c.execute("""CREATE TABLE IF NOT EXISTS user_groups (
                    user_id INTEGER, group_id INTEGER,
                    PRIMARY KEY (user_id, group_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE)""")
                
                # Таблица имен топиков
                c.execute("CREATE TABLE IF NOT EXISTS topic_names (topic_id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
                
                # Прямой доступ к топикам
                c.execute("""CREATE TABLE IF NOT EXISTS direct_topic_access (
                    user_id INTEGER,
                    topic_id INTEGER,
                    PRIMARY KEY (user_id, topic_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (topic_id) REFERENCES topic_names(topic_id) ON DELETE CASCADE
                )""")

                # Таблица ролей
                c.execute("""CREATE TABLE IF NOT EXISTS roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )""")
                
                # Связь пользователей с ролями (и топиками для модераторов)
                c.execute("""CREATE TABLE IF NOT EXISTS user_roles (
                    user_id INTEGER,
                    role_id INTEGER,
                    topic_id INTEGER,
                    PRIMARY KEY (user_id, role_id, topic_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
                    FOREIGN KEY (topic_id) REFERENCES topic_names(topic_id) ON DELETE CASCADE
                )""")

                # Индексы
                c.execute("CREATE INDEX IF NOT EXISTS idx_user_groups_user_id ON user_groups(user_id)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_group_topics_topic_id ON group_topics(topic_id)")

                # Предзаполнение ролей
                c.execute("INSERT OR IGNORE INTO roles (name) VALUES ('superadmin')")
                c.execute("INSERT OR IGNORE INTO roles (name) VALUES ('admin')")
                c.execute("INSERT OR IGNORE INTO roles (name) VALUES ('moderator')")

        logger.info("🗄 БД инициализирована. Поддержка Native FK (Cascade) включена.")
    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации БД: {e}")
        raise