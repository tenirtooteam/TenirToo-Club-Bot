from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
import math

def build_paginated_menu(
    item_buttons: list[InlineKeyboardButton],
    static_buttons: list[InlineKeyboardButton],
    page: int,
    limit: int,
    callback_prefix: str,
    adjust_items: int = 1,
    search_type: str = None, # 'user', 'group', 'topic'
    search_action: str = None, # 'info', 'select', etc.
    search_context: str = None # Additional data (e.g. topic_id)
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
    total_items = len(item_buttons)
    total_pages = max(1, math.ceil(total_items / limit))
    
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"{callback_prefix}_pg_{page - 1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"{callback_prefix}_pg_{page + 1}"))
        
    if nav_buttons:
        builder.row(*nav_buttons)

    # Add search button if total items > limit
    if search_type and total_items > limit:
        search_cb = f"search_start_{search_type}_{search_action}"
        if search_context:
            search_cb += f"_{search_context}"
        builder.row(InlineKeyboardButton(text="🔎 Поиск", callback_data=search_cb))
        
    # Add static buttons
    for s_btn in static_buttons:
        builder.row(s_btn)
        
    return builder.as_markup()
