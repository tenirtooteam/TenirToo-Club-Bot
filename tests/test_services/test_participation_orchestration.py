# Unit tests for EventService.apply_participation_change — the single participation
# orchestrator (feature 014). Mocks assert args/kwargs (R-TEST-3); DB is isolated per test.
import pytest
from unittest.mock import patch, AsyncMock
from database import db
from services.event_service import EventService

OWNER_ID = 111
JOINER_ID = 222

NOTIFY = "services.event_service.EventService.notify_organizers_of_direct_join"
REFRESH = "services.announcement_service.AnnouncementService.refresh_announcements"


def _event(is_approved: int = 1) -> int:
    db.add_user(OWNER_ID, "Owner", "One")
    db.add_user(JOINER_ID, "Joiner", "Two")
    return db.create_event(
        title="Каракол", start_date="10 июня", end_date="",
        creator_id=OWNER_ID, is_approved=is_approved,
    )


@pytest.mark.asyncio
async def test_join_changes_state_fires_both_consequences():
    event_id = _event()
    with patch(NOTIFY, new_callable=AsyncMock) as notify, patch(REFRESH, new_callable=AsyncMock) as refresh:
        success, _ = await EventService.apply_participation_change(AsyncMock(), event_id, JOINER_ID, "join")
    assert success is True
    assert db.is_event_participant(event_id, JOINER_ID) is True
    assert notify.await_count == 1
    assert refresh.await_count == 1


@pytest.mark.asyncio
async def test_join_noop_when_already_participant():
    event_id = _event()
    db.add_event_participant(event_id, JOINER_ID)
    with patch(NOTIFY, new_callable=AsyncMock) as notify, patch(REFRESH, new_callable=AsyncMock) as refresh:
        success, _ = await EventService.apply_participation_change(AsyncMock(), event_id, JOINER_ID, "join")
    assert success is True                         # already in the intended state
    assert db.is_event_participant(event_id, JOINER_ID) is True
    assert notify.await_count == 0                 # no consequence on no-op
    assert refresh.await_count == 0


@pytest.mark.asyncio
async def test_leave_changes_state_refreshes_without_notify():
    event_id = _event()
    db.add_event_participant(event_id, JOINER_ID)
    with patch(NOTIFY, new_callable=AsyncMock) as notify, patch(REFRESH, new_callable=AsyncMock) as refresh:
        success, _ = await EventService.apply_participation_change(AsyncMock(), event_id, JOINER_ID, "leave")
    assert success is True
    assert db.is_event_participant(event_id, JOINER_ID) is False
    assert notify.await_count == 0                 # never notify on leave
    assert refresh.await_count == 1


@pytest.mark.asyncio
async def test_leave_of_non_participant_is_not_a_join():
    """The No.7 invariant: 'leave' from a non-participant never adds them, fires nothing."""
    event_id = _event()
    with patch(NOTIFY, new_callable=AsyncMock) as notify, patch(REFRESH, new_callable=AsyncMock) as refresh:
        success, _ = await EventService.apply_participation_change(AsyncMock(), event_id, JOINER_ID, "leave")
    assert db.is_event_participant(event_id, JOINER_ID) is False   # NOT added
    assert success is True                         # end state matches leave intent
    assert notify.await_count == 0
    assert refresh.await_count == 0


@pytest.mark.asyncio
async def test_refresh_targets_all_copies_of_the_event():
    event_id = _event()
    with patch(NOTIFY, new_callable=AsyncMock), patch(REFRESH, new_callable=AsyncMock) as refresh:
        await EventService.apply_participation_change(AsyncMock(), event_id, JOINER_ID, "join")
    # Refresh is invoked at the event level, so it fans out to every announcement copy.
    args, kwargs = refresh.call_args
    assert args[1] == "event"
    assert args[2] == event_id


@pytest.mark.asyncio
async def test_outcome_is_structural_not_message_based():
    """Success/changed classification comes from participant state, never message text."""
    event_id = _event()
    with patch(NOTIFY, new_callable=AsyncMock), patch(REFRESH, new_callable=AsyncMock):
        s_join, _ = await EventService.apply_participation_change(AsyncMock(), event_id, JOINER_ID, "join")
        s_leave, _ = await EventService.apply_participation_change(AsyncMock(), event_id, JOINER_ID, "leave")
    assert s_join is True and s_leave is True
    assert db.is_event_participant(event_id, JOINER_ID) is False


@pytest.mark.asyncio
async def test_unknown_intent_refused_without_side_effects():
    event_id = _event()
    with patch(NOTIFY, new_callable=AsyncMock) as notify, patch(REFRESH, new_callable=AsyncMock) as refresh:
        success, message = await EventService.apply_participation_change(AsyncMock(), event_id, JOINER_ID, "toggle")
    assert success is False
    assert isinstance(message, str) and message
    assert db.is_event_participant(event_id, JOINER_ID) is False
    assert notify.await_count == 0
    assert refresh.await_count == 0


@pytest.mark.asyncio
async def test_side_effect_failure_does_not_roll_back_or_raise():
    """FR-008: a raising refresh keeps the mutation and success; no exception escapes."""
    event_id = _event()
    with patch(NOTIFY, new_callable=AsyncMock), \
         patch(REFRESH, new_callable=AsyncMock, side_effect=RuntimeError("telegram down")):
        success, _ = await EventService.apply_participation_change(AsyncMock(), event_id, JOINER_ID, "join")
    assert success is True
    assert db.is_event_participant(event_id, JOINER_ID) is True   # mutation persisted
