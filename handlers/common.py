# Файл: handlers/common.py
import math
import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database import db
import keyboards as kb
from services.callback_guard import safe_callback
from services.permission_service import PermissionService
from services.ui_service import UIService
from services.management_service import ManagementService

router = Router()
logger = logging.getLogger(__name__)


def _fetch_search_results(s_type: str, query: str) -> list:
    """Централизованный диспетчер поиска по типам сущностей."""
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
@UIService.sterile_command(redirect=True, error_prefix="справка")
async def cmd_help(message: types.Message, state: FSMContext):
    """Выводит справку по боту."""
    user_id = message.from_user.id
    
    help_text = (
        "🤖 <b>Информационный гид Tenir-Too Bot</b>\n\n"
        "<b>Команды:</b>\n"
        "🔹 /start : Главное меню\n"
        "🔹 /help  : Вызов этой справки\n"
    )

    manageable_topics = PermissionService.get_manageable_topics(user_id)
    if manageable_topics:
        help_text += (
            "\n<b>Модерация:</b>\n"
            "🔹 /mod   : Панель модератора топиков\n"
        )

    if PermissionService.is_global_admin(user_id):
        help_text += (
            "\n<b>Администрирование:</b>\n"
            "🔹 /admin : Полный доступ к настройкам\n"
        )
    
    help_text += "\n<i>Бот работает в скрытом режиме: сообщения от неавторизованных пользователей удаляются автоматически.</i>"

    return help_text, None


@router.callback_query(F.data == "close_menu")
@safe_callback()
async def close_menu_handler(callback: types.CallbackQuery, state: FSMContext):
    """Удаляет меню и очищает состояние трекинга."""
    await UIService.delete_msg(callback.message)
    await state.update_data(last_menu_id=None)


@router.callback_query(F.data.startswith("usr_pg_"))
@safe_callback()
async def process_user_pagination(callback: types.CallbackQuery, state: FSMContext):
    """Пагинация в списке выбора пользователей при поиске."""
    page = int(callback.data.split("_")[2])
    data = await state.get_data()
    query = data.get("disambig_query", "")

    if not query:
        await callback.answer("Контекст поиска утерян.", show_alert=True)
        return

    results = db.find_users_by_query(query)
    total_pages = math.ceil(len(results) / 7)
    start_idx = (page - 1) * 7
    markup = kb.user_disambiguation_kb(results[start_idx:start_idx + 7], page, total_pages)
    await UIService.show_menu(state, callback, "🔍 Кто именно из пользователей?", reply_markup=markup)


@router.callback_query(F.data.startswith("usr_pick_"))
@safe_callback()
async def process_user_pick(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора конкретного пользователя после поиска."""
    target_user_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    action = data.get("disambig_action")
    context_id = data.get("disambig_context")

    if action == "dir_add":
        success, result = ManagementService.grant_direct_access(str(target_user_id), context_id)
        await UIService.show_menu(state, callback, result)
    elif action == "mod_add":
        success, result = ManagementService.assign_moderator_role(str(target_user_id), context_id)
        await UIService.show_menu(state, callback, result)
    elif action == "admin_role_target":
        # Переход к выбору роли для админа
        await UIService.show_menu(
            state, callback, 
            f"Выберите роль для пользователя {db.get_user_name(target_user_id)}:",
            reply_markup=kb.role_selection_kb(target_user_id)
        )


@router.callback_query(F.data == "roles_dashboard")
@safe_callback()
async def roles_dashboard_menu(callback: types.CallbackQuery, state: FSMContext):
    await UIService.generic_navigator(state, callback, callback.data)


@router.callback_query(F.data == "roles_faq")
@safe_callback()
async def roles_faq_view(callback: types.CallbackQuery, state: FSMContext):
    await UIService.generic_navigator(state, callback, callback.data)


@router.callback_query(F.data == "list_users_roles")
@safe_callback()
async def list_users_with_roles(callback: types.CallbackQuery, state: FSMContext):
    await UIService.generic_navigator(state, callback, callback.data)


@router.callback_query(F.data.startswith("search_start_"))
@safe_callback()
async def search_start_handler(callback: types.CallbackQuery, state: FSMContext):
    """Инициация глобального поиска."""
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
    
    await UIService.ask_input(state, callback, f"🔎 {prompts.get(search_type, 'Введите запрос:')}", SearchStates.waiting_for_query)


@router.message(SearchStates.waiting_for_query)
async def search_query_handler(message: types.Message, state: FSMContext):
    """Обработка поискового запроса."""
    query = message.text.strip()
    data = await state.get_data()
    s_type = data.get("search_type")
    s_action = data.get("search_action")
    s_context = data.get("search_context")

    results = _fetch_search_results(s_type, query)
    await state.update_data(search_query=query)

    if not results:
        await UIService.show_temp_message(state, message, "❓ По вашему запросу ничего не найдено.", reply_markup=kb.back_to_main_kb())
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
        await callback.answer("Поиск истек.", show_alert=True)
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
    """Обработка выбора из результатов поиска."""
    parts = callback.data.split("_")
    s_type = parts[2]
    s_action = parts[3]
    item_id = int(parts[4])
    data = await state.get_data()
    s_context = data.get("search_context")
    
    await perform_search_pick(state, callback, s_type, s_action, s_context, item_id)


async def perform_search_pick(state, event, s_type, s_action, s_context, item_id):
    """Универсальный роутер результатов поиска: делегирует навигацию системному роутеру."""
    if s_action == "info":
        return await UIService.generic_navigator(state, event, f"{s_type}_info_{item_id}")
        
    if s_action == "mod_add":
        success, result = ManagementService.assign_moderator_role(str(item_id), int(s_context))
        return await UIService.show_menu(state, event, result, reply_markup=kb.back_to_main_kb())
        
    if s_action == "dir_add":
        success, result = ManagementService.grant_direct_access(str(item_id), int(s_context))
        return await UIService.show_menu(state, event, result, reply_markup=kb.back_to_main_kb())

    if s_action == "admin_role_target":
        return await UIService.generic_navigator(state, event, f"user_roles_manage_{item_id}")


@router.callback_query(F.data.startswith("confirm_exe_"))
@safe_callback()
async def confirm_execution(callback: types.CallbackQuery, state: FSMContext):
    """Системная точка исполнения подтвержденных удалений (Admin/Moderator)."""
    # Формат: confirm_exe_{action}:{target_id}:{extra_id}
    # Разделяем по ':' для надежного извлечения параметров, так как action может содержать '_'
    main_parts = callback.data.split(":")
    action = main_parts[0].replace("confirm_exe_", "")
    target_id = int(main_parts[1])
    extra_id = int(main_parts[2])
    
    # 1. Логирование для аудита (Security Audit)
    logger.warning(f"🛡 [AUDIT] Админ {callback.from_user.id} подтвердил удаление: {action} (Target: {target_id}, Extra: {extra_id})")

    # 2. Выполнение мутации через сервис (Sterile Mutation)
    success, msg, next_callback = ManagementService.execute_deletion(action, target_id, extra_id)
    
    if not success:
        await callback.answer(msg, show_alert=True)
        return

    await callback.answer(msg)
    
    # Sterile UI Navigation: возвращаемся в нужный раздел через навигатор
    await UIService.generic_navigator(state, callback, next_callback)

