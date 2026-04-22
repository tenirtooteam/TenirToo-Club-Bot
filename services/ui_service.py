# Файл: services/ui_service.py
import logging
from functools import wraps
from aiogram import Bot, types
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)


class UIService:

    @staticmethod
    async def clear_last_menu(state: FSMContext, bot: Bot, chat_id: int):
        """Удаляет последнее запомненное меню или системное сообщение из чата."""
        data = await state.get_data()
        last_id = data.get("last_menu_id")
        if last_id:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=last_id)
                logger.info(f"🧹 Удалено сообщение: {last_id}")
            except Exception:
                pass
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
        удаляет старое меню/промпт, удаляет сообщение пользователя,
        сбрасывает состояние ввода.
        """
        await UIService.clear_last_menu(state, message.bot, message.chat.id)
        await UIService.delete_msg(message)
        await state.set_state(None)

    @staticmethod
    async def send_redirected_menu(
        message: types.Message, 
        state: FSMContext, 
        text: str, 
        reply_markup: types.InlineKeyboardMarkup = None,
        error_prefix: str = "меню"
    ):
        """
        Реализует протокол «Стерильного интерфейса» для команд:
        перенос в ЛС из групп с очисткой триггеров.
        """
        user_id = message.from_user.id
        
        if message.chat.type != "private" and error_prefix is not None:
            try:
                sent_message = await message.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                await state.update_data(last_menu_id=sent_message.message_id)
                await UIService.delete_msg(message)
                return sent_message
            except Exception:
                error_msg = (
                    f"⚠️ <b>{message.from_user.first_name}</b>, я не могу отправить вам {error_prefix} в ЛС.\n"
                    f"Пожалуйста, сначала напишите мне в личные сообщения (нажмите /start)."
                )
                sent_error = await message.answer(error_msg, parse_mode="HTML")
                await state.update_data(last_menu_id=sent_error.message_id)
                await UIService.delete_msg(message)
                return sent_error
        else:
            # Если уже в личке или редирект не требуется
            await UIService.finish_input(state, message)
            sent_message = await message.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            await state.update_data(last_menu_id=sent_message.message_id)
            return sent_message

    @staticmethod
    async def ask_input(
        state: FSMContext, 
        event: types.Message | types.CallbackQuery, 
        text: str, 
        state_to_set=None
    ):
        """
        Удаляет текущее меню, отправляет промпт и ставит его на слежение (last_menu_id).
        """
        bot = event.bot if isinstance(event, types.Message) else event.message.bot
        chat_id = event.chat.id if isinstance(event, types.Message) else event.message.chat.id
        
        await UIService.clear_last_menu(state, bot, chat_id)
        
        if isinstance(event, types.Message):
            await UIService.delete_msg(event)
            
        msg_source = event if isinstance(event, types.Message) else event.message
        sent = await msg_source.answer(text, parse_mode="HTML")
        
        await state.update_data(last_menu_id=sent.message_id)
        if state_to_set:
            await state.set_state(state_to_set)
        return sent

    @staticmethod
    async def show_temp_message(
        state: FSMContext, 
        message: types.Message, 
        text: str, 
        reply_markup: types.InlineKeyboardMarkup = None
    ):
        """Отправляет временное сообщение и ставит на слежение."""
        await UIService.clear_last_menu(state, message.bot, message.chat.id)
        await UIService.delete_msg(message)
        
        sent = await message.answer(text, reply_markup=reply_markup, parse_mode="HTML")
        await state.update_data(last_menu_id=sent.message_id)
        return sent

    @staticmethod
    def sterile_command(redirect: bool = False, error_prefix: str = "меню"):
        """
        Декоратор для командных хендлеров. 
        Автоматизирует редирект в ЛС, удаление триггеров и трекинг меню.
        Хендлер должен возвращать: (text, reply_markup) или просто text.
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(message: types.Message, state: FSMContext, *args, **kwargs):
                # Вызываем хендлер для получения данных
                result = await func(message, state, *args, **kwargs)
                
                if result is None:
                    return
                
                # Распаковываем (текст, клавиатура)
                if isinstance(result, tuple):
                    text, reply_markup = result
                else:
                    text, reply_markup = result, None
                
                # Делегируем отправку стандартному методу
                return await UIService.send_redirected_menu(
                    message=message,
                    state=state,
                    text=text,
                    reply_markup=reply_markup,
                    error_prefix=error_prefix if redirect else None
                )
            return wrapper
        return decorator