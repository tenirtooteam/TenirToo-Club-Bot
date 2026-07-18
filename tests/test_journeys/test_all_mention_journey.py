"""Journey @all: Input -> Gate -> Broadcast (feature 013, US3, №5).

Гонит реальный хендлер handle_all_mention. Позитив (модератор рассылает) + негатив
(не-модератор -> 0 рассылок, триггер всё равно удалён). R-TEST-3: args + kwargs.
"""
import pytest
from unittest.mock import AsyncMock, patch

import config
from database import db
from handlers.user import handle_all_mention


def _authorized(n: int) -> list[tuple]:
    return [(1000 + i, f"User{i}", "") for i in range(n)]


@pytest.mark.asyncio
async def test_all_mention_moderator_broadcasts(create_context, mock_bot, db_setup):
    """Модератор топика пишет @all -> рассылка уходит, триггер удалён."""
    mod_id = 100
    topic_id = 5
    db.add_user(mod_id, "Mod", "One")
    db.register_topic_if_not_exists(topic_id)
    db.grant_role(mod_id, db.get_role_id("moderator"), topic_id=topic_id)

    _, _, message, _ = await create_context(
        user_id=mod_id, chat_id=config.GROUP_ID, text="@all срочно", thread_id=topic_id,
        chat_type="supergroup",
    )

    with patch("handlers.user.UIService.delete_msg", new_callable=AsyncMock) as mock_delete, \
         patch("services.notification_service.db.get_topic_authorized_users", return_value=_authorized(3)), \
         patch("services.notification_service.asyncio.sleep", new_callable=AsyncMock):
        await handle_all_mention(message, mock_bot)

    mock_delete.assert_called_once()
    assert mock_bot.send_message.call_count == 1, "Модератор -> рассылка уходит"
    kwargs = mock_bot.send_message.call_args.kwargs
    assert kwargs["chat_id"] == config.GROUP_ID
    assert kwargs["message_thread_id"] == topic_id
    assert kwargs["parse_mode"] == "HTML"
    assert "срочно" in kwargs["text"]
    assert "tg://user?id=1000" in kwargs["text"]


@pytest.mark.asyncio
async def test_all_mention_requires_moderator(create_context, mock_bot, db_setup):
    """Не-модератор пишет @all -> 0 рассылок, но триггер всё равно удалён (тихий отказ)."""
    user_id = 300  # не модератор, не суперадмин
    topic_id = 5
    db.add_user(user_id, "Plain", "User")
    db.register_topic_if_not_exists(topic_id)

    _, _, message, _ = await create_context(
        user_id=user_id, chat_id=config.GROUP_ID, text="@all спам", thread_id=topic_id,
        chat_type="supergroup",
    )

    with patch("handlers.user.UIService.delete_msg", new_callable=AsyncMock) as mock_delete, \
         patch("services.notification_service.db.get_topic_authorized_users", return_value=_authorized(3)), \
         patch("services.notification_service.asyncio.sleep", new_callable=AsyncMock):
        await handle_all_mention(message, mock_bot)

    mock_delete.assert_called_once(), "Триггер удаляется всегда (чистота чата)"
    assert mock_bot.send_message.call_count == 0, "Не-модератор -> рассылки нет (тихий отказ)"
