# Файл: loader.py
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN

# Инициализируем бота и диспетчер здесь
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())