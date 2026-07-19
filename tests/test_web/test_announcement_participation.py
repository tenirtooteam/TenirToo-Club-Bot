# Web-endpoint tests for the announcements toggle endpoint (feature 014).
# Endpoints are called directly (no network) per R-TEST-2; mocks assert args/kwargs (R-TEST-3).
import pytest
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException
from database import db
from web.routers.announcements import toggle_participation

OWNER_ID = 111
JOINER_ID = 222


def _event_with_two_announcements(is_approved: int = 1):
    """Approved event published as two announcement copies in two different topics."""
    db.add_user(OWNER_ID, "Owner", "One")
    db.add_user(JOINER_ID, "Joiner", "Two")
    event_id = db.create_event(
        title="Каракол", start_date="10 июня", end_date="",
        creator_id=OWNER_ID, is_approved=is_approved,
    )
    db.register_topic_if_not_exists(1)
    db.register_topic_if_not_exists(2)
    ann1 = db.create_announcement("event", event_id, 1, OWNER_ID, chat_id=-1001, message_id=501)
    ann2 = db.create_announcement("event", event_id, 2, OWNER_ID, chat_id=-1002, message_id=502)
    return event_id, ann1, ann2


# --- [Feature 014 / T008] Parity of the announcement endpoint (post-migration) ---

@pytest.mark.asyncio
async def test_announcement_join_refreshes_all_copies():
    """[Feature 014 fix] A JOIN via one announcement refreshes EVERY published copy of the
    event (the pre-014 endpoint hand-edited only the clicked one)."""
    event_id, ann1, ann2 = _event_with_two_announcements()
    fake_bot = AsyncMock()
    with patch("services.permission_service.PermissionService.can_user_write_in_topic", return_value=True), \
         patch("services.event_service.EventService.notify_organizers_of_direct_join", new_callable=AsyncMock), \
         patch("services.announcement_service.AnnouncementService.format_announcement_text", return_value="<b>x</b>"), \
         patch("loader.bot", fake_bot):
        await toggle_participation(ann1, action="join", user_id=JOINER_ID)

    assert db.is_event_participant(event_id, JOINER_ID) is True
    edited = [c.kwargs.get("message_id") for c in fake_bot.edit_message_text.call_args_list]
    assert 501 in edited and 502 in edited   # DRIFT CLOSED: both copies refreshed


@pytest.mark.asyncio
async def test_announcement_join_notifies_organizers():
    """A JOIN via an announcement notifies organizers once."""
    event_id, ann1, _ = _event_with_two_announcements()
    fake_bot = AsyncMock()
    with patch("services.permission_service.PermissionService.can_user_write_in_topic", return_value=True), \
         patch("services.event_service.EventService.notify_organizers_of_direct_join", new_callable=AsyncMock) as mock_notify, \
         patch("services.announcement_service.AnnouncementService.format_announcement_text", return_value="<b>x</b>"), \
         patch("loader.bot", fake_bot):
        await toggle_participation(ann1, action="join", user_id=JOINER_ID)
    assert mock_notify.await_count == 1


@pytest.mark.asyncio
async def test_announcement_missing_announcement_404():
    with pytest.raises(HTTPException) as exc:
        await toggle_participation(999999, action="join", user_id=JOINER_ID)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_announcement_no_topic_access_denied():
    """Guard: a member without write access to the announcement topic is refused."""
    event_id, ann1, _ = _event_with_two_announcements()
    with patch("services.permission_service.PermissionService.can_user_write_in_topic", return_value=False):
        with pytest.raises(HTTPException) as exc:
            await toggle_participation(ann1, action="join", user_id=JOINER_ID)
    assert exc.value.status_code == 403
    assert db.is_event_participant(event_id, JOINER_ID) is False


# --- [Feature 014 / T015] Explicit-intent hardening on the announcement endpoint ---

@pytest.mark.asyncio
async def test_announcement_leave_of_non_participant_no_silent_join():
    """No.7 on web: a 'leave' from a non-participant never joins them, notifies no one."""
    event_id, ann1, _ = _event_with_two_announcements()
    with patch("services.permission_service.PermissionService.can_user_write_in_topic", return_value=True), \
         patch("services.event_service.EventService.notify_organizers_of_direct_join", new_callable=AsyncMock) as mock_notify, \
         patch("services.announcement_service.AnnouncementService.refresh_announcements", new_callable=AsyncMock) as mock_refresh:
        result = await toggle_participation(ann1, action="leave", user_id=JOINER_ID)
    assert db.is_event_participant(event_id, JOINER_ID) is False  # NOT silently added
    assert mock_notify.await_count == 0
    assert mock_refresh.await_count == 0
    assert result["success"] is True


@pytest.mark.asyncio
async def test_announcement_invalid_or_missing_action_400():
    event_id, ann1, _ = _event_with_two_announcements()
    with pytest.raises(HTTPException) as exc:
        await toggle_participation(ann1, action="toggle", user_id=JOINER_ID)
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException) as exc:
        await toggle_participation(ann1, user_id=JOINER_ID)  # no action
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_announcement_denied_guard_fires_no_consequences():
    """C2/FR-006: on a denied topic guard, neither notify nor refresh runs."""
    event_id, ann1, _ = _event_with_two_announcements()
    with patch("services.permission_service.PermissionService.can_user_write_in_topic", return_value=False), \
         patch("services.event_service.EventService.notify_organizers_of_direct_join", new_callable=AsyncMock) as mock_notify, \
         patch("services.announcement_service.AnnouncementService.refresh_announcements", new_callable=AsyncMock) as mock_refresh:
        with pytest.raises(HTTPException) as exc:
            await toggle_participation(ann1, action="join", user_id=JOINER_ID)
    assert exc.value.status_code == 403
    assert mock_notify.await_count == 0
    assert mock_refresh.await_count == 0


@pytest.mark.asyncio
async def test_announcement_repeat_join_is_noop():
    """FR-007: a repeat JOIN via an announcement fires neither notify nor refresh."""
    event_id, ann1, _ = _event_with_two_announcements()
    db.add_event_participant(event_id, JOINER_ID)  # already in
    with patch("services.permission_service.PermissionService.can_user_write_in_topic", return_value=True), \
         patch("services.event_service.EventService.notify_organizers_of_direct_join", new_callable=AsyncMock) as mock_notify, \
         patch("services.announcement_service.AnnouncementService.refresh_announcements", new_callable=AsyncMock) as mock_refresh:
        result = await toggle_participation(ann1, action="join", user_id=JOINER_ID)
    assert result["success"] is True
    assert db.is_event_participant(event_id, JOINER_ID) is True
    assert mock_notify.await_count == 0
    assert mock_refresh.await_count == 0
