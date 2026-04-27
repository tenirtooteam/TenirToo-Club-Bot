import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from handlers.moderator import moderator_dashboard, moderator_rename_topic_finish
from aiogram.fsm.context import FSMContext

@pytest.fixture
def mock_state():
    state = AsyncMock(spec=FSMContext)
    state.get_data.return_value = {}
    return state

@pytest.mark.asyncio
async def test_moderator_dashboard_no_rights(mock_state):
    message = AsyncMock()
    message.from_user.id = 123
    
    with patch("services.permission_service.PermissionService.get_manageable_topics", return_value=[]):
        res = await moderator_dashboard.__wrapped__(message, mock_state)
        text, markup = res
        assert "нет прав" in text
        assert markup is None

@pytest.mark.asyncio
async def test_moderator_dashboard_with_rights(mock_state):
    message = AsyncMock()
    message.from_user.id = 123
    
    with patch("services.permission_service.PermissionService.get_manageable_topics", return_value=[1, 2]):
        res = await moderator_dashboard.__wrapped__(message, mock_state)
        text, markup = res
        assert "Панель модератора" in text
        assert markup is not None

@pytest.mark.asyncio
async def test_moderator_rename_topic_finish_success(mock_state):
    message = AsyncMock()
    message.text = "New Topic Name"
    message.bot = AsyncMock()
    
    mock_state.get_data.return_value = {"moderator_edit_topic_id": 10}
    
    with patch("services.management_service.ManagementService.update_topic_name", return_value=(True, "✅")) as mock_update:
        with patch("services.ui_service.UIService.generic_navigator", AsyncMock()) as mock_nav:
            await moderator_rename_topic_finish(message, mock_state)
            
            mock_update.assert_called_once_with(10, "New Topic Name")
            # Проверка вызова Telegram API
            message.bot.edit_forum_topic.assert_called_once()
            mock_nav.assert_called_once()
