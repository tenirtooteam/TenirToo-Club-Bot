# Файл: tests/test_web/test_e2e_auth.py
"""E2E auth-wiring через реальный эндпоинт [Уровень A, дыра №2].

Отличие от test_auth.py/test_auth_freshness.py (юнит на validate_webapp_init_data):
здесь запрос проходит ВЕСЬ стек — заголовок X-TG-Init-Data → get_current_user_id
(Depends) → маршрут → отображение HTTPException в HTTP-статус + JSON-тело. Сеть не
трогается (in-process ASGI), R-TEST-2 соблюдён; httpx не требуется.
"""
import time

import pytest

from .conftest import TEST_BOT_TOKEN, forge_init_data

INIT_PATH = "/api/dashboard/init"


@pytest.mark.asyncio
async def test_valid_init_data_authorizes(web_call):
    resp = await web_call("GET", INIT_PATH, init=forge_init_data(user_id=777))
    assert resp.status == 200
    assert resp.json["user_id"] == 777


@pytest.mark.asyncio
async def test_missing_header_401(web_call):
    resp = await web_call("GET", INIT_PATH)  # без X-TG-Init-Data
    assert resp.status == 401
    assert "Missing" in resp.json["detail"]


@pytest.mark.asyncio
async def test_tampered_hash_401(web_call):
    resp = await web_call("GET", INIT_PATH, init=forge_init_data(user_id=777, tamper=True))
    assert resp.status == 401
    assert resp.json["detail"] == "Invalid session"


@pytest.mark.asyncio
async def test_stale_auth_date_401(web_call):
    stale = int(time.time()) - 86400 - 100  # старше TTL (86400 c) [FR-006]
    resp = await web_call("GET", INIT_PATH, init=forge_init_data(user_id=777, auth_date=stale))
    assert resp.status == 401
    assert resp.json["detail"] == "Invalid session"


@pytest.mark.asyncio
async def test_future_auth_date_401(web_call):
    future = int(time.time()) + 400  # дальше допуска перекоса (300 c) [FR-005]
    resp = await web_call("GET", INIT_PATH, init=forge_init_data(user_id=777, auth_date=future))
    assert resp.status == 401
    assert resp.json["detail"] == "Invalid session"


@pytest.mark.asyncio
async def test_malformed_user_json_401(web_call):
    # Подпись валидна, но user не парсится как JSON → 401 на извлечении user_id.
    resp = await web_call("GET", INIT_PATH, init=forge_init_data(raw_user="{broken-json"))
    assert resp.status == 401
    assert resp.json["detail"] == "Invalid user data"


@pytest.mark.asyncio
async def test_signed_without_user_401(web_call):
    resp = await web_call("GET", INIT_PATH, init=forge_init_data(omit_user=True))
    assert resp.status == 401
    assert resp.json["detail"] == "Invalid user data"


@pytest.mark.asyncio
async def test_wrong_token_signature_rejected(web_call):
    bad = forge_init_data(user_id=777, token=TEST_BOT_TOKEN + "X")
    resp = await web_call("GET", INIT_PATH, init=bad)
    assert resp.status == 401
    assert resp.json["detail"] == "Invalid session"
