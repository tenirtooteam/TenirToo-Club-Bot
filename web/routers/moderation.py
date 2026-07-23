# Файл: web/routers/moderation.py
"""Домен модерации событий для TMA [feature 016].

Тонкий адаптер над существующими сервисами — новой бизнес-логики нет:
очередь -> ManagementService.get_moderation_queue (скоупинг под зрителя, D1/FR-007);
резолв -> ManagementService.resolve_request (атомарный CAS feature 007 → exactly-once).

Authority-parity (R-SEC-3, R-ARCH-7) перепроверяется server-side ПО ТИПУ заявки перед
резолвом: черновики (event_approval) — только глобальный админ; участие (event_participation)
— только организаторы этого похода (EventService.is_organizer_of_event). Блочного require_admin
на домене НЕТ. Идентичность — только из проверенных init-data (R-SEC-1). display() на JSON-
границе разворачивает HTML-сущности; фронт re-экранирует (D3, defense in depth).
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database import db
from services.event_service import EventService
from services.management_service import ManagementService

from ..auth import get_current_user_id
from ..serialization import display

router = APIRouter()
logger = logging.getLogger(__name__)


class ResolvePayload(BaseModel):
    """Тело резолва: решение + необязательный комментарий."""
    status: str
    comment: Optional[str] = None


def _can_resolve(user_id: int, request) -> bool:
    """Authority-parity по типу заявки (D1/FR-007)."""
    entity_type = request["entity_type"]
    if entity_type == "event_approval":
        return db.is_global_admin(user_id)
    if entity_type == "event_participation":
        return EventService.is_organizer_of_event(user_id, request["entity_id"])
    return False


@router.get("/queue")
async def get_queue(user_id: int = Depends(get_current_user_id)):
    """Скоупленная под зрителя очередь pending-заявок (D1/FR-007)."""
    items = ManagementService.get_moderation_queue(user_id)
    return {
        "items": [
            {
                **it,
                "event_title": display(it["event_title"]),
                "requester_name": display(it["requester_name"]),
            }
            for it in items
        ]
    }


@router.post("/requests/{request_id}/resolve")
async def resolve_request(
    request_id: int,
    payload: ResolvePayload,
    user_id: int = Depends(get_current_user_id),
):
    """Одобрить/отклонить заявку. Право перепроверяется по типу перед resolve_request."""
    if payload.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Некорректное решение.")

    request = db.get_audit_request(request_id)
    if request is None:
        # Заявка исчезла — идемпотентный fail-closed, не транспортная ошибка.
        return {"success": False, "message": "⚠️ Заявка не найдена или уже обработана."}

    if not _can_resolve(user_id, request):
        logger.warning(
            f"[016] Resolve denied: user={user_id} request={request_id} type={request['entity_type']}"
        )
        raise HTTPException(status_code=403, detail="❌ У вас нет прав на это действие.")

    from loader import bot
    success, message = await ManagementService.resolve_request(
        bot, request_id, payload.status, payload.comment
    )
    return {"success": success, "message": message}


@router.get("/events/{event_id}/participants")
async def get_participants(event_id: int, user_id: int = Depends(get_current_user_id)):
    """Состав похода для его организаторов (US3). Источник — get_event_details (без нового read)."""
    event = db.get_event_details(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Поход не найден.")
    if not EventService.is_organizer_of_event(user_id, event_id):
        raise HTTPException(status_code=403, detail="❌ У вас нет прав на это действие.")

    organizers = set(event["leads"])
    if event["creator_id"] is not None:
        organizers.add(event["creator_id"])

    participants = [
        {
            "user_id": uid,
            "display_name": display(db.get_user_name(uid)) or f"ID:{uid}",
            "is_organizer": uid in organizers,
        }
        for uid in event["participants"]
    ]
    return {
        "event_id": event_id,
        "event_title": display(event["title"]),
        "capacity": None,  # capacity презентационный — жёсткого серверного лимита нет (spec)
        "participants": participants,
    }


@router.delete("/events/{event_id}/participants/{user_id}")
async def remove_participant(
    event_id: int, user_id: int, caller_id: int = Depends(get_current_user_id)
):
    """Снятие участника организатором (US3). {user_id} — цель, идентичность caller — из init-data.

    Снятие идёт через единую точку последствий feature 014 (remove-only: не-участник = no-op,
    без скрытой записи, BUG-4; рефреш анонса при фактическом изменении).
    """
    if not EventService.is_organizer_of_event(caller_id, event_id):
        logger.warning(
            f"[016] Remove denied: caller={caller_id} event={event_id} target={user_id}"
        )
        raise HTTPException(status_code=403, detail="❌ У вас нет прав на это действие.")

    from loader import bot
    success, message = await EventService.apply_participation_change(
        bot, event_id, user_id, "leave"
    )
    return {"success": success, "message": message}
