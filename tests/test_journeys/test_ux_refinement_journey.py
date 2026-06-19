# -*- coding: utf-8 -*-
import pytest
from database import db
from services.ui_service import UIService
from services.help_service import HelpService
import keyboards as kb
from handlers.moderator import moderator_toggle_direct_access

@pytest.mark.asyncio
async def test_admin_onboarding_loop_prevention(db_setup, mock_bot, create_context):
    user, chat, message, state = await create_context(user_id=111, chat_id=111)
    await state.update_data(admin_onboarded=True, some_other_key="val")

    await UIService.clear_fsm_data_safely(state)

    data = await state.get_data()
    assert data.get("admin_onboarded") is True
    assert "some_other_key" not in data


@pytest.mark.asyncio
async def test_admin_onboarding_escape_hatch(db_setup, mock_bot, create_callback):
    callback, state = await create_callback(chat_id=111, user_id=111, data="landing")
    await state.update_data(admin_onboarded=False) # Trigger onboarding

    await UIService.show_admin_dashboard(state, callback)

    # Verify mock_bot received an edit_message_text call (or EditMessageText request)
    markup = None
    for call in mock_bot.mock_calls:
        if call[0] == "":
            req = call[1][0]
            if req.__class__.__name__ == "EditMessageText":
                markup = req.reply_markup
                break
        elif call[0] == "edit_message_text":
            markup = call[2].get("reply_markup") or (call[1][1] if len(call[1]) > 1 else None)
            break

    assert markup is not None

    # Check if there is a close button
    close_button = None
    for row in markup.inline_keyboard:
        for btn in row:
            if btn.callback_data == "close_menu":
                close_button = btn
                break
    assert close_button is not None
    assert "Закрыть" in close_button.text


@pytest.mark.asyncio
async def test_search_results_back_button(db_setup):
    # Test that search_results_kb includes the back button with search_context
    results = [(1, "Test User")]
    markup = kb.search_results_kb(results, "user", "info", "my_custom_context")

    back_btn = None
    for row in markup.inline_keyboard:
        for btn in row:
            if btn.callback_data == "my_custom_context":
                back_btn = btn
                break
    assert back_btn is not None
    assert "Назад" in back_btn.text or "НАЗАД" in back_btn.text


@pytest.mark.asyncio
async def test_moderator_toggle_redirect(db_setup, mock_bot, user_session):
    mod_id = 901
    target_id = 902
    topic_id = 42

    db.add_user(mod_id, "Mod", "User")
    db.add_user(target_id, "Target", "User")
    db.update_topic_name(topic_id, "Topic name")
    db.grant_role(mod_id, db.get_role_id("moderator"), topic_id=topic_id)
    db.grant_direct_access(mod_id, topic_id)

    session = user_session(user_id=mod_id, chat_id=mod_id)

    # Trigger callback
    await session.send_callback(
        handler=moderator_toggle_direct_access,
        callback_data=f"mod_tgl_dir_{target_id}_{topic_id}"
    )

    # Safely search calls without print statements to avoid console encoding crash
    text = ""
    for call in mock_bot.mock_calls:
        if call[0] == "":
            req = call[1][0]
            if req.__class__.__name__ == "EditMessageText":
                text = req.text
                break
        elif call[0] == "edit_message_text":
            text = call[2].get("text") or (call[1][1] if len(call[1]) > 1 else "")
            break

    assert "Управление:" in text


@pytest.mark.asyncio
async def test_terminology_drift(db_setup):
    # Help text check
    help_text = HelpService.get_help("events")
    assert "Походы клуба" in help_text
    assert "Мероприятия клуба" not in help_text

    # User main menu check (Pohody button text instead of Meropriyatiya)
    markup = kb.user_main_kb()
    btn_texts = []
    for row in markup.inline_keyboard:
        for btn in row:
            btn_texts.append(btn.text)
    assert any("ПОХОДЫ" in t or "Походы" in t for t in btn_texts)
    assert not any("МЕРОПРИЯТИЯ" in t or "Мероприятия" in t for t in btn_texts)
