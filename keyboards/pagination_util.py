from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
import math

def build_paginated_menu(
    item_buttons: list[InlineKeyboardButton],
    static_buttons: list[InlineKeyboardButton],
    page: int,
    limit: int,
    callback_prefix: str,
    adjust_items: int = 1
):
    builder = InlineKeyboardBuilder()
    start = (page - 1) * limit
    end = start + limit
    
    # Add items
    for btn in item_buttons[start:end]:
        builder.button(text=btn.text, callback_data=btn.callback_data)
        
    builder.adjust(adjust_items)
    
    # Add navigation
    nav_buttons = []
    total_pages = max(1, math.ceil(len(item_buttons) / limit))
    
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"{callback_prefix}_pg_{page - 1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"{callback_prefix}_pg_{page + 1}"))
        
    if nav_buttons:
        builder.row(*nav_buttons)
        
    # Add static buttons
    for s_btn in static_buttons:
        builder.row(s_btn)
        
    return builder.as_markup()
