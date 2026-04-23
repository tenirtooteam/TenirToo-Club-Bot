import pytest
from unittest.mock import patch
from services.permission_service import PermissionService
from database import db, topics, roles

def test_is_superadmin():
    admin_id = 123
    with patch("services.permission_service.ADMIN_ID", admin_id):
        # Совпадение ID
        assert PermissionService.is_superadmin(admin_id) is True
        # Не совпадение
        assert PermissionService.is_superadmin(456) is False

def test_is_global_admin():
    admin_id = 100
    with patch("services.permission_service.ADMIN_ID", admin_id):
        assert PermissionService.is_global_admin(admin_id) is True
        
        # Обычный юзер
        assert PermissionService.is_global_admin(200) is False
        
        # Юзер с ролью admin в БД
        db.add_user(200, "A", "D")
        r_id = db.get_role_id("admin")
        db.grant_role(200, r_id)
        assert PermissionService.is_global_admin(200) is True

def test_can_manage_topic():
    admin_id = 1
    mod_id = 2
    t_id = 10
    
    with patch("services.permission_service.ADMIN_ID", admin_id):
        topics.register_topic_if_not_exists(t_id)
        db.add_user(mod_id, "M", "O")
        r_id = db.get_role_id("moderator")
        db.grant_role(mod_id, r_id, t_id)
        
        # Админ может
        assert PermissionService.can_manage_topic(admin_id, t_id) is True
        # Модератор топика может
        assert PermissionService.can_manage_topic(mod_id, t_id) is True
        # Другой юзер не может
        assert PermissionService.can_manage_topic(999, t_id) is False

def test_can_user_write_in_topic():
    t_id = 50
    u_id = 500
    topics.register_topic_if_not_exists(t_id)
    db.add_user(u_id, "U", "5")
    
    # Публичный топик - можно всем
    assert PermissionService.can_user_write_in_topic(u_id, t_id) is True
    
    # Ограничиваем топик (выдаем прямой доступ другому юзеру)
    db.add_user(999, "X", "Y")
    db.grant_direct_access(999, t_id)
    
    # Теперь u_id не может писать
    assert PermissionService.can_user_write_in_topic(u_id, t_id) is False
    
    # Даем доступ u_id напрямую
    db.grant_direct_access(u_id, t_id)
    assert PermissionService.can_user_write_in_topic(u_id, t_id) is True
