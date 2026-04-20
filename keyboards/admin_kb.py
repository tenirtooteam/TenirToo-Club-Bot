# Файл: keyboards/admin_kb.py
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import db


def main_admin_kb(is_superadmin: bool = False):
    builder = InlineKeyboardBuilder()
    builder.button(text="📂 Группы доступа", callback_data="manage_groups")
    builder.button(text="📍 Все топики (Имена/Доступ)", callback_data="all_topics_list")
    builder.button(text="👥 Пользователи", callback_data="manage_users")
    if is_superadmin:
        builder.button(text="👑 Управление ролями", callback_data="manage_roles")
    builder.button(text="❌ Закрыть", callback_data="close_menu")
    builder.adjust(1)
    return builder.as_markup()

def all_topics_kb():
    builder = InlineKeyboardBuilder()
    topic_ids = db.get_all_unique_topics()
    for t_id in topic_ids:
        t_name = db.get_topic_name(t_id)
        builder.button(text=f"ID: {t_id} | {t_name}", callback_data=f"topic_global_view_{t_id}")
    builder.button(text="⬅️ Назад", callback_data="admin_main")
    builder.button(text="❌ Закрыть", callback_data="close_menu")
    builder.adjust(1)
    return builder.as_markup()

def topic_edit_kb(topic_id, group_id=0):
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Переименовать", callback_data=f"topic_rename_{topic_id}_{group_id}")
    if group_id != 0:
        builder.button(text="🗑 Убрать из группы", callback_data=f"topic_del_{topic_id}_{group_id}")
        builder.button(text="⬅️ Назад", callback_data=f"group_topics_list_{group_id}")
    else:
        builder.button(text="🗑 Удалить из БД", callback_data=f"global_topic_del_{topic_id}")
        builder.button(text="⬅️ Назад", callback_data="all_topics_list")
    builder.button(text="❌ Закрыть", callback_data="close_menu")
    builder.adjust(1)
    return builder.as_markup()

def group_topics_list_kb(group_id):
    builder = InlineKeyboardBuilder()
    topics = db.get_topics_of_group(group_id)
    for t_id in topics:
        t_name = db.get_topic_name(t_id)
        builder.button(text=f"ID: {t_id} | {t_name}", callback_data=f"topic_in_group_{t_id}_{group_id}")
    builder.button(text="➕ Добавить топик (ID)", callback_data=f"add_topic_to_{group_id}")
    builder.button(text="⬅️ Назад", callback_data=f"group_info_{group_id}")
    builder.button(text="❌ Закрыть", callback_data="close_menu")
    builder.adjust(1)
    return builder.as_markup()

def available_topics_kb(group_id):
    builder = InlineKeyboardBuilder()
    all_topics = db.get_all_unique_topics()
    group_topics = set(db.get_topics_of_group(group_id))
    available = [t for t in all_topics if t not in group_topics]
    if not available:
        builder.button(text="🚫 Все топики уже в группе", callback_data="noop")
    for t_id in available:
        t_name = db.get_topic_name(t_id)
        builder.button(text=f"📍 {t_name} (ID: {t_id})", callback_data=f"topic_add_confirm_{t_id}_{group_id}")
    builder.button(text="⬅️ Назад", callback_data=f"group_topics_list_{group_id}")
    builder.button(text="❌ Закрыть", callback_data="close_menu")
    builder.adjust(1)
    return builder.as_markup()

def groups_list_kb():
    builder = InlineKeyboardBuilder()
    groups = db.get_all_groups()
    for g_id, g_name in groups:
        builder.button(text=f"🔹 {g_name}", callback_data=f"group_info_{g_id}")
    builder.button(text="➕ Создать группу", callback_data="add_group_start")
    builder.button(text="⬅️ Назад", callback_data="admin_main")
    builder.button(text="❌ Закрыть", callback_data="close_menu")
    builder.adjust(1)
    return builder.as_markup()

def group_edit_kb(group_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="📍 Список топиков", callback_data=f"group_topics_list_{group_id}")
    builder.button(text="🗑 Удалить группу", callback_data=f"del_group_{group_id}")
    builder.button(text="⬅️ Назад", callback_data="manage_groups")
    builder.button(text="❌ Закрыть", callback_data="close_menu")
    builder.adjust(1)
    return builder.as_markup()

def users_list_kb():
    builder = InlineKeyboardBuilder()
    users = db.get_all_users()
    for u_id, f_name, l_name in users:
        builder.button(text=f"👤 {f_name} {l_name}", callback_data=f"user_info_{u_id}")
    builder.button(text="➕ Добавить пользователя", callback_data="add_user_start")
    builder.button(text="⬅️ Назад", callback_data="admin_main")
    builder.button(text="❌ Закрыть", callback_data="close_menu")
    builder.adjust(1)
    return builder.as_markup()

def user_edit_kb(user_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="🏷 Переименовать", callback_data=f"user_rename_{user_id}")
    builder.button(text="🔐 Управление группами", callback_data=f"user_groups_manage_{user_id}")
    builder.button(text="🗑 Удалить пользователя", callback_data=f"user_delete_{user_id}")
    builder.button(text="⬅️ Назад", callback_data="manage_users")
    builder.button(text="❌ Закрыть", callback_data="close_menu")
    builder.adjust(1)
    return builder.as_markup()

def user_groups_edit_kb(user_id):
    builder = InlineKeyboardBuilder()
    all_groups = db.get_all_groups()
    user_groups = [g[0] for g in db.get_user_groups(user_id)]
    for g_id, g_name in all_groups:
        status = "✅" if g_id in user_groups else "❌"
        action = "rev" if g_id in user_groups else "gra"
        builder.button(text=f"{status} {g_name}", callback_data=f"u_gr_{action}_{user_id}_{g_id}")
    builder.button(text="⬅️ Назад", callback_data=f"user_info_{user_id}")
    builder.button(text="❌ Закрыть", callback_data="close_menu")
    builder.adjust(1)
    return builder.as_markup()

def manage_roles_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Назначить роль пользователю", callback_data="assign_role_start")
    builder.button(text="📋 Список пользователей с ролями", callback_data="list_users_roles")
    builder.button(text="➕ Создать новую роль", callback_data="create_role_start")
    builder.button(text="⬅️ Назад", callback_data="admin_main")
    builder.button(text="❌ Закрыть", callback_data="close_menu")
    builder.adjust(1)
    return builder.as_markup()


def role_selection_kb(user_id: int, topic_id: int = None):
    """Клавиатура выбора роли для пользователя."""
    builder = InlineKeyboardBuilder()
    roles = db.get_all_roles()  # Новая функция, которую добавим позже
    for role_id, role_name in roles:
        # Не даём назначать superadmin через интерфейс (только суперадмин сам может, но упростим)
        if role_name == 'superadmin':
            continue
        callback_data = f"role_assign_{user_id}_{role_id}"
        if topic_id is not None:
            callback_data += f"_{topic_id}"
        builder.button(text=role_name.capitalize(), callback_data=callback_data)
    builder.button(text="⬅️ Назад", callback_data=f"user_roles_manage_{user_id}")
    builder.button(text="❌ Закрыть", callback_data="close_menu")
    builder.adjust(1)
    return builder.as_markup()


def user_roles_manage_kb(user_id: int):
    """Клавиатура управления ролями конкретного пользователя."""
    builder = InlineKeyboardBuilder()
    from config import ADMIN_ID  # добавьте в начало файла
    user_roles = list(db.get_user_roles(user_id))
    if user_id == ADMIN_ID and not any(r[0] == 'superadmin' for r in user_roles):
        user_roles.append(('superadmin', None))
    for role_name, topic_id in user_roles:
        if topic_id is None:
            display = f"✅ {role_name} (глобально)"
            callback = f"role_revoke_{user_id}_{db.get_role_id(role_name)}_None"
        else:
            topic_name = db.get_topic_name(topic_id)
            display = f"✅ {role_name} топика {topic_name}"
            callback = f"role_revoke_{user_id}_{db.get_role_id(role_name)}_{topic_id}"
        builder.button(text=display, callback_data=callback)
    builder.button(text="➕ Назначить роль", callback_data=f"role_assign_user_{user_id}")
    builder.button(text="⬅️ Назад", callback_data="manage_users")
    builder.button(text="❌ Закрыть", callback_data="close_menu")
    builder.adjust(1)
    return builder.as_markup()


def topic_selection_for_role_kb(user_id: int):
    """Клавиатура выбора топика для роли модератора."""
    builder = InlineKeyboardBuilder()
    topics = db.get_all_unique_topics()
    for t_id in topics:
        t_name = db.get_topic_name(t_id)
        builder.button(text=f"{t_name}", callback_data=f"role_assign_topic_{user_id}_{t_id}")
    builder.button(text="⬅️ Назад", callback_data=f"role_assign_user_{user_id}")
    builder.button(text="❌ Закрыть", callback_data="close_menu")
    builder.adjust(1)
    return builder.as_markup()

def back_to_manage_roles_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="manage_roles")
    builder.button(text="❌ Закрыть", callback_data="close_menu")
    builder.adjust(1)
    builder = InlineKeyboardBuilder()
    users = db.get_all_users()
    
    direct_users = set(u[0] for u in db.get_direct_access_users(topic_id))
    all_authorized = set(u[0] for u in db.get_topic_authorized_users(topic_id))
    has_access = direct_users | all_authorized
    
    for u_id, f_name, l_name in users:
        if u_id not in has_access:
            builder.button(
                text=f"❌ {f_name} {l_name}",
                callback_data=f"mod_tgl_dir_{u_id}_{topic_id}"
            )
            
    builder.button(
        text="⬅️ Назад",
        callback_data=f"mod_users_manage_{topic_id}"
    )
    builder.button(text="❌ Закрыть", callback_data="close_menu")
    builder.adjust(1)
    return builder.as_markup()


def moderator_topic_moderators_kb(topic_id: int):
    """Список модераторов топика с возможностью добавить/удалить."""
    builder = InlineKeyboardBuilder()
    moderators = db.get_moderators_of_topic(topic_id)
    for u_id, f_name, l_name in moderators:
        builder.button(
            text=f"👑 {f_name} {l_name}",
            callback_data=f"mod_moderator_remove_{u_id}_{topic_id}"
        )
    builder.button(
        text="➕ Назначить модератора",
        callback_data=f"mod_moderator_add_{topic_id}"
    )
    builder.button(
        text="⬅️ Назад",
        callback_data=f"mod_topic_select_{topic_id}"
    )
    builder.button(text="❌ Закрыть", callback_data="close_menu")
    builder.adjust(1)
    return builder.as_markup()