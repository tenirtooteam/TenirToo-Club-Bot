import pytest
from aiogram.types import InlineKeyboardButton
from keyboards.pagination_util import build_paginated_menu

def test_build_paginated_menu_first_page():
    # 10 кнопок, лимит 7
    items = [InlineKeyboardButton(text=f"Item {i}", callback_data=f"i_{i}") for i in range(1, 11)]
    static = [InlineKeyboardButton(text="Back", callback_data="back")]
    
    markup = build_paginated_menu(items, static, page=1, limit=7, callback_prefix="test")
    
    # Проверяем количество кнопок на 1-й странице (7 айтемов + 1 навигация "Вперёд" + 1 статик)
    # В aiogram 3 markup.inline_keyboard - это список списков
    rows = markup.inline_keyboard
    
    # Считаем общее кол-во кнопок
    all_btns = [b for row in rows for b in row]
    
    # 7 элементов
    assert any(b.text == "Item 1" for b in all_btns)
    assert any(b.text == "Item 7" for b in all_btns)
    assert not any(b.text == "Item 8" for b in all_btns)
    
    # Навигация (только вперед)
    assert any("Вперёд" in b.text for b in all_btns)
    assert not any("Назад" in b.text for b in all_btns)
    
    # Статическая
    assert any(b.text == "Back" for b in all_btns)

def test_build_paginated_menu_last_page():
    items = [InlineKeyboardButton(text=f"Item {i}", callback_data=f"i_{i}") for i in range(1, 11)]
    
    markup = build_paginated_menu(items, [], page=2, limit=7, callback_prefix="test")
    all_btns = [b for row in markup.inline_keyboard for b in row]
    
    # Должно быть 3 элемента (8, 9, 10)
    assert any(b.text == "Item 10" for b in all_btns)
    assert not any(b.text == "Item 1" for b in all_btns)
    
    # Навигация (только назад)
    assert any("Назад" in b.text for b in all_btns)
    assert not any("Вперёд" in b.text for b in all_btns)

def test_build_paginated_menu_search_injection():
    items = [InlineKeyboardButton(text=f"Item {i}", callback_data=f"i_{i}") for i in range(1, 10)]
    
    # Поиск должен появиться, так как 9 > 7
    markup = build_paginated_menu(items, [], page=1, limit=7, callback_prefix="test", search_type="user", search_action="select")
    all_btns = [b for row in markup.inline_keyboard for b in row]
    
    assert any("Поиск" in b.text for b in all_btns)
    assert any(b.callback_data == "search_start_user_select" for b in all_btns)
