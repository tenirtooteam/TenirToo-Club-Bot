import pytest
from unittest.mock import patch
from database import roles, members, topics

def test_grant_and_revoke_role():
    u_id = 301
    members.add_user(u_id, "Role", "User")
    r_id = roles.get_role_id("admin")
    
    assert roles.grant_role(u_id, r_id) is True
    # Повторное назначение той же роли
    assert roles.grant_role(u_id, r_id) is False
    
    assert roles.is_global_admin(u_id) is True
    
    assert roles.revoke_role(u_id, r_id) is True
    assert roles.is_global_admin(u_id) is False

def test_moderator_role():
    u_id = 302
    t_id = 33
    members.add_user(u_id, "Mod", "User")
    topics.update_topic_name(t_id, "Mod Topic")
    r_id = roles.get_role_id("moderator")
    
    assert roles.grant_role(u_id, r_id, t_id) is True
    assert roles.is_moderator_of_topic(u_id, t_id) is True
    
    mods = roles.get_moderators_of_topic(t_id)
    assert len(mods) == 1
    assert mods[0][0] == u_id

def test_virtual_superadmin():
    admin_id = 777
    with patch("config.ADMIN_ID", admin_id):
        # Пользователь не в БД, но в конфиге он админ
        user_roles = roles.get_user_roles(admin_id)
        assert any(r[0] == 'superadmin' for r in user_roles)
        
        # Если он уже есть в БД с другой ролью, superadmin все равно должен добавиться
        members.add_user(admin_id, "Real", "Admin")
        topics.register_topic_if_not_exists(1) # Создаем топик для FK
        r_id = roles.get_role_id("moderator")
        assert roles.grant_role(admin_id, r_id, 1) is True
        
        user_roles = roles.get_user_roles(admin_id)
        role_names = [r[0] for r in user_roles]
        assert "superadmin" in role_names
        assert "moderator" in role_names
