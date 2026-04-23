import pytest
import sqlite3
import os
from unittest.mock import AsyncMock, MagicMock
from database import connection
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

@pytest.fixture(autouse=True)
def mock_db_path(monkeypatch, tmp_path):
    """Подменяет путь к БД на временный файл или :memory:"""
    # Используем временный файл в tmp_path, чтобы WAL работал корректно (в :memory: WAL может капризничать)
    db_file = tmp_path / "test_bot.db"
    monkeypatch.setattr(connection, "DB_PATH", str(db_file))
    connection.init_db()
    return str(db_file)

@pytest.fixture
def db_conn():
    """Фикстура для получения прямого соединения с тестовой БД"""
    with connection.get_conn() as conn:
        yield conn

@pytest.fixture
def mock_bot():
    """Мок для aiogram.Bot"""
    bot = AsyncMock(spec=Bot)
    bot.id = 123456789
    # Важно: в aiogram 3 методы вызываются как bot(method)
    bot.return_value = MagicMock() # результат вызова метода (Message и т.д.)
    
    bot.send_message = AsyncMock()
    bot.edit_message_text = AsyncMock()
    bot.delete_message = AsyncMock()
    bot.answer_callback_query = AsyncMock()
    return bot

@pytest.fixture
def mock_dispatcher():
    """Мок диспетчера с памятью"""
    dp = Dispatcher(storage=MemoryStorage())
    return dp

@pytest.fixture
def mock_state():
    """Мок для FSMContext"""
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.set_data = AsyncMock()
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    return state
