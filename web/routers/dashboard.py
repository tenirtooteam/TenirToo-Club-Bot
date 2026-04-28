# Файл: web/routers/dashboard.py
import logging
from fastapi import APIRouter, Depends, HTTPException
from services.permission_service import PermissionService
from services.management_service import ManagementService
from database import db
from ..auth import get_current_user_id

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/init")
async def get_dashboard_init(user_id: int = Depends(get_current_user_id)):
    """Возвращает начальные данные для дашборда (имя, роль, базовые статы)."""
    user_name = db.get_user_name(user_id) or "Путешественник"
    is_admin = PermissionService.is_global_admin(user_id)
    
    # Можно расширить статистикой позже
    return {
        "user_id": user_id,
        "name": user_name,
        "is_admin": is_admin,
        "stats": {
            "events_active": len(db.get_active_events()),
            "topics_available": len(db.get_user_available_topics(user_id))
        }
    }

@router.get("/topics")
async def get_user_topics(user_id: int = Depends(get_current_user_id)):
    """Возвращает список топиков, доступных пользователю."""
    topics = db.get_user_available_topics(user_id)
    return [{"id": t[0], "name": t[1]} for t in topics]

@router.get("/profile")
async def get_user_profile(user_id: int = Depends(get_current_user_id)):
    """Возвращает полные данные профиля пользователя."""
    user_name = db.get_user_name(user_id)
    roles = db.get_user_roles(user_id)
    
    return {
        "user_id": user_id,
        "name": user_name,
        "roles": [{"name": r[0], "topic_id": r[1]} for r in roles]
    }

@router.get("/events")
async def get_all_events(user_id: int = Depends(get_current_user_id)):
    """Возвращает список всех активных мероприятий."""
    events = db.get_active_events()
    results = []
    for e in events:
        # Для каждого ивента получаем детали (участники и т.д.)
        details = db.get_event_details(e['event_id'])
        if details:
            results.append({
                "id": e['event_id'],
                "title": e['title'],
                "date": e['start_date'],
                "participants_count": len(details['participants']),
                "is_participant": user_id in details['participants']
            })
    return results

@router.get("/events/{event_id}")
async def get_event_view(event_id: int, user_id: int = Depends(get_current_user_id)):
    """Возвращает детали мероприятия для просмотра в TMA."""
    details = db.get_event_details(event_id)
    if not details:
        raise HTTPException(status_code=404, detail="Event not found")
        
    return {
        "id": event_id,
        "title": details["title"],
        "start_date": details["start_date"],
        "end_date": details["end_date"],
        "participants_count": len(details["participants"]),
        "is_participant": user_id in details["participants"],
        "status": "approved" if details["is_approved"] else "pending"
    }

@router.post("/events/{event_id}/toggle")
async def toggle_event_participation_direct(event_id: int, user_id: int = Depends(get_current_user_id)):
    """Переключает участие в мероприятии напрямую из списка (без анонса)."""
    success, message = ManagementService.toggle_event_participation(event_id, user_id)
    
    if success and "записаны" in message:
        from loader import bot
        from services.event_service import EventService
        from services.announcement_service import AnnouncementService
        
        # Уведомляем организаторов
        await EventService.notify_organizers_of_direct_join(bot, event_id, user_id)
        
        # Обновляем анонс в группе [CC-2]
        await AnnouncementService.refresh_announcements(bot, "event", event_id)
        
    return {"success": success, "message": message}

# --- Admin Section (Mirroring Bot Start Menu) ---

@router.get("/admin/topics")
async def get_all_topics_admin(user_id: int = Depends(get_current_user_id)):
    """Возвращает список ВСЕХ топиков для админа."""
    if not PermissionService.is_global_admin(user_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    topic_ids = db.get_all_unique_topics()
    names_map = db.get_topic_names_by_ids(topic_ids)
    return [{"id": tid, "name": names_map.get(tid, f"ID: {tid}")} for tid in topic_ids]

@router.get("/admin/groups")
async def get_all_groups_admin(user_id: int = Depends(get_current_user_id)):
    """Возвращает список всех шаблонов доступа (групп)."""
    if not PermissionService.is_global_admin(user_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    groups = db.get_all_groups()
    return [{"id": g[0], "name": g[1]} for g in groups]

@router.get("/roles/faq")
async def get_roles_faq(user_id: int = Depends(get_current_user_id)):
    """Возвращает текст FAQ по ролям из HelpService."""
    from services.help_service import HelpService
    return {"text": HelpService.get_help("roles")}
