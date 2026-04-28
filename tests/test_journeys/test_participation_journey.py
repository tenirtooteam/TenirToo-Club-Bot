import pytest
from unittest.mock import AsyncMock, patch
from database import db
from services.management_service import ManagementService
from services.event_service import EventService
from handlers.events import join_event
from aiogram import types
import config

@pytest.mark.asyncio
async def test_participation_request_notifies_admin(db_setup, create_callback, mock_bot):
    """
    Тест Case 3: Подача заявки на участие через карту ивента уведомляет админа. [CP-3.48]
    """
    creator_id = 1001
    applicant_id = 777
    db.add_user(creator_id, "Creator", "User")
    db.add_user(applicant_id, "Applicant", "User")
    
    # Создаем ивент (уже одобренный, чтобы можно было вступить)
    event_id = db.create_event("Test Event", "2026-01-01", None, creator_id, is_approved=1)
    
    callback, state = await create_callback(user_id=applicant_id, data=f"event_join:{event_id}")
    
    # Мокаем проверку на участие (по умолчанию False)
    with patch("services.event_service.EventService.is_event_participant", return_value=False):
        with patch("aiogram.types.CallbackQuery.answer", new_callable=AsyncMock):
            await join_event(callback, state)
        
    # 1. Проверяем, что заявка создана в БД
    req_id = ManagementService.get_user_pending_request_id(applicant_id, "event_participation", event_id)
    assert req_id is not None
    
    # 2. Проверяем УВЕДОМЛЕНИЕ ОРГАНИЗАТОРА [CC-3]
    # Должен быть вызван notify_admins_of_participation_request
    # И в итоге bot.send_message создателю (creator_id)
    found = False
    for call in mock_bot.send_message.call_args_list:
        c_id = call.kwargs.get("chat_id") or (call.args[0] if call.args else None)
        text = call.kwargs.get("text", "") or (call.args[1] if len(call.args) > 1 else "")
        if c_id == creator_id and "заявка на участие" in text.lower():
            found = True
            break
    assert found, f"Организатор {creator_id} не получил уведомление. Вызовы: {mock_bot.send_message.call_args_list}"

@pytest.mark.asyncio
async def test_audit_resolution_notifies_participant(db_setup, mock_bot):
    """
    Тест Case 4: Одобрение заявки админом уведомляет участника о результате. [PL-5.1.13]
    """
    admin_id = 999
    applicant_id = 888
    
    db.add_user(admin_id, "Admin", "User")
    db.add_user(applicant_id, "Applicant", "User")
    event_id = db.create_event("Big Expedition", "2026-05-01", None, admin_id, is_approved=1)
    
    # 1. Подаем заявку (Manual DB Entry to isolate audit logic)
    req_id = db.create_audit_request(applicant_id, "event_participation", event_id)
    
    # 2. Одобряем заявку через ManagementService (как это делает админ)
    # resolve_request(bot, request_id, status, comment=None)
    success, msg = await ManagementService.resolve_request(mock_bot, req_id, "approved", "Welcome!")
    assert success
    
    # 3. Проверяем уведомление участнику [PL-5.1.13]
    # Должен быть вызов bot.send_message(applicant_id, ...)
    found = False
    for call in mock_bot.send_message.call_args_list:
        if call.kwargs.get("chat_id") == applicant_id:
            text = call.kwargs.get("text").lower()
            if "запись на мероприятие" in text and "big expedition" in text and "одобрена" in text:
                found = True
                break
    assert found, "Участник не получил корректное уведомление об одобрении"
