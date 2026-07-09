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
async def test_dashboard_toggle_pending_event_denied():
    """A member must not be able to join a pending event via the dashboard."""
    event_id = _make_event(is_approved=0)
    with pytest.raises(HTTPException) as exc:
        await toggle_event_participation_direct(event_id, user_id=JOINER_ID)
    assert exc.value.status_code == 403
    assert db.is_event_participant(event_id, JOINER_ID) is False


@pytest.mark.asyncio
async def test_dashboard_toggle_approved_event_allowed():
    """An approved event (no topic context) still lets a member join."""
    event_id = _make_event(is_approved=1)
    with patch("services.event_service.EventService.notify_organizers_of_direct_join", new_callable=AsyncMock), \
         patch("services.announcement_service.AnnouncementService.refresh_announcements", new_callable=AsyncMock):
        result = await toggle_event_participation_direct(event_id, user_id=JOINER_ID)
    assert result["success"] is True
    assert db.is_event_participant(event_id, JOINER_ID) is True
