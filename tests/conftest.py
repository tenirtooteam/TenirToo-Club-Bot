import pytest
import os
import datetime
from unittest.mock import AsyncMock
from aiogram import Bot, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey

from database import connection
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

    # [Feature 008 / US2] Холодные мемо регистрации на каждый тест (изоляция).
    from services.management_service import reset_registration_cache
    reset_registration_cache()

    yield test_db

    # После теста можно удалить, но tmp_path сам очистится
    if os.path.exists(str(test_db)):
        try:
            os.remove(str(test_db))
        except Exception:
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
    async def _factory(user_id=123, chat_id=123, text="test", thread_id=None, chat_type="private"):
        user = types.User(id=user_id, is_bot=False, first_name="TestUser", last_name="Tester")
        chat = types.Chat(id=chat_id, type=chat_type)
        message = types.Message(
            message_id=1,
            date=datetime.datetime.now(),
            chat=chat,
            from_user=user,
            text=text,
            message_thread_id=thread_id
        )
        message._bot = mock_bot
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
        message._bot = mock_bot
        callback = types.CallbackQuery(
            id="1",
            from_user=user,
            chat_instance="1",
            message=message,
            data=data
        )
        callback._bot = mock_bot
        state = FSMContext(storage=storage, key=StorageKey(bot_id=mock_bot.id, chat_id=chat_id, user_id=user_id))
        return callback, state

    return _factory

class UserSessionSimulator:
    def __init__(self, mock_bot, storage, user_id=123, chat_id=123):
        self.bot = mock_bot
        self.storage = storage
        self.user_id = user_id
        self.chat_id = chat_id
        self.key = StorageKey(bot_id=mock_bot.id, chat_id=chat_id, user_id=user_id)
        self.state = FSMContext(storage=storage, key=self.key)

    async def send_message(self, handler, text: str, thread_id: int = None, chat_type: str = "private"):
        self.bot.reset_mock()
        user = types.User(id=self.user_id, is_bot=False, first_name="TestUser", last_name="Tester")
        chat = types.Chat(id=self.chat_id, type=chat_type)
        message = types.Message(
            message_id=999,
            date=datetime.datetime.now(),
            chat=chat,
            from_user=user,
            text=text,
            message_thread_id=thread_id
        )
        message._bot = self.bot
        await handler(message, self.state)
        self.assert_ux_integrity()

    async def send_callback(self, handler, callback_data: str, message_id: int = 1):
        self.bot.reset_mock()
        user = types.User(id=self.user_id, is_bot=False, first_name="TestUser")
        chat = types.Chat(id=self.chat_id, type="private")
        message = types.Message(
            message_id=message_id,
            date=datetime.datetime.now(),
            chat=chat,
            text="Menu Context"
        )
        message._bot = self.bot
        callback = types.CallbackQuery(
            id="1",
            from_user=user,
            chat_instance="1",
            message=message,
            data=callback_data
        )
        callback._bot = self.bot

        from unittest.mock import patch
        with patch("aiogram.types.CallbackQuery.answer", new_callable=AsyncMock):
            await handler(callback, self.state)

        self.assert_ux_integrity()

    def assert_ux_integrity(self):
        calls = self.bot.mock_calls
        # Допускаем до 5 вызовов (например, при рассылке анонсов админам)
        assert len(calls) <= 5, f"Anti-spam check failed: too many bot interactions ({len(calls)})"

        for call in calls:
            method_name = call[0]
            # Игнорируем вызовы delete_webhook, start_polling и т.д.
            if method_name in ("delete_webhook", "start_polling"):
                continue

            kwargs = call[2]
            args = call[1]

            text = kwargs.get("text")
            reply_markup = kwargs.get("reply_markup")

            if not text and len(args) > 1:
                if method_name in ("send_message", "edit_message_text"):
                    text = args[1]
            if not reply_markup and len(args) > 2:
                if method_name == "send_message":
                    reply_markup = args[2]

            if text:
                assert self.is_valid_html(text), f"HTML markup validation failed for text: {text}"

            if reply_markup and isinstance(reply_markup, types.InlineKeyboardMarkup):
                assert self.has_navigation_footer(reply_markup), f"Navigation footer check failed for keyboard: {reply_markup}"

    @staticmethod
    def is_valid_html(text: str) -> bool:
        for t in ['b', 'i', 'code', 'u', 's', 'a']:
            open_count = text.count(f'<{t}')
            close_count = text.count(f'</{t}>')
            if open_count != close_count:
                return False
        return True

    @staticmethod
    def has_navigation_footer(reply_markup) -> bool:
        for row in reply_markup.inline_keyboard:
            for btn in row:
                if btn.callback_data:
                    cb = btn.callback_data
                    if cb in ("landing", "close_menu", "event_list", "user_main", "date_retry") or cb.startswith("help:") or "⬅️" in btn.text or "❌" in btn.text or "❓" in btn.text or "🔄" in btn.text or "cancel" in cb:
                        return True
        return False


@pytest.fixture
def user_session(mock_bot, storage):
    """Фикстура для создания UserSessionSimulator."""
    def _create(user_id=123, chat_id=123):
        return UserSessionSimulator(mock_bot, storage, user_id, chat_id)
    return _create

