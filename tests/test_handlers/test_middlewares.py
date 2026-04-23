import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, Chat, User, ForumTopicEdited
from middlewares.access_check import UserManagerMiddleware, ForumUtilityMiddleware, AccessGuardMiddleware
from database import db

@pytest.fixture
def mock_handler():
    handler = AsyncMock()
    handler.return_value = "handler_result"
    return handler

@pytest.fixture
def mock_event():
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 123
    message.from_user.is_bot = False
    message.from_user.first_name = "Ivan"
    message.from_user.last_name = "Ivanov"
    message.chat = MagicMock(spec=Chat)
    message.chat.type = "supergroup"
    message.message_thread_id = 10
    message.delete = AsyncMock()
    message.bot = MagicMock()
    message.bot.id = 999
    return message

@pytest.mark.asyncio
async def test_user_manager_middleware(mock_handler, mock_event):
    middleware = UserManagerMiddleware()
    data = {}
    
    with patch("services.management_service.ManagementService.ensure_user_registered", AsyncMock()) as mock_ensure:
        result = await middleware(mock_handler, mock_event, data)
        
        assert result == "handler_result"
        mock_ensure.assert_called_once_with(mock_event.from_user)
        mock_handler.assert_called_once_with(mock_event, data)

@pytest.mark.asyncio
async def test_forum_utility_middleware_private(mock_handler, mock_event):
    mock_event.chat.type = "private"
    middleware = ForumUtilityMiddleware()
    
    result = await middleware(mock_handler, mock_event, {})
    assert result == "handler_result"
    mock_handler.assert_called_once()

@pytest.mark.asyncio
async def test_forum_utility_middleware_sync_topic(mock_handler, mock_event):
    mock_event.chat.type = "supergroup"
    mock_event.forum_topic_edited = MagicMock(spec=ForumTopicEdited)
    mock_event.forum_topic_edited.name = "New Name"
    mock_event.message_thread_id = 55
    
    middleware = ForumUtilityMiddleware()
    
    with patch("database.db.update_topic_name") as mock_update:
        await middleware(mock_handler, mock_event, {})
        mock_update.assert_called_once_with(55, "New Name")
        mock_event.delete.assert_called_once()
        # Обработчик не должен вызываться дальше при редактировании топика
        mock_handler.assert_not_called()

@pytest.mark.asyncio
async def test_access_guard_middleware_allowed(mock_handler, mock_event):
    middleware = AccessGuardMiddleware()
    
    with patch("services.permission_service.PermissionService.can_user_write_in_topic", return_value=True):
        with patch("services.permission_service.PermissionService.is_global_admin", return_value=False):
            with patch("config.IMMUNITY_FOR_ADMINS", False):
                result = await middleware(mock_handler, mock_event, {})
                assert result == "handler_result"
                mock_handler.assert_called_once()

@pytest.mark.asyncio
async def test_access_guard_middleware_denied(mock_handler, mock_event):
    middleware = AccessGuardMiddleware()
    
    with patch("services.permission_service.PermissionService.can_user_write_in_topic", return_value=False):
        with patch("services.permission_service.PermissionService.is_global_admin", return_value=False):
            with patch("config.IMMUNITY_FOR_ADMINS", False):
                await middleware(mock_handler, mock_event, {})
                mock_event.delete.assert_called_once()
                mock_handler.assert_not_called()
