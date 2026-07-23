"""E2E резолва заявок модерации через TMA [Уровень A, feature 016 US1/US2].

POST /api/moderation/requests/{id}/resolve — authority-parity по типу (D1/FR-007):
черновики (event_approval) резолвит только глобальный админ, участие (event_participation)
— только организаторы похода. Атомарный CAS (feature 007) даёт exactly-once. Reject-семантика
(FR-003): reject черновика удаляет его, reject участия не трогает состав.
"""
import json

import pytest

from database import db

from .conftest import forge_init_data, seed_event, seed_user

ADMIN = 811
ORGANIZER = 812
JOINER = 813
STRANGER = 814
DRAFTER = 815

JSON_HEADERS = {"Content-Type": "application/json"}


def _body(**payload):
    return json.dumps(payload, ensure_ascii=False).encode()


def _seed_participation():
    seed_user(ADMIN, "Админ", admin=True)
    seed_user(ORGANIZER, "Орг")
    seed_user(JOINER, "Заявитель")
    seed_user(STRANGER, "Чужак")
    event_id = seed_event(ORGANIZER, "Поход")  # approved, организатор=ORGANIZER
    req_id = db.create_audit_request(JOINER, "event_participation", event_id)
    return event_id, req_id


def _seed_draft():
    seed_user(ADMIN, "Админ", admin=True)
    seed_user(ORGANIZER, "Орг")
    seed_user(DRAFTER, "Черновик")
    draft = seed_event(DRAFTER, "Черновик", approved=False)
    req_id = db.create_audit_request(DRAFTER, "event_approval", draft)
    return draft, req_id


async def _resolve(web_call, req_id, user_id, **payload):
    return await web_call(
        "POST", f"/api/moderation/requests/{req_id}/resolve",
        init=forge_init_data(user_id), headers=JSON_HEADERS, body=_body(**payload),
    )


@pytest.mark.asyncio
async def test_organizer_approves_participation(web_call, fake_bot):
    event_id, req_id = _seed_participation()
    resp = await _resolve(web_call, req_id, ORGANIZER, status="approved")

    assert resp.status == 200, resp.json
    assert resp.json["success"] is True
    assert db.is_event_participant(event_id, JOINER)


@pytest.mark.asyncio
async def test_admin_cannot_resolve_foreign_participation_403(web_call, fake_bot):
    # D1: глобальный админ НЕ универсальный резолвер участия (только организаторы)
    event_id, req_id = _seed_participation()
    resp = await _resolve(web_call, req_id, ADMIN, status="approved")

    assert resp.status == 403
    assert not db.is_event_participant(event_id, JOINER)


@pytest.mark.asyncio
async def test_stranger_cannot_resolve_participation_403(web_call, fake_bot):
    event_id, req_id = _seed_participation()
    resp = await _resolve(web_call, req_id, STRANGER, status="approved")

    assert resp.status == 403
    assert not db.is_event_participant(event_id, JOINER)


@pytest.mark.asyncio
async def test_admin_approves_draft(web_call, fake_bot):
    draft, req_id = _seed_draft()
    resp = await _resolve(web_call, req_id, ADMIN, status="approved")

    assert resp.status == 200, resp.json
    assert resp.json["success"] is True
    assert db.get_event_details(draft)["is_approved"] == 1


@pytest.mark.asyncio
async def test_organizer_cannot_resolve_draft_403(web_call, fake_bot):
    draft, req_id = _seed_draft()
    resp = await _resolve(web_call, req_id, ORGANIZER, status="approved")

    assert resp.status == 403
    assert db.get_event_details(draft)["is_approved"] == 0


@pytest.mark.asyncio
async def test_exactly_once_second_resolve_is_noop(web_call, fake_bot):
    event_id, req_id = _seed_participation()
    first = await _resolve(web_call, req_id, ORGANIZER, status="approved")
    second = await _resolve(web_call, req_id, ORGANIZER, status="approved")

    assert first.json["success"] is True
    assert second.json["success"] is False   # идемпотентно: заявка уже обработана
    assert db.is_event_participant(event_id, JOINER)


@pytest.mark.asyncio
async def test_reject_draft_deletes_it(web_call, fake_bot):
    draft, req_id = _seed_draft()
    resp = await _resolve(web_call, req_id, ADMIN, status="rejected", comment="нет")

    assert resp.status == 200, resp.json
    assert resp.json["success"] is True
    assert db.get_event_details(draft) is None   # черновик удалён (FR-003)


@pytest.mark.asyncio
async def test_reject_participation_leaves_roster(web_call, fake_bot):
    event_id, req_id = _seed_participation()
    resp = await _resolve(web_call, req_id, ORGANIZER, status="rejected")

    assert resp.status == 200, resp.json
    assert resp.json["success"] is True
    assert not db.is_event_participant(event_id, JOINER)   # состав не изменился (FR-003)


@pytest.mark.asyncio
async def test_bad_status_400(web_call, fake_bot):
    _, req_id = _seed_participation()
    resp = await _resolve(web_call, req_id, ORGANIZER, status="maybe")

    assert resp.status == 400


@pytest.mark.asyncio
async def test_resolve_requires_auth(web_call):
    resp = await web_call(
        "POST", "/api/moderation/requests/1/resolve",
        headers=JSON_HEADERS, body=_body(status="approved"),
    )
    assert resp.status == 401
