import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext
from handlers.common import cmd_help, close_menu_handler

@pytest.fixture
def mock_state():
    state = AsyncMock(spec=FSMContext)
    state.get_data.return_value = {}
    return state

@pytest.mark.asyncio
async def test_cmd_help_as_user(mock_state):
    message = AsyncMock()
    message.from_user.id = 123
    
    with patch("services.permission_service.PermissionService.is_global_admin", return_value=False):
        with patch("services.permission_service.PermissionService.get_manageable_topics", return_value=[]):
            # Используем __wrapped__, чтобы получить чистый результат без редиректа декоратора
            res = await cmd_help.__wrapped__(message, mock_state)
            text, markup = res
            
            assert "Информационный гид" in text
            assert "Администрирование" not in text
            assert "Модерация" not in text

@pytest.mark.asyncio
async def test_cmd_help_as_admin(mock_state):
    message = AsyncMock()
    message.from_user.id = 1
    
    with patch("services.permission_service.PermissionService.is_global_admin", return_value=True):
        with patch("services.permission_service.PermissionService.get_manageable_topics", return_value=[1]):
            res = await cmd_help.__wrapped__(message, mock_state)
            text, markup = res
            
            assert "Администрирование" in text
            assert "Модерация" in text

@pytest.mark.asyncio
async def test_close_menu_handler(mock_state):
    callback = AsyncMock()
    callback.message = AsyncMock()
    
    with patch("services.ui_service.UIService.delete_msg", AsyncMock()) as mock_delete:
        await close_menu_handler(callback, mock_state)
        
        mock_delete.assert_called_once_with(callback.message)
        mock_state.update_data.assert_called_once_with(last_menu_id=None, last_menu_ids=[])


@pytest.mark.asyncio
async def test_universal_help_handler(mock_state):
    from handlers.common import universal_help_handler
    callback = AsyncMock()
    callback.data = "help:templates:manage_groups"
    
    # Используем __wrapped__ для обхода декоратора safe_callback
    with patch("handlers.common.show_help_view", AsyncMock()) as mock_show:
        await universal_help_handler.__wrapped__(callback, mock_state)
        mock_show.assert_called_once_with(mock_state, callback, "templates", "manage_groups")


@pytest.mark.asyncio
async def test_show_help_view(mock_state):
    from handlers.common import show_help_view
    event = AsyncMock()
    
    with patch("services.help_service.HelpService.get_help", return_value="Test Help") as mock_get:
        with patch("services.ui_service.UIService.sterile_show", AsyncMock()) as mock_ui:
            await show_help_view(mock_state, event, "test_key", "back_point")
            
            mock_get.assert_called_once_with("test_key")
            mock_ui.assert_called_once()
            args, kwargs = mock_ui.call_args
            assert args[2] == "Test Help"
            assert kwargs["reply_markup"] is not None
