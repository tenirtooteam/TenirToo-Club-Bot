import pytest
from unittest.mock import AsyncMock, patch
from database import db
from handlers.events import start_event_creation, process_event_title, process_event_dates, process_date_confirm

@pytest.mark.asyncio
async def test_event_creation_journey_via_simulator(db_setup, mock_bot, user_session):
    # 1. Готовим пользователя в БД
    user_id = 12345
    db.add_user(user_id, "Иван", "Иванов")

    # Инициализируем симулятор сессии для пользователя
    session = user_session(user_id=user_id, chat_id=user_id)

    # 2. Шаг 1: Клик по кнопке "Создать мероприятие"
    await session.send_callback(
        handler=start_event_creation,
        callback_data="event_create"
    )

    # Проверяем, что бот перешел в стейт waiting_for_title
    current_state = await session.state.get_state()
    assert current_state == "EventCreation:waiting_for_title"

    # 3. Шаг 2: Ввод названия мероприятия
    await session.send_message(
        handler=process_event_title,
        text="Поход на Пик Учитель"
    )

    # Проверяем переход в стейт waiting_for_dates
    current_state = await session.state.get_state()
    assert current_state == "EventCreation:waiting_for_dates"

    # Проверяем сохраненные данные в FSM
    fsm_data = await session.state.get_data()
    assert fsm_data["title"] == "Поход на Пик Учитель"

    # 4. Шаг 3: Ввод даты текстом
    # Чтобы дата 15 мая распарсилась корректно в тестах без падения из-за года,
    # мы можем ввести ISO-формат типа "2026-05-15", который парсится однозначно.
    await session.send_message(
        handler=process_event_dates,
        text="2026-05-15"
    )

    # Проверяем переход в стейт confirm_date
    current_state = await session.state.get_state()
    assert current_state == "EventCreation:confirm_date"

    fsm_data = await session.state.get_data()
    assert fsm_data["dates"] == "2026-05-15"
    assert fsm_data["start_iso"] == "2026-05-15"
    assert fsm_data["end_iso"] is None

    # 5. Шаг 4: Клик по кнопке "Один день" (date_confirm)
    # Нам нужно запатчить уведомления, чтобы они не падали на отправке
    with patch("services.event_service.EventService.notify_admins_for_approval", new_callable=AsyncMock) as mock_notify:
        await session.send_callback(
            handler=process_date_confirm,
            callback_data="date_confirm:2026-05-15:one"
        )

        # Проверяем отправку уведомления
        mock_notify.assert_called_once()

    # Проверяем сброс стейта
    current_state = await session.state.get_state()
    assert current_state is None

    # 6. Проверяем, что ивент успешно создан в БД
    db.get_active_events()
    pending_events = db.get_pending_events()

    # Т.к. ивент создается неодобренным (is_approved=0), он должен быть в pending
    assert len(pending_events) == 1
    event = pending_events[0]
    assert event.title == "Поход на Пик Учитель"
    assert event.start_date == "2026-05-15"
    assert event.creator_id == user_id

    # Проверяем, что создатель автоматически добавлен в лидеры и участники [CP-3.48]
    details = db.get_event_details(event.id)
    assert user_id in details.leads
    assert user_id in details.participants

    # Проверяем, что была создана заявка на аудит
    pending_audit_ids = db.get_pending_requests_by_type("event_approval", event.id)
    assert len(pending_audit_ids) == 1

    audit_req = db.get_audit_request(pending_audit_ids[0])
    assert audit_req.user_id == user_id
    assert audit_req.entity_id == event.id
    assert audit_req.entity_type == "event_approval"
    assert audit_req.status == "pending"
