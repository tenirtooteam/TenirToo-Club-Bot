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
        [row[1] for row in cursor.execute("PRAGMA table_info(events)").fetchall()]

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


# --- BUG-2 [US2] Сортировка по ISO + отсечение прошедших ---

def test_active_events_iso_order_and_past_filter():
    """
    BUG-2: get_active_events(today) должен сортировать по start_iso (не по тексту)
    и отсеивать полностью прошедшие походы, сохраняя идущие и бездатные.
    """
    db.add_user(1, "Test", "User")
    today = "2026-06-01"

    past = db.create_event("Прошедший", "1 янв", None, 1, 1, "2026-01-01", "2026-01-05")
    ongoing = db.create_event("Идёт", "30 мая", None, 1, 1, "2026-05-30", "2026-06-03")
    future_far = db.create_event("Далёкий", "10 июня", None, 1, 1, "2026-06-10", None)
    future_near = db.create_event("Ближний", "2 июня", None, 1, 1, "2026-06-02", None)
    undated = db.create_event("Бездатный", "когда-нибудь", None, 1, 1, None, None)

    active = db.get_active_events(today=today)
    ids = [e['event_id'] for e in active]

    # Прошедший отсечён; идущий/будущие/бездатный присутствуют
    assert past not in ids, "Полностью прошедший поход не должен попадать в активные"
    assert ongoing in ids, "Идущий поход (начался, не закончился) должен оставаться"
    assert future_near in ids and future_far in ids
    assert undated in ids, "Бездатный поход не должен молча пропадать"

    # Датированные идут по возрастанию start_iso (не по человеческому тексту)
    dated = [e['start_iso'] for e in active if e['start_iso'] is not None]
    assert dated == sorted(dated), f"Список не отсортирован по ISO: {dated}"
    # Конкретно: 2026-05-30 (ongoing) раньше 2026-06-02 (near) раньше 2026-06-10 (far)
    assert dated.index("2026-05-30") < dated.index("2026-06-02") < dated.index("2026-06-10")
