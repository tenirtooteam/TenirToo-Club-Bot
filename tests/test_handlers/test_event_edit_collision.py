import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from handlers.events import process_date_confirm, EventCreation

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
         patch("aiogram.types.Message.edit_text", new_callable=AsyncMock), \
         patch("handlers.events.show_event_card", new_callable=AsyncMock):

        await process_date_confirm(callback, state)

        assert mock_update.called, "Должен быть вызван апдейт"
        assert not mock_create.called, "Создание не должно вызываться"

        # Проверяем аргументы (используем позиционные)
        args, _ = mock_update.call_args
        assert args[0] == 55
        assert args[1] == "Updated Title"


@pytest.mark.asyncio
async def test_date_confirm_range_create_persists_full_human(create_callback, db_setup):
    """
    BUG-1 [US1] CREATE: диапазон '10-15 июня' должен сохранить ПОЛНЫЕ human-части
    (start='10 июня', end='15 июня'), а не обрезок '10'.
    """
    callback, state = await create_callback(user_id=123, data="date_confirm:2026-06-10:2026-06-15")
    await state.set_state(EventCreation.confirm_date)
    await state.update_data(
        title="Поход",
        dates="10-15 июня",
        start_iso="2026-06-10",
        end_iso="2026-06-15",
    )

    with patch("handlers.events.ManagementService.create_event_action", MagicMock(return_value=0)) as mock_create, \
         patch("aiogram.types.CallbackQuery.answer", new_callable=AsyncMock):
        await process_date_confirm(callback, state)

    assert mock_create.called
    _, kwargs = mock_create.call_args
    assert kwargs["start_date"] == "10 июня", f"start обрезан: {kwargs['start_date']!r}"
    assert kwargs["end_date"] == "15 июня", f"end неверен: {kwargs['end_date']!r}"


@pytest.mark.asyncio
async def test_date_confirm_range_edit_persists_full_human(create_callback, db_setup):
    """
    BUG-1 [US1] EDIT: тот же диапазон при редактировании должен применить
    декомпозицию (в текущем коде ветка отбрасывала результат сплита).
    """
    callback, state = await create_callback(user_id=123, data="date_confirm:2026-06-10:2026-06-15")
    await state.set_state(EventCreation.confirm_date)
    await state.update_data(
        edit_event_id=77,
        new_title="Ред. Поход",
        dates="10-15 июня",
        start_iso="2026-06-10",
        end_iso="2026-06-15",
    )

    with patch("database.db.update_event_details") as mock_update, \
         patch("aiogram.types.Message.edit_text", new_callable=AsyncMock), \
         patch("handlers.events.show_event_card", new_callable=AsyncMock):
        await process_date_confirm(callback, state)

    assert mock_update.called
    args, _ = mock_update.call_args
    # (event_id, title, start_date, end_date, start_iso, end_iso)
    assert args[2] == "10 июня", f"start обрезан: {args[2]!r}"
    assert args[3] == "15 июня", f"end неверен: {args[3]!r}"
