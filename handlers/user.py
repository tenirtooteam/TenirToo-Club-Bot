# Файл: handlers/user.py
import logging
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import keyboards as kb
from services.ui_service import UIService
from services.callback_guard import safe_callback
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
@UIService.sterile_command(redirect=True, error_prefix="меню")
async def cmd_start(message: types.Message, state: FSMContext):
    """Единая точка входа: определяет роль и показывает нужный дашборд [RA-1]."""
    user_id = message.from_user.id
    text, kb_func = await UIService.get_landing_data(user_id)
    return text, kb_func()


@router.callback_query(F.data == "user_main")
@safe_callback()
async def back_to_user_main(callback: types.CallbackQuery, state: FSMContext):
    """Возврат на главную панель (ролевой роутинг)."""
    await UIService.generic_navigator(state, callback, "landing")


@router.callback_query(F.data == "user_profile_view")
@safe_callback()
async def user_profile_callback(callback: types.CallbackQuery, state: FSMContext):
    await UIService.generic_navigator(state, callback, callback.data)


@router.callback_query(F.data == "user_topics")
@safe_callback()
async def show_user_topics(callback: types.CallbackQuery, state: FSMContext):
    """Список топиков, к которым у юзера есть доступ."""
    await UIService.generic_navigator(state, callback, callback.data)


@router.callback_query(F.data.startswith("u_topic_info_"))
@safe_callback()
async def user_topic_detail(callback: types.CallbackQuery, state: FSMContext):
    """Информация о любом топике в системе."""
    await UIService.generic_navigator(state, callback, callback.data)


@router.message(F.chat.type != "private", F.text.startswith("@all"))
async def handle_all_mention(message: types.Message, bot: Bot):
    """Хендлер для нативного оповещения всех участников топика."""
    topic_id = message.message_thread_id if message.message_thread_id else -1

    # Сразу удаляем сообщение-триггер для чистоты чата
    await UIService.delete_msg(message)

    # Подготовка текста (убираем сам тег из сообщения)
    raw_text = message.text or ""
    clean_text = raw_text.replace("@all", "", 1).strip()

    if not clean_text:
        clean_text = "Внимание! Срочное сообщение."

    sender_name = message.from_user.first_name

    # Запускаем рассылку через сервис
    await NotificationService.send_native_all(
        bot=bot,
        chat_id=message.chat.id,
        topic_id=topic_id,
        sender_name=sender_name,
        text=clean_text
    )