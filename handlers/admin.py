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
from services.management_service import ManagementService

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
@UIService.sterile_command(redirect=True, error_prefix="админ-панель")
async def admin_dashboard(message: types.Message, state: FSMContext):
    """Панель управления администратора с поддержкой перехода из групп в ЛС."""
    user_id = message.from_user.id
    is_superadmin = PermissionService.is_superadmin(user_id)
    
    return "🛠 <b>Панель управления</b>", kb.main_admin_kb(is_superadmin=is_superadmin)


@router.callback_query(F.data == "admin_main")
@safe_callback()
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    is_superadmin = PermissionService.is_superadmin(callback.from_user.id)
    await UIService.show_menu(
        state, callback, 
        "🛠 <b>Панель управления</b>", 
        reply_markup=kb.main_admin_kb(is_superadmin=is_superadmin)
    )


# --- УПРАВЛЕНИЕ ГРУППАМИ ---

@router.callback_query(F.data.startswith("manage_groups"))
@safe_callback()
async def show_groups(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_pg_")
    page = int(parts[1]) if len(parts) > 1 else 1
    await UIService.show_menu(state, callback, "📂 <b>Группы доступа:</b>", reply_markup=kb.groups_list_kb(page=page))


@router.callback_query(F.data.startswith("topic_assign_pg_"))
@safe_callback()
async def role_assign_choose_topic(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_pg_")
    page = int(parts[1]) if len(parts) > 1 else 1
    user_id = int(parts[0].replace("topic_assign_pg_", ""))
    user_name = db.get_user_name(user_id)
    await UIService.show_menu(
        state, callback, 
        f"📍 Выбери топик для {user_name} в роли Модератора:",
        reply_markup=kb.topic_selection_for_role_kb(user_id, page=page)
    )


@router.callback_query(F.data.startswith("group_info_"))
@safe_callback()
async def group_detail(callback: types.CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split("_")[-1])
    group_name = db.get_group_name(group_id)
    await UIService.show_menu(
        state, callback, 
        f"⚙️ <b>Настройка группы: {group_name}</b> (ID: {group_id})",
        reply_markup=kb.group_edit_kb(group_id)
    )


@router.callback_query(F.data == "add_group_start")
@safe_callback()
async def add_group_init(callback: types.CallbackQuery, state: FSMContext):
    await UIService.ask_input(state, callback, "✍️ Введи название для новой группы:", AdminStates.waiting_for_group_name)


@router.message(AdminStates.waiting_for_group_name)
async def process_group_add(message: types.Message, state: FSMContext):
    success, text = ManagementService.create_group(message.text)
    if not success:
        await UIService.show_temp_message(state, message, text)
        return

    await UIService.show_menu(state, message, text, reply_markup=kb.main_admin_kb())


@router.callback_query(F.data.startswith("del_group_"))
@safe_callback()
async def delete_group_handler(callback: types.CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split("_")[-1])
    db.delete_group(group_id)
    await callback.answer(f"Группа удалена")
    await show_groups(callback, state)


# --- УПРАВЛЕНИЕ ТОПИКАМИ ---

@router.callback_query(F.data.startswith("all_topics_list"))
@safe_callback()
async def show_all_topics(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_pg_")
    page = int(parts[1]) if len(parts) > 1 else 1
    await UIService.show_menu(state, callback, "📍 <b>Все топики:</b>", reply_markup=kb.all_topics_kb(page=page))


@router.callback_query(
    F.data.startswith("topic_global_view_") | F.data.startswith("topic_in_group_")
)
@safe_callback()
async def topic_detail(callback: types.CallbackQuery, state: FSMContext):
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
    await UIService.show_menu(state, callback, text, reply_markup=kb.topic_edit_kb(topic_id, group_id=group_id))


@router.callback_query(F.data.startswith("group_topics_list_"))
@safe_callback()
async def show_group_topics(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_pg_")
    page = int(parts[1]) if len(parts) > 1 else 1
    group_id = int(parts[0].replace("group_topics_list_", ""))
    g_name = db.get_group_name(group_id)
    await UIService.show_menu(
        state, callback,
        f"📍 <b>Топики в группе {g_name} (ID: {group_id}):</b>",
        reply_markup=kb.group_topics_list_kb(group_id, page=page)
    )


@router.callback_query(F.data.startswith("topic_del_"))
@safe_callback()
async def remove_topic_from_group_handler(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    topic_id, group_id = int(parts[2]), int(parts[3])
    db.remove_topic_from_group(group_id, topic_id)
    await callback.answer("Топик убран из группы")
    group_name = db.get_group_name(group_id)
    await UIService.show_menu(
        state, callback,
        f"📍 <b>Топики группы: {group_name}</b>",
        reply_markup=kb.group_topics_list_kb(group_id)
    )


@router.callback_query(F.data.startswith("add_topic_to_"))
@safe_callback()
async def add_topic_to_group_init(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_pg_")
    page = int(parts[1]) if len(parts) > 1 else 1
    group_id = int(parts[0].replace("add_topic_to_", ""))
    await UIService.show_menu(
        state, callback, 
        "📍 Выберите топик для добавления в группу:",
        reply_markup=kb.available_topics_kb(group_id, page=page)
    )


@router.callback_query(F.data.startswith("topic_add_confirm_"))
@safe_callback()
async def confirm_add_topic(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    topic_id, group_id = int(parts[3]), int(parts[4])
    db.add_topic_to_group(group_id, topic_id)
    group_name = db.get_group_name(group_id)
    await callback.answer("✅ Топик добавлен!")
    await UIService.show_menu(
        state, callback,
        f"📍 <b>Топики группы: {group_name}</b>",
        reply_markup=kb.group_topics_list_kb(group_id)
    )


@router.callback_query(F.data.startswith("topic_rename_"))
@safe_callback()
async def topic_rename_init(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    t_id, g_id = int(parts[2]), int(parts[3])
    await state.update_data(edit_topic_id=t_id, edit_group_id=g_id)
    await UIService.ask_input(state, callback, f"✍️ Введи новое название для ID: {t_id}:", AdminStates.waiting_for_topic_name)


@router.message(AdminStates.waiting_for_topic_name)
async def process_topic_name_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    t_id = data.get('edit_topic_id')
    new_name = message.text

    if t_id is None:
        await state.set_state(None)
        await UIService.show_temp_message(state, message, "❌ Ошибка: данные топика потеряны.")
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

    await UIService.show_menu(
        state, message, 
        f"✅ Топик {t_id} обновлен.{status}", 
        reply_markup=kb.main_admin_kb()
    )





@router.callback_query(F.data.startswith("global_topic_del_"))
@safe_callback()
async def global_topic_delete_handler(callback: types.CallbackQuery, state: FSMContext):
    topic_id = int(callback.data.split("_")[-1])
    db.delete_topic(topic_id)
    await callback.answer("✅ Топик полностью удален из БД!")
    await show_all_topics(callback, state)


# --- УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ---

@router.callback_query(F.data.startswith("manage_users"))
@safe_callback()
async def show_users(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_pg_")
    page = int(parts[1]) if len(parts) > 1 else 1
    await UIService.show_menu(state, callback, "👥 <b>Список пользователей:</b>", reply_markup=kb.users_list_kb(page=page))


@router.callback_query(F.data == "add_user_start")
@safe_callback()
async def add_user_init(callback: types.CallbackQuery, state: FSMContext):
    await UIService.ask_input(state, callback, "✍️ Введи: <code>ID Имя Фамилия</code>", AdminStates.waiting_for_user_data)


@router.message(AdminStates.waiting_for_user_data)
async def process_user_add(message: types.Message, state: FSMContext):
    success, text = ManagementService.add_user(message.text)
    if not success:
        await UIService.show_temp_message(state, message, text)
        return

    await UIService.show_menu(state, message, text, reply_markup=kb.users_list_kb())


@router.callback_query(F.data.startswith("user_info_"))
@safe_callback()
async def user_detail(callback: types.CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[-1])
    user_name = db.get_user_name(user_id)
    user_groups = db.get_user_groups(user_id)
    groups_str = ", ".join(g[1] for g in user_groups) if user_groups else "нет активных групп"
    
    # Собираем роли и топики
    roles = list(db.get_user_roles(user_id))
    
    # Доступные топики (ID и Названия)
    available_ids = db.get_user_available_topics(user_id)
    available_topics = [(t_id, db.get_topic_name(t_id)) for t_id in available_ids]

    text = UIService.format_user_card(user_id, user_name, groups_str, roles, available_topics)
    await UIService.show_menu(state, callback, text, reply_markup=kb.user_edit_kb(user_id))


@router.callback_query(F.data.startswith("user_rename_"))
@safe_callback()
async def user_rename_init(callback: types.CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[-1])
    await state.update_data(edit_user_id=user_id)
    await UIService.ask_input(state, callback, "✍️ Введи новое Имя и Фамилию:", AdminStates.waiting_for_new_name)


@router.message(AdminStates.waiting_for_new_name)
async def process_user_rename(message: types.Message, state: FSMContext):
    parts = message.text.split()
    if len(parts) < 2:
        await UIService.show_temp_message(state, message, "❌ Введи Имя и Фамилию!")
        return

    data = await state.get_data()
    db.update_user_name(data['edit_user_id'], parts[0], parts[1])
    await UIService.show_menu(state, message, "✅ Данные обновлены.", reply_markup=kb.users_list_kb())


@router.callback_query(F.data.startswith("user_groups_manage_"))
@safe_callback()
async def user_groups_ui(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_pg_")
    page = int(parts[1]) if len(parts) > 1 else 1
    user_id = int(parts[0].replace("user_groups_manage_", ""))
    u_name = db.get_user_name(user_id)
    await UIService.show_menu(
        state, callback, 
        f"Разрешения супер-групп пользователя {u_name}:",
        reply_markup=kb.user_groups_edit_kb(user_id, page=page)
    )


@router.callback_query(F.data.startswith("user_group_toggle_"))
@safe_callback()
async def toggle_group(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    user_id, group_id = int(parts[3]), int(parts[4])

    user_groups = set(g[0] for g in db.get_user_groups(user_id))
    if group_id in user_groups:
        db.revoke_group(user_id, group_id)
    else:
        db.grant_group(user_id, group_id)

    u_name = db.get_user_name(user_id)
    await UIService.show_menu(
        state, callback,
        f"Разрешения супер-групп пользователя {u_name}:",
        reply_markup=kb.user_groups_edit_kb(user_id)
    )


@router.callback_query(F.data.startswith("user_delete_"))
@safe_callback()
async def user_delete_handler(callback: types.CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[-1])
    db.delete_user(user_id)
    await callback.answer("Пользователь удален")
    await show_users(callback, state)

# --- УПРАВЛЕНИЕ РОЛЯМИ ---




@router.callback_query(F.data.startswith("role_assign_user_"))
@safe_callback()
async def role_assign_choose_user(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назначить роль' из карточки пользователя."""
    user_id = int(callback.data.split("_")[-1])
    await UIService.show_menu(
        state, callback, 
        f"Выберите роль для пользователя {db.get_user_name(user_id)}:",
        reply_markup=kb.role_selection_kb(user_id)
    )


@router.callback_query(F.data.startswith("user_roles_manage_"))
@safe_callback()
async def user_roles_manage_handler(callback: types.CallbackQuery, state: FSMContext):
    """Меню управления ролями конкретного пользователя."""
    user_id = int(callback.data.split("_")[-1])
    await UIService.show_menu(
        state, callback, 
        f"Управление ролями пользователя {user_id}",
        reply_markup=kb.user_roles_manage_kb(user_id)
    )


@router.callback_query(F.data.startswith("role_pick_"))
@safe_callback()
async def role_pick_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик после выбора роли из role_selection_kb."""
    parts = callback.data.split("_")
    user_id = int(parts[2])
    role_id = int(parts[3])
    role_name = db.get_role_name_by_id(role_id)
    
    if role_name == 'moderator':
        await UIService.show_menu(
            state, callback, 
            f"📍 Выбери топик для назначения модератором:",
            reply_markup=kb.topic_selection_for_role_kb(user_id)
        )
    else:
        success = db.grant_role(user_id, role_id, None)
        if success:
            await callback.answer("✅ Роль назначена.")
        else:
            await callback.answer("❌ Не удалось назначить роль (возможно, уже есть).")
            
        await UIService.show_menu(
            state, callback, 
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

    await UIService.show_menu(
        state, callback, 
        f"Управление ролями пользователя {user_id}",
        reply_markup=kb.user_roles_manage_kb(user_id)
    )


@router.callback_query(F.data.startswith("role_revoke_"))
@safe_callback()
async def role_revoke_handler(callback: types.CallbackQuery, state: FSMContext):
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

    await UIService.show_menu(
        state, callback, 
        f"Управление ролями пользователя {user_id}",
        reply_markup=kb.user_roles_manage_kb(user_id)
    )



