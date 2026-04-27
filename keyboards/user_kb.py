# File: keyboards/user_kb.py
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import db
from keyboards.pagination_util import add_nav_footer, build_paginated_menu


def user_main_kb():
    from aiogram.types import WebAppInfo
    import config
    builder = InlineKeyboardBuilder()
    
    if config.WEBAPP_URL and config.WEBAPP_URL.startswith("http"):
        builder.button(text="🏔 ЛИЧНЫЙ КАБИНЕТ (Mini App)", web_app=WebAppInfo(url=config.WEBAPP_URL))
        
    builder.button(text="[ 📍 МОИ ТОПИКИ ]", callback_data="user_topics")
    builder.button(text="[ 🏔 МЕРОПРИЯТИЯ ]", callback_data="event_list")
    builder.button(text="[ 👤 МОЙ ПРОФИЛЬ ]", callback_data="user_profile_view")
    builder.adjust(1)
    add_nav_footer(builder, help_key="main_menu", help_back_data="landing")
    return builder.as_markup()


def user_topics_list_kb(user_id: int, page: int = 1, limit: int = 7):
    from aiogram.types import InlineKeyboardButton
    all_topics = db.get_all_unique_topics()
    user_available = set(db.get_user_available_topics(user_id))
    names_map = db.get_topic_names_by_ids(all_topics)
    
    item_buttons = []
    for t_id in all_topics:
        t_name = names_map.get(t_id, f"ID: {t_id}")
        status = "✅" if t_id in user_available else "❌"
        label = "" if t_id in user_available else " [Нет доступа]"
        item_buttons.append(InlineKeyboardButton(
            text=f"{status} {t_name}{label}",
            callback_data=f"u_topic_info_{t_id}"
        ))

    static_buttons = [
        InlineKeyboardButton(text="❌ ЗАКРЫТЬ", callback_data="close_menu")
    ]
    return build_paginated_menu(item_buttons, static_buttons, page, limit, "user_topics", help_key="topics", help_back_data="user_topics")


def user_profile_kb():
    builder = InlineKeyboardBuilder()
    add_nav_footer(builder, back_data="user_main", help_key="profile", help_back_data="user_profile_view")
    return builder.as_markup()


def user_topic_detail_kb(topic_id: int):
    builder = InlineKeyboardBuilder()
    add_nav_footer(builder, back_data="user_topics", help_key="profile", help_back_data=f"u_topic_info_{topic_id}")
    return builder.as_markup()