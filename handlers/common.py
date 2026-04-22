# Файл: handlers/common.py
import math
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database import db
import keyboards as kb
from services.callback_guard import safe_callback
from services.permission_service import PermissionService
from services.ui_service import UIService

router = Router()


def _fetch_search_results(s_type: str, query: str) -> list:
    """Вспомогательная функция: единая точка выборки результатов поиска."""
    if s_type == "user":
        return [(u[0], f"{u[1]} {u[2]}") for u in db.find_users_by_query(query)]
    elif s_type == "group":
        return db.find_groups_by_query(query)
    elif s_type == "topic":
        return db.find_topics_by_query(query)
    return []

class SearchStates(StatesGroup):
    waiting_for_query = State()

@router.message(Command("help"))
@UIService.sterile_command(redirect=True, error_prefix="справку")
async def cmd_help(message: types.Message, state: FSMContext):
    """Глобальная команда помощи: отправка в ЛС и чистка в группе."""
    user_id = message.from_user.id
    
    # Сборка текста справки согласно ролям [cite: 113, 231, 232]
    help_text = (
        "📖 <b>Справочник команд Tenir-Too Bot</b>\n\n"
        "<b>Общие:</b>\n"
        "— /start : Главное меню\n"
        "— /help  : Показать эту справку\n"
    )

    # Добавляем блок для модераторов
    manageable_topics = PermissionService.get_manageable_topics(user_id)
    if manageable_topics:
        help_text += (
            "\n<b>Модератор:</b>\n"
            "— /mod   : Панель управления топиками\n"
        )

    # Добавляем блок для админов
    if PermissionService.is_global_admin(user_id):
        help_text += (
            "\n<b>Администратор:</b>\n"
            "— /admin : Глобальная панель управления\n"
        )
    
    help_text += "\n<i>Все меню открываются в личных сообщениях для чистоты общих чатов.</i>"

    return help_text, None



@router.callback_query(F.data.startswith("usr_pg_"))
@safe_callback()
async def process_user_pagination(callback: types.CallbackQuery, state: FSMContext):
    """Глобальный пагинатор поиска пользователей."""
    page = int(callback.data.split("_")[2])
    data = await state.get_data()
    query = data.get("disambig_query", "")

    if not query:
        await callback.answer("Сессия истекла.", show_alert=True)
        return

    results = db.find_users_by_query(query)
    total_pages = math.ceil(len(results) / 7)
    start_idx = (page - 1) * 7
    markup = kb.user_disambiguation_kb(results[start_idx:start_idx + 7], page, total_pages)
    await UIService.show_menu(state, callback, "👥 Выберите пользователя:", reply_markup=markup)

@router.callback_query(F.data.startswith("usr_pick_"))
@safe_callback()
async def process_user_pick(callback: types.CallbackQuery, state: FSMContext):
    """Глобальный обработчик выбора найденного пользователя."""
    target_user_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    action = data.get("disambig_action")
    context_id = data.get("disambig_context")

    user_name = db.get_user_name(target_user_id)

    if action == "dir_add":
        db.grant_direct_access(target_user_id, context_id)
        await UIService.show_menu(state, callback, f"✅ Прямой доступ выдан пользователю: {user_name}")
    elif action == "mod_add":
        role_id = db.get_role_id("moderator")
        if role_id != 0:
            db.grant_role(target_user_id, role_id, context_id)
            await UIService.show_menu(state, callback, f"✅ {user_name} назначен модератором.")
        else:
            await UIService.show_menu(state, callback, "❌ Ошибка роли.")
    elif action == "admin_role_target":
        await state.set_state(None)
        await UIService.show_menu(
            state, callback,
            f"Пользователь {user_name} выбран. Выберите роль:",
            reply_markup=kb.role_selection_kb(target_user_id)
        )

    # Сбрасываем стейт
    await state.update_data(disambig_query=None, disambig_action=None, disambig_context=None, disambig_role_id=None)

@router.callback_query(F.data == "roles_dashboard")
@safe_callback()
async def roles_dashboard_menu(callback: types.CallbackQuery, state: FSMContext):
    """Общий дашборд ролей для админов и модераторов."""
    user_id = callback.from_user.id
    is_admin = PermissionService.is_global_admin(user_id)
    is_mod = bool(PermissionService.get_manageable_topics(user_id))

    if not (is_admin or is_mod):
        await callback.answer("У вас нет доступа к этому разделу.", show_alert=True)
        return

    text = (
        "🛡 <b>Информационный центр ролей</b>\n\n"
        "Здесь вы можете ознакомиться с правами доступа в системе и увидеть список назначенных ответственных."
    )
    await UIService.show_menu(state, callback, text, reply_markup=kb.roles_dashboard_kb(is_admin))


@router.callback_query(F.data == "roles_faq")
@safe_callback()
async def roles_faq_view(callback: types.CallbackQuery, state: FSMContext):
    """FAQ по ролям."""
    faq_text = (
        "📖 <b>Справочник ролей системы</b>\n\n"
        "👑 <b>Администратор (Глобальный)</b>\n"
        "— Полный доступ ко всем топикам и настройкам.\n"
        "— Управление группами и пользователями.\n"
        "— Назначение ролей другим участникам.\n\n"
        "🛡 <b>Модератор топика</b>\n"
        "— Управление конкретным топиком (переименование).\n"
        "— Управление группами доступа для своего топика.\n"
        "— Управление прямым доступом участников в свой топик.\n"
        "— Назначение других модераторов на свой топик.\n\n"
        "👤 <b>Участник</b>\n"
        "— Может читать и писать в топики, если состоит в нужной группе.\n"
        "— Если доступа нет, сообщения будут удаляться автоматически."
    )
    await UIService.show_menu(state, callback, faq_text, reply_markup=kb.back_to_roles_dashboard_kb())


@router.callback_query(F.data == "list_users_roles")
@safe_callback()
async def list_users_with_roles(callback: types.CallbackQuery, state: FSMContext):
    """Вывод списка всех пользователей, имеющих роли в системе."""
    users = db.get_all_users()
    lines = []

    for u_id, f_name, l_name in users:
        roles = db.get_user_roles(u_id)
        if roles:
            role_strs = []
            for r_name, t_id in roles:
                if t_id:
                    t_name = db.get_topic_name(t_id)
                    role_strs.append(f"{r_name} ({t_name})")
                else:
                    role_strs.append(r_name)
            lines.append(f"👤 {f_name} {l_name} (<code>{u_id}</code>): {', '.join(role_strs)}")

    text = "👥 <b>Список пользователей с ролями:</b>\n\n" + ("\n".join(lines) if lines else "Пока ролей не назначено.")
    await UIService.show_menu(state, callback, text, reply_markup=kb.back_to_roles_dashboard_kb())


@router.callback_query(F.data.startswith("search_start_"))
@safe_callback()
async def search_start_handler(callback: types.CallbackQuery, state: FSMContext):
    """Универсальный инициатор поиска."""
    parts = callback.data.split("_")
    search_type = parts[2]   # user, group, topic
    search_action = parts[3] # info, select, add_to_group, etc.
    search_context = parts[4] if len(parts) > 4 else None
    
    prompts = {
        "user": "Введите имя, фамилию или ID пользователя для поиска:",
        "group": "Введите название группы для поиска:",
        "topic": "Введите название топика для поиска:"
    }
    
    await state.update_data(
        search_type=search_type,
        search_action=search_action,
        search_context=search_context
    )
    
    await UIService.ask_input(state, callback, f"🔎 {prompts.get(search_type, 'Введите запрос для поиска:')}", SearchStates.waiting_for_query)


@router.message(SearchStates.waiting_for_query)
async def search_query_handler(message: types.Message, state: FSMContext):
    """Обработка введенного поискового запроса."""
    query = message.text.strip()
    data = await state.get_data()
    s_type = data.get("search_type")
    s_action = data.get("search_action")
    s_context = data.get("search_context")

    results = _fetch_search_results(s_type, query)
    await state.update_data(search_query=query)

    if not results:
        await UIService.show_temp_message(state, message, "❌ По вашему запросу ничего не найдено.")
        return

    if len(results) == 1:
        await perform_search_pick(state, message, s_type, s_action, s_context, results[0][0])
        return

    markup = kb.search_results_kb(results, s_type, s_action, s_context, page=1)
    await UIService.show_menu(
        state, message,
        f"🔍 Найдено вариантов: {len(results)}. Выберите нужный:",
        reply_markup=markup
    )


@router.callback_query(F.data.startswith("search_pg_"))
@safe_callback()
async def search_results_pagination(callback: types.CallbackQuery, state: FSMContext):
    """Пагинация результатов поиска."""
    parts = callback.data.split("_")
    page = int(parts[2])
    data = await state.get_data()
    query = data.get("search_query")
    s_type = data.get("search_type")
    s_action = data.get("search_action")
    s_context = data.get("search_context")

    if not query:
        await callback.answer("Запрос истек.", show_alert=True)
        return

    results = _fetch_search_results(s_type, query)
    markup = kb.search_results_kb(results, s_type, s_action, s_context, page=page)
    await UIService.show_menu(
        state, callback,
        f"🔍 Найдено вариантов: {len(results)}. Выберите нужный:",
        reply_markup=markup
    )


@router.callback_query(F.data.startswith("search_pick_"))
@safe_callback()
async def search_pick_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора элемента из результатов поиска."""
    parts = callback.data.split("_")
    s_type = parts[2]
    s_action = parts[3]
    item_id = int(parts[4])
    # Контекст может быть зашит в стейте
    data = await state.get_data()
    s_context = data.get("search_context")
    
    await perform_search_pick(state, callback, s_type, s_action, s_context, item_id)


async def perform_search_pick(state, event, s_type, s_action, s_context, item_id):
    """Универсальный роутер действий после выбора элемента."""
    # Сбрасываем стейт поиска (state.set_state(None) сделает UIService.show_menu для Message)
    
    text = ""
    markup = None
    
    # Подготовка контента
    if s_type == "user":
        if s_action == "info":
            text = UIService.format_user_card(
                item_id, db.get_user_name(item_id), "", 
                db.get_user_roles(item_id), db.get_user_available_topics(item_id)
            )
            markup = kb.user_edit_kb(item_id)
        elif s_action == "role":
            text = f"Пользователь выбран. Назначение роли:"
            markup = kb.role_selection_kb(item_id)
            
    elif s_type == "group":
        if s_action == "info":
            text = f"🔹 <b>Группа: {db.get_group_name(item_id)}</b>"
            markup = kb.group_edit_kb(item_id)
            
    elif s_type == "topic":
        if s_action == "info":
            text = f"📍 <b>Топик: {db.get_topic_name(item_id)}</b>"
            markup = kb.topic_edit_kb(item_id)
        elif s_action == "mod_select":
            text = f"💎 <b>Управление топиком {db.get_topic_name(item_id)}</b>"
            markup = kb.moderator_topic_menu_kb(item_id)

    # Применяем изменения согласно Sterile UI
    await UIService.show_menu(state, event, text, reply_markup=markup)


@router.callback_query(F.data == "close_menu")
async def global_close_menu(callback: types.CallbackQuery, state: FSMContext):
    """Единый обработчик кнопки 'Закрыть' для всего бота."""
    await UIService.delete_msg(callback.message)
    await state.update_data(last_menu_id=None)
    await callback.answer("Закрыто")