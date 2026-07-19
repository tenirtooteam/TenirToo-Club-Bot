# Файл: tests/test_web/conftest.py
"""E2E-инфраструктура веб-моста (TMA) без Telegram [Уровень A].

Тестирует реальный стек FastAPI (auth → router → service → SQLite) напрямую через
ASGI, без внешнего HTTP-клиента (httpx недоступен в offline-окружении). Драйвер
`web_call` строит ASGI-scope и await'ит приложение в петле теста — покрываются
маршрутизация, извлечение заголовков, Depends, отображение HTTPException в статус
и разбор query-параметров.

Крипта initData подделывается ЧЕСТНО: настоящий HMAC-SHA256 тестовым токеном
(forge_init_data), поэтому web.auth.validate_webapp_init_data проходит реальную
проверку — это покрывает и сам auth-слой (feature 006, FR-005/007), а не обходит его.
"""
import hashlib
import hmac
import json as _json
import time
import urllib.parse
from dataclasses import dataclass
from typing import Optional
from unittest.mock import AsyncMock, patch

import pytest

from database import db
from services.management_service import ManagementService

# Токен, которым подписываем forged initData. НЕ равен прод-токену: web.auth.BOT_TOKEN
# подменяется на него в фикстуре web_app (см. ниже), чтобы валидация сошлась.
TEST_BOT_TOKEN = "123456789:TEST-WEB-E2E-TOKEN-abcdefghijklmnopqrstuv"


# --------------------------------------------------------------------------- #
#  Forge initData (честный HMAC)                                              #
# --------------------------------------------------------------------------- #
def forge_init_data(
    user_id: int = 123,
    *,
    token: str = TEST_BOT_TOKEN,
    auth_date: Optional[int] = None,
    first_name: str = "TestUser",
    username: str = "tester",
    raw_user: Optional[str] = None,
    omit_user: bool = False,
    tamper: bool = False,
) -> str:
    """Собирает валидную (или намеренно битую) строку Telegram WebApp initData.

    auth_date=None → «сейчас». raw_user переопределяет JSON поля user (для теста кривого
    JSON). omit_user=True — подписанная строка вовсе без user. tamper=True — валидные поля,
    но испорченный hash (негативный тест подписи).
    """
    if auth_date is None:
        auth_date = int(time.time())

    fields: dict[str, str] = {"auth_date": str(auth_date), "query_id": "AAETestQueryId"}
    if not omit_user:
        if raw_user is not None:
            fields["user"] = raw_user
        else:
            fields["user"] = _json.dumps(
                {"id": user_id, "first_name": first_name, "username": username},
                separators=(",", ":"),
                ensure_ascii=False,
            )

    data_check_string = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    fields["hash"] = "0" * 64 if tamper else computed
    return urllib.parse.urlencode(fields)


def auth_headers(init_data: str) -> dict[str, str]:
    return {"X-TG-Init-Data": init_data}


# --------------------------------------------------------------------------- #
#  ASGI-драйвер                                                               #
# --------------------------------------------------------------------------- #
@dataclass
class WebResponse:
    status: int
    json: object
    body: bytes
    headers: dict[str, str]


async def _asgi_call(app, method, path, *, headers=None, query_string="", body=b"") -> WebResponse:
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query_string.encode(),
        "root_path": "",
        "headers": raw_headers,
        "server": ("testserver", 80),
        "client": ("testclient", 12345),
    }

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    captured: dict = {"status": None, "headers": [], "chunks": []}

    async def send(message):
        if message["type"] == "http.response.start":
            captured["status"] = message["status"]
            captured["headers"] = message.get("headers", [])
        elif message["type"] == "http.response.body":
            captured["chunks"].append(message.get("body", b""))

    await app(scope, receive, send)

    body_bytes = b"".join(captured["chunks"])
    try:
        parsed = _json.loads(body_bytes) if body_bytes else None
    except ValueError:
        parsed = None
    hdrs = {k.decode().lower(): v.decode() for k, v in captured["headers"]}
    return WebResponse(status=captured["status"], json=parsed, body=body_bytes, headers=hdrs)


# --------------------------------------------------------------------------- #
#  Фикстуры                                                                   #
# --------------------------------------------------------------------------- #
@pytest.fixture
def web_app(monkeypatch):
    """FastAPI-приложение веб-моста с подменённым на тестовый BOT_TOKEN.

    web.auth делает `from config import BOT_TOKEN` (биндится при импорте), поэтому
    патчим именно атрибут web.auth.BOT_TOKEN — тем же токеном, которым forge_init_data
    подписывает данные.
    """
    import web.auth as web_auth

    monkeypatch.setattr(web_auth, "BOT_TOKEN", TEST_BOT_TOKEN)
    from web.main import app

    return app


@pytest.fixture
def web_call(web_app):
    """Возвращает async-функцию вызова эндпоинта: web_call(method, path, init=..., action=...)."""

    async def _call(method, path, *, init: Optional[str] = None, headers=None, query_string="", body=b""):
        hdrs = dict(headers or {})
        if init is not None:
            hdrs.update(auth_headers(init))
        return await _asgi_call(web_app, method, path, headers=hdrs, query_string=query_string, body=body)

    return _call


@pytest.fixture
def fake_bot():
    """Подменяет loader.bot на AsyncMock — toggle-эндпоинты дёргают bot через `from loader import bot`.

    Реальная мутация участия проходит по-настоящему (сервис + SQLite); хвост последствий
    (уведомления, refresh анонсов) уходит в no-op мок. Импорт loader строит настоящий Bot
    один раз с прод-токеном валидного формата — сети не касается.
    """
    bot = AsyncMock()
    with patch("loader.bot", bot):
        yield bot


# --------------------------------------------------------------------------- #
#  Хелперы сидинга (поверх фасада db, изолированная БД из корневого db_setup)  #
# --------------------------------------------------------------------------- #
def seed_user(user_id: int, first="Иван", last="Иванов", *, admin=False) -> int:
    db.add_user(user_id, first, last)
    if admin:
        db.grant_role(user_id, db.get_role_id("admin"))
    return user_id


def seed_topic(topic_id: int, name="Походы", *, grant_to: Optional[int] = None) -> int:
    db.update_topic_name(topic_id, name)
    if grant_to is not None:
        db.grant_direct_access(grant_to, topic_id)
    return topic_id


def seed_event(creator_id: int, title="Поход на Пик", *, approved=True) -> int:
    """Одобренный квик-ивент (creator → участник+лид) или, при approved=False, событие на модерации."""
    if approved:
        return ManagementService.create_quick_event(creator_id, title)
    return db.create_event(
        title=title, start_date="Оперативно", end_date=None,
        creator_id=creator_id, is_approved=0, start_iso="2026-07-19", end_iso="2026-07-19",
    )


def seed_announcement(event_id: int, topic_id: int, creator_id: int) -> int:
    return db.create_announcement("event", event_id, topic_id, creator_id)
