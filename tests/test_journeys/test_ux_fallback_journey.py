# -*- coding: utf-8 -*-
import pytest
from unittest.mock import AsyncMock, MagicMock
from database import db
from handlers.events import start_event_creation, show_events_list
from handlers.errors import default_callback_handler
from services.callback_guard import safe_callback
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest

@pytest.mark.asyncio
async def test_event_creation_escape_hatch(db_setup, mock_bot, user_session):
    user_id = 12345
    db.add_user(user_id, "Elon", "Musk")

    session = user_session(user_id=user_id, chat_id=user_id)

    # 1. Start event creation
    await session.send_callback(
        handler=start_event_creation,
        callback_data="event_create"
    )

    # Verify FSM is active
    state = await session.state.get_state()
    assert state == "EventCreation:waiting_for_title"

    # 2. Click "Escape Hatch" cancel button (sends event_list callback)
    await session.send_callback(
        handler=show_events_list,
        callback_data="event_list"
    )

    # Verify FSM state is reset
    state = await session.state.get_state()
    assert state is None

    # Verify custom FSM data is cleared safely
    data = await session.state.get_data()
    # FSM keys like title, dates, etc., must be cleared, leaving only sterile UI keys
    assert "title" not in data
    assert "dates" not in data


@pytest.mark.asyncio
async def test_security_fallback_handler(db_setup, mock_bot):
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = MagicMock()
    callback.from_user.id = 123
    callback.bot = mock_bot
    callback.answer = AsyncMock()

    # Trigger default fallback for unhandled callbacks
    await default_callback_handler(callback)

    callback.answer.assert_called_once_with(
        "\u274c \u0414\u0435\u0439\u0441\u0442\u0432\u0438\u0435 \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u043e \u0438\u043b\u0438 \u043d\u0435 \u043f\u043e\u0434\u0434\u0435\u0440\u0436\u0438\u0432\u0430\u0435\u0442\u0441\u044f.",
        show_alert=True
    )


@pytest.mark.asyncio
async def test_safe_callback_decorator(db_setup, mock_bot):
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = MagicMock()
    callback.from_user.id = 123
    callback.data = "click"
    callback.answer = AsyncMock()

    # 1. Create a dummy handler that raises "message is not modified" TelegramBadRequest
    @safe_callback()
    async def failing_handler(cb):
        # We need a valid dummy method instance for TelegramBadRequest constructor
        mock_method = MagicMock()
        raise TelegramBadRequest(message="message is not modified", method=mock_method)

    await failing_handler(callback)

    # Verify exception is caught and callback is answered silently
    callback.answer.assert_called_once()

    # 2. Test generic exception handling
    callback.answer.reset_mock()
    @safe_callback()
    async def generic_failing_handler(cb):
        raise ValueError("Some critical DB failure")

    await generic_failing_handler(callback)

    # Verify critical error warning is displayed as alert
    callback.answer.assert_called_once_with(
        "\u274c \u041a\u0440\u0438\u0442\u0438\u0447\u0435\u0441\u043a\u0430\u044f \u043e\u0448\u0438\u0431\u043a\u0430.",
        show_alert=True
    )
