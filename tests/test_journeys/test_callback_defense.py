# US4 (feature 006): deletion/grant callbacks must re-check authority server-side (defense-in-depth).
# R-PROC-3 reproduces FR-009/FR-010; negative path required by R-TEST-3.
import pytest
from unittest.mock import patch, AsyncMock
import config
from database import db
from handlers.common import confirm_execution, perform_search_pick

NON_ADMIN = 222
TOPIC_ID = 555


# --- confirm_execution (FR-009) ---

@pytest.mark.asyncio
async def test_confirm_execution_denies_non_admin(create_callback):
    """A non-admin must not be able to execute a confirmed user deletion."""
    callback, state = await create_callback(user_id=NON_ADMIN, data="confirm_exe_user_del:333:0")
    with patch("services.management_service.ManagementService.execute_deletion") as mock_del, \
         patch("services.ui_service.UIService.generic_navigator", new_callable=AsyncMock), \
         patch("aiogram.types.CallbackQuery.answer", new_callable=AsyncMock) as mock_answer:
        await confirm_execution(callback, state)
    mock_del.assert_not_called()
    mock_answer.assert_awaited()
    _, kwargs = mock_answer.call_args
    assert kwargs.get("show_alert") is True


@pytest.mark.asyncio
async def test_confirm_execution_allows_admin(create_callback):
    """A global admin still executes the deletion (regression guard)."""
    callback, state = await create_callback(user_id=config.ADMIN_ID, data="confirm_exe_user_del:333:0")
    with patch("services.management_service.ManagementService.execute_deletion",
               return_value=(True, "ok", "manage_users")) as mock_del, \
         patch("services.ui_service.UIService.generic_navigator", new_callable=AsyncMock), \
         patch("aiogram.types.CallbackQuery.answer", new_callable=AsyncMock):
        await confirm_execution(callback, state)
    mock_del.assert_called_once()


# --- perform_search_pick grants (FR-010) ---

@pytest.mark.asyncio
async def test_search_pick_mod_add_denies_non_manager(create_callback):
    """A non-manager must not be able to appoint a moderator via search-pick."""
    db.register_topic_if_not_exists(TOPIC_ID)
    db.add_user(NON_ADMIN, "A", "B")
    callback, state = await create_callback(user_id=NON_ADMIN, data="pick")
    with patch("services.management_service.ManagementService.assign_moderator_role_by_id") as mock_assign, \
         patch("services.ui_service.UIService.sterile_show", new_callable=AsyncMock), \
         patch("aiogram.types.CallbackQuery.answer", new_callable=AsyncMock) as mock_answer:
        await perform_search_pick(state, callback, "user", "mod_add", str(TOPIC_ID), 333)
    mock_assign.assert_not_called()
    mock_answer.assert_awaited()


@pytest.mark.asyncio
async def test_search_pick_dir_add_denies_non_manager(create_callback):
    """A non-manager must not be able to grant direct access via search-pick."""
    db.register_topic_if_not_exists(TOPIC_ID)
    db.add_user(NON_ADMIN, "A", "B")
    callback, state = await create_callback(user_id=NON_ADMIN, data="pick")
    with patch("services.management_service.ManagementService.grant_direct_access_by_id") as mock_grant, \
         patch("services.ui_service.UIService.sterile_show", new_callable=AsyncMock), \
         patch("aiogram.types.CallbackQuery.answer", new_callable=AsyncMock):
        await perform_search_pick(state, callback, "user", "dir_add", str(TOPIC_ID), 333)
    mock_grant.assert_not_called()


@pytest.mark.asyncio
async def test_search_pick_mod_add_allows_admin(create_callback):
    """A global admin still appoints a moderator (regression guard)."""
    db.register_topic_if_not_exists(TOPIC_ID)
    callback, state = await create_callback(user_id=config.ADMIN_ID, data="pick")
    with patch("services.management_service.ManagementService.assign_moderator_role_by_id",
               return_value=(True, "ok")) as mock_assign, \
         patch("services.ui_service.UIService.sterile_show", new_callable=AsyncMock), \
         patch("services.ui_service.UIService.clear_fsm_data_safely", new_callable=AsyncMock):
        await perform_search_pick(state, callback, "user", "mod_add", str(TOPIC_ID), 333)
    mock_assign.assert_called_once()
