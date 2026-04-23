# Файл: handlers/user.py
import logging
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import keyboards as kb
from database import db
from services.ui_service import UIService
from services.callback_guard import safe_callback
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
@UIService.sterile_command(redirect=True, error_prefix="меню")
async def cmd_start(message: types.Message, state: FSMContext):
    """Главное меню пользователя с поддержкой перехода из групп в ЛС."""
    welcome_text = (
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        f"Добро пожаловать в систему управления доступом клуба <b>«Теңир-Too»</b>.\n\n"
        f"Используй кнопки ниже для навигации:"
    )

    return welcome_text, kb.user_main_kb()


@router.callback_query(F.data == "user_main")
@safe_callback()
async def back_to_user_main(callback: types.CallbackQuery, state: FSMContext):
    await UIService.show_menu(
        state, callback, 
        "Главное меню участника:",
        reply_markup=kb.user_main_kb()
    )


@router.callback_query(F.data == "user_profile_view")
@safe_callback()
async def user_profile_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    db_name = db.get_user_name(user_id)
    user_templates = db.get_user_group_templates(user_id)
    groups_str = ", ".join(g[1] for g in user_templates) if user_templates else "нет назначенных шаблонов"
    
    # Собираем роли и топики
    roles = list(db.get_user_roles(user_id))
    
    # Доступные топики (ID и Названия)
    # Доступные топики (уже в формате (id, name))
    available_topics = db.get_user_available_topics(user_id)

    text = UIService.format_user_card(user_id, db_name, groups_str, roles, available_topics)
    await UIService.show_menu(state, callback, text, reply_markup=kb.user_profile_kb())


@router.callback_query(F.data == "user_topics")
@safe_callback()
async def show_user_topics(callback: types.CallbackQuery, state: FSMContext):
    """Список топиков, к которым у юзера есть доступ."""
    await UIService.show_menu(
        state, callback, 
        "📍 <b>Топики, в которых ты можешь писать:</b>",
        reply_markup=kb.user_topics_list_kb(callback.from_user.id)
    )


@router.callback_query(F.data.startswith("u_topic_info_"))
@safe_callback()
async def user_topic_detail(callback: types.CallbackQuery, state: FSMContext):
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
        f"👥 <b>Связанные шаблоны:</b>\n{groups_str}\n\n"
        f"🔐 <b>Твой статус:</b> {access_status}\n\n"
        f"<i>Если доступа нет, твои сообщения в этом топике будут удаляться автоматически.</i>"
    )
    await UIService.show_menu(state, callback, text, reply_markup=kb.user_topic_detail_kb())


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