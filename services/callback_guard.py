import logging
from functools import wraps
from aiogram import types
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)

def safe_callback():
    """
    Декоратор для безопасной обработки колбэков.
    - Игнорирует ошибки "message is not modified".
    - Предотвращает повторное выполнение при дублировании нажатий.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(callback: types.CallbackQuery, *args, **kwargs):
            try:
                return await func(callback, *args, **kwargs)
            except TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    logger.debug(f"Игнорируем неизменённое сообщение от {callback.from_user.id}")
                    await callback.answer()
                else:
                    logger.error(f"Ошибка API при обработке колбэка {callback.data}: {e}")
                    await callback.answer("⚠️ Произошла ошибка. Попробуйте позже.", show_alert=True)
            except Exception as e:
                logger.error(f"Неизвестная ошибка в колбэке {callback.data}: {e}", exc_info=True)
                await callback.answer("❌ Критическая ошибка.", show_alert=True)
        return wrapper
    return decorator
