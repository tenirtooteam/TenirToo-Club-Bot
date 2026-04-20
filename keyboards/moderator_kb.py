# Файл: keyboards/moderator_kb.py
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import db


def moderator_topics_list_kb(topics: list, page: int = 1, limit: int = 7):
    """Список топиков, доступных модератору для управления."""
    from keyboards.pagination_util import build_paginated_menu
    from aiogram.types import InlineKeyboardButton
    
    item_buttons = []
    for topic_id in topics:
        topic_name = db.get_topic_name(topic_id)
        item_buttons.append(InlineKeyboardButton(
            text=f"📍 {topic_name} (ID: {topic_id})",
            callback_data=f"mod_topic_select_{topic_id}"
        ))
        
    static_buttons = [
        InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu")
    ]
    return build_paginated_menu(item_buttons, static_buttons, page, limit, "moderator")


def moderator_topic_menu_kb(topic_id: int):
    """Главное меню управления конкретным топиком для модератора."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📝 Переименовать топик",
        callback_data=f"mod_topic_rename_{topic_id}"
    )
    builder.button(
        text="📂 Управление группами доступа",
        callback_data=f"mod_topic_groups_{topic_id}"
    )
    builder.button(
        text="👥 Управление пользователями",
        callback_data=f"mod_users_manage_{topic_id}"
    )
    builder.button(
        text="👑 Модераторы топика",
        callback_data=f"mod_topic_moderators_{topic_id}"
    )
    builder.button(text="⬅️ Назад", callback_data="moderator")
    builder.button(text="❌ Закрыть", callback_data="close_menu")
    builder.adjust(1)
    return builder.as_markup()


def moderator_group_list_kb(topic_id: int, page: int = 1, limit: int = 7):
    """Список групп, привязанных к топику, с возможностью отвязать."""
    from keyboards.pagination_util import build_paginated_menu
    from aiogram.types import InlineKeyboardButton
    all_groups = db.get_all_groups()
    attached_groups = []
    for g_id, g_name in all_groups:
        topics = db.get_topics_of_group(g_id)
        if topic_id in topics:
            attached_groups.append((g_id, g_name))

    item_buttons = []
    for g_id, g_name in attached_groups:
        item_buttons.append(InlineKeyboardButton(
            text=f"🔹 {g_name} ❌ (Отвязать)",
            callback_data=f"mod_group_remove_{g_id}_{topic_id}"
        ))

    static_buttons = [
        InlineKeyboardButton(
            text="➕ Привязать существующую группу",
            callback_data=f"mod_gr_addlist_{topic_id}"
        ),
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"mod_topic_select_{topic_id}"
        ),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu")
    ]
    return build_paginated_menu(item_buttons, static_buttons, page, limit, f"mod_topic_groups_{topic_id}")


def moderator_available_groups_kb(topic_id: int, page: int = 1, limit: int = 7):
    """Список всех остальных групп для привязки к топику."""
    from keyboards.pagination_util import build_paginated_menu
    from aiogram.types import InlineKeyboardButton
    all_groups = db.get_all_groups()
    unattached_groups = []
    for g_id, g_name in all_groups:
        topics = db.get_topics_of_group(g_id)
        if topic_id not in topics:
            unattached_groups.append((g_id, g_name))
            
    item_buttons = []
    for g_id, g_name in unattached_groups:
        item_buttons.append(InlineKeyboardButton(
            text=f"🔗 {g_name}",
            callback_data=f"mod_gr_link_{g_id}_{topic_id}"
        ))
        
    static_buttons = [
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"mod_topic_groups_{topic_id}"
        ),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu")
    ]
    return build_paginated_menu(item_buttons, static_buttons, page, limit, f"mod_gr_addlist_{topic_id}")



def moderator_users_list_kb(topic_id: int, page: int = 1, limit: int = 7):
    """Список пользователей с управлением прямым доступом (модератор)."""
    from keyboards.pagination_util import build_paginated_menu
    from aiogram.types import InlineKeyboardButton
    users = db.get_all_users()
    
    direct_users = set(u[0] for u in db.get_direct_access_users(topic_id))
    all_authorized = set(u[0] for u in db.get_topic_authorized_users(topic_id))
    group_users = all_authorized - direct_users
    
    item_buttons = []
    for u_id, f_name, l_name in users:
        if u_id in direct_users:
            item_buttons.append(InlineKeyboardButton(
                text=f"✅ {f_name} {l_name}",
                callback_data=f"mod_tgl_dir_{u_id}_{topic_id}"
            ))
        elif u_id in group_users:
            item_buttons.append(InlineKeyboardButton(
                text=f"🌐 {f_name} {l_name}",
                callback_data=f"mod_tgl_dir_{u_id}_{topic_id}"
            ))
            
    static_buttons = [
        InlineKeyboardButton(
            text="➕ Выдать доступ",
            callback_data=f"mod_add_user_list_{topic_id}"
        ),
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"mod_topic_select_{topic_id}"
        ),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu")
    ]
    return build_paginated_menu(item_buttons, static_buttons, page, limit, f"mod_users_manage_{topic_id}")


def moderator_users_to_add_kb(topic_id: int, page: int = 1, limit: int = 7):
    """Список пользователей без доступа для выдачи им прямого допуска."""
    from keyboards.pagination_util import build_paginated_menu
    from aiogram.types import InlineKeyboardButton
    users = db.get_all_users()
    
    direct_users = set(u[0] for u in db.get_direct_access_users(topic_id))
    all_authorized = set(u[0] for u in db.get_topic_authorized_users(topic_id))
    has_access = direct_users | all_authorized
    
    item_buttons = []
    for u_id, f_name, l_name in users:
        if u_id not in has_access:
            item_buttons.append(InlineKeyboardButton(
                text=f"❌ {f_name} {l_name}",
                callback_data=f"mod_tgl_dir_{u_id}_{topic_id}"
            ))
            
    static_buttons = [
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"mod_users_manage_{topic_id}"
        ),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu")
    ]
    return build_paginated_menu(item_buttons, static_buttons, page, limit, f"mod_add_user_list_{topic_id}")


def moderator_topic_moderators_kb(topic_id: int, page: int = 1, limit: int = 7):
    """Список модераторов топика с возможностью добавить/удалить."""
    from keyboards.pagination_util import build_paginated_menu
    from aiogram.types import InlineKeyboardButton
    moderators = db.get_moderators_of_topic(topic_id)
    
    item_buttons = []
    for u_id, f_name, l_name in moderators:
        item_buttons.append(InlineKeyboardButton(
            text=f"👑 {f_name} {l_name}",
            callback_data=f"mod_moderator_remove_{u_id}_{topic_id}"
        ))
        
    static_buttons = [
        InlineKeyboardButton(
            text="➕ Назначить модератора",
            callback_data=f"mod_moderator_add_{topic_id}"
        ),
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"mod_topic_select_{topic_id}"
        ),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu")
    ]
    return build_paginated_menu(item_buttons, static_buttons, page, limit, f"mod_topic_moderators_{topic_id}")
