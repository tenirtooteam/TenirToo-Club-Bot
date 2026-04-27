import pytest
import datetime
from unittest.mock import AsyncMock, patch
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, User, Message, Chat

from handlers.events import process_date_confirm, EventCreation
from database import db

@pytest.mark.asyncio
async def test_event_edit_collision_regression(create_callback, db_setup):
    """
    Регрессионный тест для бага: Редактирование -> Кнопка даты -> Сохранение.
    Использует унифицированные фикстуры [PL-2.2.56].
    """
    # 1. Подготовка контекста через фабрику
    callback, state = await create_callback(user_id=123, data="date_confirm:2026-05-01:one")
    
    # 2. Имитируем стейт редактирования
    await state.set_state(EventCreation.editing_dates)
    await state.update_data(
        edit_event_id=55, 
        new_title="Updated Title",
        dates="2026-05-01",
        start_iso="2026-05-01"
    )
    
    # 3. Патчим только то, что специфично для логики UI
    with patch("database.db.update_event_details") as mock_update, \
         patch("database.db.create_event") as mock_create, \
         patch("aiogram.types.Message.edit_text", new_callable=AsyncMock) as mock_edit, \
         patch("handlers.events.show_event_card", new_callable=AsyncMock) as mock_card:
        
        await process_date_confirm(callback, state)
        
        assert mock_update.called, "Должен быть вызван апдейт"
        assert not mock_create.called, "Создание не должно вызываться"
        
        # Проверяем аргументы (используем позиционные)
        args, _ = mock_update.call_args
        assert args[0] == 55
        assert args[1] == "Updated Title"
