import pytest
from database import members

def test_add_user_and_exists():
    user_id = 1
    fname = "Ivan"
    lname = "Ivanov"
    
    # Добавление
    assert members.add_user(user_id, fname, lname) is True
    assert members.user_exists(user_id) is True
    
    # Повторное добавление (должно вернуть False из-за UNIQUE/IntegrityError)
    assert members.add_user(user_id, fname, lname) is False

def test_update_user_name():
    user_id = 2
    members.add_user(user_id, "Old", "Name")
    
    members.update_user_name(user_id, "New", "Name")
    assert members.get_user_name(user_id) == "New Name"

def test_delete_user():
    user_id = 3
    members.add_user(user_id, "To", "Delete")
    assert members.user_exists(user_id) is True
    
    members.delete_user(user_id)
    assert members.user_exists(user_id) is False

def test_get_all_users_sorting():
    # Очистка не нужна, так как фикстура создает новую БД для каждого теста (если она function scoped)
    # Но наша фикстура mock_db_path имеет autouse=True и область видимости по умолчанию (function).
    
    members.add_user(101, "Zaira", "Alieva")
    members.add_user(102, "Almaz", "Bakirov")
    
    users = members.get_all_users()
    # Сортировка по имени (A-Z)
    assert users[0][1] == "Almaz"
    assert users[1][1] == "Zaira"

def test_find_users_by_query():
    members.add_user(201, "Алексей", "Петров")
    members.add_user(202, "Иван", "Иванов")
    members.add_user(203, "Петр", "Алексеев")
    
    # Поиск по части имени
    results = members.find_users_by_query("алекс")
    assert len(results) == 2  # Алексей и Алексеев
    
    # Поиск по имени и фамилии
    results = members.find_users_by_query("иван иванов")
    assert len(results) == 1
    assert results[0][0] == 202
    
    # Тест на регистронезависимость кириллицы (ВАЖНО)
    results = members.find_users_by_query("ИВАН")
    assert len(results) == 1
    assert results[0][0] == 202

    results = members.find_users_by_query("пЕТРОВ")
    assert len(results) == 1
    assert results[0][0] == 201

    # Пустой запрос
    assert members.find_users_by_query("") == []
