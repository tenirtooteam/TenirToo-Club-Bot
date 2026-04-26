from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
import math

def add_nav_footer(builder: InlineKeyboardBuilder, back_data: str = None, include_close: bool = True, help_key: str = None, help_back_data: str = None):
    """
    Универсальный помощник для добавления кнопок навигации в 'подвал' меню [PL-5.1.14].
    Сверхкомпактный режим: [Назад] [Закрыть] [❓]
    """
    nav_buttons = []
    if back_data:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=back_data))
    
    if include_close:
        nav_buttons.append(InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu"))
    
    if help_key:
        back_link = help_back_data or back_data or "close_menu"
        nav_buttons.append(InlineKeyboardButton(text="❓", callback_data=f"help:{help_key}:{back_link}"))
    
    if nav_buttons:
        builder.row(*nav_buttons)


def build_paginated_menu(
    item_buttons: list[InlineKeyboardButton],
    static_buttons: list[InlineKeyboardButton],
    page: int,
    limit: int,
    callback_prefix: str,
    adjust_items: int = 1,
    search_type: str = None, # 'user', 'group', 'topic'
    search_action: str = None, # 'info', 'select', etc.
    search_context: str = None, # Additional data (e.g. topic_id)
    help_key: str = None
):
    builder = InlineKeyboardBuilder()
    start = (page - 1) * limit
    end = start + limit
    
    # 1. Основной список элементов
    for btn in item_buttons[start:end]:
        builder.button(text=btn.text, callback_data=btn.callback_data)
        
    builder.adjust(adjust_items)
    
    # 2. Навигация по страницам (Стрелки)
    nav_arrows = []
    total_items = len(item_buttons)
    total_pages = max(1, math.ceil(total_items / limit))
    
    if page > 1:
        nav_arrows.append(InlineKeyboardButton(text="◀️ Пред.", callback_data=f"{callback_prefix}_pg_{page - 1}"))
    if total_pages > 1:
        nav_arrows.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="ignore"))
    if page < total_pages:
        nav_arrows.append(InlineKeyboardButton(text="След. ▶️", callback_data=f"{callback_prefix}_pg_{page + 1}"))
        
    if nav_arrows:
        builder.row(*nav_arrows)

    # 3. Кнопка поиска
    if search_type and total_items > limit:
        search_cb = f"search_start_{search_type}_{search_action}"
        if search_context:
            search_cb += f"_{search_context}"
        builder.row(InlineKeyboardButton(text="🔎 Поиск", callback_data=search_cb))
        
    # 4. Статичные функциональные кнопки (фильтруем кнопки навигации и справки)
    footer_back_data = None
    footer_help_key = help_key
    
    for s_btn in static_buttons:
        # Если в статичных кнопках есть "Назад" или "Закрыть", мы их обработаем в футере
        if s_btn.callback_data == "close_menu":
            continue
        if s_btn.text == "⬅️ Назад" or s_btn.callback_data == callback_prefix:
            footer_back_data = s_btn.callback_data
            continue
        # Если в статичных кнопках есть справка (help:key:back)
        if s_btn.callback_data.startswith("help:"):
            parts = s_btn.callback_data.split(":")
            if len(parts) >= 2:
                footer_help_key = parts[1]
                continue
                
        # Остальные (функциональные) кнопки — на всю строку
        builder.row(s_btn)
        
    # 5. Универсальный футер [PL-5.1.14]
    add_nav_footer(builder, back_data=footer_back_data, help_key=footer_help_key)
        
    return builder.as_markup()
