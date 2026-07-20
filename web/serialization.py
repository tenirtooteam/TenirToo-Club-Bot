# Файл: web/serialization.py
"""Сериализация отображаемых строк для JSON-границы TMA [feature 015, D3].

Мутации хранят названия/даты HTML-escaped (для parse_mode=HTML бота). JSON — не HTML-контекст,
поэтому на границе веб-моста строки разворачиваются обратно в сырой человекочитаемый вид, чтобы
escape-by-default рендер-слой фронта (textContent) показал корректные глифы. Мутационные методы
ManagementService при этом НЕ трогаются — бот сохраняет своё HTML-экранирование.

Рендер-слой всё равно экранирует на DOM независимо (defense in depth, FR-013)."""
import html
from typing import Optional


def display(value: Optional[str]) -> Optional[str]:
    """Разворачивает HTML-сущности в отображаемом строковом поле. No-op для строк без сущностей
    и для не-строк (None и т.п.)."""
    if isinstance(value, str):
        return html.unescape(value)
    return value
