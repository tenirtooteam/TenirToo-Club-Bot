import sqlite3
import pytest
from unittest.mock import patch
from contextlib import contextmanager
from database import events, db

# Глобальное соединение in-memory для тестов (чтобы данные сохранялись между вызовами get_conn)
shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
shared_conn.execute("PRAGMA foreign_keys = ON;")

class MockConnection:
    def __init__(self, conn):
        self.conn = conn
        self.commit_called = False
        
    def cursor(self): return self.conn.cursor()
    def execute(self, *args, **kwargs): return self.conn.execute(*args, **kwargs)
    def commit(self): 
        self.commit_called = True
        self.conn.commit()
    def __enter__(self): 
        self.conn.__enter__()
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None: self.commit_called = True
        self.conn.__exit__(exc_type, exc_val, exc_tb)

# Переменная для отслеживания текущего мок-соединения
current_mock_conn = None

@contextmanager
def mock_get_conn():
    global current_mock_conn
    current_mock_conn = MockConnection(shared_conn)
    try:
        yield current_mock_conn
    finally:
        pass

@pytest.fixture(autouse=True)
def setup_test_db():
    """Поднимает структуру БД в памяти перед каждым тестом."""
    with patch('database.connection.get_conn', new=mock_get_conn):
        with patch('database.events.get_conn', new=mock_get_conn):
            with patch('database.db.get_conn', new=mock_get_conn):
                # Создаем таблицы (эмуляция init_db)
                c = shared_conn.cursor()
                c.execute("CREATE TABLE users (user_id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT)")
                
                c.execute("""CREATE TABLE events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT,
                    creator_id INTEGER,
                    is_approved INTEGER DEFAULT 0,
                    sheet_url TEXT,
                    FOREIGN KEY (creator_id) REFERENCES users(user_id) ON DELETE SET NULL
                )""")

                c.execute("""CREATE TABLE event_leads (
                    event_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    PRIMARY KEY (event_id, user_id),
                    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )""")

                c.execute("""CREATE TABLE event_participants (
                    event_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    PRIMARY KEY (event_id, user_id),
                    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )""")
                shared_conn.commit()
                
                yield # Выполнение теста
                
                # Очистка базы после теста
                c.execute("DROP TABLE IF EXISTS event_participants")
                c.execute("DROP TABLE IF EXISTS event_leads")
                c.execute("DROP TABLE IF EXISTS events")
                c.execute("DROP TABLE IF EXISTS users")
                shared_conn.commit()

def test_create_event():
    with patch('database.events.get_conn', new=mock_get_conn):
        shared_conn.execute("INSERT INTO users (user_id, first_name) VALUES (1, 'Test')")
        event_id = events.create_event("Поход", "01-01", "02-01", 1, 1)
        
        assert event_id > 0
        details = events.get_event_details(event_id)
        assert details is not None
        assert details["title"] == "Поход"
        assert details["creator_id"] == 1

def test_orphan_protection_set_null():
    """[CC-1] Проверяет, что при удалении юзера его мероприятие остается, а creator_id становится NULL."""
    with patch('database.events.get_conn', new=mock_get_conn):
        shared_conn.execute("INSERT INTO users (user_id, first_name) VALUES (99, 'To Delete')")
        event_id = events.create_event("Осиротевший Поход", "01-01", "", 99, 1)
        
        # Удаляем пользователя (эмуляция удаления из базы)
        shared_conn.execute("DELETE FROM users WHERE user_id = 99")
        shared_conn.commit()
        
        # Мероприятие должно остаться
        details = events.get_event_details(event_id)
        assert details is not None
        assert details["creator_id"] is None # Правило SET NULL сработало

def test_participants_cascade():
    """Проверяет, что при удалении юзера он пропадает из участников мероприятия (CASCADE)."""
    with patch('database.events.get_conn', new=mock_get_conn):
        shared_conn.execute("INSERT INTO users (user_id, first_name) VALUES (10, 'Lead')")
        shared_conn.execute("INSERT INTO users (user_id, first_name) VALUES (11, 'Part')")
        
        event_id = events.create_event("Поход с участниками", "01-01", "", 10, 1)
        events.add_event_participant(event_id, 11)
        
        details_before = events.get_event_details(event_id)
        assert 11 in details_before["participants"]
        
        # Удаляем участника
        shared_conn.execute("DELETE FROM users WHERE user_id = 11")
        shared_conn.commit()
        
        details_after = events.get_event_details(event_id)
        assert 11 not in details_after["participants"]

def test_transaction_commits():
    """[CC-1] Убеждаемся, что DML операции (create_event) вызывают commit() или контекстный менеджер with conn:."""
    with patch('database.events.get_conn', new=mock_get_conn):
        shared_conn.execute("INSERT INTO users (user_id, first_name) VALUES (88, 'Transact')")
        
        events.create_event("Транзакция", "01", "02", 88, 1)
        # Проверяем, что флаг commit_called был установлен (вызван __exit__ без ошибок)
        assert current_mock_conn.commit_called is True

