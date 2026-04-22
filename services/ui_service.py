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
    async def show_menu(
        state: FSMContext,
        event: types.Message | types.CallbackQuery,
        text: str,
        reply_markup: types.InlineKeyboardMarkup = None,
        parse_mode: str = "HTML"
    ):
        """
        Универсальный метод отображения/обновления меню.
        Соблюдает Sterile UI Protocol:
        - Если CallbackQuery — редактирует текущее сообщение.
        - Если Message — чистит чат и шлет новое.
        - Всегда гарантирует актуальность last_menu_id.
        """
        is_cb = isinstance(event, types.CallbackQuery)

        if is_cb:
            try:
                await event.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
                await event.answer()
            except Exception:
                # На случай, если сообщение нельзя редактировать (старое или контент тот же)
                # Пересоздаем меню через режим Message
                new_msg = await event.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
                await state.update_data(last_menu_id=new_msg.message_id)
                await UIService.delete_msg(event.message)
                await event.answer()
        else:
            await UIService.finish_input(state, event)
            new_msg = await event.bot.send_message(
                event.chat.id, text, reply_markup=reply_markup, parse_mode=parse_mode
            )
            await state.update_data(last_menu_id=new_msg.message_id)

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

    @staticmethod
    def format_user_card(user_id: int, user_name: str, groups_str: str, roles: list, available_topics: list) -> str:
        """
        Красивое оформление карточки пользователя с ролями и топиками.
        roles: список кортежей (role_name, topic_id) — topic_id может быть None.
        available_topics: список кортежей (topic_id, topic_name).
        Имя топика для модератора берётся из available_topics — без обращения к БД.
        UI-сервис не должен знать о слое БД.
        """
        # Индекс имён топиков — строим из переданных данных
        topic_name_map = {t_id: t_name for t_id, t_name in available_topics}

        # Сортируем роли
        role_priority = {"superadmin": 0, "admin": 1, "moderator": 2}
        sorted_roles = sorted(roles, key=lambda x: role_priority.get(x[0], 99))

        role_blocks = []
        is_global_admin = False
        for r_name, t_id in sorted_roles:
            if r_name in ["superadmin", "admin"]:
                is_global_admin = True
                role_blocks.append(
                    "┌── 👑 <b>АДМИНИСТРАТОР</b> ──┐\n"
                    "│  <i>Глобальный доступ</i>\n"
                    "└───────────────────┘"
                )
            elif r_name == "moderator":
                # Имя берётся из переданного индекса, без обращения к БД из UI-слоя
                t_name = topic_name_map.get(t_id, f"ID:{t_id}" if t_id else "???")
                role_blocks.append(
                    f"┌── 🛡 <b>МОДЕРАТОР</b> ──┐\n"
                    f"│  <b>Топик:</b> {t_name}\n"
                    f"└──────────────────┘"
                )

        roles_display = "\n".join(role_blocks) if role_blocks else "👤 <b>Участник</b>"

        # Топики
        if is_global_admin:
            topics_display = "  • <b>Все топики (Глобальный доступ)</b>"
        else:
            topics_display = (
                "\n".join([f"  • {t_name} (ID: {t_id})" for t_id, t_name in available_topics])
                if available_topics else "  <i>нет доступных топиков</i>"
            )

        text = (
            f"{roles_display}\n\n"
            f"👤 <b>Профиль:</b> {user_name}\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            f"🔐 <b>Группы:</b> {groups_str}\n\n"
            f"📍 <b>Доступные топики:</b>\n{topics_display}"
        )
        return text