import pytest
from database import db
from services.management_service import ManagementService

def test_template_mass_apply_logic():
    # Создаем шаблон и топик
    g_id = db.create_group("MassTemplate")
    t_id = 101
    db.register_topic_if_not_exists(t_id)
    
    # Добавляем 100 пользователей в шаблон
    user_ids = []
    for i in range(1, 101):
        u_id = 1000 + i
        db.add_user(u_id, f"User{i}", "")
        db.add_to_group_template(g_id, u_id)
        user_ids.append(u_id)
    
    # Применяем шаблон
    success, msg = ManagementService.apply_group_to_topic(g_id, t_id)
    assert success is True
    assert "Добавлено 100 чел" in msg
    
    # Проверяем доступ
    for u_id in user_ids:
        assert db.can_write(u_id, t_id) is True

def test_template_sync_logic():
    g_id = db.create_group("SyncTemplate")
    t_id = 102
    db.register_topic_if_not_exists(t_id)
    
    # Сначала даем прямой доступ "чужому" юзеру
    db.add_user(9999, "Legacy", "User")
    db.grant_direct_access(9999, t_id)
    assert db.can_write(9999, t_id) is True
    
    # В шаблоне только 1 новый юзер
    db.add_user(8888, "New", "User")
    db.add_to_group_template(g_id, 8888)
    
    # Синхронизируем
    success, msg = ManagementService.sync_group_to_topic(g_id, t_id)
    assert success is True
    
    # Старый юзер должен потерять доступ, новый — получить
    assert db.can_write(9999, t_id) is False
    assert db.can_write(8888, t_id) is True

def test_template_empty_sync():
    g_id = db.create_group("EmptyTemplate")
    t_id = 103
    db.register_topic_if_not_exists(t_id)
    db.add_user(111, "Target", "")
    db.grant_direct_access(111, t_id)
    
    # Синхро с ПУСТЫМ шаблоном должно очистить доступ
    success, msg = ManagementService.sync_group_to_topic(g_id, t_id)
    assert success is True
    assert db.can_write(111, t_id) is False
