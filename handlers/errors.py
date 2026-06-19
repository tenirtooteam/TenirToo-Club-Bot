import logging
from aiogram import Router, types
from aiogram.types import ErrorEvent

logger = logging.getLogger(__name__)
router = Router()

@router.errors()
async def global_errors_handler(event: ErrorEvent):
    exception = event.exception
    update = event.update
    logger.exception(f"🔥 Необработанное исключение: {exception} при обработке обновления {update}")

    # Попробуем отправить уведомление пользователю, если есть контекст сообщения или колбэка
    message = None
    if update.message:
        message = update.message
    elif update.callback_query and update.callback_query.message:
        message = update.callback_query.message

    if message:
        try:
            await message.answer(
                "⚠️ Произошла внутренняя ошибка в работе ассистента.\n"
                "Разработчики уже уведомлены. Пожалуйста, попробуйте позже."
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить сообщение об ошибке пользователю: {e}")
    return True


@router.callback_query()
async def default_callback_handler(callback: types.CallbackQuery):
    """Fallback handler for unhandled callback queries."""
    await callback.answer("❌ Действие недоступно или не поддерживается.", show_alert=True)
