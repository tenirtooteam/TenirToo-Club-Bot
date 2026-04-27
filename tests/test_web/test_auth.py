# Файл: tests/test_web/test_auth.py
import pytest
import hmac
import hashlib
import urllib.parse
from web.auth import validate_webapp_init_data
from config import BOT_TOKEN

def test_validate_webapp_init_data_success():
    # Имитируем корректные данные от Telegram
    user_data = '{"id":12345,"first_name":"Test"}'
    auth_date = "1714220000"
    
    # Собираем строку для хэширования (без hash)
    # Ключи должны быть отсортированы по алфавиту
    check_data = f"auth_date={auth_date}\nuser={user_data}"
    
    # Вычисляем хэш
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, check_data.encode(), hashlib.sha256).hexdigest()
    
    # Финальная строка запроса
    init_data = f"auth_date={auth_date}&user={urllib.parse.quote(user_data)}&hash={computed_hash}"
    
    result = validate_webapp_init_data(init_data)
    
    assert result is not None
    assert result["auth_date"] == auth_date
    assert "user" in result

def test_validate_webapp_init_data_fail():
    # Некорректный хэш
    init_data = "auth_date=123&user=abc&hash=wrong_hash"
    assert validate_webapp_init_data(init_data) is None

def test_validate_webapp_init_data_empty():
    assert validate_webapp_init_data("") is None
