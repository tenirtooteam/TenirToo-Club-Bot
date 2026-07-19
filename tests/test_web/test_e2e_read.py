# Файл: tests/test_web/test_e2e_read.py
"""E2E чтения TMA через реальный стек [Уровень A, дыра №1].

GET-эндпоинты дашборда и анонсов ранее не были покрыты вовсе. Каждый запрос идёт
запрос → auth (forged initData) → router → service → SQLite → JSON. Сеть не трогается
(in-process ASGI, R-TEST-2), httpx не нужен.
"""
import pytest

from database import db

from .conftest import forge_init_data, seed_announcement, seed_event, seed_topic, seed_user

USER = 501
ADMIN = 502
OTHER = 503


# --------------------------------------------------------------------------- #
#  Dashboard: /init                                                           #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_init_regular_user(web_call):
    seed_user(USER, "Мария", "Петрова")
    resp = await web_call("GET", "/api/dashboard/init", init=forge_init_data(USER))
    assert resp.status == 200
    assert resp.json["user_id"] == USER
    assert resp.json["name"] == "Мария Петрова"
    assert resp.json["is_admin"] is False
    assert "events_active" in resp.json["stats"]
    assert "topics_available" in resp.json["stats"]


@pytest.mark.asyncio
async def test_init_admin_flag(web_call):
    seed_user(ADMIN, "Алексей", "Смирнов", admin=True)
    resp = await web_call("GET", "/api/dashboard/init", init=forge_init_data(ADMIN))
    assert resp.status == 200
    assert resp.json["is_admin"] is True


@pytest.mark.asyncio
async def test_init_unknown_user_still_authorizes(web_call):
    # Пользователь не в БД — эндпоинт всё равно авторизует и возвращает валидный профиль.
    resp = await web_call("GET", "/api/dashboard/init", init=forge_init_data(99999))
    assert resp.status == 200
    assert resp.json["user_id"] == 99999
    assert isinstance(resp.json["name"], str) and resp.json["name"]


# --------------------------------------------------------------------------- #
#  Dashboard: /topics, /profile                                               #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_topics_lists_direct_access(web_call):
    seed_user(USER)
    seed_topic(5, "Альпинизм", grant_to=USER)
    resp = await web_call("GET", "/api/dashboard/topics", init=forge_init_data(USER))
    assert resp.status == 200
    assert resp.json == [{"id": 5, "name": "Альпинизм"}]


@pytest.mark.asyncio
async def test_topics_empty_when_no_access(web_call):
    seed_user(USER)
    resp = await web_call("GET", "/api/dashboard/topics", init=forge_init_data(USER))
    assert resp.status == 200
    assert resp.json == []


@pytest.mark.asyncio
async def test_profile_returns_roles(web_call):
    seed_user(USER, "Мария", "Петрова")
    seed_topic(7, "Походы")
    db.grant_role(USER, db.get_role_id("moderator"), topic_id=7)
    resp = await web_call("GET", "/api/dashboard/profile", init=forge_init_data(USER))
    assert resp.status == 200
    assert resp.json["user_id"] == USER
    assert resp.json["name"] == "Мария Петрова"
    assert any(r["topic_id"] == 7 for r in resp.json["roles"])


# --------------------------------------------------------------------------- #
#  Dashboard: /events, /events/{id}                                           #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_events_list_marks_participation(web_call):
    seed_user(USER, "Создатель")
    seed_user(OTHER, "Сторонний")
    event_id = seed_event(USER, "Пик Учитель")  # creator → участник

    # Создатель видит себя участником
    r1 = await web_call("GET", "/api/dashboard/events", init=forge_init_data(USER))
    assert r1.status == 200
    mine = next(e for e in r1.json if e["id"] == event_id)
    assert mine["title"] == "Пик Учитель"
    assert mine["is_participant"] is True
    assert mine["participants_count"] == 1

    # Сторонний — не участник
    r2 = await web_call("GET", "/api/dashboard/events", init=forge_init_data(OTHER))
    mine2 = next(e for e in r2.json if e["id"] == event_id)
    assert mine2["is_participant"] is False


@pytest.mark.asyncio
async def test_event_view_ok_and_404(web_call):
    seed_user(USER)
    event_id = seed_event(USER, "Каракол")

    ok = await web_call("GET", f"/api/dashboard/events/{event_id}", init=forge_init_data(USER))
    assert ok.status == 200
    assert ok.json["title"] == "Каракол"
    assert ok.json["status"] == "approved"

    missing = await web_call("GET", "/api/dashboard/events/999999", init=forge_init_data(USER))
    assert missing.status == 404


# --------------------------------------------------------------------------- #
#  Dashboard: admin-gated + roles/faq                                         #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_admin_topics_gate(web_call):
    seed_user(ADMIN, admin=True)
    seed_user(USER)
    seed_topic(3, "Секретный")

    allowed = await web_call("GET", "/api/dashboard/admin/topics", init=forge_init_data(ADMIN))
    assert allowed.status == 200
    assert isinstance(allowed.json, list)

    denied = await web_call("GET", "/api/dashboard/admin/topics", init=forge_init_data(USER))
    assert denied.status == 403


@pytest.mark.asyncio
async def test_admin_groups_gate(web_call):
    seed_user(ADMIN, admin=True)
    seed_user(USER)

    allowed = await web_call("GET", "/api/dashboard/admin/groups", init=forge_init_data(ADMIN))
    assert allowed.status == 200
    assert isinstance(allowed.json, list)

    denied = await web_call("GET", "/api/dashboard/admin/groups", init=forge_init_data(USER))
    assert denied.status == 403


@pytest.mark.asyncio
async def test_roles_faq_returns_text(web_call):
    seed_user(USER)
    resp = await web_call("GET", "/api/dashboard/roles/faq", init=forge_init_data(USER))
    assert resp.status == 200
    assert isinstance(resp.json["text"], str) and resp.json["text"]


# --------------------------------------------------------------------------- #
#  Announcements: GET details (200 / 403 / 404 / 400)                         #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_announcement_details_ok(web_call):
    seed_user(USER, "Участник")
    topic_id = seed_topic(1, "Походы", grant_to=USER)
    event_id = seed_event(USER, "Публичный поход")
    ann_id = seed_announcement(event_id, topic_id, USER)

    resp = await web_call("GET", f"/api/announcements/{ann_id}", init=forge_init_data(USER))
    assert resp.status == 200
    assert resp.json["event_id"] == event_id
    assert resp.json["title"] == "Публичный поход"
    assert resp.json["is_participant"] is True  # creator


@pytest.mark.asyncio
async def test_announcement_details_no_topic_access_403(web_call):
    seed_user(USER)          # без доступа к топику
    owner = seed_user(601, "Владелец")
    topic_id = seed_topic(1, "Закрытый", grant_to=owner)  # доступ только у владельца
    event_id = seed_event(owner, "Закрытый поход")
    ann_id = seed_announcement(event_id, topic_id, owner)

    resp = await web_call("GET", f"/api/announcements/{ann_id}", init=forge_init_data(USER))
    assert resp.status == 403


@pytest.mark.asyncio
async def test_announcement_details_missing_404(web_call):
    seed_user(USER)
    resp = await web_call("GET", "/api/announcements/999999", init=forge_init_data(USER))
    assert resp.status == 404


@pytest.mark.asyncio
async def test_announcement_details_non_event_400(web_call):
    seed_user(USER)
    topic_id = seed_topic(1, "Походы", grant_to=USER)  # доступ есть → пройдём до проверки типа
    ann_id = db.create_announcement("poll", 42, topic_id, USER)

    resp = await web_call("GET", f"/api/announcements/{ann_id}", init=forge_init_data(USER))
    assert resp.status == 400
