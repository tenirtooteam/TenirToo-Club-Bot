import pytest
from database import permissions, members, topics, groups

def test_direct_access():
    u_id = 401
    t_id = 40
    members.add_user(u_id, "Direct", "User")
    topics.update_topic_name(t_id, "T40")
    
    assert permissions.grant_direct_access(u_id, t_id) is True
    assert permissions.has_direct_access(u_id, t_id) is True
    assert permissions.can_write(u_id, t_id) is True
    
    permissions.revoke_direct_access(u_id, t_id)
    assert permissions.has_direct_access(u_id, t_id) is False

def test_topic_restriction_logic():
    t_id = 50
    topics.update_topic_name(t_id, "T50")
    
    # Изначально публичный
    assert permissions.is_topic_restricted(t_id) is False
    
    # В новой модели привязка к группе-шаблону НЕ делает топик ограниченным
    g_id = groups.create_group("G50")
    groups.add_topic_to_group(g_id, t_id)
    assert permissions.is_topic_restricted(t_id) is False
    
    # Ограничиваем через прямой доступ
    members.add_user(999, "Foreign", "Key") # Создаем юзера для FK
    assert permissions.grant_direct_access(999, t_id) is True
    assert permissions.is_topic_restricted(t_id) is True


def test_get_topic_authorized_users():
    t_id = 60
    u1, u2, u3 = 601, 602, 603
    members.add_user(u1, "A", "1")
    members.add_user(u2, "B", "1")
    members.add_user(u3, "C", "1")
    topics.update_topic_name(t_id, "T60")
    
    # Публичный топик -> все юзеры (3)
    auth_users = permissions.get_topic_authorized_users(t_id)
    assert len(auth_users) == 3
    
    # Ограничиваем: только u2 напрямую
    # Наличие топика в группе G60 само по себе доступ не меняет
    g_id = groups.create_group("G60")
    groups.add_topic_to_group(g_id, t_id)
    permissions.grant_direct_access(u2, t_id)
    
    auth_users = permissions.get_topic_authorized_users(t_id)
    assert len(auth_users) == 1
    ids = [u[0] for u in auth_users]
    assert u2 in ids
    assert u1 not in ids
