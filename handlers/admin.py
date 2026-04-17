# Файл: handlers/admin.py
import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import keyboards as kb
from database import db
from config import ADMIN_ID, GROUP_ID
from services.callback_guard import safe_callback
from services.ui_service import UIService
from aiogram.filters import Filter

logger = logging.getLogger(__name__)

class IsAdmin(Filter):
    async def __call__(self, event: types.Message | types.CallbackQuery) -> bool:
        user_id = event.from_user.id
        if user_id != ADMIN_ID:
            logger.warning(f"🚫 Несанкционированный доступ к админке: {user_id}")
            return False
        return True

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


class AdminStates(StatesGroup):
    waiting_for_group_name = State()
    waiting_for_topic_name = State()
    waiting_for_user_data = State()
    waiting_for_new_name = State()


# --- ГЛАВНОЕ МЕНЮ ---

@router.message(Command("admin"))
async def admin_dashboard(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        logger.warning(f"🚫 Попытка доступа к админке: {message.from_user.id}")
        return

    # Закрываем старое меню и чистим команду пользователя
    await UIService.finish_input(state, message)

    sent_message = await message.answer(
        "🛠 <b>Панель управления</b>",
        reply_markup=kb.main_admin_kb(),
        parse_mode="HTML"
    )
    await state.update_data(last_menu_id=sent_message.message_id)


@router.callback_query(F.data == "admin_main")
@safe_callback()
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text("🛠 <b>Панель управления</b>", reply_markup=kb.main_admin_kb(), parse_mode="HTML")


# --- УПРАВЛЕНИЕ ГРУППАМИ ---

@router.callback_query(F.data == "manage_groups")
@safe_callback()
async def show_groups(callback: types.CallbackQuery):
    await callback.message.edit_text("📂 <b>Группы доступа:</b>", reply_markup=kb.groups_list_kb(), parse_mode="HTML")


@router.callback_query(F.data.startswith("group_info_"))
@safe_callback()
async def group_detail(callback: types.CallbackQuery):
    group_id = int(callback.data.split("_")[-1])
    group_name = db.get_group_name(group_id)
    await callback.message.edit_text(f"⚙️ <b>Настройка группы: {group_name}</b> (ID: {group_id})",
                                     reply_markup=kb.group_edit_kb(group_id), parse_mode="HTML")


@router.callback_query(F.data == "add_group_start")
@safe_callback()
async def add_group_init(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("✍️ Введи название для новой группы:")
    await state.set_state(AdminStates.waiting_for_group_name)


@router.message(AdminStates.waiting_for_group_name)
async def process_group_add(message: types.Message, state: FSMContext):
    db.create_group(message.text)

    # Очистка интерфейса
    await UIService.finish_input(state, message)

    sent_message = await message.answer(
        f"✅ Группа <b>{message.text}</b> создана!",
        reply_markup=kb.main_admin_kb(),
        parse_mode="HTML"
    )
    await state.update_data(last_menu_id=sent_message.message_id)


@router.callback_query(F.data.startswith("del_group_"))
@safe_callback()
async def delete_group_handler(callback: types.CallbackQuery):
    group_id = int(callback.data.split("_")[-1])
    db.delete_group(group_id)
    await callback.answer(f"Группа удалена")
    await show_groups(callback)


# --- УПРАВЛЕНИЕ ТОПИКАМИ ---

@router.callback_query(F.data == "all_topics_list")
@safe_callback()
async def show_all_topics(callback: types.CallbackQuery):
    await callback.message.edit_text("📍 <b>Все топики в системе:</b>", reply_markup=kb.all_topics_kb(),
                                     parse_mode="HTML")


@router.callback_query(F.data.startswith("topic_global_view_"))
@safe_callback()
async def topic_global_detail(callback: types.CallbackQuery):
    topic_id = int(callback.data.split("_")[-1])
    t_name = db.get_topic_name(topic_id)
    access_groups = db.get_groups_by_topic(topic_id)
    groups_str = ", ".join(access_groups) if access_groups else "НЕТ ДОСТУПА"
    text = (
        f"📍 <b>Информация о топике</b>\n\n"
        f"<b>Наименование:</b> {t_name}\n"
        f"<b>ID:</b> <code>{topic_id}</code>\n"
        f"<b>Доступ имеют:</b> {groups_str}"
    )
    await callback.message.edit_text(text, reply_markup=kb.topic_edit_kb(topic_id, group_id=0), parse_mode="HTML")


@router.callback_query(F.data.startswith("group_topics_list_"))
@safe_callback()
async def show_group_topics(callback: types.CallbackQuery):
    group_id = int(callback.data.split("_")[-1])
    group_name = db.get_group_name(group_id)
    await callback.message.edit_text(f"📍 <b>Топики группы: {group_name}</b>",
                                     reply_markup=kb.group_topics_list_kb(group_id), parse_mode="HTML")


@router.callback_query(F.data.startswith("topic_del_"))
@safe_callback()
async def remove_topic_from_group_handler(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    topic_id, group_id = int(parts[2]), int(parts[3])
    db.remove_topic_from_group(group_id, topic_id)
    await callback.answer("Топик убран из группы")
    group_name = db.get_group_name(group_id)
    await callback.message.edit_text(
        f"📍 <b>Топики группы: {group_name}</b>",
        reply_markup=kb.group_topics_list_kb(group_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("add_topic_to_"))
@safe_callback()
async def add_topic_to_group_init(callback: types.CallbackQuery):
    group_id = int(callback.data.split("_")[-1])
    group_name = db.get_group_name(group_id)
    await callback.message.edit_text(
        f"➕ <b>Выбери топик для добавления в группу «{group_name}»:</b>",
        reply_markup=kb.available_topics_kb(group_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("topic_add_confirm_"))
@safe_callback()
async def confirm_add_topic(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    topic_id, group_id = int(parts[3]), int(parts[4])
    db.add_topic_to_group(group_id, topic_id)
    group_name = db.get_group_name(group_id)
    await callback.answer("✅ Топик добавлен!")
    await callback.message.edit_text(
        f"📍 <b>Топики группы: {group_name}</b>",
        reply_markup=kb.group_topics_list_kb(group_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("topic_rename_"))
@safe_callback()
async def topic_rename_init(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    t_id, g_id = int(parts[2]), int(parts[3])
    await state.update_data(edit_topic_id=t_id, edit_group_id=g_id)
    await callback.message.answer(f"✍️ Введи новое название для ID: {t_id}:")
    await state.set_state(AdminStates.waiting_for_topic_name)


@router.message(AdminStates.waiting_for_topic_name)
async def process_topic_name_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    t_id = data.get('edit_topic_id')
    new_name = message.text

    if t_id is None:
        await state.set_state(None)
        await message.answer("❌ Ошибка: данные топика потеряны.")
        return

    db.update_topic_name(t_id, new_name)

    status = ""
    if t_id != -1:
        try:
            await message.bot.edit_forum_topic(chat_id=GROUP_ID, message_thread_id=t_id, name=new_name)
            status = "\n✅ Синхронизировано с Telegram."
        except Exception as e:
            logger.warning(f"⚠️ Ошибка API: {e}")
            status = f"\n⚠️ Только в БД (Ошибка API)"

    await UIService.finish_input(state, message)

    sent_message = await message.answer(f"✅ Топик {t_id} обновлен.{status}", reply_markup=kb.main_admin_kb(),
                                        parse_mode="HTML")
    await state.update_data(last_menu_id=sent_message.message_id)


@router.callback_query(F.data.startswith("topic_in_group_"))
@safe_callback()
async def topic_in_group_detail(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    topic_id, group_id = int(parts[3]), int(parts[4])
    t_name = db.get_topic_name(topic_id)
    access_groups = db.get_groups_by_topic(topic_id)
    groups_str = ", ".join(access_groups) if access_groups else "НЕТ ДОСТУПА"
    text = (
        f"📍 <b>Информация о топике</b>\n\n"
        f"<b>Наименование:</b> {t_name}\n"
        f"<b>ID:</b> <code>{topic_id}</code>\n"
        f"<b>Доступ имеют:</b> {groups_str}"
    )
    await callback.message.edit_text(
        text, reply_markup=kb.topic_edit_kb(topic_id, group_id=group_id), parse_mode="HTML"
    )


# --- УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ---

@router.callback_query(F.data == "manage_users")
@safe_callback()
async def show_users(callback: types.CallbackQuery):
    await callback.message.edit_text("👥 <b>Список пользователей:</b>", reply_markup=kb.users_list_kb(),
                                     parse_mode="HTML")


@router.callback_query(F.data == "add_user_start")
@safe_callback()
async def add_user_init(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("✍️ Введи: <code>ID Имя Фамилия</code>", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_user_data)


@router.message(AdminStates.waiting_for_user_data)
async def process_user_add(message: types.Message, state: FSMContext):
    parts = message.text.split()
    if len(parts) < 3 or not parts[0].isdigit():
        await message.answer("❌ Формат: ID Имя Фамилия")
        return

    db.add_user(int(parts[0]), parts[1], parts[2])

    await UIService.finish_input(state, message)

    sent_message = await message.answer(
        f"✅ Пользователь {parts[1]} добавлен!",
        reply_markup=kb.users_list_kb(),
        parse_mode="HTML"
    )
    await state.update_data(last_menu_id=sent_message.message_id)


@router.callback_query(F.data.startswith("user_info_"))
@safe_callback()
async def user_detail(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    user_name = db.get_user_name(user_id)
    user_groups = db.get_user_groups(user_id)
    groups_str = ", ".join(g[1] for g in user_groups) if user_groups else "нет прав"
    text = f"👤 <b>Пользователь:</b> {user_name}\nID: <code>{user_id}</code>\n🔐 <b>Доступ:</b> {groups_str}"
    await callback.message.edit_text(text, reply_markup=kb.user_edit_kb(user_id), parse_mode="HTML")


@router.callback_query(F.data.startswith("user_rename_"))
@safe_callback()
async def user_rename_init(callback: types.CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[-1])
    await state.update_data(edit_user_id=user_id)
    await callback.message.answer(f"✍️ Введи новое Имя и Фамилию:", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_new_name)


@router.message(AdminStates.waiting_for_new_name)
async def process_user_rename(message: types.Message, state: FSMContext):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Введи Имя и Фамилию!")
        return

    data = await state.get_data()
    db.update_user_name(data['edit_user_id'], parts[0], parts[1])

    await UIService.finish_input(state, message)

    sent_message = await message.answer(f"✅ Данные обновлены.", reply_markup=kb.users_list_kb(), parse_mode="HTML")
    await state.update_data(last_menu_id=sent_message.message_id)


@router.callback_query(F.data.startswith("user_groups_manage_"))
@safe_callback()
async def user_groups_ui(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    user_name = db.get_user_name(user_id)
    await callback.message.edit_text(f"🔐 Настройка доступа: <b>{user_name}</b>",
                                     reply_markup=kb.user_groups_edit_kb(user_id), parse_mode="HTML")


@router.callback_query(F.data.startswith("u_gr_"))
@safe_callback()
async def toggle_group(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    action, user_id, group_id = parts[2], int(parts[3]), int(parts[4])
    if action == "gra":
        db.grant_group(user_id, group_id)
    else:
        db.revoke_group(user_id, group_id)
    await callback.message.edit_reply_markup(reply_markup=kb.user_groups_edit_kb(user_id))


@router.callback_query(F.data.startswith("user_delete_"))
@safe_callback()
async def user_delete_handler(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    db.delete_user(user_id)
    await callback.answer("Пользователь удален")
    await show_users(callback)