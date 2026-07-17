# Файл: database/connection.py
import sqlite3
import os
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Путь к БД можно переопределить через переменную окружения для тестов
DB_PATH = os.environ.get("BOT_DB_PATH", os.path.join(os.path.dirname(__file__), "bot.db"))

# [Feature 008 / US1] Единое переиспользуемое соединение на процесс.
# Под однопоточным циклом asyncio синхронные операции db.* не переплетаются в
# середине транзакции (внутри `with get_conn()` нет await), поэтому одно общее
# соединение потокобезопасно и не требует пула/блокировки. Это убирает churn
# ~6 connect+PRAGMA-циклов на сообщение до ≤1 (SC-001, FR-001).
_shared_conn = None


def _new_connection():
    """Создаёт соединение с однократным применением WAL + Foreign Keys (FR-002)."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _get_shared_conn():
    """Лениво создаёт и возвращает общее соединение (FR-001, FR-007)."""
    global _shared_conn
    if _shared_conn is None:
        _shared_conn = _new_connection()
    return _shared_conn


def close_shared_conn():
    """
    Закрывает и сбрасывает общее соединение.
    Вызывается при переинициализации БД (смена DB_PATH в тестах — FR-006) и при
    остановке бота. Следующий вызов get_conn() лениво создаст новое соединение.
    """
    global _shared_conn
    if _shared_conn is not None:
        try:
            _shared_conn.close()
        except sqlite3.Error:
            pass
        _shared_conn = None


@contextmanager
def get_conn():
    """
    Контекстный менеджер соединения.
    Отдаёт ОБЩЕЕ переиспользуемое соединение и НЕ закрывает его на выходе
    (FR-001). Семантика транзакций сохранена: вызывающий код использует
    `with conn:` для commit/rollback (FR-003). При исключении откатываем
    возможную незавершённую транзакцию, чтобы не «отравить» общее соединение.
    """
    conn = _get_shared_conn()
    try:
        yield conn
    except Exception:
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
        raise


def init_db():
    """Создает таблицы и проверяет поддержку Foreign Keys."""
    # [Feature 008 / FR-006] Сбрасываем общее соединение перед (пере)инициализацией,
    # чтобы после смены DB_PATH (тесты) get_conn() привязался к актуальной БД.
    close_shared_conn()
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
                    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
                    FOREIGN KEY (topic_id) REFERENCES topic_names(topic_id) ON DELETE CASCADE)""")

                # Таблица пользователей
                c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT)")

                # Таблица участников шаблонов групп (NEW TEMPLATE MODEL)
                c.execute("""CREATE TABLE IF NOT EXISTS group_members (
                    group_id INTEGER,
                    user_id INTEGER,
                    PRIMARY KEY (group_id, user_id),
                    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE)""")

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

                # Таблицы Мероприятий (Expedition Protocol)
                c.execute("""CREATE TABLE IF NOT EXISTS events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT,
                    start_iso TEXT,
                    end_iso TEXT,
                    creator_id INTEGER,
                    is_approved INTEGER DEFAULT 0,
                    sheet_url TEXT,
                    FOREIGN KEY (creator_id) REFERENCES users(user_id) ON DELETE SET NULL
                )""")

                # Миграция: Проверяем наличие новых колонок для старых баз
                columns = [col[1] for col in c.execute("PRAGMA table_info(events)").fetchall()]
                if 'start_iso' not in columns:
                    c.execute("ALTER TABLE events ADD COLUMN start_iso TEXT")
                if 'end_iso' not in columns:
                    c.execute("ALTER TABLE events ADD COLUMN end_iso TEXT")

                c.execute("""CREATE TABLE IF NOT EXISTS event_leads (
                    event_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    PRIMARY KEY (event_id, user_id),
                    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )""")

                c.execute("""CREATE TABLE IF NOT EXISTS event_participants (
                    event_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    PRIMARY KEY (event_id, user_id),
                    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )""")

                # Таблица заявок на аудит
                c.execute("""CREATE TABLE IF NOT EXISTS audit_requests (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    entity_type TEXT    NOT NULL,
                    entity_id   INTEGER NOT NULL,
                    status      TEXT    NOT NULL DEFAULT 'pending',
                    comment     TEXT,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )""")

                # Таблица анонсов (Dispatcher Model)
                c.execute("""CREATE TABLE IF NOT EXISTS announcements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,         -- 'event', 'gear', 'fee'
                    target_id INTEGER NOT NULL,  -- ID связанной сущности
                    topic_id INTEGER NOT NULL,   -- Топик, к которому привязан доступ
                    creator_id INTEGER NOT NULL, -- Кто создал анонс
                    chat_id INTEGER,            -- ID чата, где опубликован
                    message_id INTEGER,         -- ID сообщения
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""")

                # [Feature 012 / №16] Персистентный FSM-storage. Составной PK повторяет
                # StorageKey aiogram; thread_id NOT NULL DEFAULT 0 — сентинел вместо None,
                # т.к. SQLite считает NULL в составном PK различными (иначе дубли строк на
                # основном пути — личные сообщения). Без FK: состояние существует и у
                # незарегистрированного пользователя, а chat_id — не пользователь.
                # updated_at — пассивные метаданные (заполняются SQL-ом, UTC; наивных
                # datetime.now() не вводим).
                c.execute("""CREATE TABLE IF NOT EXISTS fsm_storage (
                    bot_id     INTEGER NOT NULL,
                    chat_id    INTEGER NOT NULL,
                    user_id    INTEGER NOT NULL,
                    thread_id  INTEGER NOT NULL DEFAULT 0,
                    destiny    TEXT    NOT NULL DEFAULT 'default',
                    state      TEXT,
                    data       TEXT    NOT NULL DEFAULT '{}',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (bot_id, chat_id, user_id, thread_id, destiny)
                )""")

                # Индексы
                c.execute("CREATE INDEX IF NOT EXISTS idx_group_members_group_id ON group_members(group_id)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_group_members_user_id ON group_members(user_id)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_group_topics_topic_id ON group_topics(topic_id)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_direct_topic_access_user_id ON direct_topic_access(user_id)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_event_participants_event_id ON event_participants(event_id)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_event_leads_event_id ON event_leads(event_id)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_requests(entity_type, entity_id)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_requests(user_id, status)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_announcements_target ON announcements(type, target_id)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_announcements_topic ON announcements(topic_id)")

                # Предзаполнение ролей
                c.execute("INSERT OR IGNORE INTO roles (name) VALUES ('superadmin')")
                c.execute("INSERT OR IGNORE INTO roles (name) VALUES ('admin')")
                c.execute("INSERT OR IGNORE INTO roles (name) VALUES ('moderator')")

        logger.info("🗄 БД инициализирована. Поддержка Native FK (Cascade) включена.")
    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации БД: {e}")
        raise
