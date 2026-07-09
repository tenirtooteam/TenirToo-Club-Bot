# Файл: web/auth.py
import hmac
import hashlib
import time
import urllib.parse
import config
from config import BOT_TOKEN
from fastapi import Header

# Допуск на перекос часов (сессия «из будущего») [feature 006, FR-005]
_AUTH_DATE_FUTURE_SKEW = 300

def validate_webapp_init_data(init_data: str) -> dict | None:
    """
    Проверяет валидность данных инициализации Telegram WebApp [CC-3].
    Возвращает словарь с данными пользователя, если проверка прошла успешно.
    """
    if not init_data:
        return None

    try:
        vals = urllib.parse.parse_qs(init_data)
        if "hash" not in vals:
            return None

        data_hash = vals.pop("hash")[0]

        # Сортируем ключи и собираем строку для проверки
        items = sorted([(k, v[0]) for k, v in vals.items()])
        data_check_string = "\n".join([f"{k}={v}" for k, v in items])

        # Создаем секретный ключ
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()

        # Вычисляем проверочный хэш
        computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if computed_hash != data_hash:
            return None

        # Anti-replay: проверка свежести auth_date [feature 006, FR-005/007]
        auth_date_raw = vals.get("auth_date", [None])[0]
        try:
            auth_date = int(auth_date_raw)
        except (TypeError, ValueError):
            return None

        now = int(time.time())
        ttl = getattr(config, "WEBAPP_SESSION_TTL_SECONDS", 86400)
        if ttl > 0 and now - auth_date > ttl:
            return None
        if auth_date - now > _AUTH_DATE_FUTURE_SKEW:
            return None

        # Возвращаем распарсенные данные (для удобства)
        return {k: v[0] for k, v in vals.items()}

    except Exception:
        return None

async def get_current_user_id(x_tg_init_data: str = Header(None)) -> int:
    """Dependency для извлечения и валидации user_id из заголовков [CC-3]."""
    from fastapi import HTTPException
    import json

    if not x_tg_init_data:
        raise HTTPException(status_code=401, detail="Missing X-TG-Init-Data header")

    user_data = validate_webapp_init_data(x_tg_init_data)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid session")

    try:
        user_info = json.loads(user_data['user'])
        return int(user_info['id'])
    except (KeyError, json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid user data")
