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
    
    return "🛠 <b>Панель управления</b>", kb.main_admin_kb()


@router.callback_query(F.data == "admin_main")
@safe_callback()
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await UIService.generic_navigator(state, callback, callback.data)


# --- УПРАВЛЕНИЕ ГРУППАМИ ---

@router.callback_query(F.data.startswith("manage_groups"))
@safe_callback()
async def show_groups(callback: types.CallbackQuery, state: FSMContext):
    await UIService.generic_navigator(state, callback, callback.data)


@router.callback_query(F.data.startswith("topic_assign_pg_"))
@safe_callback()
async def role_assign_choose_topic(callback: types.CallbackQuery, state: FSMContext):
    await UIService.generic_navigator(state, callback, callback.data)


@router.callback_query(F.data.startswith("group_info_"))
@safe_callback()
async def group_detail(callback: types.CallbackQuery, state: FSMContext):
    await UIService.generic_navigator(state, callback, callback.data)


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

    await UIService.show_admin_dashboard(state, message, text=text)


@router.callback_query(F.data.startswith("del_group_"))
@safe_callback()
async def delete_group_init(callback: types.CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split("_")[-1])
    text, back = UIService.get_confirmation_ui("group_del", group_id)
    await UIService.show_menu(
        state, callback, text, 
        reply_markup=kb.confirmation_kb("group_del", group_id, back)
    )


# --- УПРАВЛЕНИЕ ТОПИКАМИ ---

@router.callback_query(F.data.startswith("all_topics_list"))
@safe_callback()
async def show_all_topics(callback: types.CallbackQuery, state: FSMContext):
    await UIService.generic_navigator(state, callback, callback.data)


@router.callback_query(F.data.startswith("topic_global_view_") | F.data.startswith("topic_in_group_"))
@safe_callback()
async def topic_detail(callback: types.CallbackQuery, state: FSMContext):
    await UIService.generic_navigator(state, callback, callback.data)


@router.callback_query(F.data.startswith("group_topics_list_"))
@safe_callback()
async def show_group_topics(callback: types.CallbackQuery, state: FSMContext):
    await UIService.generic_navigator(state, callback, callback.data)


@router.callback_query(F.data.startswith("topic_del_"))
@safe_callback()
async def remove_topic_from_group_init(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    topic_id, group_id = int(parts[2]), int(parts[3])
    text, back = UIService.get_confirmation_ui("topic_del", topic_id, extra_id=group_id)
    await UIService.show_menu(
        state, callback, text,
        reply_markup=kb.confirmation_kb("topic_del", topic_id, back, extra_id=group_id)
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
    success, msg = ManagementService.add_topic_to_group(group_id, topic_id)
    await callback.answer(msg)
    await UIService.generic_navigator(state, callback, f"group_topics_list_{group_id}")


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

    ManagementService.update_topic_name(t_id, new_name)

    status = ""
    if t_id != -1:
        try:
            await message.bot.edit_forum_topic(chat_id=GROUP_ID, message_thread_id=t_id, name=new_name)
            status = "\n✅ Синхронизировано с Telegram."
        except Exception as e:
            logger.warning(f"⚠️ Ошибка API: {e}")
            status = f"\n⚠️ Только в БД (Ошибка API)"

    await UIService.show_admin_dashboard(state, message, text=f"✅ Топик {t_id} обновлен.{status}")





@router.callback_query(F.data.startswith("global_topic_del_"))
@safe_callback()
async def global_topic_delete_init(callback: types.CallbackQuery, state: FSMContext):
    topic_id = int(callback.data.split("_")[-1])
    text, back = UIService.get_confirmation_ui("global_topic_del", topic_id)
    await UIService.show_menu(
        state, callback, text,
        reply_markup=kb.confirmation_kb("global_topic_del", topic_id, back)
    )


# --- УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ---

@router.callback_query(F.data.startswith("manage_users"))
@safe_callback()
async def show_users(callback: types.CallbackQuery, state: FSMContext):
    await UIService.generic_navigator(state, callback, callback.data)


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

    await UIService.generic_navigator(state, message, "manage_users")


@router.callback_query(F.data.startswith("user_info_"))
@safe_callback()
async def user_detail(callback: types.CallbackQuery, state: FSMContext):
    await UIService.generic_navigator(state, callback, callback.data)


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
    success, msg = ManagementService.update_user_name(data['edit_user_id'], parts[0], parts[1])
    if not success:
        await UIService.show_temp_message(state, message, msg)
        return
    await UIService.generic_navigator(state, message, "manage_users")


@router.callback_query(F.data.startswith("user_groups_manage_"))
@safe_callback()
async def user_groups_ui(callback: types.CallbackQuery, state: FSMContext):
    await UIService.generic_navigator(state, callback, callback.data)


@router.callback_query(F.data.startswith("user_group_toggle_"))
@safe_callback()
async def toggle_group(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    user_id, group_id = int(parts[3]), int(parts[4])

    success, msg = ManagementService.toggle_user_group(user_id, group_id)
    await callback.answer(msg)
    await UIService.generic_navigator(state, callback, f"user_groups_manage_{user_id}")


@router.callback_query(F.data.startswith("user_delete_"))
@safe_callback()
async def user_delete_init(callback: types.CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[-1])
    text, back = UIService.get_confirmation_ui("user_del", user_id)
    await UIService.show_menu(
        state, callback, text,
        reply_markup=kb.confirmation_kb("user_del", user_id, back)
    )

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
    await UIService.generic_navigator(state, callback, callback.data)


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
        success, msg = ManagementService.grant_role(user_id, role_id, None)
        await callback.answer(msg)
        await UIService.generic_navigator(state, callback, f"user_roles_manage_{user_id}")


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
        
    success = ManagementService.grant_role(user_id, mod_role_id, topic_id)
    if success:
        await callback.answer("✅ Роль модератора назначена.")
    else:
        await callback.answer("❌ Ошибка (возможно, уже модератор этого топика).")

    await UIService.generic_navigator(state, callback, f"user_roles_manage_{user_id}")


@router.callback_query(F.data.startswith("role_revoke_"))
@safe_callback()
async def role_revoke_init(callback: types.CallbackQuery, state: FSMContext):
    """Отзыв роли у пользователя с подтверждением."""
    parts = callback.data.split("_")
    user_id, role_id = int(parts[2]), int(parts[3])
    topic_id_str = parts[4]
    extra = 0 if topic_id_str == "None" else int(topic_id_str)
    
    text, back = UIService.get_confirmation_ui(f"role_rev_{role_id}", user_id, extra_id=extra)
    await UIService.show_menu(
        state, callback, text,
        reply_markup=kb.confirmation_kb(f"role_rev_{role_id}", user_id, back, extra_id=extra)
    )



