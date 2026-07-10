# -*- coding: utf-8 -*-
import pytest
from unittest.mock import AsyncMock, MagicMock
from database import db
from middlewares.access_check import UserManagerMiddleware, ForumUtilityMiddleware, AccessGuardMiddleware
from middlewares.fsm_button_guard import FsmButtonGuardMiddleware

@pytest.mark.asyncio
async def test_user_manager_middleware_registration(db_setup, mock_bot, create_context):
    user_id = 111222
    _, _, message, state = await create_context(user_id=user_id, chat_id=user_id, text="Hello bot!")

    assert not db.user_exists(user_id)

    middleware = UserManagerMiddleware()

    async def dummy_handler(event, data):
        return "passed"

    result = await middleware(dummy_handler, message, {"state": state})
    assert result == "passed"

    # Verify user registered in DB
    assert db.user_exists(user_id)


@pytest.mark.asyncio
async def test_forum_utility_topic_rename_sync(db_setup, mock_bot):
    topic_id = 33
    db.update_topic_name(topic_id, "Old Name")

    message = MagicMock()
    message.chat = MagicMock()
    message.chat.type = "supergroup"
    message.message_thread_id = topic_id
    message.forum_topic_edited = MagicMock()
    message.forum_topic_edited.name = "New Super Name"
    message.forum_topic_deleted = None
    message.forum_topic_created = None
    message.delete = AsyncMock()

    middleware = ForumUtilityMiddleware()

    async def dummy_handler(event, data):
        return "passed"

    result = await middleware(dummy_handler, message, {})
    assert result is None
    message.delete.assert_called_once()

    # Verify topic renamed in DB
    assert db.get_topic_name(topic_id) == "New Super Name"


@pytest.mark.asyncio
async def test_forum_utility_topic_deleted_cascade(db_setup, mock_bot):
    topic_id = 44
    user_id = 555
    db.add_user(user_id, "John", "Doe")
    db.update_topic_name(topic_id, "Deleted Topic")
    db.grant_role(user_id, db.get_role_id("moderator"), topic_id=topic_id)

    message = MagicMock()
    message.chat = MagicMock()
    message.chat.type = "supergroup"
    message.message_thread_id = topic_id
    message.forum_topic_deleted = MagicMock()
    message.forum_topic_edited = None
    message.forum_topic_created = None

    middleware = ForumUtilityMiddleware()

    async def dummy_handler(event, data):
        return "passed"

    result = await middleware(dummy_handler, message, {})
    assert result is None

    # Verify topic deleted from DB
    assert topic_id not in db.get_all_unique_topics()

    # Verify moderator role Cascade Purged
    roles = db.get_user_roles(user_id)
    assert len(roles) == 0


@pytest.mark.asyncio
async def test_access_guard_middleware(db_setup, mock_bot):
    topic_id = 55
    user_id = 8888
    db.add_user(user_id, "Blocked", "User")
    db.update_topic_name(topic_id, "Secret Topic")
    db.grant_direct_access(999, topic_id) # make restricted

    message = MagicMock()
    message.chat = MagicMock()
    message.chat.type = "supergroup"
    message.from_user = MagicMock()
    message.from_user.id = user_id
    message.from_user.first_name = "Blocked"
    message.from_user.last_name = "User"
    message.message_thread_id = topic_id
    message.bot = mock_bot
    message.delete = AsyncMock()

    middleware = AccessGuardMiddleware()

    async def dummy_handler(event, data):
        return "passed"

    # User is not authorized to write, should delete and early return
    result = await middleware(dummy_handler, message, {})
    assert result is None
    message.delete.assert_called_once()


@pytest.mark.asyncio
async def test_access_guard_none_sender_passthrough(db_setup, mock_bot):
    """
    C2 [tail]: сообщение без отправителя (пост канала / анонимный админ →
    from_user is None) не должно ронять AccessGuardMiddleware — проходит дальше.
    """
    message = MagicMock()
    message.chat = MagicMock()
    message.chat.type = "supergroup"
    message.from_user = None  # нет отправителя
    message.bot = mock_bot
    message.message_thread_id = 77

    middleware = AccessGuardMiddleware()

    async def dummy_handler(event, data):
        return "passed"

    # Сейчас: event.from_user.id → AttributeError. После фикса — сквозной проход.
    result = await middleware(dummy_handler, message, {})
    assert result == "passed"


@pytest.mark.asyncio
async def test_fsm_button_guard_middleware(db_setup, mock_bot, storage):
    user_id = 999

    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.storage.base import StorageKey
    state = FSMContext(storage=storage, key=StorageKey(bot_id=mock_bot.id, chat_id=user_id, user_id=user_id))

    # Set FSM state
    await state.set_state("SomeState:waiting")
    await state.update_data(last_menu_id=1234)

    callback = MagicMock()
    callback.message = MagicMock()
    callback.message.chat = MagicMock()
    callback.message.chat.type = "private"
    callback.message.chat.id = user_id
    callback.message.message_id = 1
    callback.data = "some_click"
    callback.bot = mock_bot
    callback.answer = AsyncMock()
    mock_bot.delete_message = AsyncMock()

    middleware = FsmButtonGuardMiddleware()

    async def dummy_handler(event, data):
        return "passed"

    result = await middleware(dummy_handler, callback, {"state": state})
    assert result is None
    mock_bot.delete_message.assert_called_once_with(chat_id=user_id, message_id=1)

    # Try with whitelisted callback "landing"
    callback_landing = MagicMock()
    callback_landing.message = MagicMock()
    callback_landing.message.chat = MagicMock()
    callback_landing.message.chat.type = "private"
    callback_landing.message.chat.id = user_id
    callback_landing.message.message_id = 1
    callback_landing.data = "landing"
    callback_landing.bot = mock_bot

    result_landing = await middleware(dummy_handler, callback_landing, {"state": state})
    assert result_landing == "passed"
