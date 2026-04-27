import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from handlers.events import approve_event_handler, reject_event_handler

@pytest.mark.asyncio
@patch('handlers.events.ManagementService')
@patch('handlers.events.PermissionService')
@patch('handlers.events.UIService', new_callable=AsyncMock)
async def test_approve_closes_menu_without_buttons(mock_ui, mock_perm, mock_mgmt):
    """[CC-2] Проверка: одобрение мероприятия должно закрывать меню и убирать кнопки."""
    callback = AsyncMock()
    callback.data = "event_approve:10"
    callback.from_user.id = 999
    state = AsyncMock()
    
    # Мокаем права и наличие заявки
    mock_perm.is_global_admin.return_value = True
    mock_mgmt.get_pending_request_id.return_value = 50
    mock_mgmt.resolve_request = AsyncMock(return_value=(True, "✅ Одобрено"))
    mock_mgmt.get_audit_request.return_value = {"entity_type": "event_approval", "entity_id": 10}
    mock_mgmt.get_entity_name.return_value = "Тест Поход"
    
    await approve_event_handler(callback, state)
    
    # Проверяем физическое удаление сообщения с кнопками
    mock_ui.delete_msg.assert_called_once_with(callback.message)

@pytest.mark.asyncio
@patch('handlers.events.ManagementService')
@patch('handlers.events.PermissionService')
@patch('handlers.events.UIService', new_callable=AsyncMock)
async def test_reject_closes_menu_without_buttons(mock_ui, mock_perm, mock_mgmt):
    """[CC-2] Проверка: отклонение мероприятия должно закрывать меню и убирать кнопки."""
    callback = AsyncMock()
    callback.data = "event_reject:20"
    callback.from_user.id = 999
    state = AsyncMock()
    
    mock_perm.is_global_admin.return_value = True
    mock_mgmt.get_pending_request_id.return_value = 60
    mock_mgmt.resolve_request = AsyncMock(return_value=(True, "❌ Отклонено"))
    
    await reject_event_handler(callback, state)
    
    # Проверяем физическое удаление сообщения с кнопками
    mock_ui.delete_msg.assert_called_once_with(callback.message)

@pytest.mark.asyncio
@patch('handlers.events.ManagementService')
@patch('handlers.events.PermissionService')
@patch('handlers.events.UIService', new_callable=AsyncMock)
@patch('handlers.events.view_event', new_callable=AsyncMock)
async def test_audit_already_processed_shows_alert(mock_view, mock_ui, mock_perm, mock_mgmt):
    """[CC-5] Проверка: если заявка уже обработана, должен быть алерт, а UI не должен меняться."""
    callback = AsyncMock()
    callback.data = "event_approve:30"
    callback.from_user.id = 999
    state = AsyncMock()
    
    mock_perm.is_global_admin.return_value = True
    # Заявка не найдена (уже обработана)
    mock_mgmt.get_pending_request_id.return_value = None
    
    await approve_event_handler(callback, state)
    
    # Должен быть показан алерт
    callback.answer.assert_called_once()
    assert callback.answer.call_args[1]["show_alert"] is True
    assert "уже была обработана" in callback.answer.call_args[0][0]
    
    # close_notification НЕ должен вызываться
    mock_ui.close_notification.assert_not_called()
    # Должен быть возврат к просмотру
    mock_view.assert_called_once()
