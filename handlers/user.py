# Файл: handlers/user.py
import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import keyboards as kb
from database import db
from services.ui_service import UIService
from services.callback_guard import safe_callback

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Главное меню пользователя с предварительной очисткой."""
    await UIService.clear_last_menu(state, message.bot, message.chat.id)
    await UIService.delete_msg(message)

    welcome_text = (
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        f"Добро пожаловать в систему управления доступом клуба <b>«Теңир-Too»</b>.\n\n"
        f"Используй кнопки ниже для навигации:"
    )
    sent_message = await message.answer(welcome_text, reply_markup=kb.user_main_kb(), parse_mode="HTML")
    await state.update_data(last_menu_id=sent_message.message_id)


@router.callback_query(F.data == "user_main")
@safe_callback()
async def back_to_user_main(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Главное меню участника:",
        reply_markup=kb.user_main_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "user_profile_view")
@safe_callback()
async def user_profile_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    db_name = db.get_user_name(user_id)
    user_groups = db.get_user_groups(user_id)
    groups_str = ", ".join(g[1] for g in user_groups) if user_groups else "нет активных групп"

    text = (
        f"👤 <b>Профиль участника</b>\n\n"
        f"<b>Имя в системе:</b> {db_name}\n"
        f"<b>Твой ID:</b> <code>{user_id}</code>\n"
        f"<b>Доступные группы:</b> {groups_str}"
    )
    await callback.message.edit_text(text, reply_markup=kb.user_topic_detail_kb(), parse_mode="HTML")


@router.callback_query(F.data == "user_topics")
@safe_callback()
async def show_user_topics(callback: types.CallbackQuery):
    """Список топиков, к которым у юзера есть доступ."""
    await callback.message.edit_text(
        "📍 <b>Топики, в которых ты можешь писать:</b>",
        reply_markup=kb.user_topics_list_kb(callback.from_user.id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("u_topic_info_"))
@safe_callback()
async def user_topic_detail(callback: types.CallbackQuery):
    """Информация о любом топике в системе."""
    topic_id = int(callback.data.split("_")[-1])
    t_name = db.get_topic_name(topic_id)
    access_groups = db.get_groups_by_topic(topic_id)
    groups_str = "\n".join(f"— {g}" for g in access_groups) if access_groups else "Доступ не настроен"

    has_access = db.can_write(callback.from_user.id, topic_id)
    access_status = "✅ У тебя есть доступ." if has_access else "❌ У тебя нет доступа."

    text = (
        f"📍 <b>Информация о топике</b>\n\n"
        f"<b>Название:</b> {t_name}\n"
        f"<b>ID:</b> <code>{topic_id}</code>\n\n"
        f"👥 <b>Доступ имеют группы:</b>\n{groups_str}\n\n"
        f"🔐 <b>Твой статус:</b> {access_status}\n\n"
        f"<i>Если доступа нет, твои сообщения в этом топике будут удаляться автоматически.</i>"
    )
    await callback.message.edit_text(text, reply_markup=kb.user_topic_detail_kb(), parse_mode="HTML")