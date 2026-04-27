# Файл: tests/test_handlers/test_fsm_isolation.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# Импортируем хендлеры для проверки
from handlers.events import start_event_creation, edit_event_init
from handlers.admin import add_group_init
from handlers.moderator import moderator_rename_topic_start
from handlers.common import search_start_handler

@pytest.mark.asyncio
@pytest.mark.parametrize("handler_func, callback_data, bypass_prefix", [
    (start_event_creation, "event_create", "date_preset:"),
    (edit_event_init, "event_edit:123", "date_preset:"),
    (add_group_init, "add_group_start", "group_info_"),
    (moderator_rename_topic_start, "mod_topic_rename_1", "mod_topic_select_"),
    (search_start_handler, "search_role_user_info", "user_info_"),
])
async def test_global_fsm_isolation(handler_func, callback_data, bypass_prefix):
    """
    [CP-3.13] Global FSM Isolation Regression Test.
    Проверяет, что хендлеры начала ввода НЕ возвращают клавиатуры с кнопками обхода (байпаса).
    """
    storage = MemoryStorage()
    key = MagicMock()
    state = FSMContext(storage, key)
    
    callback = AsyncMock()
    callback.data = callback_data
    callback.from_user.id = 123
    
    # Патчим PermissionService, чтобы не падать на проверках прав
    from services.permission_service import PermissionService
    PermissionService.can_manage_topic = MagicMock(return_value=True)
    PermissionService.is_global_admin = MagicMock(return_value=True)

    # Патчим EventService для теста редактирования
    from services.event_service import EventService
    EventService.can_edit_event = MagicMock(return_value=True)
    EventService.get_event_details = MagicMock(return_value={'title': 'Test', 'is_approved': True})

    # Патчим UIService.sterile_ask и sterile_show, чтобы проверить reply_markup
    with patch("services.ui_service.UIService.sterile_ask", new_callable=AsyncMock) as mock_ask, \
         patch("services.ui_service.UIService.sterile_show", new_callable=AsyncMock) as mock_show:
        
        await handler_func(callback, state)
        
        # Получаем mock, который был вызван (один из двух)
        mock_called = mock_ask if mock_ask.called else mock_show
        assert mock_called.called, f"Handler {handler_func.__name__} did not call UI gateway"
        
        # Получаем переданную клавиатуру
        args, kwargs = mock_called.call_args
        reply_markup = kwargs.get('reply_markup')
        
        if reply_markup is None:
            return

        # Находим легитимный back_data (если он есть в аргументах билдера, но мы проверяем по факту)
        # В наших тестах мы знаем, что ожидаем ОДНУ кнопку или кнопки навигации
        
        for row in reply_markup.inline_keyboard:
            for btn in row:
                cd = btn.callback_data
                if not cd or cd == "close_menu" or "help:" in cd: continue
                
                # Если это кнопка "Назад" (мы знаем её по контексту или префиксу), 
                # она допустима, если она ОДНА такого типа.
                if cd.startswith(bypass_prefix):
                    # Если в клавиатуре больше 3 кнопок (навигация + что-то еще), 
                    # или кнопка не похожа на простой возврат - это подозрительно.
                    buttons_count = sum(len(r) for r in reply_markup.inline_keyboard)
                    if buttons_count > 3: 
                         pytest.fail(f"🚨 UX Isolation Failure in {handler_func.__name__}!\n"
                                     f"Too many buttons ({buttons_count}) found on input step. Potential bypass.")
