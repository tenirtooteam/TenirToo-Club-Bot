# -*- coding: utf-8 -*-
import pytest
from database import db
from handlers.admin import add_user_init, process_user_add, user_rename_init, process_user_rename, user_delete_init
from handlers.common import confirm_execution
from services.management_service import ManagementService
import config

@pytest.mark.asyncio
async def test_admin_user_crud_journey(db_setup, mock_bot, user_session):
    admin_id = config.ADMIN_ID
    db.add_user(admin_id, "Admin", "User")
    db.grant_role(admin_id, db.get_role_id("admin"))

    session = user_session(user_id=admin_id, chat_id=admin_id)

    # 1. Add User (Start FSM)
    await session.send_callback(
        handler=add_user_init,
        callback_data="add_user_start"
    )

    # Assert state changed to waiting_for_user_data
    state = await session.state.get_state()
    assert state == "AdminStates:waiting_for_user_data"

    # Input User Data
    await session.send_message(
        handler=process_user_add,
        text="112233 Elon Musk"
    )

    # Verify user created in DB
    assert db.user_exists(112233)
    assert db.get_user_name(112233) == "Elon Musk"

    # 2. Rename User
    await session.send_callback(
        handler=user_rename_init,
        callback_data="user_rename_112233"
    )

    # Assert state changed to waiting_for_new_name
    state = await session.state.get_state()
    assert state == "AdminStates:waiting_for_new_name"

    # Input New Name
    await session.send_message(
        handler=process_user_rename,
        text="Elon Gates"
    )

    # Verify name updated in DB
    assert db.get_user_name(112233) == "Elon Gates"

    # 3. Delete User
    await session.send_callback(
        handler=user_delete_init,
        callback_data="user_delete_112233"
    )

    # Confirm Deletion
    await session.send_callback(
        handler=confirm_execution,
        callback_data="confirm_exe_user_del:112233:0"
    )

    # Verify user deleted from DB
    assert not db.user_exists(112233)


@pytest.mark.asyncio
async def test_admin_template_sync_journey(db_setup, mock_bot, user_session):
    # Setup test users and topics
    user_id = 9911
    topic_id = 77
    db.add_user(user_id, "Mark", "Zuckerberg")
    db.update_topic_name(topic_id, "Meta Topic")

    # Ensure topic is restricted to test template behavior
    # (can_write will look at direct access which we sync)
    # 1. Create template group
    success, text = ManagementService.create_group("Dev Team")
    assert success
    
    # Retrieve dynamic group ID
    groups = db.get_all_groups()
    group_id = groups[0][0] # first group id
    
    # Add user to template group
    db.add_to_group_template(group_id, user_id)
    
    # Link topic to group template
    db.add_topic_to_group(group_id, topic_id)

    # 2. Sync group to topic (applies permissions)
    success, msg = ManagementService.sync_group_to_topic(group_id, topic_id)
    assert success

    # Verify user has access to topic now
    assert db.can_write(user_id, topic_id)
