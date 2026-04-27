# Файл: tests/test_integration/test_template_operations.py
import pytest
from database import db
from services.management_service import ManagementService

@pytest.mark.asyncio
async def test_template_bulk_apply_and_sync(db_conn):
    # 1. Setup entities
    u1, u2 = 101, 102
    g_id = db.create_group("Test Template")
    t_id = 500
    db.register_topic_if_not_exists(t_id)
    db.update_topic_name(t_id, "Target Topic")
    
    db.add_user(u1, "User", "One")
    db.add_user(u2, "User", "Two")
    db.add_to_group_template(g_id, u1)
    db.add_to_group_template(g_id, u2)
    
    # 2. Test Apply
    success, msg = ManagementService.apply_group_to_topic(g_id, t_id)
    assert success is True
    authorized = [u[0] for u in db.get_direct_access_users(t_id)]
    assert u1 in authorized
    assert u2 in authorized
    
    # 3. Modify template and Sync
    db.remove_from_group_template(g_id, u1)
    success, msg = ManagementService.sync_group_to_topic(g_id, t_id)
    assert success is True
    authorized = [u[0] for u in db.get_direct_access_users(t_id)]
    assert u1 not in authorized
    assert u2 in authorized

@pytest.mark.asyncio
async def test_cascade_delete_integrity(db_conn):
    # Setup
    u_id = 201
    g_id = db.create_group("Cascade Group")
    t_id = 600
    db.register_topic_if_not_exists(t_id)
    db.update_topic_name(t_id, "Cascade Topic")
    db.add_user(u_id, "Cascade", "User")
    
    # Link everything
    db.add_to_group_template(g_id, u_id)
    db.add_topic_to_group(g_id, t_id)
    db.grant_direct_access(u_id, t_id)
    
    # Verify links exist
    assert u_id in db.get_group_template_members(g_id)
    assert t_id in db.get_topics_of_group(g_id)
    assert u_id in [u[0] for u in db.get_direct_access_users(t_id)]
    
    # Delete Topic -> Should clean group_topics and direct_topic_access
    db.delete_topic(t_id)
    assert t_id not in db.get_topics_of_group(g_id)
    # Note: direct_topic_access is linked to topic_id, so it should be empty
    assert len(db.get_direct_access_users(t_id)) == 0
    
    # Delete Group -> Should clean group_members
    db.delete_group(g_id)
    # After group deletion, members of that group template should be gone from group_members
    # (Checking via members table isn't enough, we check group_members directly via DB if possible, 
    # but get_group_template_members will return empty list)
    assert len(db.get_group_template_members(g_id)) == 0
