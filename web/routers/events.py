# Файл: web/routers/events.py
"""Домен авторинга событий для TMA [feature 015].

Тонкий адаптер над существующими санитизирующими мутациями — НОВОЙ бизнес-логики нет:
создание -> ManagementService.create_event_action (+ submit_request + notify), редактирование
-> ManagementService.update_event_details. Даты разбираются на сервере через DateService
(R-CODE-5). Authority-parity (R-SEC-3, R-ARCH-7): создание — любому авторизованному (как в
боте, без admin-гейта); редактирование — per-event через EventService.can_edit_event.
БЛОЧНОГО require_admin на домене НЕТ (это инструмент домена 017).
"""
import logging
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services.date_service import DateService
from services.event_service import EventService
from services.management_service import ManagementService

from ..auth import get_current_user_id

router = APIRouter()
logger = logging.getLogger(__name__)


class EventPayload(BaseModel):
    """Тело формы авторинга: сырые человекочитаемые строки, разбор — на сервере."""
    title: str
    date_text: str
    end_date_text: Optional[str] = None


def _resolve_dates(date_text: str, end_date_text: Optional[str]) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
    """Воспроизводит разбор дат хендлера (R-CODE-5): возвращает
    (start_human, end_human, start_iso, end_iso). Нераспознанная дата -> start_iso is None."""
    human, iso_start, iso_end = DateService.parse_smart_date(date_text)

    if end_date_text and end_date_text.strip():
        # Явный конец диапазона отдельным полем (паритет с шагом "добавить дату окончания").
        end_human, end_iso, _ = DateService.parse_smart_date(end_date_text)
        return human, end_human, iso_start, end_iso
    if iso_end:
        # Диапазон внутри date_text ("10-15 июня"): декомпозируем human, месяц не теряется [BUG-1].
        s_human, e_human = DateService.split_human_range(date_text)
        return s_human, e_human, iso_start, iso_end
    return human, None, iso_start, None


@router.post("")
async def create_event(payload: EventPayload, user_id: int = Depends(get_current_user_id)):
    """Создаёт поход из TMA. Только сессия — паритет с ботовым event_create (без admin-гейта)."""
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="Введите название похода.")

    s_human, e_human, iso_start, iso_end = _resolve_dates(payload.date_text, payload.end_date_text)

    # Мутация + санитизация — в сервисе (R-DATA-1); создатель авто-регистрируется участником и лидом.
    event_id = ManagementService.create_event_action(
        title=payload.title,
        start_date=s_human,
        creator_id=user_id,
        is_approved=0,
        end_date=e_human,
        start_iso=iso_start,
        end_iso=iso_end,
    )
    if event_id <= 0:
        raise HTTPException(status_code=500, detail="Ошибка базы данных")

    # Хвост создания — паритет с ботом: заявка в очередь одобрения + уведомление админов.
    ManagementService.submit_request(user_id, "event_approval", event_id)
    from loader import bot
    await EventService.notify_admins_for_approval(bot, event_id)

    return {
        "success": True,
        "event_id": event_id,
        "date_recognized": iso_start is not None,
        "message": "🚀 Поход создан и отправлен на модерацию!",
    }


@router.put("/{event_id}")
async def update_event(event_id: int, payload: EventPayload, user_id: int = Depends(get_current_user_id)):
    """Редактирует поход из TMA. Право — per-event через can_edit_event (authority-parity)."""
    if EventService.get_event_details(event_id) is None:
        raise HTTPException(status_code=404, detail="Поход не найден.")

    # Серверный авторитет: создатель/организатор/глобал-админ — тот же критерий, что в боте.
    if not EventService.can_edit_event(user_id, event_id):
        logger.warning(f"[015 US2] Edit denied: user={user_id} event={event_id}")
        raise HTTPException(status_code=403, detail="❌ У вас нет прав на редактирование.")

    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="Введите название похода.")

    s_human, e_human, iso_start, iso_end = _resolve_dates(payload.date_text, payload.end_date_text)

    ManagementService.update_event_details(
        event_id, payload.title, s_human, e_human, iso_start, iso_end
    )

    return {
        "success": True,
        "event_id": event_id,
        "date_recognized": iso_start is not None,
        "message": "✅ Изменения сохранены!",
    }
