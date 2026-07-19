# Web-endpoint tests for the dashboard direct-join guard (US1, feature 006).
# Endpoints are called directly (no network) per R-TEST-2; httpx/TestClient is not installed.
import pytest
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException
from database import db
from web.routers.dashboard import toggle_event_participation_direct

OWNER_ID = 111
JOINER_ID = 222


def _make_event(is_approved: int) -> int:
    db.add_user(OWNER_ID, "Owner", "One")
    db.add_user(JOINER_ID, "Joiner", "Two")
    return db.create_event(
        title="Каракол",
        start_date="10 июня",
        end_date="",
        creator_id=OWNER_ID,
        is_approved=is_approved,
    )


@pytest.mark.asyncio
async def test_dashboard_join_pending_event_denied():
    """A member must not be able to join a pending event via the dashboard."""
    event_id = _make_event(is_approved=0)
    with pytest.raises(HTTPException) as exc:
        await toggle_event_participation_direct(event_id, action="join", user_id=JOINER_ID)
    assert exc.value.status_code == 403
    assert db.is_event_participant(event_id, JOINER_ID) is False


@pytest.mark.asyncio
async def test_dashboard_join_approved_event_allowed():
    """An approved event (no topic context) still lets a member join."""
    event_id = _make_event(is_approved=1)
    with patch("services.event_service.EventService.notify_organizers_of_direct_join", new_callable=AsyncMock), \
         patch("services.announcement_service.AnnouncementService.refresh_announcements", new_callable=AsyncMock):
        result = await toggle_event_participation_direct(event_id, action="join", user_id=JOINER_ID)
    assert result["success"] is True
    assert db.is_event_participant(event_id, JOINER_ID) is True


# --- [Feature 014 / T007] Parity of the dashboard consequence set (post-migration) ---

@pytest.mark.asyncio
async def test_dashboard_join_fires_notify_and_refresh():
    """A dashboard JOIN notifies organizers and refreshes announcements."""
    event_id = _make_event(is_approved=1)
    with patch("services.event_service.EventService.notify_organizers_of_direct_join", new_callable=AsyncMock) as mock_notify, \
         patch("services.announcement_service.AnnouncementService.refresh_announcements", new_callable=AsyncMock) as mock_refresh:
        await toggle_event_participation_direct(event_id, action="join", user_id=JOINER_ID)
    assert db.is_event_participant(event_id, JOINER_ID) is True
    assert mock_notify.await_count == 1
    assert mock_refresh.await_count == 1


@pytest.mark.asyncio
async def test_dashboard_leave_now_refreshes_all():
    """[Feature 014 fix] A dashboard LEAVE now refreshes announcements (the pre-014 gap),
    and still never notifies organizers."""
    event_id = _make_event(is_approved=1)
    db.add_event_participant(event_id, JOINER_ID)  # participant -> "leave" removes
    with patch("services.event_service.EventService.notify_organizers_of_direct_join", new_callable=AsyncMock) as mock_notify, \
         patch("services.announcement_service.AnnouncementService.refresh_announcements", new_callable=AsyncMock) as mock_refresh:
        await toggle_event_participation_direct(event_id, action="leave", user_id=JOINER_ID)
    assert db.is_event_participant(event_id, JOINER_ID) is False
    assert mock_notify.await_count == 0
    assert mock_refresh.await_count == 1  # DRIFT CLOSED: all copies refreshed on leave


# --- [Feature 014 / T015] Explicit-intent hardening: No.7, 400, guard-deny negative ---

@pytest.mark.asyncio
async def test_dashboard_leave_of_non_participant_no_silent_join():
    """No.7 on web: a 'leave' from a non-participant never joins them, notifies no one."""
    event_id = _make_event(is_approved=1)  # JOINER is NOT a participant
    with patch("services.event_service.EventService.notify_organizers_of_direct_join", new_callable=AsyncMock) as mock_notify, \
         patch("services.announcement_service.AnnouncementService.refresh_announcements", new_callable=AsyncMock) as mock_refresh:
        result = await toggle_event_participation_direct(event_id, action="leave", user_id=JOINER_ID)
    assert db.is_event_participant(event_id, JOINER_ID) is False  # NOT silently added
    assert mock_notify.await_count == 0
    assert mock_refresh.await_count == 0
    assert result["success"] is True  # end state matches the leave intent


@pytest.mark.asyncio
async def test_dashboard_invalid_action_400():
    event_id = _make_event(is_approved=1)
    for bad in ("toggle", "", "JOIN"):
        with pytest.raises(HTTPException) as exc:
            await toggle_event_participation_direct(event_id, action=bad, user_id=JOINER_ID)
        assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_dashboard_missing_action_400():
    event_id = _make_event(is_approved=1)
    with pytest.raises(HTTPException) as exc:
        await toggle_event_participation_direct(event_id, user_id=JOINER_ID)  # no action
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_dashboard_denied_guard_fires_no_consequences():
    """C2/FR-006: a denied guard (pending event) produces zero consequences."""
    event_id = _make_event(is_approved=0)  # pending -> guard denies
    with patch("services.event_service.EventService.notify_organizers_of_direct_join", new_callable=AsyncMock) as mock_notify, \
         patch("services.announcement_service.AnnouncementService.refresh_announcements", new_callable=AsyncMock) as mock_refresh:
        with pytest.raises(HTTPException) as exc:
            await toggle_event_participation_direct(event_id, action="join", user_id=JOINER_ID)
    assert exc.value.status_code == 403
    assert mock_notify.await_count == 0
    assert mock_refresh.await_count == 0
    assert db.is_event_participant(event_id, JOINER_ID) is False


# --- [Feature 014 / T016] Change-gating and delivery-failure isolation at the surface level ---

@pytest.mark.asyncio
async def test_dashboard_repeat_join_is_noop():
    """FR-007: a repeat JOIN (already a participant) fires neither notify nor refresh."""
    event_id = _make_event(is_approved=1)
    db.add_event_participant(event_id, JOINER_ID)  # already in
    with patch("services.event_service.EventService.notify_organizers_of_direct_join", new_callable=AsyncMock) as mock_notify, \
         patch("services.announcement_service.AnnouncementService.refresh_announcements", new_callable=AsyncMock) as mock_refresh:
        result = await toggle_event_participation_direct(event_id, action="join", user_id=JOINER_ID)
    assert result["success"] is True
    assert db.is_event_participant(event_id, JOINER_ID) is True
    assert mock_notify.await_count == 0
    assert mock_refresh.await_count == 0


@pytest.mark.asyncio
async def test_dashboard_join_survives_refresh_failure():
    """FR-008: a failing announcement refresh does not roll back the join nor 500 the endpoint."""
    event_id = _make_event(is_approved=1)
    with patch("services.event_service.EventService.notify_organizers_of_direct_join", new_callable=AsyncMock), \
         patch("services.announcement_service.AnnouncementService.refresh_announcements",
               new_callable=AsyncMock, side_effect=RuntimeError("telegram down")):
        result = await toggle_event_participation_direct(event_id, action="join", user_id=JOINER_ID)
    assert result["success"] is True                              # success preserved
    assert db.is_event_participant(event_id, JOINER_ID) is True   # mutation persisted
