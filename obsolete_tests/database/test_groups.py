import pytest
from database import groups, members, topics, permissions

def test_group_lifecycle():
    g_id = groups.create_group("Test Group")
    assert g_id > 0
    assert groups.get_group_name(g_id) == "Test Group"
    
    groups.delete_group(g_id)
    assert groups.get_group_name(g_id) == "Неизвестная группа"

def test_group_topic_linking():
    g_id = groups.create_group("G1")
    t_id = 10
    topics.update_topic_name(t_id, "T1")
    
    assert groups.add_topic_to_group(g_id, t_id) is True
    assert t_id in groups.get_topics_of_group(g_id)
    assert "G1" in groups.get_groups_by_topic(t_id)
    
    groups.remove_topic_from_group(g_id, t_id)
    assert t_id not in groups.get_topics_of_group(g_id)

def test_group_template_membership():
    u_id = 100
    g_id = groups.create_group("Template Group")
    members.add_user(u_id, "U", "1")
    
    assert groups.add_to_group_template(g_id, u_id) is True
    members_list = groups.get_group_template_members(g_id)
    assert u_id in members_list
    
    groups.remove_from_group_template(g_id, u_id)
    assert u_id not in groups.get_group_template_members(g_id)

def test_batch_group_helpers():
    u_id = 101
    g_id = groups.create_group("Batch G")
    t_id = 77
    topics.update_topic_name(t_id, "T77") # Register topic to satisfy FK
    members.add_user(u_id, "B", "1")
    assert groups.add_to_group_template(g_id, u_id) is True
    assert groups.add_topic_to_group(g_id, t_id) is True
    
    # Test get_user_group_membership_ids
    m_ids = groups.get_user_group_membership_ids(u_id)
    assert g_id in m_ids
    
    # Test get_group_ids_by_topic
    gt_ids = groups.get_group_ids_by_topic(t_id)
    assert g_id in gt_ids
