# Файл: services/date_service.py
import datetime
import dateparser
import logging
from typing import Optional, Tuple, List
from aiogram.types import InlineKeyboardButton

logger = logging.getLogger(__name__)

class DateService:
    # Русские названия дней недели
    WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

    @staticmethod
    def get_weekday_suffix(iso_date: str) -> str:
        """Возвращает строку вида ' (Пн)' для ISO даты."""
        try:
            dt = datetime.datetime.strptime(iso_date, "%Y-%m-%d")
            return f" ({DateService.WEEKDAYS[dt.weekday()]})"
        except (ValueError, TypeError):
            return ""

    @staticmethod
    def parse_smart_date(text: str) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Парсит текст в даты. 
        Возвращает (human_readable, start_iso, end_iso).
        Пример: "15 мая" -> ("15 мая", "2026-05-15", None)
        """
        text = text.strip()
        
        # Обработка диапазонов (например "15-20 мая")
        # Исключаем ISO даты (YYYY-MM-DD), у которых 2 тире [CC-2]
        if text.count("-") == 1:
            parts = text.split("-")
            start_p = parts[0].strip()
            end_p = parts[1].strip()
            
            if not any(m in start_p.lower() for m in ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]):
                month_part = "".join([c for c in end_p if not c.isdigit()]).strip()
                start_p = f"{start_p} {month_part}"
            
            start_dt = dateparser.parse(start_p, languages=['ru', 'en'], settings={'PREFER_DATES_FROM': 'future'})
            end_dt = dateparser.parse(end_p, languages=['ru', 'en'], settings={'PREFER_DATES_FROM': 'future'})
            
            if start_dt and end_dt:
                # Возвращаем ЧИСТЫЙ текст без скобок для БД [CC-2]
                return text, start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")

        # Одиночная дата
        dt = dateparser.parse(text, languages=['ru', 'en'], settings={'PREFER_DATES_FROM': 'future'})
        if dt:
            return text, dt.strftime("%Y-%m-%d"), None
            
        return text, None, None

    @staticmethod
    def get_quick_date_buttons() -> List[InlineKeyboardButton]:
        """Генерирует кнопки: Сегодня, Завтра, Ближайшая Сб, Ближайшее Вс."""
        now = datetime.datetime.now()
        buttons = []
        
        # Сегодня
        buttons.append(InlineKeyboardButton(
            text=f"Сегодня ({now.strftime('%d.%m')})", 
            callback_data=f"date_preset:{now.strftime('%Y-%m-%d')}"
        ))
        
        # Завтра
        tomorrow = now + datetime.timedelta(days=1)
        buttons.append(InlineKeyboardButton(
            text=f"Завтра ({tomorrow.strftime('%d.%m')})", 
            callback_data=f"date_preset:{tomorrow.strftime('%Y-%m-%d')}"
        ))
        
        # Ближайшая суббота (если сегодня суббота, берем следующую?)
        # Обычно люди ищут субботу на этой неделе
        days_to_sat = (5 - now.weekday()) % 7
        if days_to_sat == 0: days_to_sat = 7 # Если сегодня Сб, предлагаем следующую
        sat = now + datetime.timedelta(days=days_to_sat)
        buttons.append(InlineKeyboardButton(
            text=f"Сб ({sat.strftime('%d.%m')})", 
            callback_data=f"date_preset:{sat.strftime('%Y-%m-%d')}"
        ))
        
        # Ближайшее воскресенье
        days_to_sun = (6 - now.weekday()) % 7
        if days_to_sun == 0: days_to_sun = 7
        sun = now + datetime.timedelta(days=days_to_sun)
        buttons.append(InlineKeyboardButton(
            text=f"Вс ({sun.strftime('%d.%m')})", 
            callback_data=f"date_preset:{sun.strftime('%Y-%m-%d')}"
        ))
        
        return buttons
