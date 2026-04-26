import sqlite3
import logging
from typing import List, Optional, Tuple, Any
from database.connection import get_conn

logger = logging.getLogger(__name__)

def create_audit_request(user_id: int, entity_type: str, entity_id: int) -> int:
    """Создает новую заявку на аудит."""
    try:
        with get_conn() as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO audit_requests (user_id, entity_type, entity_id, status) VALUES (?, ?, ?, 'pending')",
                    (user_id, entity_type, entity_id)
                )
                return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка создания audit_request: {e}")
        return -1

def get_audit_request(request_id: int) -> Optional[dict]:
    """Получает детали заявки по ID."""
    try:
        with get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, user_id, entity_type, entity_id, status, comment FROM audit_requests WHERE id = ?", (request_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "user_id": row[1],
                    "entity_type": row[2],
                    "entity_id": row[3],
                    "status": row[4],
                    "comment": row[5]
                }
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка получения audit_request {request_id}: {e}")
    return None

def resolve_audit_request(request_id: int, status: str, comment: str = None) -> bool:
    """Обновляет статус заявки (approve/reject)."""
    try:
        with get_conn() as conn:
            with conn:
                conn.execute(
                    "UPDATE audit_requests SET status = ?, comment = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status, comment, request_id)
                )
        return True
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка разрешения audit_request {request_id}: {e}")
        return False

def get_pending_requests_by_type(entity_type: str, entity_id: int) -> List[int]:
    """Возвращает ID всех 'pending' заявок для конкретной сущности."""
    try:
        with get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM audit_requests WHERE entity_type = ? AND entity_id = ? AND status = 'pending'",
                (entity_type, entity_id)
            )
            return [r[0] for r in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка получения pending заявок: {e}")
        return []

def get_user_pending_request(user_id: int, entity_type: str, entity_id: int) -> Optional[int]:
    """Проверяет, есть ли у пользователя уже активная заявка на эту сущность."""
    try:
        with get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM audit_requests WHERE user_id = ? AND entity_type = ? AND entity_id = ? AND status = 'pending'",
                (user_id, entity_type, entity_id)
            )
            row = cursor.fetchone()
            return row[0] if row else None
    except sqlite3.Error as e:
        logger.error(f"❌ Ошибка проверки активной заявки пользователя: {e}")
        return None
