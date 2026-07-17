# Файл: loader.py
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
# [Feature 012 / №16] Персистентный FSM-storage через фасад БД (R-ARCH-1): состояние
# и стек стерильного интерфейса переживают рестарт. Конструктор БД не касается —
# таблица создаётся позже в init_db() (main.py).
from database.db import SQLiteStorage

# Инициализируем бота и диспетчер здесь
from aiogram.client.default import DefaultBotProperties
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=SQLiteStorage())
