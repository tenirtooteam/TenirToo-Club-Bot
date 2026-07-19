# Файл: tests/test_web/test_e2e_toggle.py
"""E2E-cap на toggle сквозь ВЕСЬ стек [Уровень A].

Бизнес-логику toggle (гарды, 400/403/404, последствия, No.7, идемпотентность) плотно
покрывают test_dashboard_participation.py / test_announcement_participation.py прямыми
вызовами (feature 014). Здесь — только сквозной happy-path: forged initData → auth →
маршрут → гард → мутация → JSON, чтобы связка «запись без Telegram» была замкнута.
loader.bot подменён на AsyncMock (fake_bot), хвост последствий — no-op.
"""
import pytest

from database import db

from .conftest import forge_init_data, seed_announcement, seed_event, seed_topic, seed_user

USER = 701


@pytest.mark.asyncio
async def test_dashboard_toggle_join_then_leave_e2e(web_call, fake_bot):
    owner = seed_user(801, "Владелец")
    seed_user(USER, "Гость")
    event_id = seed_event(owner, "Пик Комсомолец")  # одобрен, USER не участник

    join = await web_call(
        "POST", f"/api/dashboard/events/{event_id}/toggle",
        init=forge_init_data(USER), query_string="action=join",
    )
    assert join.status == 200
    assert join.json["success"] is True
    assert db.is_event_participant(event_id, USER) is True

    leave = await web_call(
        "POST", f"/api/dashboard/events/{event_id}/toggle",
        init=forge_init_data(USER), query_string="action=leave",
    )
    assert leave.status == 200
    assert leave.json["success"] is True
    assert db.is_event_participant(event_id, USER) is False


@pytest.mark.asyncio
async def test_announcement_toggle_join_e2e(web_call, fake_bot):
    owner = seed_user(802, "Владелец")
    seed_user(USER, "Гость")
    topic_id = seed_topic(1, "Походы", grant_to=USER)  # доступ к топику анонса
    event_id = seed_event(owner, "Публичный поход")
    ann_id = seed_announcement(event_id, topic_id, owner)

    resp = await web_call(
        "POST", f"/api/announcements/{ann_id}/toggle",
        init=forge_init_data(USER), query_string="action=join",
    )
    assert resp.status == 200
    assert resp.json["success"] is True
    assert db.is_event_participant(event_id, USER) is True
