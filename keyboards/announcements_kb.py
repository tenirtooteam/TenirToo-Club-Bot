# Файл: keyboards/announcements_kb.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_announcement_kb(ann_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для анонса: Кнопка участия."""
    builder = InlineKeyboardBuilder()
    
    # Мы используем префикс ann_join, чтобы в хендлере понять, 
    # что это клик по анонсу-диспетчеру
    builder.button(text="✅ Иду / ❌ Передумал", callback_data=f"ann_join:{ann_id}")
    
    return builder.as_markup()
