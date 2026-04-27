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

# Google Sheets Integration
GOOGLE_CREDS_PATH = os.getenv("GOOGLE_CREDS_PATH", "google_creds.json")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")

# Модерация Мероприятий
REQUIRE_ADMIN_EVENT_AUDIT = os.getenv("REQUIRE_ADMIN_EVENT_AUDIT", "True").lower() in ("true", "1", "yes")

# Logging Configuration
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 5

# WebApp Configuration [PL-2.2.3]
WEBAPP_HOST = os.getenv("WEBAPP_HOST", "0.0.0.0")
WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", "8000"))
WEBAPP_URL = os.getenv("WEBAPP_URL", "")
WEBAPP_CORS_ORIGINS = ["*"]