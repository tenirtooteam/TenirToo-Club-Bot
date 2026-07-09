# Tests for the unified direct-join guard EventService.check_direct_join_allowed (US1, feature 006).
# R-PROC-3: these reproduce the FR-001/FR-002 gap before the guard exists.
from database import db
from services.event_service import EventService

TOPIC_ID = 555
OWNER_ID = 111       # a user who holds access (makes the topic "restricted")
JOINER_ID = 222      # the user attempting to join


def _make_event(is_approved: int) -> int:
    db.add_user(OWNER_ID, "Owner", "One")
    db.add_user(JOINER_ID, "Joiner", "Two")
    return db.create_event(
        title="Ала-Арча",
        start_date="15 мая",
        end_date="",
        creator_id=OWNER_ID,
        is_approved=is_approved,
    )


def _make_restricted_topic():
    db.register_topic_if_not_exists(TOPIC_ID)
    # Granting OWNER_ID direct access marks the topic as restricted (Default-Deny, R-DB-1)
    db.grant_direct_access(OWNER_ID, TOPIC_ID)


def test_pending_event_denied_no_topic():
    event_id = _make_event(is_approved=0)
    allowed, reason = EventService.check_direct_join_allowed(JOINER_ID, event_id, topic_id=None)
    assert allowed is False
    assert "модерац" in reason.lower()


def test_approved_event_no_topic_allowed():
    event_id = _make_event(is_approved=1)
    allowed, reason = EventService.check_direct_join_allowed(JOINER_ID, event_id, topic_id=None)
    assert allowed is True
    assert reason == ""


def test_approved_event_topic_without_access_denied():
    event_id = _make_event(is_approved=1)
    _make_restricted_topic()  # JOINER_ID has no access
    allowed, reason = EventService.check_direct_join_allowed(JOINER_ID, event_id, topic_id=TOPIC_ID)
    assert allowed is False
    assert reason != ""


def test_approved_event_topic_with_access_allowed():
    event_id = _make_event(is_approved=1)
    _make_restricted_topic()
    db.grant_direct_access(JOINER_ID, TOPIC_ID)
    allowed, reason = EventService.check_direct_join_allowed(JOINER_ID, event_id, topic_id=TOPIC_ID)
    assert allowed is True
    assert reason == ""


def test_missing_event_denied():
    allowed, reason = EventService.check_direct_join_allowed(JOINER_ID, 999999, topic_id=None)
    assert allowed is False
    assert reason != ""
