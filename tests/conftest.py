import pytest
import os
import asyncio
import datetime
from unittest.mock import AsyncMock, MagicMock
from aiogram import Bot, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey

from database import db, connection
import config

# Мокаем ADMIN_ID для тестов, чтобы не было коллизий с реальным админом [CC-1]
config.ADMIN_ID = 999999999
config.GROUP_ID = -100123456789

@pytest.fixture(autouse=True)
def mock_config_ids(monkeypatch):
    """Гарантирует, что во время тестов используются тестовые ID."""
    monkeypatch.setattr("config.ADMIN_ID", 999999999)
    monkeypatch.setattr("config.GROUP_ID", -100123456789)

@pytest.fixture(autouse=True)
def db_setup(tmp_path):
    """
    Изолированная БД для каждого теста.
    Создает временный файл БД и инициализирует таблицы.
    """
    test_db = tmp_path / "test_bot.db"
    os.environ["BOT_DB_PATH"] = str(test_db)
    
    # Сбрасываем кэш пути в модуле connection, если он уже импортирован
    connection.DB_PATH = str(test_db)
    
    connection.init_db()
    yield test_db
    
    # После теста можно удалить, но tmp_path сам очистится
    if os.path.exists(str(test_db)):
        try:
            os.remove(str(test_db))
        except:
            pass

@pytest.fixture
def mock_bot():
    """Глобальный мок бота."""
    bot = AsyncMock(spec=Bot)
    bot.id = 123456789
    return bot

@pytest.fixture
def storage():
    """Память для FSM."""
    return MemoryStorage()

@pytest.fixture
def create_context(mock_bot, storage):
    """
    Фабрика для создания контекста пользователя.
    Возвращает (user, chat, message, state)
    """
    async def _factory(user_id=123, chat_id=123, text="test", thread_id=None):
        user = types.User(id=user_id, is_bot=False, first_name="TestUser", last_name="Tester")
        chat = types.Chat(id=chat_id, type="private")
        message = types.Message(
            message_id=1,
            date=datetime.datetime.now(),
            chat=chat,
            from_user=user,
            text=text,
            message_thread_id=thread_id
        )
        state = FSMContext(storage=storage, key=StorageKey(bot_id=mock_bot.id, chat_id=chat_id, user_id=user_id))
        return user, chat, message, state
    
    return _factory

@pytest.fixture
def create_callback(mock_bot, storage):
    """Фабрика для создания CallbackQuery."""
    async def _factory(user_id=123, chat_id=123, data="data"):
        user = types.User(id=user_id, is_bot=False, first_name="TestUser")
        chat = types.Chat(id=chat_id, type="private")
        message = types.Message(
            message_id=1,
            date=datetime.datetime.now(),
            chat=chat,
            text="Menu Context"
        )
        callback = types.CallbackQuery(
            id="1",
            from_user=user,
            chat_instance="1",
            message=message,
            data=data
        )
        state = FSMContext(storage=storage, key=StorageKey(bot_id=mock_bot.id, chat_id=chat_id, user_id=user_id))
        return callback, state
        
    return _factory
