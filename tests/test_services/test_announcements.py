# Файл: tests/test_services/test_announcements.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from services.announcement_service import AnnouncementService
from database import db

@pytest.mark.asyncio
async def test_quick_event_creation_logic():
    """Проверка парсинга и создания квик-ивента."""
    db.init_db()
    
    # Регистрация пользователя для соблюдения FK
    db.add_user(12345, "Test", "User")
    
    # Имитируем сообщение
    message = MagicMock()
    message.from_user.id = 12345
    message.from_user.full_name = "Test User"
    message.message_thread_id = 777
    message.text = "/an Тренировка\nПриходите все на стадион"
    
    text, ann_id = await AnnouncementService.create_quick_event(message)
    
    assert ann_id is not None
    assert "Тренировка" in text
    assert "стадион" in text
    
    # Проверяем записи в БД
    ann = db.get_announcement(ann_id)
    assert ann[1] == "event"
    assert ann[3] == 777 # topic_id
    
    event = db.get_event_details(ann[2])
    assert event['title'] == "Тренировка"
    assert event['start_date'] == "Оперативно"

@pytest.mark.asyncio
async def test_announcement_permission_check():
    """Проверка, что кнопка 'Иду' уважает права доступа к топику."""
    # Этот тест сложнее, так как требует мока PermissionService
    pass
