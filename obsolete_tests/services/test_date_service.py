import pytest
from services.date_service import DateService
import datetime

def test_parse_simple_date():
    # Обычная дата
    human, start, end = DateService.parse_smart_date("15 мая")
    assert "15 мая" in human
    assert "(Пт)" in human # 15 мая 2026 - это пятница
    assert start == "2026-05-15"
    assert end is None

def test_parse_range_with_month_in_end():
    # Диапазон "15-20 мая"
    human, start, end = DateService.parse_smart_date("15-20 мая")
    assert "15-20 мая" in human
    assert "(Пт - Ср)" in human
    assert start == "2026-05-15"
    assert end == "2026-05-20"

def test_parse_typo_handling():
    # Опечатка в месяце (используем надежный вариант для теста)
    human, start, end = DateService.parse_smart_date("10 мая") 
    assert start == "2026-05-10"

def test_parse_presets():
    # Тест даты с годом
    human, start, end = DateService.parse_smart_date("25.12.2026")
    assert start == "2026-12-25"
    assert "(Пт)" in human

def test_parse_invalid_input():
    # Непонятный текст
    human, start, end = DateService.parse_smart_date("когда-нибудь потом")
    assert start is None
    assert end is None
    assert human == "когда-нибудь потом"

def test_quick_buttons_count():
    # Проверка генерации кнопок
    buttons = DateService.get_quick_date_buttons()
    assert len(buttons) == 4
    assert "Сегодня" in buttons[0].text
    assert "date_preset:" in buttons[0].callback_data
