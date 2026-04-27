# Файл: web/routers/announcements.py
import json
import logging
from fastapi import APIRouter, Header, HTTPException, Depends
from services.event_service import EventService
from services.management_service import ManagementService
from services.permission_service import PermissionService
from database import db
from ..auth import validate_webapp_init_data

router = APIRouter()
logger = logging.getLogger(__name__)

async def get_current_user_id(x_tg_init_data: str = Header(None)) -> int:
    """Dependency для извлечения и валидации user_id из заголовков [CC-3]."""
    if not x_tg_init_data:
        raise HTTPException(status_code=401, detail="Missing X-TG-Init-Data header")
    
    user_data = validate_webapp_init_data(x_tg_init_data)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    try:
        user_info = json.loads(user_data['user'])
        return int(user_info['id'])
    except (KeyError, json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid user data")

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
async def toggle_participation(ann_id: int, user_id: int = Depends(get_current_user_id)):
    """Переключает участие пользователя в мероприятии через TMA."""
    ann = db.get_announcement(ann_id)
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    ann_type, target_id, topic_id = ann[1], ann[2], ann[3]
    
    if not PermissionService.can_user_write_in_topic(user_id, topic_id):
         raise HTTPException(status_code=403, detail="Access denied")

    if ann_type != "event":
         raise HTTPException(status_code=400, detail="Only event participation is supported")

    success, message = ManagementService.toggle_event_participation(target_id, user_id)
    
    # Реактивность: обновляем сообщение в Telegram, если есть привязка [PL-5.1.18]
    if success:
        chat_id, message_id = ann[5], ann[6] # Из БД анонсов
        if chat_id and message_id:
            from loader import bot
            from services.announcement_service import AnnouncementService
            from keyboards.announcements_kb import get_announcement_kb
            
            try:
                new_text = AnnouncementService.format_announcement_text(ann_id)
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=new_text,
                    reply_markup=get_announcement_kb(ann_id)
                )
            except Exception as e:
                logger.warning(f"Не удалось обновить сообщение анонса {ann_id} из Web: {e}")

    # Уведомление организаторов [PL-5.1.13]
    if success and "записаны" in message:
        from loader import bot
        await EventService.notify_organizers_of_direct_join(bot, target_id, user_id)
    
    return {"success": success, "message": message}
