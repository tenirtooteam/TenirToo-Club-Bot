import sqlite3
import logging
from typing import List, Dict, Any, Optional
from database.connection import get_conn

logger = logging.getLogger(__name__)

def create_event(title: str, start_date: str, end_date: str, creator_id: int, is_approved: int = 0) -> int:
    try:
        with get_conn() as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO events (title, start_date, end_date, creator_id, is_approved) VALUES (?, ?, ?, ?, ?)",
                    (title, start_date, end_date, creator_id, is_approved)
                )
                return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка создания мероприятия: {e}")
        return -1

def update_event_details(event_id: int, title: str, start_date: str, end_date: str) -> bool:
    try:
        with get_conn() as conn:
            with conn:
                conn.execute(
                    "UPDATE events SET title = ?, start_date = ?, end_date = ? WHERE event_id = ?",
                    (title, start_date, end_date, event_id)
                )
        return True
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка обновления мероприятия {event_id}: {e}")
        return False

def approve_event(event_id: int) -> bool:
    try:
        with get_conn() as conn:
            with conn:
                conn.execute("UPDATE events SET is_approved = 1 WHERE event_id = ?", (event_id,))
        return True
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка одобрения мероприятия {event_id}: {e}")
        return False

def set_event_sheet_url(event_id: int, sheet_url: str) -> bool:
    try:
        with get_conn() as conn:
            with conn:
                conn.execute("UPDATE events SET sheet_url = ? WHERE event_id = ?", (sheet_url, event_id))
        return True
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка установки sheet_url для {event_id}: {e}")
        return False

def delete_event(event_id: int) -> bool:
    try:
        from database.announcements import delete_announcements_by_target
        with get_conn() as conn:
            with conn:
                conn.execute("DELETE FROM events WHERE event_id = ?", (event_id,))
        
        # Ручная зачистка анонсов (т.к. там нет FK из-за полиморфизма)
        delete_announcements_by_target("event", event_id)
        return True
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка удаления мероприятия {event_id}: {e}")
        return False

def add_event_lead(event_id: int, user_id: int) -> bool:
    try:
        with get_conn() as conn:
            with conn:
                conn.execute("INSERT OR IGNORE INTO event_leads (event_id, user_id) VALUES (?, ?)", (event_id, user_id))
        return True
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка добавления лидера {user_id} в {event_id}: {e}")
        return False

def add_event_participant(event_id: int, user_id: int) -> bool:
    try:
        with get_conn() as conn:
            with conn:
                conn.execute("INSERT OR IGNORE INTO event_participants (event_id, user_id) VALUES (?, ?)", (event_id, user_id))
        return True
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка добавления участника {user_id} в {event_id}: {e}")
        return False

def remove_event_participant(event_id: int, user_id: int) -> bool:
    try:
        with get_conn() as conn:
            with conn:
                conn.execute("DELETE FROM event_participants WHERE event_id = ? AND user_id = ?", (event_id, user_id))
        return True
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка удаления участника {user_id} из {event_id}: {e}")
        return False

def is_event_participant(event_id: int, user_id: int) -> bool:
    try:
        with get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM event_participants WHERE event_id = ? AND user_id = ?", (event_id, user_id))
            return cursor.fetchone() is not None
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка проверки участника: {e}")
        return False

def get_event_details(event_id: int) -> Optional[Dict[str, Any]]:
    try:
        with get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT event_id, title, start_date, end_date, creator_id, is_approved, sheet_url FROM events WHERE event_id = ?", (event_id,))
            row = cursor.fetchone()
            if not row:
                return None
                
            cursor.execute("SELECT user_id FROM event_leads WHERE event_id = ?", (event_id,))
            leads = [r[0] for r in cursor.fetchall()]
            
            cursor.execute("SELECT user_id FROM event_participants WHERE event_id = ?", (event_id,))
            participants = [r[0] for r in cursor.fetchall()]
            
            return {
                "event_id": row[0],
                "title": row[1],
                "start_date": row[2],
                "end_date": row[3],
                "creator_id": row[4],
                "is_approved": bool(row[5]),
                "sheet_url": row[6],
                "leads": leads,
                "participants": participants
            }
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка получения деталей {event_id}: {e}")
        return None

def get_active_events() -> List[Dict[str, Any]]:
    try:
        with get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT event_id, title, start_date, end_date FROM events WHERE is_approved = 1 ORDER BY start_date ASC")
            return [{"event_id": r[0], "title": r[1], "start_date": r[2], "end_date": r[3]} for r in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка получения списка активных мероприятий: {e}")
        return []

def get_pending_events() -> List[Dict[str, Any]]:
    try:
        with get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT event_id, title, start_date, end_date, creator_id FROM events WHERE is_approved = 0 ORDER BY event_id ASC")
            return [{"event_id": r[0], "title": r[1], "start_date": r[2], "end_date": r[3], "creator_id": r[4]} for r in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка получения списка ожидающих мероприятий: {e}")
        return []
