# Journey tests: announcement direct-join must enforce the unified guard (US1, feature 006).
# Negative paths required by R-TEST-3; assertions check args+kwargs of callback.answer.
import pytest
from unittest.mock import patch, AsyncMock
from database import db
from handlers.announcements import announcement_join_handler

TOPIC_ID = 777
OWNER_ID = 111
JOINER_ID = 222


def _seed(is_approved: int, grant_joiner_access: bool) -> int:
    db.add_user(OWNER_ID, "Owner", "One")
    db.add_user(JOINER_ID, "Joiner", "Two")
    db.register_topic_if_not_exists(TOPIC_ID)
    db.grant_direct_access(OWNER_ID, TOPIC_ID)  # topic becomes restricted
    if grant_joiner_access:
        db.grant_direct_access(JOINER_ID, TOPIC_ID)
    event_id = db.create_event(
        title="Сон-Куль", start_date="Оперативно", end_date="",
        creator_id=OWNER_ID, is_approved=is_approved,
    )
    ann_id = db.create_announcement(a_type="event", target_id=event_id, topic_id=TOPIC_ID, creator_id=OWNER_ID)
    return event_id, ann_id


async def _run(create_callback, ann_id):
    callback, state = await create_callback(user_id=JOINER_ID, data=f"ann_join:{ann_id}:1")
    with patch("aiogram.types.CallbackQuery.answer", new_callable=AsyncMock) as mock_answer:
        await announcement_join_handler(callback, state)
    return mock_answer


@pytest.mark.asyncio
async def test_announcement_join_unapproved_event_denied(create_callback):
    """User HAS topic access but the event is pending -> approval gate denies, no participant added."""
    event_id, ann_id = _seed(is_approved=0, grant_joiner_access=True)
    mock_answer = await _run(create_callback, ann_id)
    mock_answer.assert_awaited()
    args, kwargs = mock_answer.call_args
    text = (args[0] if args else kwargs.get("text", ""))
    assert kwargs.get("show_alert") is True
    assert "модерац" in text.lower()
    assert db.is_event_participant(event_id, JOINER_ID) is False


@pytest.mark.asyncio
async def test_announcement_join_no_topic_access_denied(create_callback):
    """Approved event but user lacks topic access -> topic gate denies, no participant added."""
    event_id, ann_id = _seed(is_approved=1, grant_joiner_access=False)
    mock_answer = await _run(create_callback, ann_id)
    mock_answer.assert_awaited()
    _, kwargs = mock_answer.call_args
    assert kwargs.get("show_alert") is True
    assert db.is_event_participant(event_id, JOINER_ID) is False
