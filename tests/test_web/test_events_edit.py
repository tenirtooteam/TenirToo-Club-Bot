# Файл: tests/test_web/test_events_edit.py
"""E2E редактирования события через TMA [Уровень A, feature 015 US2].

PUT /api/events/{id} — authority-parity: право правит создатель/организатор/глобал-админ
(EventService.can_edit_event), НЕ блочный require_admin. Создатель-не-админ обязан иметь
возможность править свой поход и в TMA — как он это делает в чате.
"""
import json

import pytest

from database import db

from .conftest import forge_init_data, seed_event, seed_user

CREATOR = 711
STRANGER = 712

JSON_HEADERS = {"Content-Type": "application/json"}


def _body(**payload) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode()


@pytest.mark.asyncio
async def test_edit_creator_non_admin_ok(web_call):
    seed_user(CREATOR, "Создатель")  # НЕ админ
    event_id = seed_event(CREATOR, "Старое название")

    resp = await web_call(
        "PUT", f"/api/events/{event_id}",
        init=forge_init_data(CREATOR),
        headers=JSON_HEADERS,
        body=_body(title="Новое название", date_text="20 июня"),
    )

    assert resp.status == 200, resp.json
    assert resp.json["success"] is True
    assert db.get_event_details(event_id)["title"] == "Новое название"


@pytest.mark.asyncio
async def test_edit_no_rights_403(web_call):
    seed_user(CREATOR, "Создатель")
    seed_user(STRANGER, "Посторонний")  # НЕ админ, не создатель
    event_id = seed_event(CREATOR, "Неприкосновенное")

    resp = await web_call(
        "PUT", f"/api/events/{event_id}",
        init=forge_init_data(STRANGER),
        headers=JSON_HEADERS,
        body=_body(title="Взлом", date_text="1 января"),
    )

    assert resp.status == 403
    # Состав/данные не изменились
    assert db.get_event_details(event_id)["title"] == "Неприкосновенное"


@pytest.mark.asyncio
async def test_edit_missing_event_404(web_call):
    seed_user(CREATOR)

    resp = await web_call(
        "PUT", "/api/events/999999",
        init=forge_init_data(CREATOR),
        headers=JSON_HEADERS,
        body=_body(title="Ничего", date_text="1 марта"),
    )

    assert resp.status == 404


@pytest.mark.asyncio
async def test_edit_empty_title_400(web_call):
    seed_user(CREATOR, "Создатель")
    event_id = seed_event(CREATOR, "Останется прежним")

    resp = await web_call(
        "PUT", f"/api/events/{event_id}",
        init=forge_init_data(CREATOR),
        headers=JSON_HEADERS,
        body=_body(title="  ", date_text="20 июня"),
    )

    assert resp.status == 400
    assert db.get_event_details(event_id)["title"] == "Останется прежним"
