# Файл: tests/test_web/test_events_create.py
"""E2E создания события через TMA [Уровень A, feature 015 US1].

POST /api/events — тонкий адаптер над ManagementService.create_event_action: любой
авторизованный пользователь (без admin-гейта, паритет с ботом), даты разбираются на
сервере через DateService, DTO-ответ со структурным success + date_recognized.
"""
import json

import pytest

from database import db
from services.event_service import EventService

from .conftest import forge_init_data, seed_user

CREATOR = 701

JSON_HEADERS = {"Content-Type": "application/json"}


def _body(**payload) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode()


@pytest.mark.asyncio
async def test_create_positive(web_call, fake_bot):
    seed_user(CREATOR, "Создатель")
    pending_before = len(EventService.get_pending_events())

    resp = await web_call(
        "POST", "/api/events",
        init=forge_init_data(CREATOR),
        headers=JSON_HEADERS,
        body=_body(title="Поход на Ала-Арчу", date_text="10-15 июня"),
    )

    assert resp.status == 200, resp.json
    assert resp.json["success"] is True
    event_id = resp.json["event_id"]
    assert event_id > 0
    assert resp.json["date_recognized"] is True

    # Создатель зарегистрирован участником И лидом (паритет с ботом, R-DATA-1)
    details = db.get_event_details(event_id)
    assert details is not None
    assert CREATOR in details["participants"]
    assert CREATOR in details["leads"]
    # На модерации и попал в очередь одобрения (submit_request)
    assert details["is_approved"] == 0
    assert len(EventService.get_pending_events()) == pending_before + 1


@pytest.mark.asyncio
async def test_create_empty_title_400(web_call, fake_bot):
    seed_user(CREATOR)
    pending_before = len(EventService.get_pending_events())

    resp = await web_call(
        "POST", "/api/events",
        init=forge_init_data(CREATOR),
        headers=JSON_HEADERS,
        body=_body(title="   ", date_text="10 июня"),
    )

    assert resp.status == 400
    # Событие не создано
    assert len(EventService.get_pending_events()) == pending_before


@pytest.mark.asyncio
async def test_create_unrecognized_date_still_saves(web_call, fake_bot):
    seed_user(CREATOR)

    resp = await web_call(
        "POST", "/api/events",
        init=forge_init_data(CREATOR),
        headers=JSON_HEADERS,
        body=_body(title="Поход-загадка", date_text="как-нибудь потом"),
    )

    # Нераспознанная дата не блокирует сохранение (паритет с ботом), но помечается
    assert resp.status == 200, resp.json
    assert resp.json["success"] is True
    assert resp.json["date_recognized"] is False
    assert resp.json["event_id"] > 0


@pytest.mark.asyncio
async def test_create_requires_auth(web_call):
    # Без initData — 401 (идентичность только из проверенных init-data, R-SEC-1)
    resp = await web_call(
        "POST", "/api/events",
        headers=JSON_HEADERS,
        body=_body(title="Аноним", date_text="10 июня"),
    )
    assert resp.status == 401
