# Файл: handlers/moderator.py
import logging
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

logger = logging.getLogger(__name__)


class IsTopicManager(Filter):
    """Фильтр: суперадмин, глобальный админ или модератор конкретного топика."""
    async def __call__(self, event: types.Message | types.CallbackQuery) -> bool:
        user_id = event.from_user.id
        # Для сообщений из групп игнорируем (модератор работает только в ЛС)
        if isinstance(event, types.Message) and event.chat.type != "private":
            return False
        if PermissionService.is_global_admin(user_id):
            return True
        return len(PermissionService.get_manageable_topics(user_id)) > 0


router = Router()
router.message.filter(IsTopicManager())
router.callback_query.filter(IsTopicManager())


class ModeratorStates(StatesGroup):
    waiting_for_topic_name = State()
    waiting_for_user_data = State()


def extract_topic_id_from_callback(callback: types.CallbackQuery) -> int:
    """Извлекает topic_id из callback-данных вида ..._<topic_id>."""
    parts = callback.data.split("_")
    try:
        return int(parts[-1])
    except (ValueError, IndexError):
        return -1


@router.message(Command("mod"))
async def moderator_dashboard(message: types.Message, state: FSMContext):
    """Главное меню модератора (выбор своего топика)."""
    await UIService.finish_input(state, message)

    user_id = message.from_user.id
    manageable_topics = PermissionService.get_manageable_topics(user_id)

    if not manageable_topics:
        await message.answer("❌ У вас нет прав на управление каким-либо топиком.")
        return

    sent_message = await message.answer(
        "🛠 <b>Панель модератора</b>\nВыберите топик для управления:",
        reply_markup=kb.moderator_topics_list_kb(manageable_topics),
        parse_mode="HTML"
    )
    await state.update_data(last_menu_id=sent_message.message_id)


@router.callback_query(F.data == "moderator")
@safe_callback()
async def back_to_moderator_main(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню модератора."""
    user_id = callback.from_user.id
    manageable_topics = PermissionService.get_manageable_topics(user_id)

    if not manageable_topics:
        await callback.message.edit_text("❌ У вас нет прав на управление каким-либо топиком.")
        return

    await callback.message.edit_text(
        "🛠 <b>Панель модератора</b>\nВыберите топик для управления:",
        reply_markup=kb.moderator_topics_list_kb(manageable_topics),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("mod_topic_select_"))
@safe_callback()
async def moderator_topic_selected(callback: types.CallbackQuery, state: FSMContext):
    """После выбора топика показывает меню управления им."""
    topic_id = extract_topic_id_from_callback(callback)
    user_id = callback.from_user.id

    if not PermissionService.can_manage_topic(user_id, topic_id):
        await callback.answer("❌ У вас нет прав на управление этим топиком.", show_alert=True)
        return

    await state.update_data(moderator_current_topic=topic_id)
    topic_name = db.get_topic_name(topic_id)

    await callback.message.edit_text(
        f"📍 <b>Управление топиком: {topic_name}</b> (ID: {topic_id})",
        reply_markup=kb.moderator_topic_menu_kb(topic_id),
        parse_mode="HTML"
    )


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
    await state.set_state(ModeratorStates.waiting_for_topic_name)
    await callback.message.answer("✍️ Введите новое название топика:")


@router.message(ModeratorStates.waiting_for_topic_name)
async def moderator_rename_topic_finish(message: types.Message, state: FSMContext):
    """Сохранение нового имени топика."""
    data = await state.get_data()
    topic_id = data.get("moderator_edit_topic_id")
    new_name = message.text.strip()

    if not new_name:
        await message.answer("❌ Название не может быть пустым.")
        return

    db.update_topic_name(topic_id, new_name)
    status = ""
    if topic_id != -1:
        try:
            await message.bot.edit_forum_topic(chat_id=GROUP_ID, message_thread_id=topic_id, name=new_name)
            status = "\n✅ Синхронизировано с Telegram."
        except Exception as e:
            logger.warning(f"⚠️ Ошибка API: {e}")
            status = f"\n⚠️ Только в БД (Ошибка API)"

    await UIService.finish_input(state, message)

    sent_message = await message.answer(
        f"✅ Топик {topic_id} переименован в '{new_name}'.{status}",
        reply_markup=kb.moderator_topic_menu_kb(topic_id),
        parse_mode="HTML"
    )
    await state.update_data(last_menu_id=sent_message.message_id)


@router.callback_query(F.data.startswith("mod_topic_groups_"))
@safe_callback()
async def moderator_show_groups(callback: types.CallbackQuery):
    """Показывает группы, связанные с топиком."""
    topic_id = extract_topic_id_from_callback(callback)
    user_id = callback.from_user.id

    if not PermissionService.can_manage_topic(user_id, topic_id):
        await callback.answer("❌ Доступ запрещён.", show_alert=True)
        return

    await callback.message.edit_text(
        f"📂 <b>Группы доступа для топика {db.get_topic_name(topic_id)}</b>",
        reply_markup=kb.moderator_group_list_kb(topic_id),
        parse_mode="HTML"
    )



@router.callback_query(F.data.startswith("mod_gr_addlist_"))
@safe_callback()
async def moderator_show_unattached_groups(callback: types.CallbackQuery):
    """Показывает список доступных глобальных групп для привязки."""
    topic_id = extract_topic_id_from_callback(callback)
    user_id = callback.from_user.id

    if not PermissionService.can_manage_topic(user_id, topic_id):
        await callback.answer("❌ Доступ запрещён.", show_alert=True)
        return

    await callback.message.edit_text(
        "🔗 <b>Выберите глобальную группу для привязки:</b>",
        reply_markup=kb.moderator_available_groups_kb(topic_id),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("mod_gr_link_"))
@safe_callback()
async def moderator_link_group(callback: types.CallbackQuery):
    """Привязывает выбранную группу к топику."""
    parts = callback.data.split("_")
    group_id = int(parts[3])
    topic_id = int(parts[4])
    user_id = callback.from_user.id

    if not PermissionService.can_manage_topic(user_id, topic_id):
        await callback.answer("❌ Доступ запрещён.", show_alert=True)
        return

    db.add_topic_to_group(group_id, topic_id)
    await callback.answer("✅ Группа привязана.")
    
    await callback.message.edit_text(
        f"📂 <b>Группы доступа для топика {db.get_topic_name(topic_id)}</b>",
        reply_markup=kb.moderator_group_list_kb(topic_id),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("mod_group_remove_"))
@safe_callback()
async def moderator_remove_group(callback: types.CallbackQuery):
    """Отвязывает группу от топика."""
    parts = callback.data.split("_")
    group_id = int(parts[3])
    topic_id = int(parts[4])
    user_id = callback.from_user.id

    if not PermissionService.can_manage_topic(user_id, topic_id):
        await callback.answer("❌ Доступ запрещён.", show_alert=True)
        return

    db.remove_topic_from_group(group_id, topic_id)
    await callback.answer("✅ Группа отвязана.")
    await callback.message.edit_reply_markup(reply_markup=kb.moderator_group_list_kb(topic_id))


@router.callback_query(F.data.startswith("mod_users_manage_"))
@safe_callback()
async def moderator_manage_users(callback: types.CallbackQuery):
    """Управление пользователями в группах топика."""
    topic_id = extract_topic_id_from_callback(callback)
    user_id = callback.from_user.id

    if not PermissionService.can_manage_topic(user_id, topic_id):
        await callback.answer("❌ Доступ запрещён.", show_alert=True)
        return

    await callback.message.edit_text(
        f"👥 <b>Пользователи и группы топика {db.get_topic_name(topic_id)}</b>",
        reply_markup=kb.moderator_users_list_kb(topic_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("mod_tgl_dir_"))
@safe_callback()
async def moderator_toggle_direct_access(callback: types.CallbackQuery):
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
        db.revoke_direct_access(target_user_id, topic_id)
        await callback.answer("🚫 Прямой доступ отозван.")
    else:
        db.grant_direct_access(target_user_id, topic_id)
        await callback.answer("✅ Прямой доступ выдан.")

    await callback.message.edit_reply_markup(reply_markup=kb.moderator_users_list_kb(topic_id))


@router.callback_query(F.data.startswith("mod_add_user_list_"))
@safe_callback()
async def moderator_add_user_list(callback: types.CallbackQuery):
    """Показывает список пользователей, у которых нет вообще никакого доступа к топику."""
    topic_id = extract_topic_id_from_callback(callback)
    user_id = callback.from_user.id

    if not PermissionService.can_manage_topic(user_id, topic_id):
        await callback.answer("❌ Доступ запрещён.", show_alert=True)
        return

    await callback.message.edit_text(
        "➕ <b>Выберите пользователя для выдачи прямого доступа:</b>",
        reply_markup=kb.moderator_users_to_add_kb(topic_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("mod_back_to_topic_"))
@safe_callback()
async def moderator_back_to_topic(callback: types.CallbackQuery):
    """Возврат в меню топика."""
    topic_id = extract_topic_id_from_callback(callback)
    user_id = callback.from_user.id

    if not PermissionService.can_manage_topic(user_id, topic_id):
        await callback.answer("❌ Доступ запрещён.", show_alert=True)
        return

    topic_name = db.get_topic_name(topic_id)
    await callback.message.edit_text(
        f"📍 <b>Управление топиком: {topic_name}</b> (ID: {topic_id})",
        reply_markup=kb.moderator_topic_menu_kb(topic_id),
        parse_mode="HTML"
    )

# --- УПРАВЛЕНИЕ МОДЕРАТОРАМИ ТОПИКА ---

@router.callback_query(F.data.startswith("mod_topic_moderators_"))
@safe_callback()
async def moderator_show_moderators(callback: types.CallbackQuery):
    """Показывает список модераторов топика."""
    topic_id = extract_topic_id_from_callback(callback)
    user_id = callback.from_user.id

    if not PermissionService.can_manage_topic(user_id, topic_id):
        await callback.answer("❌ Доступ запрещён.", show_alert=True)
        return

    await callback.message.edit_text(
        f"👑 <b>Модераторы топика {db.get_topic_name(topic_id)}</b>",
        reply_markup=kb.moderator_topic_moderators_kb(topic_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("mod_moderator_add_"))
@safe_callback()
async def moderator_add_moderator_start(callback: types.CallbackQuery, state: FSMContext):
    """Запрос ID пользователя для назначения модератором."""
    topic_id = extract_topic_id_from_callback(callback)
    user_id = callback.from_user.id

    if not PermissionService.can_manage_topic(user_id, topic_id):
        await callback.answer("❌ Доступ запрещён.", show_alert=True)
        return

    await state.update_data(moderator_add_target_topic=topic_id)
    await state.set_state(ModeratorStates.waiting_for_user_data)
    await callback.message.answer(
        "✍️ Введите ID пользователя, которого хотите сделать модератором этого топика:"
    )


@router.message(ModeratorStates.waiting_for_user_data)
async def moderator_add_moderator_finish(message: types.Message, state: FSMContext):
    """Назначение пользователя модератором топика."""
    try:
        target_user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Некорректный ID. Введите число.")
        return

    if not db.user_exists(target_user_id):
        await message.answer("❌ Пользователь с таким ID не найден в системе.")
        return

    data = await state.get_data()
    topic_id = data.get("moderator_add_target_topic")

    # Проверяем, не является ли уже модератором или админом
    if PermissionService.is_moderator_of_topic(target_user_id, topic_id):
        await message.answer("❌ Этот пользователь уже является модератором данного топика.")
        return

    # Назначаем роль moderator с topic_id
    role_id = db.get_role_id("moderator")
    if role_id == 0:
        await message.answer("❌ Роль 'moderator' не найдена в БД.")
        return

    success = db.grant_role(target_user_id, role_id, topic_id)
    if success:
        await message.answer(
            f"✅ Пользователь {db.get_user_name(target_user_id)} назначен модератором топика {db.get_topic_name(topic_id)}."
        )
    else:
        await message.answer("❌ Не удалось назначить модератора.")

    await UIService.finish_input(state, message)

    sent_message = await message.answer(
        f"👑 <b>Модераторы топика {db.get_topic_name(topic_id)}</b>",
        reply_markup=kb.moderator_topic_moderators_kb(topic_id),
        parse_mode="HTML"
    )
    await state.update_data(last_menu_id=sent_message.message_id)


@router.callback_query(F.data.startswith("mod_moderator_remove_"))
@safe_callback()
async def moderator_remove_moderator(callback: types.CallbackQuery):
    """Снятие роли модератора с пользователя в этом топике."""
    parts = callback.data.split("_")
    target_user_id = int(parts[3])
    topic_id = int(parts[4])

    operator_id = callback.from_user.id
    if not PermissionService.can_manage_topic(operator_id, topic_id):
        await callback.answer("❌ Доступ запрещён.", show_alert=True)
        return

    # Защита от снятия самого себя? Оставим как есть, модератор может снять себя.
    role_id = db.get_role_id("moderator")
    if role_id == 0:
        await callback.answer("❌ Роль не найдена.")
        return

    success = db.revoke_role(target_user_id, role_id, topic_id)
    if success:
        await callback.answer("✅ Модератор удалён.")
    else:
        await callback.answer("❌ Не удалось удалить модератора.")

    await callback.message.edit_reply_markup(
        reply_markup=kb.moderator_topic_moderators_kb(topic_id)
    )

@router.callback_query(F.data == "close_menu")
@safe_callback()
async def global_close_menu(callback: types.CallbackQuery, state: FSMContext):
    await UIService.delete_msg(callback.message)
    await state.update_data(last_menu_id=None)
    await callback.answer("Закрыто")