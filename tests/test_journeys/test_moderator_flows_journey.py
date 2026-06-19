# -*- coding: utf-8 -*-
import pytest
from unittest.mock import AsyncMock, patch
from database import db
from handlers.moderator import (
    moderator_rename_topic_start,
    moderator_rename_topic_finish,
    moderator_link_group,
    moderator_remove_group_init,
    moderator_toggle_direct_access,
    moderator_add_moderator_start
)
from handlers.common import confirm_execution
from services.management_service import ManagementService
from services.permission_service import PermissionService

@pytest.mark.asyncio
async def test_moderator_topic_rename_journey(db_setup, mock_bot, user_session):
    # 1. Setup moderator user and a topic they manage
    mod_id = 445566
    topic_id = 20
    db.add_user(mod_id, "Mod", "User")
    db.update_topic_name(topic_id, "Old Topic Name")
    db.grant_role(mod_id, db.get_role_id("moderator"), topic_id=topic_id)

    session = user_session(user_id=mod_id, chat_id=mod_id)

    # 2. Start FSM topic rename
    await session.send_callback(
        handler=moderator_rename_topic_start,
        callback_data=f"mod_topic_rename_{topic_id}"
    )

    state = await session.state.get_state()
    assert state == "ModeratorStates:waiting_for_topic_name"

    # 3. Enter new topic name
    await session.send_message(
        handler=moderator_rename_topic_finish,
        text="Peak Pobeda"
    )

    # Verify database updated
    assert db.get_topic_name(topic_id) == "Peak Pobeda"

    # 4. Scoped access check: another user with no rights tries to rename topic 20
    normal_id = 778899
    db.add_user(normal_id, "Normal", "User")
    session_normal = user_session(user_id=normal_id, chat_id=normal_id)

    # The handler checks can_manage_topic. If it returns False, it answers callback with alert.
    # Because of IsTopicManager filter, the handler won't even be called since normal user manages 0 topics.
    # But let's verify PermissionService directly to be absolutely sure:
    assert not PermissionService.can_manage_topic(normal_id, topic_id)


@pytest.mark.asyncio
async def test_moderator_template_group_journey(db_setup, mock_bot, user_session):
    mod_id = 445566
    topic_id = 20
    db.add_user(mod_id, "Mod", "User")
    db.update_topic_name(topic_id, "My Topic")
    db.grant_role(mod_id, db.get_role_id("moderator"), topic_id=topic_id)

    # Create group template
    ManagementService.create_group("Alpinists")
    groups = db.get_all_groups()
    group_id = groups[0][0]

    session = user_session(user_id=mod_id, chat_id=mod_id)

    # 1. Link group to topic
    await session.send_callback(
        handler=moderator_link_group,
        callback_data=f"mod_gr_link_{group_id}_{topic_id}"
    )

    # Verify group is linked to topic in DB
    group_ids = db.get_group_ids_by_topic(topic_id)
    assert group_id in group_ids

    # 2. Initiate group unlink
    await session.send_callback(
        handler=moderator_remove_group_init,
        callback_data=f"mod_group_remove_{group_id}_{topic_id}"
    )

    # Check confirmation KB was sent
    calls = mock_bot.mock_calls
    assert len(calls) > 0

    # 3. Confirm unlink
    # Format for confirmation: confirm_exe_mod_topic_del:{topic_id}:{group_id}
    await session.send_callback(
        handler=confirm_execution,
        callback_data=f"confirm_exe_mod_topic_del:{topic_id}:{group_id}"
    )

    # Verify group is unlinked in DB
    group_ids = db.get_group_ids_by_topic(topic_id)
    assert group_id not in group_ids


@pytest.mark.asyncio
async def test_moderator_direct_access_and_mod_assign_journey(db_setup, mock_bot, user_session):
    mod_id = 445566
    topic_id = 20
    target_id = 999000
    db.add_user(mod_id, "Mod", "User")
    db.add_user(target_id, "Target", "User")
    db.update_topic_name(topic_id, "Peak Lenin")
    db.grant_role(mod_id, db.get_role_id("moderator"), topic_id=topic_id)

    # Grant direct access to mod first, so the topic is recognized as "restricted" 
    # instead of fallback "public" (which considers all users as group-authorized)
    db.grant_direct_access(mod_id, topic_id)

    session = user_session(user_id=mod_id, chat_id=mod_id)

    # Verify user does not have access initially
    assert not db.can_write(target_id, topic_id)

    # 1. Grant direct access
    await session.send_callback(
        handler=moderator_toggle_direct_access,
        callback_data=f"mod_tgl_dir_{target_id}_{topic_id}"
    )

    # Verify access granted in DB
    assert db.can_write(target_id, topic_id)

    # 2. Revoke direct access
    await session.send_callback(
        handler=moderator_toggle_direct_access,
        callback_data=f"mod_tgl_dir_{target_id}_{topic_id}"
    )

    # Verify access revoked in DB
    assert not db.can_write(target_id, topic_id)

    # 3. Start assigning another moderator to this topic
    await session.send_callback(
        handler=moderator_add_moderator_start,
        callback_data=f"mod_moderator_add_{topic_id}"
    )

    # Assert search FSM is active
    state = await session.state.get_state()
    assert state == "SearchStates:waiting_for_query"
    
    # Assert search config carries topic context
    data = await session.state.get_data()
    assert data.get("search_type") == "user"
    assert data.get("search_action") == "mod_add"
    assert data.get("search_context") == topic_id
