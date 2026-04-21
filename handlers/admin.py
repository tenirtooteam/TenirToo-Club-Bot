# Файл: handlers/admin.py
import logging
from aiogram import Router, F, types
from aiogram.filters import Command, Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import keyboards as kb
from database import db
from config import ADMIN_ID, GROUP_ID
from services.callback_guard import safe_callback
from services.ui_service import UIService
from services.permission_service import PermissionService

logger = logging.getLogger(__name__)


class IsGlobalAdmin(Filter):
    """Фильтр для глобальных администраторов (superadmin + admin)."""
    async def __call__(self, event: types.Message | types.CallbackQuery) -> bool:
        user_id = event.from_user.id
        if not PermissionService.is_global_admin(user_id):
            logger.warning(f"🚫 Несанкционированный доступ к админке: {user_id}")
            return False
        return True


router = Router()
router.message.filter(IsGlobalAdmin())
router.callback_query.filter(IsGlobalAdmin())

class AdminStates(StatesGroup):
    waiting_for_group_name = State()
    waiting_for_topic_name = State()
    waiting_for_user_data = State()
    waiting_for_new_name = State()
    # Новые состояния для управления ролями
    waiting_for_new_role_user = State()      # выбор пользователя для назначения роли

# --- ГЛАВНОЕ МЕНЮ ---

@router.message(Command("admin"))
async def admin_dashboard(message: types.Message, state: FSMContext):
    await UIService.finish_input(state, message)

    is_superadmin = PermissionService.is_superadmin(message.from_user.id)
    sent_message = await message.answer(
        "🛠 <b>Панель управления</b>",
        reply_markup=kb.main_admin_kb(is_superadmin=is_superadmin),
        parse_mode="HTML"
    )
    await state.update_data(last_menu_id=sent_message.message_id)


@router.callback_query(F.data == "admin_main")
@safe_callback()
async def back_to_main(callback: types.CallbackQuery):
    is_superadmin = PermissionService.is_superadmin(callback.from_user.id)
    await callback.message.edit_text(
        "🛠 <b>Панель управления</b>",
        reply_markup=kb.main_admin_kb(is_superadmin=is_superadmin),
        parse_mode="HTML"
    )


# --- УПРАВЛЕНИЕ ГРУППАМИ ---

@router.callback_query(F.data.startswith("manage_groups"))
@safe_callback()
async def show_groups(callback: types.CallbackQuery):
    parts = callback.data.split("_pg_")
    page = int(parts[1]) if len(parts) > 1 else 1
    await callback.message.edit_text("📂 <b>Группы доступа:</b>", reply_markup=kb.groups_list_kb(page=page),
                                     parse_mode="HTML")


@router.callback_query(F.data.startswith("topic_assign_pg_"))
@safe_callback()
async def role_assign_choose_topic(callback: types.CallbackQuery):
    parts = callback.data.split("_pg_")
    page = int(parts[1]) if len(parts) > 1 else 1
    user_id = int(parts[0].replace("topic_assign_pg_", ""))
    user_name = db.get_user_name(user_id)
    await callback.message.edit_text(f"📍 Выбери топик для {user_name} в роли Модератора:",
                                     reply_markup=kb.topic_selection_for_role_kb(user_id, page=page), parse_mode="HTML")


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

@router.callback_query(F.data.startswith("all_topics_list"))
@safe_callback()
async def show_all_topics(callback: types.CallbackQuery):
    parts = callback.data.split("_pg_")
    page = int(parts[1]) if len(parts) > 1 else 1
    await callback.message.edit_text("📍 <b>Все топики:</b>", reply_markup=kb.all_topics_kb(page=page), parse_mode="HTML")


@router.callback_query(
    F.data.startswith("topic_global_view_") | F.data.startswith("topic_in_group_")
)
@safe_callback()
async def topic_detail(callback: types.CallbackQuery):
    data = callback.data
    if data.startswith("topic_global_view_"):
        topic_id = int(data.split("_")[-1])
        group_id = 0
    else:
        parts = data.split("_")
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
    await callback.message.edit_text(text, reply_markup=kb.topic_edit_kb(topic_id, group_id=group_id), parse_mode="HTML")


@router.callback_query(F.data.startswith("group_topics_list_"))
@safe_callback()
async def show_group_topics(callback: types.CallbackQuery):
    parts = callback.data.split("_pg_")
    page = int(parts[1]) if len(parts) > 1 else 1
    group_id = int(parts[0].replace("group_topics_list_", ""))
    g_name = db.get_group_name(group_id)
    await callback.message.edit_text(f"📍 <b>Топики в группе {g_name} (ID: {group_id}):</b>",
                                     reply_markup=kb.group_topics_list_kb(group_id, page=page), parse_mode="HTML")


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
    parts = callback.data.split("_pg_")
    page = int(parts[1]) if len(parts) > 1 else 1
    group_id = int(parts[0].replace("add_topic_to_", ""))
    await callback.message.edit_text("📍 Выберите топик для добавления в группу:",
                                     reply_markup=kb.available_topics_kb(group_id, page=page),
                                     parse_mode="HTML")


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





@router.callback_query(F.data.startswith("global_topic_del_"))
@safe_callback()
async def global_topic_delete_handler(callback: types.CallbackQuery):
    topic_id = int(callback.data.split("_")[-1])
    db.delete_topic(topic_id)
    await callback.answer("✅ Топик полностью удален из БД!")
    await show_all_topics(callback)


# --- УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ---

@router.callback_query(F.data.startswith("manage_users"))
@safe_callback()
async def show_users(callback: types.CallbackQuery):
    parts = callback.data.split("_pg_")
    page = int(parts[1]) if len(parts) > 1 else 1
    await callback.message.edit_text("👥 <b>Список пользователей:</b>", reply_markup=kb.users_list_kb(page=page),
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
    await callback.message.answer("✍️ Введи новое Имя и Фамилию:")
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

    sent_message = await message.answer("✅ Данные обновлены.", reply_markup=kb.users_list_kb())
    await state.update_data(last_menu_id=sent_message.message_id)


@router.callback_query(F.data.startswith("user_groups_manage_"))
@safe_callback()
async def user_groups_ui(callback: types.CallbackQuery):
    parts = callback.data.split("_pg_")
    page = int(parts[1]) if len(parts) > 1 else 1
    user_id = int(parts[0].replace("user_groups_manage_", ""))
    u_name = db.get_user_name(user_id)
    await callback.message.edit_text(f"Разрешения супер-групп пользователя {u_name}:",
                                     reply_markup=kb.user_groups_edit_kb(user_id, page=page), parse_mode="HTML")


@router.callback_query(F.data.startswith("user_group_toggle_"))
@safe_callback()
async def toggle_group(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    user_id, group_id = int(parts[3]), int(parts[4])
    
    user_groups = set(g[0] for g in db.get_user_groups(user_id))
    if group_id in user_groups:
        db.revoke_group(user_id, group_id)
    else:
        db.grant_group(user_id, group_id)
        
    await callback.message.edit_reply_markup(reply_markup=kb.user_groups_edit_kb(user_id))


@router.callback_query(F.data.startswith("user_delete_"))
@safe_callback()
async def user_delete_handler(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    db.delete_user(user_id)
    await callback.answer("Пользователь удален")
    await show_users(callback)

# --- УПРАВЛЕНИЕ РОЛЯМИ ---

@router.callback_query(F.data == "manage_roles")
@safe_callback()
async def manage_roles_menu(callback: types.CallbackQuery):
    """Меню управления ролями (только для суперадмина)."""
    await callback.message.edit_text(
        "👑 <b>Управление ролями</b>",
        reply_markup=kb.manage_roles_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "list_users_roles")
@safe_callback()
async def list_users_with_roles(callback: types.CallbackQuery):
    """Показывает список всех пользователей с указанием их ролей."""
    users = db.get_all_users()
    if not users:
        await callback.message.edit_text("👥 Нет пользователей в системе.")
        return

    text_lines = ["👥 <b>Пользователи и их роли:</b>\n"]
    for user_id, first_name, last_name in users:
        roles = db.get_user_roles(user_id)
            
        if not roles:
            continue
            
        roles_str_parts = []
        for r_name, t_id in roles:
            if t_id is not None:
                t_name = db.get_topic_name(t_id)
                roles_str_parts.append(f"{r_name} (топик: {t_name} ID:{t_id})")
            else:
                roles_str_parts.append(r_name)
        roles_str = ", ".join(roles_str_parts)
        text_lines.append(f"• {first_name} {last_name} (ID: <code>{user_id}</code>): {roles_str}")

    text = "\n".join(text_lines)
    if len(text_lines) == 1:
        text += "Пока ни у кого нет назначенных ролей."
        
    await callback.message.edit_text(
        text,
        reply_markup=kb.back_to_manage_roles_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "assign_role_start")
@safe_callback()
async def assign_role_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало назначения роли: запрос ID пользователя."""
    await callback.message.edit_text(
        "✍️ Введи ID пользователя, его Имя или Фамилию, которому нужно назначить роль:"
    )
    await state.update_data(last_menu_id=callback.message.message_id)
    await state.set_state(AdminStates.waiting_for_new_role_user)


@router.message(AdminStates.waiting_for_new_role_user)
async def process_role_user_id(message: types.Message, state: FSMContext):
    """Получение ID или ФИО пользователя и переход к выбору роли."""
    text = message.text.strip()
    
    async def _on_user_found(u_id):
        await message.answer(
            f"Пользователь {db.get_user_name(u_id)} найден. Выберите роль:",
            reply_markup=kb.role_selection_kb(u_id)
        )
        await UIService.finish_input(state, message)
        
    if text.isdigit():
        user_id = int(text)
        if not db.user_exists(user_id):
            await message.answer("❌ Пользователь с таким ID не найден.")
            return
        await _on_user_found(user_id)
    else:
        results = db.find_users_by_query(text)
        if not results:
            await message.answer("❌ Никого не найдено.")
            return
        elif len(results) == 1:
            await _on_user_found(results[0][0])
        else:
            await state.update_data(
                disambig_query=text, 
                disambig_action="admin_role_target", 
                disambig_context=None
            )
            import math
            total_pages = math.ceil(len(results)/7)
            markup = kb.user_disambiguation_kb(results[:7], 1, total_pages)
            await UIService.finish_input(state, message)
            await message.answer("👥 Найдено несколько человек. Кого вы имели в виду?", reply_markup=markup)


@router.callback_query(F.data.startswith("role_assign_user_"))
@safe_callback()
async def role_assign_choose_user(callback: types.CallbackQuery):
    """Обработчик кнопки 'Назначить роль' из карточки пользователя."""
    user_id = int(callback.data.split("_")[-1])
    await callback.message.edit_text(
        f"Выберите роль для пользователя {db.get_user_name(user_id)}:",
        reply_markup=kb.role_selection_kb(user_id)
    )


@router.callback_query(F.data.startswith("user_roles_manage_"))
@safe_callback()
async def user_roles_manage_handler(callback: types.CallbackQuery):
    """Меню управления ролями конкретного пользователя."""
    user_id = int(callback.data.split("_")[-1])
    await callback.message.edit_text(
        f"Управление ролями пользователя {user_id}",
        reply_markup=kb.user_roles_manage_kb(user_id)
    )


@router.callback_query(F.data.startswith("role_pick_"))
@safe_callback()
async def role_pick_handler(callback: types.CallbackQuery):
    """Обработчик после выбора роли из role_selection_kb."""
    parts = callback.data.split("_")
    user_id = int(parts[2])
    role_id = int(parts[3])
    role_name = db.get_role_name_by_id(role_id)
    
    if role_name == 'moderator':
        await callback.message.edit_text(
            f"📍 Выбери топик для назначения модератором:",
            reply_markup=kb.topic_selection_for_role_kb(user_id)
        )
    else:
        success = db.grant_role(user_id, role_id, None)
        if success:
            await callback.answer("✅ Роль назначена.")
        else:
            await callback.answer("❌ Не удалось назначить роль (возможно, уже есть).")
            
        await callback.message.edit_text(
            f"Управление ролями пользователя {user_id}",
            reply_markup=kb.user_roles_manage_kb(user_id)
        )


@router.callback_query(F.data.startswith("role_assign_topic_"))
@safe_callback()
async def role_assign_topic_confirm(callback: types.CallbackQuery, state: FSMContext):
    """Назначение роли модератора после выбора топика в инлайн-клавиатуре."""
    parts = callback.data.split("_")
    user_id = int(parts[3])
    topic_id = int(parts[4])
    mod_role_id = db.get_role_id("moderator")
    
    if mod_role_id == 0:
        await callback.answer("❌ Системная ошибка: роль модератора не найдена.")
        return
        
    success = db.grant_role(user_id, mod_role_id, topic_id)
    if success:
        await callback.answer("✅ Роль модератора назначена.")
    else:
        await callback.answer("❌ Ошибка (возможно, уже модератор этого топика).")

    await callback.message.edit_text(
        f"Управление ролями пользователя {user_id}",
        reply_markup=kb.user_roles_manage_kb(user_id)
    )


@router.callback_query(F.data.startswith("role_revoke_"))
@safe_callback()
async def role_revoke_handler(callback: types.CallbackQuery):
    """Отзыв роли у пользователя."""
    parts = callback.data.split("_")
    user_id = int(parts[2])
    role_id = int(parts[3])
    topic_id_str = parts[4]
    topic_id = None if topic_id_str == "None" else int(topic_id_str)

    success = db.revoke_role(user_id, role_id, topic_id)
    if success:
        await callback.answer("✅ Роль отозвана.")
    else:
        await callback.answer("❌ Ошибка при отзыве роли.")

    await callback.message.edit_reply_markup(reply_markup=kb.user_roles_manage_kb(user_id))



