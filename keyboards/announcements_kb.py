# Файл: keyboards/announcements_kb.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
import config

def get_announcement_kb(announcement_id: int, is_group: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для анонса: в группах — Текст, в ЛС — TMA Dashboard."""
    builder = InlineKeyboardBuilder()

    if is_group:
        # В группах используем классические кнопки (две в ряд)
        builder.row(
            InlineKeyboardButton(text="✅ Иду", callback_data=f"ann_join:{announcement_id}:1"),
            InlineKeyboardButton(text="🚶 Не иду", callback_data=f"ann_join:{announcement_id}:0")
        )
    else:
        # В ЛС даем кнопку Личного Кабинета (Mini App)
        # Шэф, тут теперь 'Центральное варево'
        builder.row(
            InlineKeyboardButton(
                text="🏔 Личный кабинет", 
                web_app=WebAppInfo(url=f"{config.WEBAPP_URL}/?ann_id={announcement_id}")
            )
        )

    return builder.as_markup()
