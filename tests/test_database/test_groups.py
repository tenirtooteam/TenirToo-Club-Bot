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

def test_user_group_access():
    u_id = 100
    g_id = groups.create_group("Access Group")
    members.add_user(u_id, "U", "1")
    
    assert groups.grant_group(u_id, g_id) is True
    user_groups = groups.get_user_groups(u_id)
    assert any(g[0] == g_id for g in user_groups)
    
    groups.revoke_group(u_id, g_id)
    assert not any(g[0] == g_id for g in groups.get_user_groups(u_id))

def test_get_user_available_topics():
    u_id = 500
    members.add_user(u_id, "U", "500")
    
    # Сценарий 1: Доступ через группу
    g_id = groups.create_group("G500")
    t1 = 501
    topics.update_topic_name(t1, "T501")
    groups.add_topic_to_group(g_id, t1)
    groups.grant_group(u_id, g_id)
    
    # Сценарий 2: Прямой доступ
    t2 = 502
    topics.update_topic_name(t2, "T502")
    permissions.grant_direct_access(u_id, t2)
    
    available = groups.get_user_available_topics(u_id)
    # Должно быть 2 топика: 501 и 502
    ids = [a[0] for a in available]
    assert t1 in ids
    assert t2 in ids
    assert len(available) == 2
