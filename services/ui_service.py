# Файл: services/ui_service.py
import logging
from aiogram import Bot, types
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)


class UIService:

    @staticmethod
    async def clear_last_menu(state: FSMContext, bot: Bot, chat_id: int):
        """Удаляет последнее запомненное меню из чата."""
        data = await state.get_data()
        last_id = data.get("last_menu_id")
        logger.info(f"🧹 clear_last_menu: last_menu_id={last_id}, chat_id={chat_id}")
        if last_id:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=last_id)
                logger.info(f"🧹 Удалено меню: {last_id}")
            except Exception as e:
                logger.warning(f"🧹 Не удалось удалить меню {last_id}: {e}")
            finally:
                await state.update_data(last_menu_id=None)

    @staticmethod
    async def delete_msg(message: types.Message):
        """Безопасное удаление одного сообщения пользователя."""
        try:
            await message.delete()
        except Exception:
            pass

    @staticmethod
    async def finish_input(state: FSMContext, message: types.Message):
        """
        Единый метод завершения FSM-ввода:
        удаляет старое меню, удаляет сообщение пользователя,
        сбрасывает состояние ввода.
        """
        await UIService.clear_last_menu(state, message.bot, message.chat.id)
        await UIService.delete_msg(message)
        await state.set_state(None)