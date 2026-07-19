# Файл: web/routers/announcements.py
import logging
from fastapi import APIRouter, HTTPException, Depends
from services.event_service import EventService
from services.permission_service import PermissionService
from database import db
from ..auth import get_current_user_id

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/{ann_id}")
async def get_announcement_details(ann_id: int, user_id: int = Depends(get_current_user_id)):
    """Возвращает детали анонса для TMA [CC-1]."""
    ann = db.get_announcement(ann_id)
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")

    ann_type, target_id, topic_id = ann[1], ann[2], ann[3]

    # Проверка прав доступа к топику [CP-2.10]
    if not PermissionService.can_user_write_in_topic(user_id, topic_id):
         raise HTTPException(status_code=403, detail="No access to this topic")

    if ann_type != "event":
         raise HTTPException(status_code=400, detail="Unsupported announcement type")

    event = EventService.get_event_details(target_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    is_participant = EventService.is_event_participant(target_id, user_id)

    return {
        "id": ann_id,
        "event_id": target_id,
        "title": event["title"],
        "start_date": event["start_date"],
        "end_date": event["end_date"],
        "is_participant": is_participant,
        "participants_count": len(event["participants"]),
        "status": "approved" if event["is_approved"] else "pending"
    }

@router.post("/{ann_id}/toggle")
async def toggle_participation(ann_id: int, action: str | None = None, user_id: int = Depends(get_current_user_id)):
    """Изменяет участие в мероприятии через анонс TMA по явному намерению.

    [Feature 014] action = "join" | "leave"; мутация + все последствия (уведомление
    организаторов на запись + обновление ВСЕХ копий анонса) — в единой точке
    EventService.apply_participation_change. Ручной edit одного сообщения удалён: обновление
    всех копий делает refresh_announcements внутри метода.
    """
    if action not in ("join", "leave"):
        raise HTTPException(status_code=400, detail="Некорректное действие. Обновите страницу.")

    ann = db.get_announcement(ann_id)
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")

    ann_type, target_id, topic_id = ann[1], ann[2], ann[3]

    if ann_type != "event":
         raise HTTPException(status_code=400, detail="Only event participation is supported")

    # Единый гард прямой записи [feature 006, FR-001/002] — топик анонса + проверка одобрения.
    allowed, reason = EventService.check_direct_join_allowed(user_id, target_id, topic_id=topic_id)
    if not allowed:
         logger.warning(f"[FR-011] Web announcement change denied: user={user_id} event={target_id} topic={topic_id} action={action} reason={reason}")
         raise HTTPException(status_code=403, detail=reason)

    from loader import bot
    success, message = await EventService.apply_participation_change(bot, target_id, user_id, action)
    return {"success": success, "message": message}
