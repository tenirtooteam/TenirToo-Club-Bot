# Файл: keyboards/admin_kb.py
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from database import db
from keyboards.pagination_util import add_nav_footer


def main_admin_kb():
    from aiogram.types import WebAppInfo
    import config
    builder = InlineKeyboardBuilder()
    
    if config.WEBAPP_URL and config.WEBAPP_URL.startswith("http"):
        builder.button(text="🏔 ЛИЧНЫЙ КАБИНЕТ (Mini App)", web_app=WebAppInfo(url=config.WEBAPP_URL))
    
    builder.button(text="[ 📂 ШАБЛОНЫ ДОСТУПА ]", callback_data="manage_groups")
    builder.button(text="[ 📍 ВСЕ ТОПИКИ ]", callback_data="all_topics_list")
    builder.button(text="[ 🏔 МЕРОПРИЯТИЯ ]", callback_data="event_list")
    builder.button(text="[ 👥 ПОЛЬЗОВАТЕЛИ ]", callback_data="manage_users")
    builder.button(text="[ 🛡 РОЛИ ]", callback_data="roles_dashboard")
    builder.button(text="[ 📊 ЭКСПОРТ В GOOGLE ]", callback_data="sheets_export_all")
    builder.button(text="[ 📥 ИМПОРТ ИЗ GOOGLE ]", callback_data="sheets_import_all")
    builder.adjust(1)
    add_nav_footer(builder, help_key="admin_menu", help_back_data="landing")
    return builder.as_markup()

def get_admin_cancel_kb(back_data: str):
    """Универсальная клавиатура отмены для административных сценариев."""
    builder = InlineKeyboardBuilder()
    add_nav_footer(builder, back_data=back_data)
    return builder.as_markup()

def back_to_main_kb():
    builder = InlineKeyboardBuilder()
    add_nav_footer(builder, back_data="admin_main", help_key="roles")
    return builder.as_markup()

def all_topics_kb(page: int = 1, limit: int = 7):
    from keyboards.pagination_util import build_paginated_menu
    topic_ids = db.get_all_unique_topics()
    
    # Оптимизация: получаем имена всех топиков одним запросом [PL-HI]
    names_map = db.get_topic_names_by_ids(topic_ids)
    
    item_buttons = []
    for t_id in topic_ids:
        t_name = names_map.get(t_id, f"ID: {t_id}")
        item_buttons.append(InlineKeyboardButton(text=f"ID: {t_id} | {t_name}", callback_data=f"topic_global_view_{t_id}"))
    static_buttons = [
        InlineKeyboardButton(text="⬅️ НАЗАД", callback_data="admin_main"),
        InlineKeyboardButton(text="❌ ЗАКРЫТЬ", callback_data="close_menu")
    ]
    return build_paginated_menu(
        item_buttons, static_buttons, page, limit, "all_topics_list",
        search_type="topic", search_action="info"
    )

def topic_edit_kb(topic_id, group_id=0):
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Переименовать", callback_data=f"topic_rename_{topic_id}_{group_id}")
    if group_id != 0:
        builder.button(text="🗑 Убрать из группы", callback_data=f"topic_del_{topic_id}_{group_id}")
    builder.adjust(1)
    
    back_data = f"group_topics_list_{group_id}" if group_id != 0 else "all_topics_list"
    add_nav_footer(builder, back_data=back_data)
    return builder.as_markup()

def group_topics_list_kb(group_id, page: int = 1, limit: int = 7):
    from keyboards.pagination_util import build_paginated_menu
    topics = db.get_topics_of_group(group_id)
    
    # Оптимизация: пакетная выборка имён [PL-HI]
    names_map = db.get_topic_names_by_ids(topics)
    
    item_buttons = []
    for t_id in topics:
        t_name = names_map.get(t_id, f"ID: {t_id}")
        item_buttons.append(InlineKeyboardButton(text=f"ID: {t_id} | {t_name}", callback_data=f"topic_in_group_{t_id}_{group_id}"))
        
    static_buttons = [
        InlineKeyboardButton(text="➕ Добавить топик в шаблон", callback_data=f"add_topic_to_{group_id}"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"group_info_{group_id}"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu")
    ]
    return build_paginated_menu(item_buttons, static_buttons, page, limit, f"group_topics_list_{group_id}", help_key="topics", help_back_data=f"group_topics_list_{group_id}")

def available_topics_kb(group_id, page: int = 1, limit: int = 7):
    from keyboards.pagination_util import build_paginated_menu
    all_topics = db.get_all_unique_topics()
    group_topics = set(db.get_topics_of_group(group_id))
    available = [t for t in all_topics if t not in group_topics]
    
    # Оптимизация: пакетная выборка имён [PL-HI]
    names_map = db.get_topic_names_by_ids(available)
    
    item_buttons = []
    if not available:
        item_buttons.append(InlineKeyboardButton(text="🚫 Все топики уже в группе", callback_data="noop"))
    else:
        for t_id in available:
            t_name = names_map.get(t_id, f"ID: {t_id}")
            item_buttons.append(InlineKeyboardButton(text=f"📍 {t_name} (ID: {t_id})", callback_data=f"topic_add_confirm_{t_id}_{group_id}"))
            
    static_buttons = [
        InlineKeyboardButton(text="⬅️ К списку топиков шаблона", callback_data=f"group_topics_list_{group_id}"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu")
    ]
    return build_paginated_menu(item_buttons, static_buttons, page, limit, f"add_topic_to_{group_id}", help_key="topics")

def groups_list_kb(page: int = 1, limit: int = 7):
    groups = db.get_all_groups()
    item_buttons = []
    for g_id, g_name in groups:
        item_buttons.append(InlineKeyboardButton(text=f"📂 {g_name}", callback_data=f"group_info_{g_id}"))
        
    static_buttons = [
        InlineKeyboardButton(text="➕ Создать шаблон", callback_data="add_group_start"),
        InlineKeyboardButton(text="❓ О шаблонах", callback_data="help:templates:manage_groups"),
        InlineKeyboardButton(text="⬅️ НАЗАД", callback_data="admin_main"),
        InlineKeyboardButton(text="❌ ЗАКРЫТЬ", callback_data="close_menu")
    ]
    from keyboards.pagination_util import build_paginated_menu
    return build_paginated_menu(
        item_buttons, static_buttons, page, limit, "manage_groups",
        search_type="group", search_action="info",
        help_key="templates", help_back_data="manage_groups"
    )

def group_edit_kb(group_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="📍 Топики в шаблоне", callback_data=f"group_topics_list_{group_id}")
    builder.button(text="⚡ Применить шаблон к топику", callback_data=f"tmpl_act_start_apply_{group_id}")
    builder.button(text="🔄 Синхронизировать топик", callback_data=f"tmpl_act_start_sync_{group_id}")
    builder.button(text="🗑 Удалить шаблон", callback_data=f"del_group_{group_id}")
    builder.adjust(1)
    add_nav_footer(builder, back_data="manage_groups", help_key="templates", help_back_data=f"group_info_{group_id}")
    return builder.as_markup()

def template_action_topic_select_kb(group_id: int, action: str, page: int = 1, limit: int = 7):
    """Клавиатура выбора топика для применения или синхронизации шаблона (с пагинацией)."""
    from keyboards.pagination_util import build_paginated_menu
    topics = db.get_all_unique_topics()
    
    # Оптимизация: пакетная выборка имён [PL-HI]
    names_map = db.get_topic_names_by_ids(topics)
    
    item_buttons = []
    for t_id in topics:
        t_name = names_map.get(t_id, f"ID: {t_id}")
        item_buttons.append(InlineKeyboardButton(text=f"📍 {t_name}", callback_data=f"tmpl_act_exec_{action}_{group_id}_{t_id}"))
    
    static_buttons = [
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"group_info_{group_id}"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu")
    ]
    return build_paginated_menu(item_buttons, static_buttons, page, limit, f"tmpl_act_start_{action}_{group_id}", help_key="topics")

def users_list_kb(page: int = 1, limit: int = 7):
    users = db.get_all_users()
    item_buttons = [
        InlineKeyboardButton(text=f"👤 {f_name} {l_name}", callback_data=f"user_info_{u_id}")
        for u_id, f_name, l_name in users
    ]
    static_buttons = [
        InlineKeyboardButton(text="➕ Добавить пользователя", callback_data="add_user_start"),
        InlineKeyboardButton(text="⬅️ НАЗАД", callback_data="admin_main"),
        InlineKeyboardButton(text="❌ ЗАКРЫТЬ", callback_data="close_menu")
    ]
    from keyboards.pagination_util import build_paginated_menu
    return build_paginated_menu(
        item_buttons, static_buttons, page, limit, "manage_users",
        search_type="user", search_action="info",
        help_key="profile", help_back_data="manage_users"
    )

def user_edit_kb(user_id, is_superadmin: bool = False):
    builder = InlineKeyboardBuilder()
    builder.button(text="🏷 Переименовать", callback_data=f"user_rename_{user_id}")
    builder.button(text="📋 Состав шаблонов", callback_data=f"user_templates_manage_{user_id}")
    builder.button(text="👑 Управление ролями", callback_data=f"user_roles_manage_{user_id}")
    
    if is_superadmin:
        builder.button(text="🗑 Удалить пользователя", callback_data=f"user_delete_{user_id}")
        
    builder.adjust(1)
    add_nav_footer(builder, back_data="manage_users", help_key="profile")
    return builder.as_markup()

def user_groups_edit_kb(user_id, page: int = 1, limit: int = 7):
    from keyboards.pagination_util import build_paginated_menu
    all_groups = db.get_all_groups()
    # Оптимизация: получаем все ID групп пользователя одним запросом [PL-HI]
    user_template_ids = set(db.get_user_group_membership_ids(user_id))
    
    item_buttons = []
    for g_id, g_name in all_groups:
        mark = "✅ " if g_id in user_template_ids else "➖ "
        item_buttons.append(InlineKeyboardButton(text=f"{mark}{g_name}", callback_data=f"user_template_toggle_{user_id}_{g_id}"))
        
    static_buttons = [
        InlineKeyboardButton(text="⬅️ НАЗАД", callback_data=f"user_info_{user_id}"),
        InlineKeyboardButton(text="❌ ЗАКРЫТЬ", callback_data="close_menu")
    ]
    return build_paginated_menu(item_buttons, static_buttons, page, limit, f"user_templates_manage_{user_id}")

def roles_dashboard_kb(is_admin: bool):
    builder = InlineKeyboardBuilder()
    builder.button(text="ℹ️ Описание ролей (FAQ)", callback_data="roles_faq")
    builder.button(text="📋 Список пользователей с ролями", callback_data="list_users_roles")
    builder.adjust(1)
    add_nav_footer(builder, back_data="admin_main" if is_admin else "moderator")
    return builder.as_markup()


def role_selection_kb(user_id: int):
    """Клавиатура выбора роли для пользователя."""
    builder = InlineKeyboardBuilder()
    roles = db.get_all_roles()
    existing_roles = db.get_user_roles(user_id)
    existing_role_names = set(r[0] for r in existing_roles)

    for role_id, role_name in roles:
        # Не даём назначать superadmin через интерфейс
        if role_name == 'superadmin':
            continue
        
        # Если роль глобальная (админ) и она уже есть - скрываем
        if role_name == 'admin' and 'admin' in existing_role_names:
            continue
            
        callback_data = f"role_pick_{user_id}_{role_id}"
        display_name = "👑 Админ" if role_name == "admin" else "🛡 Модератор" if role_name == "moderator" else role_name.capitalize()
        builder.button(text=display_name, callback_data=callback_data)
        
    builder.adjust(1)
    add_nav_footer(builder, back_data=f"user_roles_manage_{user_id}")
    return builder.as_markup()


def user_roles_manage_kb(user_id: int):
    """Клавиатура управления ролями конкретного пользователя."""
    builder = InlineKeyboardBuilder()
    user_roles = list(db.get_user_roles(user_id))
    
    # Оптимизация: собираем ID топиков для пакетной выборки имён [PL-HI]
    topic_ids = [tid for _, tid in user_roles if tid is not None]
    names_map = db.get_topic_names_by_ids(topic_ids)
    
    for role_name, topic_id in user_roles:
        if topic_id is None:
            display = f"✅ {role_name} (глобально)"
            callback = f"role_revoke_{user_id}_{db.get_role_id(role_name)}_None"
        else:
            topic_name = names_map.get(topic_id, f"Топик {topic_id}")
            display = f"✅ {role_name} топика {topic_name}"
            callback = f"role_revoke_{user_id}_{db.get_role_id(role_name)}_{topic_id}"
        builder.button(text=display, callback_data=callback)
    builder.button(text="➕ Назначить роль", callback_data=f"role_assign_user_{user_id}")
    builder.adjust(1)
    add_nav_footer(builder, back_data=f"user_info_{user_id}", help_key="templates")
    return builder.as_markup()


def topic_selection_for_role_kb(user_id, page: int = 1, limit: int = 7):
    from keyboards.pagination_util import build_paginated_menu
    all_topics = db.get_all_unique_topics()
    
    # Оптимизация: пакетная выборка имён [PL-HI]
    names_map = db.get_topic_names_by_ids(all_topics)
    
    item_buttons = []
    for t_id in all_topics:
        t_name = names_map.get(t_id, f"ID: {t_id}")
        item_buttons.append(InlineKeyboardButton(text=f"📍 {t_name}", callback_data=f"role_assign_topic_{user_id}_{t_id}"))
        
    static_buttons = [
        InlineKeyboardButton(text="⬅️ НАЗАД", callback_data=f"role_assign_user_{user_id}"),
        InlineKeyboardButton(text="❌ ЗАКРЫТЬ", callback_data="close_menu")
    ]
    return build_paginated_menu(item_buttons, static_buttons, page, limit, f"topic_assign_pg_{user_id}")

def back_to_roles_dashboard_kb():
    builder = InlineKeyboardBuilder()
    add_nav_footer(builder, back_data="roles_dashboard")
    return builder.as_markup()




def search_results_kb(results, search_type, search_action, search_context=None, page: int = 1, limit: int = 7):
    """Клавиатура для отображения результатов глобального поиска."""
    from keyboards.pagination_util import build_paginated_menu
    item_buttons = []
    for item_id, name in results:
        item_buttons.append(InlineKeyboardButton(
            text=name, 
            callback_data=f"search_pick_{search_type}_{search_action}_{item_id}"
        ))
        
    static_buttons = [
        InlineKeyboardButton(text="🔎 Искать заново", callback_data=f"search_start_{search_type}_{search_action}_{search_context if search_context else ''}"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu")
    ]
    return build_paginated_menu(item_buttons, static_buttons, page, limit, "search")


def confirmation_kb(action_type: str, target_id: int, back_callback: str, extra_id: int = 0):
    """
    Универсальная клавиатура подтверждения.
    action_type: group_del, topic_del, global_topic_del, user_del
    """
    builder = InlineKeyboardBuilder()
    
    # Используем двоеточие как разделитель для параметров, чтобы не конфликтовать с подчеркиваниями в action_type
    callback_data = f"confirm_exe_{action_type}:{target_id}:{extra_id}"
        
    builder.button(text="🗑 Да, удалить", callback_data=callback_data)
    builder.button(text="🔙 Отмена", callback_data=back_callback)
    builder.adjust(1)
    return builder.as_markup()


def simple_back_kb(back_data: str):
    """Универсальная клавиатура с одной кнопкой 'Назад'."""
    builder = InlineKeyboardBuilder()
    add_nav_footer(builder, back_data=back_data)
    return builder.as_markup()

