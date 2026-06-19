# -*- coding: utf-8 -*-
import pytest
from database import db
from handlers.user import cmd_start
import config
from aiogram.methods import SendMessage, EditMessageText

@pytest.mark.asyncio
async def test_start_routing_unregistered(db_setup, mock_bot, user_session):
    user_id = 77777
    db.add_user(user_id, "TestUser", "Tester")

    session = user_session(user_id=user_id, chat_id=user_id)
    await session.send_message(handler=cmd_start, text="/start")

    calls = mock_bot.mock_calls
    assert len(calls) > 0

    sent_text = ""
    for call in calls:
        if call[0] == "":  # direct bot() call
            method_obj = call[1][0]
            if isinstance(method_obj, (SendMessage, EditMessageText)):
                sent_text = method_obj.text
                break

    # "\u0414\u043e\u0431\u0440\u043e \u043f\u043e\u0436\u0430\u043b\u043e\u0432\u0430\u0442\u044c" == "Добро пожаловать"
    assert "\u0414\u043e\u0431\u0440\u043e \u043f\u043e\u0436\u0430\u043b\u043e\u0432\u0430\u0442\u044c" in sent_text


@pytest.mark.asyncio
async def test_start_routing_admin(db_setup, mock_bot, user_session):
    admin_id = config.ADMIN_ID
    db.add_user(admin_id, "Admin", "User")
    db.grant_role(admin_id, db.get_role_id("admin"))

    session = user_session(user_id=admin_id, chat_id=admin_id)
    await session.send_message(handler=cmd_start, text="/start")

    calls = mock_bot.mock_calls
    sent_text = ""
    for call in calls:
        if call[0] == "":  # direct bot() call
            method_obj = call[1][0]
            if isinstance(method_obj, (SendMessage, EditMessageText)):
                sent_text = method_obj.text
                break

    # "\u041f\u0430\u043d\u0435\u043b\u044c \u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u044f" == "Панель управления"
    assert "\u041f\u0430\u043d\u0435\u043b\u044c \u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u044f" in sent_text


@pytest.mark.asyncio
async def test_start_routing_moderator(db_setup, mock_bot, user_session):
    mod_id = 88888
    db.add_user(mod_id, "Mod", "User")
    db.update_topic_name(10, "Test Topic")
    db.grant_role(mod_id, db.get_role_id("moderator"), topic_id=10)

    session = user_session(user_id=mod_id, chat_id=mod_id)
    await session.send_message(handler=cmd_start, text="/start")

    calls = mock_bot.mock_calls
    sent_text = ""
    for call in calls:
        if call[0] == "":  # direct bot() call
            method_obj = call[1][0]
            if isinstance(method_obj, (SendMessage, EditMessageText)):
                sent_text = method_obj.text
                break

    # "\u041f\u0430\u043d\u0435\u043b\u044c \u043c\u043e\u0434\u0435\u0440\u0430\u0442\u043e\u0440\u0430" == "Панель модератора"
    # "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0442\u043e\u043f\u0438\u043a:" == "Выберите топик:"
    assert "\u041f\u0430\u043d\u0435\u043b\u044c \u043c\u043e\u0434\u0435\u0440\u0430\u0442\u043e\u0440\u0430" in sent_text
    assert "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0442\u043e\u043f\u0438\u043a:" in sent_text


@pytest.mark.asyncio
async def test_start_routing_override_admin(db_setup, mock_bot, user_session):
    admin_id = config.ADMIN_ID
    db.add_user(admin_id, "Admin", "User")

    from services.ui_service import UIService
    text, kb_func = await UIService.get_landing_data(admin_id, role_override="admin")

    # "\u041f\u0430\u043d\u0435\u043b\u044c \u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u044f" == "Панель управления"
    assert "\u041f\u0430\u043d\u0435\u043b\u044c \u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u044f" in text
    assert kb_func is not None
