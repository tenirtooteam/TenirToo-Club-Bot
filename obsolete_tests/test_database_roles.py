import sqlite3
import pytest
from unittest.mock import patch
from contextlib import contextmanager
from database import roles, db

shared_conn = sqlite3.connect(":memory:", check_same_thread=False)

@contextmanager
def mock_get_conn():
    try:
        yield shared_conn
    finally:
        pass

@pytest.fixture(autouse=True)
def setup_test_db():
    with patch('database.connection.get_conn', new=mock_get_conn):
        with patch('database.roles.get_conn', new=mock_get_conn):
            c = shared_conn.cursor()
            c.execute("CREATE TABLE users (user_id INTEGER PRIMARY KEY, first_name TEXT)")
            c.execute("CREATE TABLE roles (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
            c.execute("CREATE TABLE user_roles (user_id INTEGER, role_id INTEGER, topic_id INTEGER)")
            
            c.execute("INSERT INTO roles (name) VALUES ('admin'), ('superadmin'), ('moderator'), ('user')")
            
            # Пользователи
            c.execute("INSERT INTO users (user_id, first_name) VALUES (1, 'Admin'), (2, 'SuperAdmin'), (3, 'Moder'), (4, 'User')")
            
            # Назначаем роли
            c.execute("INSERT INTO user_roles (user_id, role_id) VALUES (1, 1)") # Admin
            c.execute("INSERT INTO user_roles (user_id, role_id) VALUES (2, 2)") # SuperAdmin
            c.execute("INSERT INTO user_roles (user_id, role_id) VALUES (3, 3)") # Moder
            
            shared_conn.commit()
            
            yield
            
            c.execute("DROP TABLE IF EXISTS user_roles")
            c.execute("DROP TABLE IF EXISTS roles")
            c.execute("DROP TABLE IF EXISTS users")
            shared_conn.commit()

def test_get_global_admin_ids():
    with patch('database.roles.get_conn', new=mock_get_conn):
        admin_ids = roles.get_global_admin_ids()
        
        assert len(admin_ids) == 2
        assert 1 in admin_ids
        assert 2 in admin_ids
        assert 3 not in admin_ids # Модератор не глобальный админ

def test_is_global_admin_system_admin():
    """[CC-1] Проверяет, что системный админ из конфига получает права без БД."""
    import config
    original_admin_id = config.ADMIN_ID
    config.ADMIN_ID = 99999
    
    try:
        # Даже если в БД нет такого юзера, он должен быть админом
        assert roles.is_global_admin(99999) is True
    finally:
        config.ADMIN_ID = original_admin_id

def test_is_global_admin_database():
    """Проверяет, что обычный админ из БД получает права."""
    with patch('database.roles.get_conn', new=mock_get_conn):
        assert roles.is_global_admin(1) is True
        assert roles.is_global_admin(3) is False
        assert roles.is_global_admin(4) is False
