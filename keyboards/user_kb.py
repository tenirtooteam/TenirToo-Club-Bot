# File: keyboards/user_kb.py
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import db
from keyboards.pagination_util import add_nav_footer


def user_main_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="📍 Мои топики", callback_data="user_topics")
    builder.button(text="🏔 Мероприятия", callback_data="event_list")
    builder.button(text="👤 Мой профиль", callback_data="user_profile_view")
    builder.adjust(1)
    add_nav_footer(builder)
    return builder.as_markup()


def user_topics_list_kb(user_id: int):
    builder = InlineKeyboardBuilder()
    all_topics = db.get_all_unique_topics()
    user_available = set(db.get_user_available_topics(user_id))
    
    # Оптимизация: пакетная выборка имён [PL-HI]
    names_map = db.get_topic_names_by_ids(all_topics)

    for t_id in all_topics:
        t_name = names_map.get(t_id, f"ID: {t_id}")
        if t_id in user_available:
            status = "✅"
            label = ""
        else:
            status = "❌"
            label = " [Нет доступа]"

        builder.button(
            text=f"{status} {t_name}{label}",
            callback_data=f"u_topic_info_{t_id}"
        )

    builder.adjust(1)
    add_nav_footer(builder, back_data="user_main")
    return builder.as_markup()


def user_profile_kb():
    builder = InlineKeyboardBuilder()
    add_nav_footer(builder, back_data="user_main")
    return builder.as_markup()


def user_topic_detail_kb():
    builder = InlineKeyboardBuilder()
    add_nav_footer(builder, back_data="user_topics")
    return builder.as_markup()