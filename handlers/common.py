# Файл: handlers/common.py
import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

import keyboards as kb
from services.callback_guard import safe_callback
from services.permission_service import PermissionService
from services.ui_service import UIService
from services.management_service import ManagementService

import callbacks as cb

router = Router()
logger = logging.getLogger(__name__)




class SearchStates(StatesGroup):
    waiting_for_query = State()


@router.message(Command("help"))
@UIService.sterile_command(redirect=True, error_prefix="справка")
async def cmd_help(message: types.Message, state: FSMContext):
    """Выводит справку по боту."""
    user_id = message.from_user.id
    from services.help_service import HelpService

    help_text = HelpService.get_help("help_general")

    manageable_topics = PermissionService.get_manageable_topics(user_id)
    if manageable_topics:
        # Инъекция динамических блоков разрешена, но основная структура в сервисе
        help_text = help_text.replace("\n\n<i>Бот работает", "\n<b>Модерация:</b>\n🔹 /mod   : Панель модератора топиков\n\n<i>Бот работает")

    if PermissionService.is_global_admin(user_id):
        help_text = help_text.replace("\n\n<i>Бот работает", "\n<b>Администрирование:</b>\n🔹 /admin : Полный доступ к настройкам\n\n<i>Бот работает")

    return help_text, None


async def show_help_view(state: FSMContext, event: types.Message | types.CallbackQuery, key: str, back_data: str = "admin_main"):
    """
    Отображает окно справки с текстом из HelpService.
    [CC-1] Sterile UI: Включает кнопку возврата.
    """
    from services.help_service import HelpService

    help_text = HelpService.get_help(key)

    # Создаем клавиатуру с кнопкой возврата
    markup = kb.simple_back_kb(back_data)

    await UIService.sterile_show(state, event, help_text, reply_markup=markup)


@router.callback_query(cb.HelpCB.filter())
@safe_callback()
async def universal_help_handler(callback: types.CallbackQuery, state: FSMContext, callback_data: cb.HelpCB):
    """Универсальный хендлер для всех кнопок помощи.

    [feature 011 / R-UI-11] Защитный разбор обеспечивает сам фильтр: `unpack()`
    внутри него ловит `(TypeError, ValueError)` и не пропускает битые данные к
    хендлеру. Прежняя ручная лесенка по `split(":")` с угадыванием формата
    больше не нужна — ключ и маршрут возврата приезжают по имени поля (FR-003).

    Данные старого формата (`help_main_menu`, `help:key`) фильтр не признаёт;
    они уходят в глобальный fallback неотвеченных колбэков (`R-SEC-2`), то есть
    деградируют безопасно, как и требует C-7.
    """
    await show_help_view(state, callback, callback_data.key, callback_data.back_data)


@router.callback_query(F.data == "close_menu")
@safe_callback()
async def close_menu_handler(callback: types.CallbackQuery, state: FSMContext):
    """Удаляет меню или заменяет его на заглушку в ЛС, сбрасывая FSM-состояние."""
    if callback.message and callback.message.chat.type == "private":
        markup = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🏔 Главное меню", callback_data="landing")]
        ])
        try:
            await callback.bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                text="🏔 <b>Интерфейс закрыт.</b>\n\nДля возврата в главное меню используйте кнопку ниже.",
                reply_markup=markup,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to edit close menu to stub: {e}")
    else:
        await UIService.delete_msg(callback.message)

    await state.update_data(last_menu_id=None, last_menu_ids=[])
    await state.set_state(None)
    await UIService.clear_fsm_data_safely(state)


@router.callback_query(F.data == "landing")
@safe_callback()
async def landing_callback_handler(callback: types.CallbackQuery, state: FSMContext):
    """Системная точка входа в главное меню через навигатор."""
    await UIService.generic_navigator(state, callback, "landing")


@router.callback_query(F.data == "roles_dashboard")
@safe_callback()
async def roles_dashboard_menu(callback: types.CallbackQuery, state: FSMContext):
    await UIService.generic_navigator(state, callback, callback.data)


@router.callback_query(F.data == "roles_faq")
@safe_callback()
async def roles_faq_view(callback: types.CallbackQuery, state: FSMContext):
    await UIService.generic_navigator(state, callback, callback.data)


@router.callback_query(cb.ListUsersRolesCB.filter())
@safe_callback()
async def list_users_with_roles(callback: types.CallbackQuery, state: FSMContext, callback_data: cb.ListUsersRolesCB):
    await UIService.generic_navigator(state, callback, callback_data)


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

    # [CP-3.11] Sterile FSM entry with back button
    await UIService.sterile_ask(
        state,
        callback,
        f"🔎 {prompts.get(search_type, 'Введите запрос:')}",
        SearchStates.waiting_for_query,
        reply_markup=kb.get_admin_cancel_kb("landing")
    )


@router.message(SearchStates.waiting_for_query)
async def search_query_handler(message: types.Message, state: FSMContext):
    """Обработка поискового запроса."""
    if not message.text:  # [BUG-3] не-текст (фото/стикер/голос)
        return await UIService.show_temp_message(state, message, "⚠️ Пожалуйста, введите <b>текст</b>.")
    query = message.text.strip()
    data = await state.get_data()
    s_type = data.get("search_type")
    s_action = data.get("search_action")
    s_context = data.get("search_context")

    results = ManagementService.search_entities(s_type, query)
    await state.update_data(search_query=query)

    if not results:
        await UIService.show_temp_message(state, message, "❓ По вашему запросу ничего не найдено.", reply_markup=kb.back_to_main_kb())
        return



    markup = kb.search_results_kb(results, s_type, s_action, s_context, page=1)
    await UIService.sterile_show(
        state, message,
        f"🔍 Найдено вариантов: {len(results)}. Выберите нужный:",
        reply_markup=markup
    )


@router.callback_query(cb.SearchPageCB.filter())
@safe_callback()
async def search_results_pagination(callback: types.CallbackQuery, state: FSMContext, callback_data: cb.SearchPageCB):
    """Пагинация результатов поиска."""
    page = callback_data.page
    data = await state.get_data()
    query = data.get("search_query")
    s_type = data.get("search_type")
    s_action = data.get("search_action")
    s_context = data.get("search_context")

    if not query:
        await callback.answer("Поиск истек.", show_alert=True)
        return

    results = ManagementService.search_entities(s_type, query)
    markup = kb.search_results_kb(results, s_type, s_action, s_context, page=page)
    await UIService.sterile_show(
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
    item_id = int(parts[-1])
    s_action = "_".join(parts[3:-1])

    data = await state.get_data()
    s_context = data.get("search_context")

    await perform_search_pick(state, callback, s_type, s_action, s_context, item_id)



async def perform_search_pick(state, event_or_msg, s_type, s_action, s_context, item_id):
    """Универсальный роутер результатов поиска: делегирует навигацию системному роутеру."""
    if s_action == "info":
        return await UIService.generic_navigator(state, event_or_msg, f"{s_type}_info_{item_id}")

    # Определяем ID пользователя, совершившего действие
    user_id = event_or_msg.from_user.id

    # [feature 006, FR-010] Defense-in-depth: выдача прав требует прав на управление топиком,
    # не полагаемся на то, что кнопка «досталась» только уполномоченному (R-ARCH-7).
    if s_action in ("mod_add", "dir_add"):
        if not PermissionService.can_manage_topic(user_id, int(s_context)):
            logger.warning(f"🛡 [FR-011] search_pick grant denied: user={user_id} action={s_action} topic={s_context}")
            await event_or_msg.answer("❌ Доступ запрещён.", show_alert=True)
            return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from keyboards.pagination_util import add_nav_footer

    # Вычисляем back_data в зависимости от прав
    if PermissionService.is_global_admin(user_id):
        back_data = "admin_main"
    else:
        back_data = "landing"

    builder = InlineKeyboardBuilder()
    add_nav_footer(builder, back_data=back_data, help_key="roles")
    reply_markup = builder.as_markup()

    if s_action == "mod_add":
        success, result = ManagementService.assign_moderator_role_by_id(item_id, int(s_context))
        await state.set_state(None)
        await UIService.clear_fsm_data_safely(state)
        return await UIService.sterile_show(state, event_or_msg, result, reply_markup=reply_markup)

    if s_action == "dir_add":
        success, result = ManagementService.grant_direct_access_by_id(item_id, int(s_context))
        await state.set_state(None)
        await UIService.clear_fsm_data_safely(state)
        return await UIService.sterile_show(state, event_or_msg, result, reply_markup=reply_markup)

    if s_action == "admin_role_target":
        await state.set_state(None)
        await UIService.clear_fsm_data_safely(state)
        return await UIService.generic_navigator(state, event_or_msg, cb.UserRolesManageCB(user_id=item_id))

    if s_action == "mod_select":
        await state.set_state(None)
        await UIService.clear_fsm_data_safely(state)
        return await UIService.generic_navigator(state, event_or_msg, cb.ModTopicSelectCB(topic_id=item_id))



def _confirm_action_authorized(user_id: int, action: str, target_id: int, extra_id: int) -> bool:
    """
    [feature 006, FR-009] Проверка полномочий на подтверждённую деструктивную операцию.
    Права через PermissionService (R-ARCH-7), без inline-сравнений с ADMIN_ID.
    - Модераторские действия — по праву на управление соответствующим топиком.
    - Удаление похода — по праву на редактирование (автор или админ).
    - Остальное (группы/топики/пользователи/роли) — только глобальный админ.
    """
    from services.event_service import EventService
    if action == "mod_topic_del":
        return PermissionService.can_manage_topic(user_id, target_id)  # target_id = топик
    if action == "mod_rem":
        return PermissionService.can_manage_topic(user_id, extra_id)   # extra_id = топик
    if action == "event_del":
        return EventService.can_edit_event(user_id, target_id)
    return PermissionService.is_global_admin(user_id)


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

    # [feature 006, FR-009] Defense-in-depth: проверяем права на сервере до мутации.
    if not _confirm_action_authorized(callback.from_user.id, action, target_id, extra_id):
        logger.warning(f"🛡 [FR-011] confirm_execution denied: user={callback.from_user.id} action={action} target={target_id}")
        await callback.answer("❌ Доступ запрещён.", show_alert=True)
        return

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

