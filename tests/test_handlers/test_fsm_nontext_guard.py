import pytest
from unittest.mock import AsyncMock, patch

from handlers.moderator import (
    moderator_rename_topic_finish,
    process_direct_access_user_search,
)
from handlers.common import search_query_handler
from handlers.events import process_editing_title, process_editing_dates


# BUG-3 [US3]: не-текстовое сообщение (фото/стикер/голос → message.text is None)
# в этих FSM-состояниях НЕ должно ронять хендлер; должен быть мягкий ответ.
NONTEXT_HANDLERS = [
    moderator_rename_topic_finish,
    process_direct_access_user_search,
    search_query_handler,
    process_editing_title,
    process_editing_dates,
]


@pytest.mark.asyncio
@pytest.mark.parametrize("handler", NONTEXT_HANDLERS, ids=lambda h: h.__name__)
async def test_nontext_message_is_handled_gracefully(handler, create_context, db_setup):
    _, _, message, state = await create_context(text=None)
    # Минимальные данные состояния (guard должен вернуть раньше, чем они понадобятся)
    await state.update_data(
        moderator_edit_topic_id=1,
        moderator_direct_access_topic=1,
        search_type="user",
        edit_event_id=1,
        new_title="X",
    )

    with patch("services.ui_service.UIService.show_temp_message", new_callable=AsyncMock) as mock_temp:
        # Не должно быть исключения (сейчас падает на message.text.strip())
        await handler(message, state)

    assert mock_temp.called, f"{handler.__name__} не дал мягкий ответ на не-текст"
