import pytest
from keyboards.event_kb import get_events_list_kb

def test_events_list_kb_back_button():
    """Проверяет, что кнопка 'Назад' ведет в user_main, а не в user_menu."""
    kb = get_events_list_kb([])
    
    # Ищем кнопку "Назад"
    back_button = None
    for row in kb.inline_keyboard:
        for btn in row:
            if "Назад" in btn.text:
                back_button = btn
                break
                
    assert back_button is not None, "Кнопка 'Назад' не найдена в клавиатуре"
    assert back_button.callback_data == "user_main", "Кнопка 'Назад' должна ссылаться на user_main"
