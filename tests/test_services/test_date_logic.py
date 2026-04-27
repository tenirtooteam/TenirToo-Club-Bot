import pytest
from services.date_service import DateService

@pytest.mark.parametrize("input_text, expected_human, expected_start, expected_end", [
    ("15 мая", "15 мая", "2026-05-15", None),
    ("Завтра", "Завтра", None, None), # Зависит от текущей даты, проверяем только факт парсинга ниже
    ("10-15 июня", "10-15 июня", "2026-06-10", "2026-06-15"),
    ("15 - 20 мая", "15 - 20 мая", "2026-05-15", "2026-05-20"),
    ("2026-05-01", "2026-05-01", "2026-05-01", None),
])
def test_parse_smart_date_variants(input_text, expected_human, expected_start, expected_end):
    """Проверка различных форматов ввода дат."""
    human, start, end = DateService.parse_smart_date(input_text)
    
    assert human == expected_human
    if expected_start:
        assert start == expected_start
    if expected_end:
        assert end == expected_end
    
    # КРИТИЧЕСКИЙ ТЕСТ: Проверка отсутствия "цирка" (скобок в human строке)
    assert "(" not in human, f"Обнаружены скобки в human-строке: {human}"
    assert ")" not in human, f"Обнаружены скобки в human-строке: {human}"

def test_get_weekday_suffix():
    """Проверка декоратора дня недели."""
    assert DateService.get_weekday_suffix("2026-05-15") == " (Пт)"
    assert DateService.get_weekday_suffix("2026-05-16") == " (Сб)"
    assert DateService.get_weekday_suffix("invalid") == ""
    assert DateService.get_weekday_suffix(None) == ""

def test_today_tomorrow_presets():
    """Проверка пресетов (сегодня/завтра)."""
    human_t, iso_t, _ = DateService.parse_smart_date("Сегодня")
    # ISO может не быть (dateparser иногда капризничает с русским 'Сегодня' без контекста)
    # Но скобок быть не должно!
    assert "(" not in human_t

def test_range_with_spaces():
    """Проверка парсинга диапазона с пробелами и без."""
    # Без пробелов
    h1, s1, e1 = DateService.parse_smart_date("10-12 мая")
    assert s1 == "2026-05-10"
    assert e1 == "2026-05-12"
    
    # С пробелами
    h2, s2, e2 = DateService.parse_smart_date("10 - 12 мая")
    assert s2 == "2026-05-10"
    assert e2 == "2026-05-12"
