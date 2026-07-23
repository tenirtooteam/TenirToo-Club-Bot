from database import db
from services.management_service import ManagementService


def _seed():
    """Черновик (event_approval) + участие в X + участие в Y + глобальный админ + организатор X."""
    for uid, fn in [(10, "Admin"), (20, "Organizer"), (30, "JoinerX"),
                    (40, "JoinerY"), (50, "Drafter"), (99, "OtherOrg")]:
        db.add_user(uid, fn, "T")
    db.grant_role(10, db.get_role_id("admin"))  # глобальный админ (topic_id IS NULL)

    draft = db.create_event("Draft", "1 июня", None, 50, 0, "2026-06-01", None)     # pending черновик, creator=50
    event_x = db.create_event("PohodX", "2 июня", None, 20, 1, "2026-06-02", None)  # approved, организатор=20
    event_y = db.create_event("PohodY", "3 июня", None, 99, 1, "2026-06-03", None)  # approved, организатор=99

    return {
        "draft": draft, "x": event_x, "y": event_y,
        "r_draft": db.create_audit_request(50, "event_approval", draft),
        "r_part_x": db.create_audit_request(30, "event_participation", event_x),
        "r_part_y": db.create_audit_request(40, "event_participation", event_y),
    }


def test_admin_sees_drafts_not_foreign_participation(db_setup):
    ids = _seed()
    queue = ManagementService.get_moderation_queue(10)  # глобальный админ, не организатор
    req_ids = {item["request_id"] for item in queue}

    assert ids["r_draft"] in req_ids, "Админ видит заявки-черновики"
    assert ids["r_part_x"] not in req_ids, "Админ НЕ видит участие в чужой поход"
    assert ids["r_part_y"] not in req_ids

    item = next(i for i in queue if i["request_id"] == ids["r_draft"])
    assert item["type"] == "event_approval"
    assert item["event_id"] == ids["draft"]
    assert item["event_title"] == "Draft"
    assert item["requester_id"] == 50
    assert "Drafter" in item["requester_name"]


def test_organizer_sees_own_participation_not_drafts_or_other_events(db_setup):
    ids = _seed()
    queue = ManagementService.get_moderation_queue(20)  # организатор X, НЕ админ
    req_ids = {item["request_id"] for item in queue}

    assert ids["r_part_x"] in req_ids, "Организатор видит участие в свой поход"
    assert ids["r_draft"] not in req_ids, "Не глобальный админ → черновики не видит"
    assert ids["r_part_y"] not in req_ids, "Не организатор Y → участие в Y не видит"

    item = next(i for i in queue if i["request_id"] == ids["r_part_x"])
    assert item["type"] == "event_participation"
    assert item["event_id"] == ids["x"]


def test_non_event_types_excluded_and_order_non_decreasing(db_setup):
    _seed()
    db.add_user(60, "Grouper", "T")
    db.create_audit_request(60, "group", 12345)  # не-событийный тип — вне scope 016

    queue = ManagementService.get_moderation_queue(10)
    assert "group" not in {i["type"] for i in queue}, "Не-событийные типы вне очереди 016"

    stamps = [i["created_at"] for i in queue]
    assert stamps == sorted(stamps), "Очередь отсортирована старейшие-первыми"
