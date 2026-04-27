import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram import types
from handlers.events import process_event_dates, approve_event_handler, reject_event_handler, show_pending_events, process_event_title
import config

@pytest.mark.asyncio
@patch('handlers.events.ManagementService')
@patch('handlers.events.PermissionService')
@patch('handlers.events.EventService')
@patch('handlers.events.show_events_list')
@patch('handlers.events.UIService', new_callable=AsyncMock)
async def test_process_event_dates_regular_user(mock_ui, mock_show_list, mock_event_service, mock_perm, mock_mgmt):
    """Обычный пользователь: мероприятие должно уйти на модерацию."""
    mock_event_service.notify_admins_for_approval = AsyncMock()
    message = AsyncMock()
    message.text = "01.01 - 02.01"
    message.from_user.id = 111
    
    state = AsyncMock()
    state.get_data.return_value = {"title": "Поход"}
    
    # Мок сервисов
    mock_perm.is_global_admin.return_value = False
    mock_mgmt.create_event_action.return_value = 10
    
    await process_event_dates(message, state)
    
    # Проверяем, что is_approved = 0
    mock_mgmt.create_event_action.assert_called_once_with("Поход", "01.01 - 02.01", 111, 0)
    
    # Проверяем уведомление админам
    mock_event_service.notify_admins_for_approval.assert_called_once_with(message.bot, 10)
    
    # Проверяем редирект с текстом модерации
    mock_show_list.assert_called_once()
    args, kwargs = mock_show_list.call_args
    assert "модерацию" in kwargs["custom_text"]

@pytest.mark.asyncio
@patch('handlers.events.ManagementService')
@patch('handlers.events.PermissionService')
@patch('handlers.events.EventService')
@patch('handlers.events.show_events_list')
@patch('handlers.events.UIService', new_callable=AsyncMock)
async def test_process_event_dates_admin_audit_on(mock_ui, mock_show_list, mock_event_service, mock_perm, mock_mgmt):
    """[CC-2] Админ с включенным аудитом: мероприятие уходит на модерацию."""
    mock_event_service.notify_admins_for_approval = AsyncMock()
    message = AsyncMock()
    message.from_user = AsyncMock()
    message.text = "01.01 - 02.01"
    message.from_user.id = 222
    
    state = AsyncMock()
    state.get_data.return_value = {"title": "Поход Админа"}
    
    mock_perm.is_global_admin.return_value = True
    mock_mgmt.create_event_action.return_value = 20
    
    original_audit = getattr(config, 'REQUIRE_ADMIN_EVENT_AUDIT', True)
    config.REQUIRE_ADMIN_EVENT_AUDIT = True
    
    try:
        await process_event_dates(message, state)
        # Уходит на модерацию (is_approved=0)
        mock_mgmt.create_event_action.assert_called_once_with("Поход Админа", "01.01 - 02.01", 222, 0)
        mock_event_service.notify_admins_for_approval.assert_called_once_with(message.bot, 20)
        
        # Проверяем редирект
        mock_show_list.assert_called_once()
        assert "модерацию" in mock_show_list.call_args[1]["custom_text"]
    finally:
        config.REQUIRE_ADMIN_EVENT_AUDIT = original_audit

@pytest.mark.asyncio
@patch('handlers.events.ManagementService')
@patch('handlers.events.PermissionService')
@patch('handlers.events.EventService')
@patch('handlers.events.show_events_list')
@patch('handlers.events.UIService', new_callable=AsyncMock)
async def test_process_event_dates_admin_audit_off(mock_ui, mock_show_list, mock_event_service, mock_perm, mock_mgmt):
    """[CC-2] Админ с выключенным аудитом: мгновенная публикация."""
    message = AsyncMock()
    message.from_user = AsyncMock()
    message.text = "01.01 - 02.01"
    message.from_user.id = 333
    
    state = AsyncMock()
    state.get_data.return_value = {"title": "Супер Поход"}
    
    mock_perm.is_global_admin.return_value = True
    mock_mgmt.create_event_action.return_value = 30
    
    original_audit = getattr(config, 'REQUIRE_ADMIN_EVENT_AUDIT', True)
    config.REQUIRE_ADMIN_EVENT_AUDIT = False
    
    try:
        await process_event_dates(message, state)
        # Одобряется сразу (is_approved=1)
        mock_mgmt.create_event_action.assert_called_once_with("Супер Поход", "01.01 - 02.01", 333, 1)
        # Уведомления не рассылаются
        mock_event_service.notify_admins_for_approval.assert_not_called()
        
        # Проверяем редирект с текстом успеха
        mock_show_list.assert_called_once()
        assert "опубликовано" in mock_show_list.call_args[1]["custom_text"]
    finally:
        config.REQUIRE_ADMIN_EVENT_AUDIT = original_audit

@pytest.mark.asyncio
@patch('handlers.events.ManagementService')
@patch('handlers.events.PermissionService')
@patch('handlers.events.UIService', new_callable=AsyncMock)
@patch('handlers.events.view_event')
async def test_approve_event_handler(mock_view, mock_ui, mock_perm, mock_mgmt):
    callback = AsyncMock()
    callback.from_user = AsyncMock()
    callback.data = "event_approve:15"
    callback.from_user.id = 999
    
    mock_perm.is_global_admin.return_value = True
    mock_mgmt.get_pending_request_id.return_value = 1
    mock_mgmt.resolve_request = AsyncMock(return_value=(True, "ok"))
    mock_mgmt.get_audit_request.return_value = {"entity_type": "event_approval", "entity_id": 15}
    
    await approve_event_handler(callback, AsyncMock())
    
    mock_ui.delete_msg.assert_called_once_with(callback.message)

@pytest.mark.asyncio
@patch('handlers.events.ManagementService')
@patch('handlers.events.PermissionService')
@patch('handlers.events.UIService', new_callable=AsyncMock)
async def test_reject_event_handler(mock_ui, mock_perm, mock_mgmt):
    callback = AsyncMock()
    callback.from_user = AsyncMock()
    callback.data = "event_reject:25"
    callback.from_user.id = 999
    
    mock_perm.is_global_admin.return_value = True
    mock_mgmt.get_pending_request_id.return_value = 1
    mock_mgmt.resolve_request = AsyncMock(return_value=(True, "ok"))
    
    await reject_event_handler(callback, AsyncMock())
    
    mock_ui.delete_msg.assert_called_once_with(callback.message)

@pytest.mark.asyncio
@patch('handlers.events.PermissionService')
@patch('handlers.events.UIService', new_callable=AsyncMock)
@patch('database.db.get_pending_events')
async def test_show_pending_events(mock_db_pending, mock_ui, mock_perm):
    """Проверка отображения списка ожидания."""
    callback = AsyncMock()
    callback.from_user.id = 777
    state = AsyncMock()
    
    mock_perm.is_global_admin.return_value = True
    mock_db_pending.return_value = [{"event_id": 1, "title": "Test", "start_date": "01.01", "end_date": "02.01"}]
    
    await show_pending_events(callback, state)
    
    mock_db_pending.assert_called_once()
    state.set_state.assert_called_once_with(None)
    mock_ui.sterile_show.assert_called_once()

@pytest.mark.asyncio
@patch('handlers.events.UIService', new_callable=AsyncMock)
async def test_process_event_title_non_text(mock_ui):
    """[CC-2] Проверка: отправка фото вместо названия не должна ронять бота."""
    message = AsyncMock()
    message.text = None # Эмуляция фото/стикера
    state = AsyncMock()
    
    await process_event_title(message, state)
    
    # Должно быть показано временное сообщение об ошибке
    mock_ui.show_temp_message.assert_called_once()
    assert "название" in mock_ui.show_temp_message.call_args[0][2]
    # Состояние не должно меняться (в aiogram 3.4.1 mock AsyncMock)
    state.set_state.assert_not_called()

@pytest.mark.asyncio
@patch('handlers.events.UIService', new_callable=AsyncMock)
async def test_process_event_dates_non_text(mock_ui):
    """[CC-2] Проверка: отправка фото вместо дат не должна ронять бота."""
    message = AsyncMock()
    message.text = None
    state = AsyncMock()
    
    await process_event_dates(message, state)
    
    mock_ui.show_temp_message.assert_called_once()
    assert "даты" in mock_ui.show_temp_message.call_args[0][2]
