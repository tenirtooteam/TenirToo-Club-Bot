import pytest
from unittest.mock import AsyncMock, patch
from database import db
from services.management_service import ManagementService
from handlers.announcements import announcement_join_handler
from aiogram import types

@pytest.mark.asyncio
async def test_quick_announcement_creation_and_auto_join(db_setup):
    """
    Тест Case 1: Создание квик-анонса и автоматическая запись создателя. [CP-3.47] [PL-6.7]
    """
    creator_id = 1001
    db.add_user(creator_id, "Creator", "User")
    
    # 1. Создаем быстрый ивент через сервис
    title = "Quick Hike"
    event_id = ManagementService.create_quick_event(creator_id, title)
    
    assert event_id > 0
    
    # 2. Проверяем детали ивента
    event = db.get_event_details(event_id)
    assert event["title"] == title
    
    # 3. ПРОВЕРКА [CC-4]: Создатель должен быть в списке участников и лидеров
    assert creator_id in event["participants"], "Создатель не добавлен в список участников автоматически"
    assert creator_id in event["leads"], "Создатель не добавлен в список лидеров автоматически"

@pytest.mark.asyncio
async def test_announcement_join_unauthorized_user(db_setup, create_callback, mock_bot):
    """
    Тест Case 2: Попытка записи левого человека (не члена топика) в квик-анонс. [CP-3.40]
    """
    creator_id = 1001
    lefter_id = 666
    topic_id = 55
    
    db.add_user(creator_id, "Creator", "User")
    db.add_user(lefter_id, "Left", "Person")
    
    # Создаем ивент и анонс
    db.register_topic_if_not_exists(topic_id)
    event_id = ManagementService.create_quick_event(creator_id, "Secret Event")
    # Имитируем запись в анонсы (в реальности это делается при /an)
    ann_id = db.create_announcement("event", event_id, topic_id, creator_id)
    
    # Подготавливаем коллбэк от "левого" юзера
    callback, state = await create_callback(user_id=lefter_id, data=f"ann_join:{ann_id}")
    
    # 1. Симулируем отсутствие прав в топике [PermissionService.can_user_write_in_topic]
    # Нам нужно замокать PermissionService, т.к. по умолчанию у нового юзера нет прав нигде
    with patch("services.permission_service.PermissionService.can_user_write_in_topic", return_value=False):
        with patch("aiogram.types.CallbackQuery.answer", new_callable=AsyncMock) as mock_answer:
            await announcement_join_handler(callback, state)
            # 2. Проверяем, что в ответ пришло предупреждение о правах
            mock_answer.assert_any_call("🚫 У вас нет доступа к этому разделу клуба.", show_alert=True)
    
    # 3. Проверяем, что в участниках ивента по-прежнему только создатель
    event = db.get_event_details(event_id)
    assert lefter_id not in event["participants"]

@pytest.mark.asyncio
async def test_announcement_join_success_notification(db_setup, create_callback, mock_bot):
    """
    Тестирует успешную запись через анонс и отправку уведомления админу. [CP-3.48]
    """
    creator_id = 1001
    member_id = 2002
    topic_id = 1
    
    db.add_user(creator_id, "Creator", "User")
    db.add_user(member_id, "Member", "User")
    db.register_topic_if_not_exists(topic_id)
    
    event_id = ManagementService.create_quick_event(creator_id, "Public Hike")
    ann_id = db.create_announcement("event", event_id, topic_id, creator_id)
    
    callback, state = await create_callback(user_id=member_id, data=f"ann_join:{ann_id}")
    
    # Симулируем наличие прав
    with patch("services.permission_service.PermissionService.can_user_write_in_topic", return_value=True):
        with patch("aiogram.types.CallbackQuery.answer", new_callable=AsyncMock):
            # Мокаем NotificationService или проверяем вызов bot.send_message
            await announcement_join_handler(callback, state)
        
    # Проверяем запись в БД
    event = db.get_event_details(event_id)
    assert member_id in event["participants"]
    
    # Проверяем, что админу/создателю ушло уведомление (mock_bot)
    # В EventService.notify_organizers_of_direct_join мы рассылаем сообщения
    # Проверим, что был хотя бы один вызов send_message
    assert mock_bot.send_message.called
    
    # Проверим текст (хотя бы наличие ключевых слов)
    found = False
    for call in mock_bot.send_message.call_args_list:
        c_id = call.kwargs.get("chat_id") or (call.args[0] if call.args else None)
        text = call.kwargs.get("text", "") or (call.args[1] if len(call.args) > 1 else "")
        if "Новый участник" in text and "Public Hike" in text:
            found = True
            break
    assert found, f"Уведомление организатору не отправлено. Вызовы: {mock_bot.send_message.call_args_list}"
