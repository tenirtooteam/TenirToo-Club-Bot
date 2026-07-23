"""E2E ростера и снятия участника через TMA [Уровень A, feature 016 US3].

GET /api/moderation/events/{id}/participants — просмотр состава (только организатор похода).
DELETE .../participants/{uid} — снятие через apply_participation_change(leave) (feature 014):
remove-only (не-участник = no-op без скрытой записи), с рефрешем публичного анонса.
"""
from unittest.mock import AsyncMock, patch

import pytest

from database import db

from .conftest import forge_init_data, seed_event, seed_user

ORGANIZER = 821
JOINER = 822
STRANGER = 823
GHOST = 824


def _seed():
    seed_user(ORGANIZER, "Орг")
    seed_user(JOINER, "Участник")
    seed_user(STRANGER, "Чужак")
    seed_user(GHOST, "Призрак")
    event_id = seed_event(ORGANIZER, "Поход")   # approved, организатор=ORGANIZER (участник+лид)
    db.add_event_participant(event_id, JOINER)  # реальный участник
    return event_id


@pytest.mark.asyncio
async def test_organizer_views_roster(web_call):
    event_id = _seed()
    resp = await web_call(
        "GET", f"/api/moderation/events/{event_id}/participants",
        init=forge_init_data(ORGANIZER),
    )
    assert resp.status == 200, resp.json
    by_id = {p["user_id"]: p for p in resp.json["participants"]}
    assert by_id[ORGANIZER]["is_organizer"] is True
    assert by_id[JOINER]["is_organizer"] is False
    assert "Участник" in by_id[JOINER]["display_name"]


@pytest.mark.asyncio
async def test_non_organizer_roster_403(web_call):
    event_id = _seed()
    resp = await web_call(
        "GET", f"/api/moderation/events/{event_id}/participants",
        init=forge_init_data(STRANGER),
    )
    assert resp.status == 403


@pytest.mark.asyncio
async def test_roster_missing_event_404(web_call):
    seed_user(ORGANIZER)
    resp = await web_call(
        "GET", "/api/moderation/events/999999/participants",
        init=forge_init_data(ORGANIZER),
    )
    assert resp.status == 404


@pytest.mark.asyncio
async def test_roster_requires_auth(web_call):
    resp = await web_call("GET", "/api/moderation/events/1/participants")
    assert resp.status == 401


@pytest.mark.asyncio
async def test_organizer_removes_participant_refreshes_announcement(web_call, fake_bot):
    event_id = _seed()
    with patch("services.announcement_service.AnnouncementService.refresh_announcements",
               new_callable=AsyncMock) as mock_refresh:
        resp = await web_call(
            "DELETE", f"/api/moderation/events/{event_id}/participants/{JOINER}",
            init=forge_init_data(ORGANIZER),
        )
    assert resp.status == 200, resp.json
    assert resp.json["success"] is True
    assert not db.is_event_participant(event_id, JOINER)
    mock_refresh.assert_awaited_once_with(fake_bot, "event", event_id)


@pytest.mark.asyncio
async def test_non_organizer_remove_403(web_call, fake_bot):
    event_id = _seed()
    resp = await web_call(
        "DELETE", f"/api/moderation/events/{event_id}/participants/{JOINER}",
        init=forge_init_data(STRANGER),
    )
    assert resp.status == 403
    assert db.is_event_participant(event_id, JOINER)  # не удалён


@pytest.mark.asyncio
async def test_remove_non_participant_is_noop(web_call, fake_bot):
    event_id = _seed()  # GHOST заведён, но НЕ участник
    with patch("services.announcement_service.AnnouncementService.refresh_announcements",
               new_callable=AsyncMock) as mock_refresh:
        resp = await web_call(
            "DELETE", f"/api/moderation/events/{event_id}/participants/{GHOST}",
            init=forge_init_data(ORGANIZER),
        )
    assert resp.status == 200, resp.json
    assert not db.is_event_participant(event_id, GHOST)  # без скрытой записи (BUG-4)
    mock_refresh.assert_not_awaited()  # состав не изменился → анонс не трогаем
