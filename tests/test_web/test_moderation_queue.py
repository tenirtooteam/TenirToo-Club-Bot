"""E2E очереди модерации через TMA [Уровень A, feature 016 US1].

GET /api/moderation/queue — скоупленная под зрителя очередь: глобальный админ видит
заявки-черновики (event_approval), организатор — заявки на участие своих походов
(event_participation). Authority-parity, D1/FR-007.
"""
import pytest

from database import db

from .conftest import forge_init_data, seed_event, seed_user

ADMIN = 801
ORGANIZER = 802
JOINER = 803
DRAFTER = 804
OTHER_ORG = 805


def _seed_queue():
    seed_user(ADMIN, "Админ", admin=True)
    seed_user(ORGANIZER, "Организатор")
    seed_user(JOINER, "Заявитель")
    seed_user(DRAFTER, "Черновик")
    seed_user(OTHER_ORG, "ЧужойОрг")

    event_x = seed_event(ORGANIZER, "Поход Организатора")           # approved, организатор=ORGANIZER
    draft = seed_event(DRAFTER, "Черновик похода", approved=False)  # pending черновик
    event_y = seed_event(OTHER_ORG, "Чужой поход")                  # approved, организатор=OTHER_ORG

    return {
        "draft": draft, "x": event_x, "y": event_y,
        "r_draft": db.create_audit_request(DRAFTER, "event_approval", draft),
        "r_part_x": db.create_audit_request(JOINER, "event_participation", event_x),
        "r_part_y": db.create_audit_request(JOINER, "event_participation", event_y),
    }


@pytest.mark.asyncio
async def test_admin_queue_sees_drafts_not_foreign_participation(web_call):
    ids = _seed_queue()
    resp = await web_call("GET", "/api/moderation/queue", init=forge_init_data(ADMIN))

    assert resp.status == 200, resp.json
    req_ids = {it["request_id"] for it in resp.json["items"]}
    assert ids["r_draft"] in req_ids
    assert ids["r_part_x"] not in req_ids
    assert ids["r_part_y"] not in req_ids


@pytest.mark.asyncio
async def test_organizer_queue_sees_own_participation_only(web_call):
    ids = _seed_queue()
    resp = await web_call("GET", "/api/moderation/queue", init=forge_init_data(ORGANIZER))

    assert resp.status == 200, resp.json
    req_ids = {it["request_id"] for it in resp.json["items"]}
    assert ids["r_part_x"] in req_ids       # участие в свой поход
    assert ids["r_draft"] not in req_ids    # не глобальный админ → без черновиков
    assert ids["r_part_y"] not in req_ids   # не организатор Y


@pytest.mark.asyncio
async def test_queue_item_carries_context(web_call):
    ids = _seed_queue()
    resp = await web_call("GET", "/api/moderation/queue", init=forge_init_data(ORGANIZER))

    item = next(it for it in resp.json["items"] if it["request_id"] == ids["r_part_x"])
    assert item["type"] == "event_participation"
    assert item["event_id"] == ids["x"]
    assert item["event_title"] == "Поход Организатора"
    assert item["requester_id"] == JOINER
    assert "Заявитель" in item["requester_name"]


@pytest.mark.asyncio
async def test_queue_requires_auth(web_call):
    resp = await web_call("GET", "/api/moderation/queue")
    assert resp.status == 401
