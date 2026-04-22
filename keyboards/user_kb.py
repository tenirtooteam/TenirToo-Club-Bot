# File: keyboards/user_kb.py
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import db


def user_main_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="📍 Мои топики", callback_data="user_topics")
    builder.button(text="👤 Мой профиль", callback_data="user_profile_view")
    builder.button(text="❌ Закрыть", callback_data="close_menu")
    builder.adjust(1)
    return builder.as_markup()


def user_topics_list_kb(user_id: int):
    builder = InlineKeyboardBuilder()
    all_topics = db.get_all_unique_topics()
    user_available = set(db.get_user_available_topics(user_id))

    for t_id in all_topics:
        t_name = db.get_topic_name(t_id)
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

    builder.button(text="⬅️ Назад", callback_data="user_main")
    builder.button(text="❌ Закрыть", callback_data="close_menu")
    builder.adjust(1)
    return builder.as_markup()


def user_profile_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="user_main")
    builder.button(text="❌ Закрыть", callback_data="close_menu")
    builder.adjust(1)
    return builder.as_markup()


def user_topic_detail_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ К списку топиков", callback_data="user_topics")
    builder.button(text="❌ Закрыть", callback_data="close_menu")
    builder.adjust(1)
    return builder.as_markup()