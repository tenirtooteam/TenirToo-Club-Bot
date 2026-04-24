import pytest
from unittest.mock import patch
from services.event_service import EventService

@patch('services.event_service.db')
def test_can_edit_event_as_creator(mock_db):
    """Проверяет, что создатель мероприятия может его редактировать."""
    # Мокаем: пользователь НЕ глобальный админ, но он является создателем
    mock_db.is_global_admin.return_value = False
    mock_db.get_event_details.return_value = {"creator_id": 123}
    
    assert EventService.can_edit_event(123, 1) == True

@patch('services.event_service.db')
def test_can_edit_event_as_admin(mock_db):
    """[CC-2] Проверяет Admin Override: администратор может редактировать ЛЮБОЕ мероприятие."""
    # Мокаем: пользователь является глобальным админом, но создатель другой
    mock_db.is_global_admin.return_value = True
    # Даже не важно, кто создатель, вызов get_event_details не должен происходить
    
    assert EventService.can_edit_event(999, 1) == True

@patch('services.event_service.db')
def test_cannot_edit_event_other_user(mock_db):
    """Проверяет, что обычный юзер не может редактировать чужое мероприятие."""
    mock_db.is_global_admin.return_value = False
    mock_db.get_event_details.return_value = {"creator_id": 123}
    
    assert EventService.can_edit_event(456, 1) == False

@patch('services.event_service.db')
def test_format_event_card(mock_db):
    """Проверяет корректность формирования карточки (замена имен участников и лидов)."""
    mock_db.get_event_details.return_value = {
        "title": "Тест Поход",
        "start_date": "01.01",
        "end_date": "02.01",
        "creator_id": 1,
        "is_approved": True,
        "participants": [2, 3],
        "leads": [1]
    }
    
    # Имитируем получение имён пользователей
    def mock_get_user_name(uid):
        names = {1: "Создатель", 2: "Участник 1", 3: "Участник 2"}
        return names.get(uid, "Неизвестно")
        
    mock_db.get_user_name.side_effect = mock_get_user_name
    
    card = EventService.format_event_card(1)
    
    assert "Тест Поход" in card
    assert "✅ Одобрено" in card
    assert "Организатор: Создатель" in card
    assert "Участник 1" in card
    assert "Участник 2" in card

@pytest.mark.asyncio
@patch('services.event_service.db')
async def test_notify_admins_for_approval(mock_db):
    """[CC-3] Проверяет рассылку администраторам при модерации."""
    from unittest.mock import AsyncMock
    import config
    
    # Мокаем БД
    mock_db.get_global_admin_ids.return_value = [10, 20]
    mock_db.get_event_details.return_value = {
        "title": "Модерация", "start_date": "01", "end_date": "02",
        "creator_id": 1, "is_approved": False, "participants": [], "leads": []
    }
    mock_db.get_user_name.return_value = "Автор"
    
    # Мокаем config.ADMIN_ID (пусть он будет 30)
    original_admin_id = config.ADMIN_ID
    config.ADMIN_ID = 30
    
    bot = AsyncMock()
    
    try:
        await EventService.notify_admins_for_approval(bot, 1)
        
        # Ожидаем, что send_message вызван для 10, 20 и 30 (config.ADMIN_ID)
        assert bot.send_message.call_count == 3
        
        called_ids = [call[0][0] for call in bot.send_message.call_args_list]
        assert 10 in called_ids
        assert 20 in called_ids
        assert 30 in called_ids
    finally:
        config.ADMIN_ID = original_admin_id
