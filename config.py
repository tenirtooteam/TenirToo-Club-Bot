# Файл: config.py
import os
from dotenv import load_dotenv

load_dotenv()

def get_env_or_raise(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise ValueError(f"❌ Критическая ошибка: Переменная окружения {key} не задана в .env")
    return value

BOT_TOKEN = get_env_or_raise("BOT_TOKEN")
ADMIN_ID  = int(get_env_or_raise("ADMIN_ID"))
GROUP_ID  = int(get_env_or_raise("GROUP_ID"))
IMMUNITY_FOR_ADMINS = os.getenv("IMMUNITY_FOR_ADMINS", "False").lower() in ("true", "1", "yes")