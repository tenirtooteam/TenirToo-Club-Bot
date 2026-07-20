# Файл: tests/test_web/test_frontend_contract.py
"""Серверные инварианты фронта [Уровень A, feature 015 US3].

Закрепляет контракты, которые переписывание фронта обязано сохранить/обеспечить:
- вход по ?ann_id= ведёт на карточку анонса (эндпоинт отдаёт её DTO) — FR-014;
- escape-by-default: заголовок с разметкой возвращается СЫРЫМИ символами (канон A1) — FR-013;
- can_edit-affordance в event-details DTO: true создателю, false постороннему — D7/U1.
"""
import json

import pytest

from .conftest import (
    forge_init_data,
    seed_announcement,
    seed_event,
    seed_topic,
    seed_user,
)

CREATOR = 721
STRANGER = 722

JSON_HEADERS = {"Content-Type": "application/json"}


def _body(**payload) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode()


@pytest.mark.asyncio
async def test_annid_entry_target(web_call):
    # Вход ?ann_id= ведёт на карточку анонса: эндпоинт возвращает её DTO (FR-014).
    seed_user(CREATOR, "Ведущий")
    topic_id = seed_topic(1, "Походы", grant_to=CREATOR)
    event_id = seed_event(CREATOR, "Поход выходного дня")
    ann_id = seed_announcement(event_id, topic_id, CREATOR)

    resp = await web_call("GET", f"/api/announcements/{ann_id}", init=forge_init_data(CREATOR))
    assert resp.status == 200
    assert resp.json["event_id"] == event_id


@pytest.mark.asyncio
async def test_markup_title_literal(web_call, fake_bot):
    # Канон A1: заголовок, введённый с разметкой, возвращается сырыми символами
    # (un-escaped, не &lt;b&gt;, не двойное экранирование). Рендер-слой затем эмитит текст-нодой.
    seed_user(CREATOR, "Автор")
    create = await web_call(
        "POST", "/api/events",
        init=forge_init_data(CREATOR),
        headers=JSON_HEADERS,
        body=_body(title="Поход <b>x</b>", date_text="10 июня"),
    )
    assert create.status == 200, create.json
    event_id = create.json["event_id"]

    view = await web_call("GET", f"/api/dashboard/events/{event_id}", init=forge_init_data(CREATOR))
    assert view.status == 200
    assert view.json["title"] == "Поход <b>x</b>"


@pytest.mark.asyncio
async def test_can_edit_flag(web_call):
    # D7/U1: event-details DTO несёт can_edit — true создателю, false постороннему.
    seed_user(CREATOR, "Создатель")
    seed_user(STRANGER, "Посторонний")
    event_id = seed_event(CREATOR, "Мой поход")

    mine = await web_call("GET", f"/api/dashboard/events/{event_id}", init=forge_init_data(CREATOR))
    assert mine.status == 200
    assert mine.json["can_edit"] is True

    theirs = await web_call("GET", f"/api/dashboard/events/{event_id}", init=forge_init_data(STRANGER))
    assert theirs.status == 200
    assert theirs.json["can_edit"] is False
