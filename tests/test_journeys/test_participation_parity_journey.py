# Cross-surface participation parity (feature 014).
#
# T004 (this file, Phase 2): characterize the CURRENT bot-handler consequence set — the
# reference every surface must match. Driven through the real handlers and the real keyboard
# producer (no hard-coded wire strings), so a later format change does not force edits.
# T012 (Phase 3) adds the web surfaces and asserts they match this reference.
import pytest
from unittest.mock import patch, AsyncMock
from database import db
from services.management_service import ManagementService
from keyboards.announcements_kb import get_announcement_kb
from handlers.announcements import announcement_join_handler
from handlers.events import leave_event

OWNER_ID = 1001
MEMBER_ID = 2002
TOPIC_ID = 1


def _ann_button_callbacks(ann_id: int):
    """Extract the real join/leave callback data from the announcement keyboard.

    Format-agnostic: the join button carries trailing action code '1', leave '0'."""
    kb = get_announcement_kb(ann_id, is_group=True)
    join_cb = leave_cb = None
    for row in kb.inline_keyboard:
        for btn in row:
            if not btn.callback_data:
                continue
            code = btn.callback_data.split(":")[-1]
            if code == "1":
                join_cb = btn.callback_data
            elif code == "0":
                leave_cb = btn.callback_data
    return join_cb, leave_cb


def _approved_event_with_announcement():
    db.add_user(OWNER_ID, "Creator", "User")
    db.add_user(MEMBER_ID, "Member", "User")
    db.register_topic_if_not_exists(TOPIC_ID)
    event_id = ManagementService.create_quick_event(OWNER_ID, "Public Hike")  # approved, creator auto-joined
    ann_id = db.create_announcement("event", event_id, TOPIC_ID, OWNER_ID)
    return event_id, ann_id


# --- [T004] Bot ann_join handler: JOIN (action code 1) ---

@pytest.mark.asyncio
async def test_bot_announcement_join_consequences(create_callback):
    event_id, ann_id = _approved_event_with_announcement()
    join_cb, _ = _ann_button_callbacks(ann_id)
    callback, state = await create_callback(user_id=MEMBER_ID, data=join_cb)

    with patch("services.permission_service.PermissionService.can_user_write_in_topic", return_value=True), \
         patch("services.event_service.EventService.notify_organizers_of_direct_join", new_callable=AsyncMock) as mock_notify, \
         patch("services.announcement_service.AnnouncementService.refresh_announcements", new_callable=AsyncMock) as mock_refresh, \
         patch("aiogram.types.CallbackQuery.answer", new_callable=AsyncMock):
        await announcement_join_handler(callback, state)

    assert db.is_event_participant(event_id, MEMBER_ID) is True
    assert mock_notify.await_count == 1        # notify on join
    assert mock_refresh.await_count == 1       # refresh all copies


# --- [T004] Bot ann_join handler: LEAVE (action code 0) ---

@pytest.mark.asyncio
async def test_bot_announcement_leave_consequences(create_callback):
    event_id, ann_id = _approved_event_with_announcement()
    db.add_event_participant(event_id, MEMBER_ID)  # already in
    _, leave_cb = _ann_button_callbacks(ann_id)
    callback, state = await create_callback(user_id=MEMBER_ID, data=leave_cb)

    with patch("services.permission_service.PermissionService.can_user_write_in_topic", return_value=True), \
         patch("services.event_service.EventService.notify_organizers_of_direct_join", new_callable=AsyncMock) as mock_notify, \
         patch("services.announcement_service.AnnouncementService.refresh_announcements", new_callable=AsyncMock) as mock_refresh, \
         patch("aiogram.types.CallbackQuery.answer", new_callable=AsyncMock):
        await announcement_join_handler(callback, state)

    assert db.is_event_participant(event_id, MEMBER_ID) is False
    assert mock_notify.await_count == 0        # no notify on leave
    assert mock_refresh.await_count == 1       # refresh all copies


# --- [T004] Bot event-card leave_event handler ---

@pytest.mark.asyncio
async def test_bot_event_card_leave_consequences(create_callback):
    event_id, _ = _approved_event_with_announcement()
    db.add_event_participant(event_id, MEMBER_ID)
    callback, state = await create_callback(user_id=MEMBER_ID, data=f"event_leave:{event_id}")

    with patch("services.event_service.EventService.notify_organizers_of_direct_join", new_callable=AsyncMock) as mock_notify, \
         patch("services.announcement_service.AnnouncementService.refresh_announcements", new_callable=AsyncMock) as mock_refresh, \
         patch("handlers.events.view_event", new_callable=AsyncMock), \
         patch("aiogram.types.CallbackQuery.answer", new_callable=AsyncMock):
        await leave_event(callback, state)

    assert db.is_event_participant(event_id, MEMBER_ID) is False
    assert mock_notify.await_count == 0        # no notify on leave
    assert mock_refresh.await_count == 1       # refresh all copies


# ---------------------------------------------------------------------------
# [T012] Cross-surface parity: identical, complete consequence set everywhere.
# ---------------------------------------------------------------------------
NOTIFY = "services.event_service.EventService.notify_organizers_of_direct_join"
REFRESH = "services.announcement_service.AnnouncementService.refresh_announcements"


async def _surface_dashboard(action, user_id, event_id, ann_id, create_callback):
    from web.routers.dashboard import toggle_event_participation_direct
    await toggle_event_participation_direct(event_id, action=action, user_id=user_id)


async def _surface_announcement_endpoint(action, user_id, event_id, ann_id, create_callback):
    from web.routers.announcements import toggle_participation
    await toggle_participation(ann_id, action=action, user_id=user_id)


async def _surface_bot_announcement(action, user_id, event_id, ann_id, create_callback):
    join_cb, leave_cb = _ann_button_callbacks(ann_id)
    callback, state = await create_callback(user_id=user_id, data=(join_cb if action == "join" else leave_cb))
    with patch("aiogram.types.CallbackQuery.answer", new_callable=AsyncMock):
        await announcement_join_handler(callback, state)


async def _surface_bot_event_card(action, user_id, event_id, ann_id, create_callback):
    assert action == "leave"  # the chat card joins via the request/audit flow, not a direct change
    callback, state = await create_callback(user_id=user_id, data=f"event_leave:{event_id}")
    with patch("handlers.events.view_event", new_callable=AsyncMock), \
         patch("aiogram.types.CallbackQuery.answer", new_callable=AsyncMock):
        await leave_event(callback, state)


async def _consequences(surface, action, user_id, event_id, ann_id, create_callback):
    """Drive one surface for one direction; return (notify_count, refresh_count)."""
    with patch("services.permission_service.PermissionService.can_user_write_in_topic", return_value=True), \
         patch("loader.bot", AsyncMock()), \
         patch(NOTIFY, new_callable=AsyncMock) as notify, \
         patch(REFRESH, new_callable=AsyncMock) as refresh:
        await surface(action, user_id, event_id, ann_id, create_callback)
    return notify.await_count, refresh.await_count


# Direct-join surfaces (A/B/C). The chat event card (D) joins via the request flow, not here.
JOIN_SURFACES = [_surface_dashboard, _surface_announcement_endpoint, _surface_bot_announcement]
LEAVE_SURFACES = JOIN_SURFACES + [_surface_bot_event_card]


@pytest.mark.asyncio
async def test_join_consequences_identical_across_surfaces(create_callback):
    """SC-001/SC-003: a JOIN on any direct surface adds the user, notifies once, refreshes once."""
    event_id, ann_id = _approved_event_with_announcement()
    results = {}
    for i, surface in enumerate(JOIN_SURFACES):
        joiner = 3001 + i
        db.add_user(joiner, "Joiner", str(i))
        counts = await _consequences(surface, "join", joiner, event_id, ann_id, create_callback)
        assert db.is_event_participant(event_id, joiner) is True, surface.__name__
        results[surface.__name__] = counts
    # Every surface produced the identical, complete consequence signature.
    assert set(results.values()) == {(1, 1)}, results


@pytest.mark.asyncio
async def test_leave_consequences_identical_across_surfaces(create_callback):
    """SC-001/SC-002/SC-003: a LEAVE on any surface removes the user, never notifies, refreshes once."""
    event_id, ann_id = _approved_event_with_announcement()
    results = {}
    for i, surface in enumerate(LEAVE_SURFACES):
        leaver = 4001 + i
        db.add_user(leaver, "Leaver", str(i))
        db.add_event_participant(event_id, leaver)  # start as a participant
        counts = await _consequences(surface, "leave", leaver, event_id, ann_id, create_callback)
        assert db.is_event_participant(event_id, leaver) is False, surface.__name__
        results[surface.__name__] = counts
    assert set(results.values()) == {(0, 1)}, results


@pytest.mark.asyncio
async def test_bot_legacy_format_button_refused(create_callback):
    """FR-011: an old-format announcement button (trailing segment is not an explicit intent
    code) is politely refused — no mutation, no guessing of direction, no side effects."""
    event_id, _ann1 = _approved_event_with_announcement()
    ann2 = db.create_announcement("event", event_id, TOPIC_ID, OWNER_ID)  # id >= 2
    legacy_data = f"ann_join:{ann2}"  # old format: last segment is the id, not "1"/"0"
    callback, state = await create_callback(user_id=MEMBER_ID, data=legacy_data)

    with patch("services.permission_service.PermissionService.can_user_write_in_topic", return_value=True), \
         patch("services.event_service.EventService.notify_organizers_of_direct_join", new_callable=AsyncMock) as mock_notify, \
         patch("services.announcement_service.AnnouncementService.refresh_announcements", new_callable=AsyncMock) as mock_refresh, \
         patch("aiogram.types.CallbackQuery.answer", new_callable=AsyncMock) as mock_answer:
        await announcement_join_handler(callback, state)

    assert db.is_event_participant(event_id, MEMBER_ID) is False  # no silent mutation
    assert mock_notify.await_count == 0
    assert mock_refresh.await_count == 0
    assert mock_answer.await_count == 1  # a polite refusal was shown
