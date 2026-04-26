# Файл: tests/test_handlers/test_event_fsm.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from handlers.events import edit_event_init, process_editing_title, process_editing_dates, EventCreation
from database import db

@pytest.mark.asyncio
async def test_event_edit_full_flow():
    """Тест полного цикла редактирования ивента через FSM."""
    # 1. Setup
    db.init_db()
    db.add_user(123, "Editor", "")
    event_id = db.create_event("Old Title", "Old Dates", None, 123)
    db.approve_event(event_id)
    db.add_event_lead(event_id, 123)

    storage = MemoryStorage()
    key = MagicMock()
    state = FSMContext(storage, key)
    
    # --- ШАГ 1: Инициализация редактирования ---
    callback = AsyncMock()
    callback.data = f"event_edit:{event_id}"
    callback.from_user.id = 123
    
    await edit_event_init(callback, state)
    
    # Проверяем переход в первый стейт
    current_state = await state.get_state()
    assert current_state == EventCreation.editing_title.state
    
    data = await state.get_data()
    assert data['edit_event_id'] == event_id

    # --- ШАГ 2: Ввод названия ---
    message = AsyncMock()
    message.text = "New Shiny Title"
    message.from_user.id = 123
    
    await process_editing_title(message, state)
    
    # Проверяем переход во второй стейт
    current_state = await state.get_state()
    assert current_state == EventCreation.editing_dates.state
    
    data = await state.get_data()
    assert data['new_title'] == "New Shiny Title"

    # --- ШАГ 3: Ввод дат ---
    message.text = "25-30 декабря"
    
    # Мокаем БД для проверки мутации (или проверяем реальную БД, т.к. она в памяти/файле)
    await process_editing_dates(message, state)
    
    # Проверяем, что стейт очищен
    current_state = await state.get_state()
    assert current_state is None
    
    # Проверяем финальный результат в БД
    updated_event = db.get_event_details(event_id)
    assert updated_event['title'] == "New Shiny Title"
    assert updated_event['start_date'] == "25-30 декабря"
