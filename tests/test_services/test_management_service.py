import pytest
from unittest.mock import MagicMock
from aiogram.types import User
from services.management_service import ManagementService
from database import db

def test_parse_and_validate_id():
    # Валидный ID
    val, err = ManagementService._parse_and_validate_id("12345")
    assert val == 12345
    assert err == ""
    
    # Не число
    val, err = ManagementService._parse_and_validate_id("abc")
    assert err == "SEARCH_REQUIRED"
    
    # Слишком длинное число
    val, err = ManagementService._parse_and_validate_id("999999999999999999999999999")
    assert "слишком длинный" in err

@pytest.mark.asyncio
async def test_ensure_user_registered():
    user = MagicMock(spec=User)
    user.id = 999
    user.first_name = "Test"
    user.last_name = "User"
    
    # Если юзер не существует
    await ManagementService.ensure_user_registered(user)
    assert db.user_exists(999) is True
    assert db.get_user_name(999) == "Test User"

def test_add_user_validation():
    # Ошибка формата
    ok, msg = ManagementService.add_user("123 Ivan")
    assert ok is False
    assert "Формат" in msg
    
    # Валидное добавление
    ok, msg = ManagementService.add_user("888 Petr Petrov")
    assert ok is True
    assert db.user_exists(888) is True

def test_create_group():
    # Пустое имя
    ok, msg = ManagementService.create_group("  ")
    assert ok is False
    
    # Слишком длинное имя
    ok, msg = ManagementService.create_group("A" * 100)
    assert ok is False
    
    # Успех
    ok, msg = ManagementService.create_group("New Group")
    assert ok is True
    assert any(g[1] == "New Group" for g in db.get_all_groups())

def test_execute_deletion():
    # Удаление группы
    g_id = db.create_group("To Delete")
    ok, msg, next_cb = ManagementService.execute_deletion("group_del", g_id)
    assert ok is True
    assert next_cb == "manage_groups"
    assert db.get_group_name(g_id) == "Неизвестная группа"
    
    # Удаление пользователя
    u_id = 7777
    db.add_user(u_id, "Del", "Me")
    ok, msg, next_cb = ManagementService.execute_deletion("user_del", u_id)
    assert ok is True
    assert db.user_exists(u_id) is False
