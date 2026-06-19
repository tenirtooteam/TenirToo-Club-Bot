# tests/test_journeys/test_ux_journeys.py
import pytest
import time
from unittest.mock import AsyncMock, patch
from aiogram import types
from aiogram.fsm.context import FSMContext

# We expect these imports to fail initially (TDD baseline check)
try:
    from middlewares.fsm_button_guard import FsmButtonGuardMiddleware
except ImportError:
    FsmButtonGuardMiddleware = None

from services.notification_service import NotificationService
from handlers.common import close_menu_handler
from services.ui_service import UIService


@pytest.mark.asyncio
async def test_fsm_button_guard_deletes_outdated_buttons(create_callback, mock_bot):
    """
    TDD Test: Verify that callback queries from obsolete messages are deleted 
    and block handler execution when FSM is active.
    """
    if FsmButtonGuardMiddleware is None:
        pytest.fail("FsmButtonGuardMiddleware is not implemented yet (Expected TDD Failure)")

    middleware = FsmButtonGuardMiddleware()
    handler = AsyncMock()

    # Create callback query from message_id 99 (obsolete message) using model_copy
    callback, state = await create_callback(chat_id=123, user_id=123, data="some_click")
    new_message = callback.message.model_copy(update={"message_id": 99})
    new_message._bot = mock_bot
    callback = callback.model_copy(update={"message": new_message})
    callback._bot = mock_bot

    # Set FSM state and track last_menu_id as 100
    await state.set_state("waiting_input")
    await state.update_data(last_menu_id=100)

    data = {"state": state}

    # Execute middleware
    await middleware(handler, callback, data)

    # Assertions:
    # 1. Handler must not be called (execution cancelled)
    handler.assert_not_called()
    # 2. Obsolete message must be deleted (checking both args and kwargs for mock assertion parity)
    mock_bot.delete_message.assert_called_once()
    call_args, call_kwargs = mock_bot.delete_message.call_args
    # Positional or keyword arguments match
    assert call_kwargs.get("chat_id") == 123 or (len(call_args) > 0 and call_args[0] == 123)
    assert call_kwargs.get("message_id") == 99 or (len(call_args) > 1 and call_args[1] == 99)


@pytest.mark.asyncio
async def test_fsm_button_guard_ignores_whitelist_and_inactive_fsm(create_callback, mock_bot):
    """
    TDD Test: Guard must pass if FSM is inactive, or callback data is in whitelist.
    """
    if FsmButtonGuardMiddleware is None:
        pytest.fail("FsmButtonGuardMiddleware is not implemented yet")

    middleware = FsmButtonGuardMiddleware()
    handler = AsyncMock()

    # Case 1: Active FSM but whitelisted callback 'landing'
    callback, state = await create_callback(chat_id=123, user_id=123, data="landing")
    new_message = callback.message.model_copy(update={"message_id": 99})
    new_message._bot = mock_bot
    callback = callback.model_copy(update={"message": new_message})
    callback._bot = mock_bot
    await state.set_state("waiting_input")
    await state.update_data(last_menu_id=100)

    await middleware(handler, callback, {"state": state})
    handler.assert_called_once()
    mock_bot.delete_message.assert_not_called()

    # Case 2: Inactive FSM
    handler.reset_mock()
    callback2, state2 = await create_callback(chat_id=123, user_id=123, data="some_click")
    new_message2 = callback2.message.model_copy(update={"message_id": 99})
    new_message2._bot = mock_bot
    callback2 = callback2.model_copy(update={"message": new_message2})
    callback2._bot = mock_bot
    await state2.set_state(None) # Inactive

    await middleware(handler, callback2, {"state": state2})
    handler.assert_called_once()


@pytest.mark.asyncio
async def test_default_deny_triggers_rate_limited_pm_alert(mock_bot, create_context):
    """
    TDD Test: AccessGuardMiddleware triggers PM alert on admin message deletion,
    and applies a 60-second rate limiter.
    """
    # Force immunity to False so global admin is moderated
    with patch("middlewares.access_check.IMMUNITY_FOR_ADMINS", False), \
         patch("services.permission_service.PermissionService.is_global_admin", return_value=True), \
         patch("services.permission_service.PermissionService.can_user_write_in_topic", return_value=False):
        
        # AccessGuardMiddleware is imported and instantiated
        from middlewares.access_check import AccessGuardMiddleware
        middleware = AccessGuardMiddleware()
        handler = AsyncMock()

        # Simulate admin message in supergroup (chat_id is negative) with thread_id=42
        _, _, message, state = await create_context(user_id=999999999, chat_id=-100123456789, chat_type="supergroup", thread_id=42)

        # 1. First trigger
        await middleware(handler, message, {"state": state})
        handler.assert_not_called() # Denied
        
        # Verify PM alert sent with Mock Assertion Parity (both args and kwargs)
        mock_bot.send_message.assert_called_once()
        args, kwargs = mock_bot.send_message.call_args
        assert kwargs.get("chat_id") == 999999999 or (len(args) > 0 and args[0] == 999999999)
        assert "Default Deny" in kwargs.get("text", "") or (len(args) > 1 and "Default Deny" in args[1])
        
        # 2. Immediate second trigger (must be rate-limited)
        mock_bot.send_message.reset_mock()
        await middleware(handler, message, {"state": state})
        mock_bot.send_message.assert_not_called() # Limited


@pytest.mark.asyncio
async def test_soft_close_creates_navigation_stub_in_pm(create_callback, mock_bot):
    """
    TDD Test: close_menu_handler in PM edits the message into a navigation stub and resets FSM.
    """
    callback, state = await create_callback(chat_id=123, user_id=123, data="close_menu")
    await state.set_state("some_state")

    await close_menu_handler(callback, state)

    # Assertions
    # 1. State is reset to None (FSM Hygiene)
    current_state = await state.get_state()
    assert current_state is None

    # 2. Message is edited into stub
    mock_bot.edit_message_text.assert_called_once()
    args, kwargs = mock_bot.edit_message_text.call_args
    assert "Интерфейс закрыт" in kwargs.get("text", "") or (len(args) > 0 and "Интерфейс закрыт" in args[0])
    
    # Inline keyboard is attached with Main Menu landing
    markup = kwargs.get("reply_markup") or (len(args) > 1 and args[1])
    assert markup is not None
    assert any(btn.callback_data == "landing" for row in markup.inline_keyboard for btn in row)


@pytest.mark.asyncio
async def test_admin_onboarding_faq_flow(create_callback, mock_bot):
    """
    TDD Test: show_admin_dashboard displays Onboarding FAQ at first, and standard dashboard after confirm.
    """
    callback, state = await create_callback(chat_id=123, user_id=123, data="landing")
    await state.update_data(admin_onboarded=False) # Not onboarded yet

    # First call - must show FAQ
    with patch("services.ui_service.UIService.sterile_show", new_callable=AsyncMock) as mock_show:
        await UIService.show_admin_dashboard(state, callback)
        mock_show.assert_called_once()
        args, kwargs = mock_show.call_args
        text_val = kwargs.get("text") or (args[2] if len(args) > 2 else "")
        assert "Sterile UI" in text_val
        # Confirm button exists
        markup = kwargs.get("reply_markup")
        assert any(btn.callback_data == "admin_confirm_onboarding" for row in markup.inline_keyboard for btn in row)

    # Simulate confirm callback
    from handlers.admin import admin_confirm_onboarding
    callback_confirm, _ = await create_callback(chat_id=123, user_id=123, data="admin_confirm_onboarding")
    
    # Mocking standard landing data rendering
    with patch("services.ui_service.UIService.show_admin_dashboard", new_callable=AsyncMock) as mock_dashboard:
        await admin_confirm_onboarding(callback_confirm, state)
        # Verify state contains admin_onboarded=True
        data = await state.get_data()
        assert data.get("admin_onboarded") is True
        mock_dashboard.assert_called_once()


@pytest.mark.asyncio
async def test_default_deny_triggers_member_pm_alert(mock_bot, create_context):
    """
    TDD Test: AccessGuardMiddleware triggers PM alert on member message deletion
    and applies rate limiting (1 hour).
    """
    with patch("middlewares.access_check.IMMUNITY_FOR_ADMINS", True), \
         patch("services.permission_service.PermissionService.is_global_admin", return_value=False), \
         patch("services.permission_service.PermissionService.can_user_write_in_topic", return_value=False):
        
        from middlewares.access_check import AccessGuardMiddleware
        middleware = AccessGuardMiddleware()
        handler = AsyncMock()

        # Simulate ordinary member message in supergroup (negative ID)
        _, _, message, state = await create_context(user_id=777777777, chat_id=-100123456789, chat_type="supergroup", thread_id=42)

        # First trigger - must send alert
        await middleware(handler, message, {"state": state})
        handler.assert_not_called() # Denied and deleted
        
        mock_bot.send_message.assert_called_once()
        args, kwargs = mock_bot.send_message.call_args
        assert kwargs.get("chat_id") == 777777777 or (len(args) > 0 and args[0] == 777777777)
        assert "Доступ ограничен" in kwargs.get("text", "") or (len(args) > 1 and "Доступ ограничен" in args[1])
        
        # Second immediate trigger - must be rate-limited (no alert sent)
        mock_bot.send_message.reset_mock()
        await middleware(handler, message, {"state": state})
        mock_bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_fsm_reset_after_group_creation(create_context, mock_bot):
    """
    TDD Test: Creating a group template successfully nullifies the FSM state.
    """
    from handlers.admin import process_group_add
    from handlers.admin import AdminStates

    _, _, message, state = await create_context(user_id=123, chat_id=123, chat_type="private", text="Спортсмены")
    await state.set_state(AdminStates.waiting_for_group_name)

    with patch("services.management_service.ManagementService.create_group", return_value=(True, "Группа создана")), \
         patch("services.ui_service.UIService.show_admin_dashboard", new_callable=AsyncMock) as mock_dashboard:
        
        await process_group_add(message, state)
        
        # FSM state must be reset to None
        curr_state = await state.get_state()
        assert curr_state is None
        mock_dashboard.assert_called_once()



@pytest.mark.asyncio
async def test_fsm_reset_after_search_pick(create_callback, mock_bot):
    """
    TDD Test: Selection in search pick handler resets FSM state, cleans up FSM data, and routes.
    """
    from handlers.common import perform_search_pick
    from handlers.common import SearchStates

    callback, state = await create_callback(chat_id=123, user_id=123, data="search_pick_user_dir_add_1")
    await state.set_state(SearchStates.waiting_for_query)
    await state.update_data(search_context=1, search_type="user", last_menu_ids=[100])

    with patch("services.management_service.ManagementService.grant_direct_access_by_id", return_value=(True, "Доступ выдан")), \
         patch("services.ui_service.UIService.sterile_show", new_callable=AsyncMock) as mock_show:
        
        await perform_search_pick(state, callback, "user", "dir_add", 1, 1)
        
        # FSM state must be reset to None
        curr_state = await state.get_state()
        assert curr_state is None
        
        # FSM custom data must be cleaned while preserving last_menu_ids
        data = await state.get_data()
        assert "search_context" not in data
        assert "search_type" not in data
        assert data.get("last_menu_ids") == [100]
        
        mock_show.assert_called_once()


@pytest.mark.asyncio
async def test_no_auto_pick_on_single_search_result(create_context, mock_bot):
    """
    TDD Test: A single search result does not auto-pick/auto-assign but renders search results markup.
    """
    from handlers.common import search_query_handler
    from handlers.common import SearchStates

    _, _, message, state = await create_context(user_id=123, chat_id=123, chat_type="private", text="Петрова")
    await state.set_state(SearchStates.waiting_for_query)
    await state.update_data(search_type="user", search_action="dir_add", search_context=1)

    # Mock search results returning 1 user
    mock_results = [(33333, "Мария Петрова")]

    with patch("services.management_service.ManagementService.search_entities", return_value=mock_results), \
         patch("services.ui_service.UIService.sterile_show", new_callable=AsyncMock) as mock_show:
         
        await search_query_handler(message, state)
        
        # Verify it did not auto-call perform_search_pick but called sterile_show to render picker keyboard
        mock_show.assert_called_once()
        args, kwargs = mock_show.call_args
        assert "Найдено вариантов: 1" in args[2] or "Найдено вариантов: 1" in kwargs.get("text", "")
        
        # State must remain waiting_for_query since user has to click explicitly
        curr_state = await state.get_state()
        assert curr_state == SearchStates.waiting_for_query

