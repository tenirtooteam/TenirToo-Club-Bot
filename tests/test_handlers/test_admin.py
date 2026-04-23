import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from handlers.admin import process_group_add, toggle_group
from aiogram.fsm.context import FSMContext

@pytest.fixture
def mock_state():
    state = AsyncMock(spec=FSMContext)
    state.get_data.return_value = {}
    return state

@pytest.mark.asyncio
async def test_process_group_add_success(mock_state):
    message = AsyncMock()
    message.text = "New Cool Group"
    
    with patch("services.management_service.ManagementService.create_group", return_value=(True, "✅ Создано")) as mock_create:
        with patch("services.ui_service.UIService.show_admin_dashboard", AsyncMock()) as mock_dash:
            await process_group_add(message, mock_state)
            
            mock_create.assert_called_once_with("New Cool Group")
            mock_dash.assert_called_once()
            args, kwargs = mock_dash.call_args
            assert "Создано" in kwargs['text']

@pytest.mark.asyncio
async def test_process_group_add_fail(mock_state):
    message = AsyncMock()
    message.text = ""
    
    with patch("services.management_service.ManagementService.create_group", return_value=(False, "❌ Ошибка")) as mock_create:
        with patch("services.ui_service.UIService.show_temp_message", AsyncMock()) as mock_temp:
            await process_group_add(message, mock_state)
            
            mock_create.assert_called_once_with("")
            mock_temp.assert_called_once()

@pytest.mark.asyncio
async def test_toggle_group_callback(mock_state):
    callback = AsyncMock()
    # Формат: user_group_toggle_{user_id}_{group_id}
    callback.data = "user_group_toggle_123_10"
    
    with patch("services.management_service.ManagementService.toggle_user_group", return_value=(True, "🔓 Группа отозвана")) as mock_toggle:
        with patch("services.ui_service.UIService.generic_navigator", AsyncMock()) as mock_nav:
            await toggle_group(callback, mock_state)
            
            mock_toggle.assert_called_once_with(123, 10)
            callback.answer.assert_called_once_with("🔓 Группа отозвана")
            mock_nav.assert_called_once_with(mock_state, callback, "user_groups_manage_123")
