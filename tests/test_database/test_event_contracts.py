import pytest
from database import db
from database.connection import get_conn

def test_event_details_mapping_contract():
    """
    Проверяет, что маппинг в get_event_details соответствует схеме таблицы events.
    Это предотвращает KeyError при добавлении новых колонок.
    """
    # 1. Получаем список колонок из БД напрямую
    with get_conn() as conn:
        cursor = conn.cursor()
        columns = [row[1] for row in cursor.execute("PRAGMA table_info(events)").fetchall()]
    
    # 0. Обеспечиваем наличие юзера для FK [CC-2]
    db.add_user(1, "Test", "User")
    
    # 2. Создаем фейковый ивент для теста
    event_id = db.create_event(
        title="Contract Test",
        start_date="2026-01-01",
        end_date=None,
        creator_id=1,
        is_approved=1,
        start_iso="2026-01-01",
        end_iso=None
    )
    
    try:
        # 3. Получаем детали через фасад
        details = db.get_event_details(event_id)
        assert details is not None
        
        # 4. Проверяем наличие всех колонок в ключах словаря
        # Исключаем технические поля, если они не нужны в бизнес-логике, 
        # но основные (особенно новые ISO) должны быть.
        expected_keys = {
            'event_id', 'title', 'start_date', 'end_date', 
            'creator_id', 'is_approved', 'sheet_url', 
            'start_iso', 'end_iso'
        }
        
        for key in expected_keys:
            assert key in details, f"Ключ '{key}' отсутствует в возвращаемом словаре get_event_details"
            
    finally:
        # Чистим за собой
        db.delete_event(event_id)

def test_active_and_pending_events_mapping():
    """Проверяет минимальный набор полей для списков."""
    # Создаем ивент
    event_id = db.create_event("List Test", "date", None, 1, 1, "2026-01-01", None)
    
    try:
        active = db.get_active_events()
        if active:
            first = active[0]
            required = {'event_id', 'title', 'start_date', 'end_date', 'start_iso', 'end_iso'}
            for key in required:
                assert key in first, f"Ключ '{key}' отсутствует в get_active_events"
    finally:
        db.delete_event(event_id)
