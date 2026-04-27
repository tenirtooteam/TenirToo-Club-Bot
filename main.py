# Файл: main.py
import asyncio
import logging
import os
from logging.handlers import RotatingFileHandler
from loader import bot, dp
from database import db
from handlers import admin, user, common, moderator, events, announcements
from middlewares.access_check import UserManagerMiddleware, ForumUtilityMiddleware, AccessGuardMiddleware
import uvicorn
from config import WEBAPP_HOST, WEBAPP_PORT, LOG_MAX_BYTES, LOG_BACKUP_COUNT
from web.main import app as web_app


def setup_logging():
    """Configure logging to console and rotating file."""
    if not os.path.exists('logs'):
        os.makedirs('logs')

    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
    log_file = 'logs/bot.log'

    # File handler [PL-2.2.1]
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=LOG_MAX_BYTES, 
        backupCount=LOG_BACKUP_COUNT, 
        encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


async def main():
    setup_logging()

    # Initialize Database
    db.init_db()

    # Register Middlewares (порядок важен!)
    # 1. Сначала регистрируем/обновляем юзера
    dp.message.outer_middleware(UserManagerMiddleware())
    # 2. Чистим сервисные сообщения и синхронизируем топики
    dp.message.outer_middleware(ForumUtilityMiddleware())
    # 3. В последнюю очередь проверяем доступ к контенту
    dp.message.outer_middleware(AccessGuardMiddleware())

    # Register Routers (common первым для перехвата глобальных кнопок)
    dp.include_router(common.router)
    dp.include_router(user.router)
    dp.include_router(admin.router)
    dp.include_router(moderator.router)
    dp.include_router(events.router)
    dp.include_router(announcements.router)

    logging.info("🚀 Запуск систем...")

    await bot.delete_webhook(drop_pending_updates=True)
    
    # WebApp Server [CC-3] [PL-2.2.1]
    web_config = uvicorn.Config(web_app, host=WEBAPP_HOST, port=WEBAPP_PORT, log_level="info")
    web_server = uvicorn.Server(web_config)

    # Запускаем параллельно: Web-сервер и Bot-polling
    await asyncio.gather(
        web_server.serve(),
        dp.start_polling(bot)
    )


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("👋 Бот остановлен вручную")