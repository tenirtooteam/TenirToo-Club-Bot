# Файл: handlers/moderator.py
import logging
import math
from aiogram import Router, F, types
from aiogram.filters import Command, Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import keyboards as kb
from database import db
from config import GROUP_ID
from services.callback_guard import safe_callback
from services.ui_service import UIService
from services.permission_service import PermissionService
from services.management_service import ManagementService

logger = logging.getLogger(__name__)


class IsTopicManager(Filter):
    """Фильтр: суперадмин, глобальный admin или модератор конкретного топика."""
    async def __call__(self, event: types.Message | types.CallbackQuery) -> bool:
        user_id = event.from_user.id
        
        # Если это сообщение из группы, разрешаем только команду /mod
        if isinstance(event, types.Message) and event.chat.type != "private":
            if not (event.text and event.text.startswith("/mod")):
                return False
        
        # Проверка прав доступа через PermissionService
        if PermissionService.is_global_admin(user_id):
            return True
        return len(PermissionService.get_manageable_topics(user_id)) > 0


router = Router()
router.message.filter(IsTopicManager())
router.callback_query.filter(IsTopicManager())


class ModeratorStates(StatesGroup):
    waiting_for_topic_name = State()
    waiting_for_user_data = State()
    waiting_for_direct_access_user = State()


def extract_topic_id_from_callback(callback: types.CallbackQuery) -> int:
    """Извлекает topic_id из callback-данных вида ..._<topic_id> или ..._<topic_id>_pg_<page>."""
    base_data = callback.data.split("_pg_")[0]
    parts = base_data.split("_")
    try:
        return int(parts[-1])
    except (ValueError, IndexError):
        return -1


@router.message(Command("mod"))
@UIService.sterile_command(redirect=True, error_prefix="панель модератора")
async def moderator_dashboard(message: types.Message, state: FSMContext):
    """Главное меню модератора (выбор своего топика). Поддерживает переход из групп в ЛС."""
    user_id = message.from_user.id
    manageable_topics = PermissionService.get_manageable_topics(user_id)

    if not manageable_topics:
        return "❌ У вас нет прав на управление каким-либо топиком.", None

    return "🛠 <b>Панель модератора</b>\nВыберите топик для управления:", kb.moderator_topics_list_kb(manageable_topics)


@router.callback_query(F.data.startswith("moderator"))
@safe_callback()
async def back_to_moderator_main(callback: types.CallbackQuery, state: FSMContext):
    await UIService.generic_navigator(state, callback, callback.data)

@router.callback_query(F.data.startswith("mod_topic_select_"))
@safe_callback()
async def moderator_topic_selected(callback: types.CallbackQuery, state: FSMContext):
    await UIService.generic_navigator(state, callback, callback.data)


@router.callback_query(F.data.startswith("mod_topic_rename_"))
@safe_callback()
async def moderator_rename_topic_start(callback: types.CallbackQuery, state: FSMContext):
    """Запрос нового имени для топика."""
    topic_id = extract_topic_id_from_callback(callback)
    user_id = callback.from_user.id

    if not PermissionService.can_manage_topic(user_id, topic_id):
        await callback.answer("❌ Доступ запрещён.", show_alert=True)
        return

    await state.update_data(moderator_edit_topic_id=topic_id)
    await UIService.ask_input(state, callback, "✍️ Введите новое название топика:", ModeratorStates.waiting_for_topic_name)


@router.message(ModeratorStates.waiting_for_topic_name)
async def moderator_rename_topic_finish(message: types.Message, state: FSMContext):
    """Сохранение нового имени топика."""
    data = await state.get_data()
    topic_id = data.get("moderator_edit_topic_id")
    new_name = message.text.strip()

    if not new_name:
        await UIService.show_temp_message(state, message, "❌ Название не может быть пустым.")
        return

    success, msg = ManagementService.update_topic_name(topic_id, new_name)
    if not success:
        await UIService.show_temp_message(state, message, msg)
        return

    status = ""
    if topic_id != -1:
        try:
            await message.bot.edit_forum_topic(chat_id=GROUP_ID, message_thread_id=topic_id, name=new_name)
            status = "\n✅ Синхронизировано с Telegram."
        except Exception as e:
            logger.warning(f"⚠️ Ошибка API: {e}")
            status = f"\n⚠️ Только в БД (Ошибка API)"

    await UIService.generic_navigator(state, message, f"mod_topic_select_{topic_id}")


@router.callback_query(F.data.startswith("mod_topic_groups_"))
@safe_callback()
async def moderator_show_groups(callback: types.CallbackQuery, state: FSMContext):
    await UIService.generic_navigator(state, callback, callback.data)



@router.callback_query(F.data.startswith("mod_gr_addlist_"))
@safe_callback()
async def moderator_show_unattached_groups(callback: types.CallbackQuery, state: FSMContext):
    await UIService.generic_navigator(state, callback, callback.data)

@router.callback_query(F.data.startswith("mod_gr_link_"))
@safe_callback()
async def moderator_link_group(callback: types.CallbackQuery, state: FSMContext):
    """Привязывает выбранную группу к топику."""
    parts = callback.data.split("_")
    group_id = int(parts[3])
    topic_id = int(parts[4])
    user_id = callback.from_user.id

    if not PermissionService.can_manage_topic(user_id, topic_id):
        await callback.answer("❌ Доступ запрещён.", show_alert=True)
        return

    ManagementService.add_topic_to_group(group_id, topic_id)
    await callback.answer("✅ Группа привязана.")
    
    await UIService.generic_navigator(state, callback, f"mod_topic_groups_{topic_id}")

@router.callback_query(F.data.startswith("mod_group_remove_"))
@safe_callback()
async def moderator_remove_group_init(callback: types.CallbackQuery, state: FSMContext):
    """Инициация отвязки группы от топика с подтверждением."""
    parts = callback.data.split("_")
    group_id, topic_id = int(parts[3]), int(parts[4])
    text, back = UIService.get_confirmation_ui("mod_topic_del", topic_id, extra_id=group_id)
    await UIService.show_menu(
        state, callback, text,
        reply_markup=kb.confirmation_kb("mod_topic_del", topic_id, back, extra_id=group_id)
    )


@router.callback_query(F.data.startswith("mod_users_manage_"))
@safe_callback()
async def moderator_manage_users(callback: types.CallbackQuery, state: FSMContext):
    await UIService.generic_navigator(state, callback, callback.data)


@router.callback_query(F.data.startswith("mod_tgl_dir_"))
@safe_callback()
async def moderator_toggle_direct_access(callback: types.CallbackQuery, state: FSMContext):
    """Выдает или забирает прямой доступ пользователя к топику."""
    parts = callback.data.split("_")
    target_user_id = int(parts[3])
    topic_id = int(parts[4])
    user_id = callback.from_user.id

    if not PermissionService.can_manage_topic(user_id, topic_id):
        await callback.answer("❌ Доступ запрещён.", show_alert=True)
        return

    direct_users = set(u[0] for u in db.get_direct_access_users(topic_id))
    all_authorized = set(u[0] for u in db.get_topic_authorized_users(topic_id))
    group_users = all_authorized - direct_users

    if target_user_id in group_users and target_user_id not in direct_users:
        await callback.answer("🌐 Пользователь имеет доступ через общую группу. Изменяется только глобальным администратором.", show_alert=True)
        return

    if target_user_id in direct_users:
        success, msg = ManagementService.revoke_direct_access(target_user_id, topic_id)
        await callback.answer(msg)
    else:
        success, msg = ManagementService.grant_direct_access(str(target_user_id), topic_id)
        await callback.answer(msg)

    await UIService.generic_navigator(state, callback, f"mod_users_manage_{topic_id}")


@router.callback_query(F.data.startswith("mod_add_user_list_"))
@safe_callback()
async def moderator_add_user_list(callback: types.CallbackQuery, state: FSMContext):
    """Начало выдачи прямого доступа: запрос ID или имени пользователя."""
    parts = callback.data.split("_pg_")
    page = int(parts[1]) if len(parts) > 1 else 1
    topic_id = extract_topic_id_from_callback(callback)
    user_id = callback.from_user.id

    if not PermissionService.can_manage_topic(user_id, topic_id):
        await callback.answer("❌ Доступ запрещён.", show_alert=True)
        return

    await state.update_data(moderator_direct_access_topic=topic_id)
    await state.set_state(ModeratorStates.waiting_for_direct_access_user)
    await UIService.show_menu(
        state, callback, 
        "✍️ Введите ID пользователя или его Фамилию и Имя для поиска:\n\nИли выберите из списка:",
        reply_markup=kb.moderator_users_to_add_kb(topic_id, page=page)
    )

@router.message(ModeratorStates.waiting_for_direct_access_user)
async def process_direct_access_user_search(message: types.Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    topic_id = data.get("moderator_direct_access_topic")

    success, result = ManagementService.grant_direct_access(text, topic_id)
    if success:
        await UIService.generic_navigator(state, message, f"mod_users_manage_{topic_id}")
        return

    if result == "SEARCH_REQUIRED":
        # Делегируем в глобальный поиск из common.py
        from handlers.common import SearchStates
        await state.update_data(search_type="user", search_action="dir_add", search_context=topic_id)
        await state.set_state(SearchStates.waiting_for_query)
        # "Пробрасываем" сообщение в глобальный хендлер
        from handlers.common import search_query_handler
        return await search_query_handler(message, state)
    else:
        await UIService.show_temp_message(state, message, result)


@router.callback_query(F.data.startswith("mod_back_to_topic_"))
@safe_callback()
async def moderator_back_to_topic(callback: types.CallbackQuery, state: FSMContext):
    await UIService.generic_navigator(state, callback, callback.data)

# --- УПРАВЛЕНИЕ МОДЕРАТОРАМИ ТОПИКА ---

@router.callback_query(F.data.startswith("mod_topic_moderators_"))
@safe_callback()
async def moderator_show_moderators(callback: types.CallbackQuery, state: FSMContext):
    await UIService.generic_navigator(state, callback, callback.data)


@router.callback_query(F.data.startswith("mod_moderator_add_"))
@safe_callback()
async def moderator_add_moderator_start(callback: types.CallbackQuery, state: FSMContext):
    """Запрос ID пользователя для назначения модератором."""
    from handlers.common import SearchStates
    topic_id = extract_topic_id_from_callback(callback)
    user_id = callback.from_user.id

    if not PermissionService.can_manage_topic(user_id, topic_id):
        await callback.answer("❌ Доступ запрещён.", show_alert=True)
        return

    await state.update_data(search_type="user", search_action="mod_add", search_context=topic_id)
    await UIService.ask_input(state, callback, "✍️ Введите ID пользователя или его Фамилию и Имя для поиска:", SearchStates.waiting_for_query)


@router.callback_query(F.data.startswith("mod_moderator_remove_"))
@safe_callback()
async def moderator_remove_moderator_init(callback: types.CallbackQuery, state: FSMContext):
    """Снятие роли модератора с подтверждением."""
    parts = callback.data.split("_")
    target_user_id, topic_id = int(parts[3]), int(parts[4])
    text, back = UIService.get_confirmation_ui("mod_rem", target_user_id, extra_id=topic_id)
    await UIService.show_menu(
        state, callback, text,
        reply_markup=kb.confirmation_kb("mod_rem", target_user_id, back, extra_id=topic_id)
    )

