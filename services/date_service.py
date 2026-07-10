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

    # Корни названий месяцев — единый источник для распознавания диапазонов [CC-2]
    MONTH_STEMS = ["янв", "фев", "мар", "апр", "май", "июн",
                   "июл", "авг", "сен", "окт", "ноя", "дек"]

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

            if not any(m in start_p.lower() for m in DateService.MONTH_STEMS):
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
    def split_human_range(text: str) -> Tuple[str, Optional[str]]:
        """
        Декомпозирует human-строку диапазона в (start_human, end_human).
        Использует ту же логику распознавания разделителя и наследования месяца,
        что и parse_smart_date, поэтому start НИКОГДА не теряет месяц [BUG-1, R-CODE-5/6]:
          "10-15 июня"        -> ("10 июня", "15 июня")
          "10 - 15 мая"       -> ("10 мая",  "15 мая")
          "10 июня - 15 июня" -> ("10 июня", "15 июня")
          "15 мая"            -> ("15 мая",  None)
        Не-диапазон / нераспознанное -> (text, None).
        """
        text = text.strip()

        # Приоритет явного разделителя с пробелами (так строится период в
        # process_event_end_date: f"{start} - {end}", где start может быть "Завтра").
        # Иначе — слитный "-" РОВНО один раз (ISO YYYY-MM-DD с двумя "-" не диапазон).
        if " - " in text:
            sep = " - "
        elif text.count("-") == 1:
            sep = "-"
        else:
            return text, None

        start_p, end_p = (p.strip() for p in text.split(sep, 1))

        # Наследуем месяц в start ТОЛЬКО когда start — голый номер дня ("10" из
        # "10-15 июня"); "Завтра"/"10 июня" не трогаем.
        if start_p.isdigit():
            month_part = "".join(c for c in end_p if not c.isdigit()).strip()
            if month_part:
                start_p = f"{start_p} {month_part}"

        return start_p, end_p

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
