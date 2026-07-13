# -*- coding: utf-8 -*-
"""
[Feature 008 / US2] Reproducing test for redundant registration lookups.

Baseline (before fix): every message re-checks the DB for user/topic
registration. Target (after fix): a short-TTL in-memory memo makes a repeat
message within the window skip the DB entirely (SC-002, FR-004), while an
expired memo re-hits the DB so changes are re-applied within the TTL (FR-005).

This test MUST fail before the cache is added and pass after it.
"""
import pytest
from unittest.mock import MagicMock

import services.management_service as mgmt
from services.management_service import ManagementService
from database import db


class _CallCounter:
    def __init__(self, real):
        self._real = real
        self.count = 0

    def __call__(self, *args, **kwargs):
        self.count += 1
        return self._real(*args, **kwargs)


def _make_user(user_id):
    user = MagicMock()
    user.id = user_id
    user.first_name = "Repeat"
    user.last_name = "Sender"
    return user


@pytest.fixture(autouse=True)
def _clear_cache():
    """Guarantee cold memos around each test in this module."""
    mgmt.reset_registration_cache()
    yield
    mgmt.reset_registration_cache()


@pytest.mark.asyncio
async def test_repeat_user_registration_skips_db(db_setup, monkeypatch):
    user_id = 4242
    db.add_user(user_id, "Repeat", "Sender")  # already registered

    spy = _CallCounter(db.user_exists)
    monkeypatch.setattr(mgmt.db, "user_exists", spy)

    user = _make_user(user_id)
    await ManagementService.ensure_user_registered(user)
    await ManagementService.ensure_user_registered(user)

    assert spy.count <= 1, (
        f"Second identical message must not re-hit the DB for user registration; "
        f"db.user_exists called {spy.count} times (pre-fix baseline: 2)"
    )


def test_repeat_topic_registration_skips_db(db_setup, monkeypatch):
    topic_id = 7777

    spy = _CallCounter(db.register_topic_if_not_exists)
    monkeypatch.setattr(mgmt.db, "register_topic_if_not_exists", spy)

    ManagementService.register_topic_if_not_exists(topic_id)
    ManagementService.register_topic_if_not_exists(topic_id)

    assert spy.count <= 1, (
        f"Second identical message must not re-hit the DB for topic registration; "
        f"db.register_topic_if_not_exists called {spy.count} times (pre-fix baseline: 2)"
    )


@pytest.mark.asyncio
async def test_expired_memo_rehits_db(db_setup, monkeypatch):
    user_id = 5151
    db.add_user(user_id, "Repeat", "Sender")

    spy = _CallCounter(db.user_exists)
    monkeypatch.setattr(mgmt.db, "user_exists", spy)

    # Controlled monotonic clock.
    clock = {"t": 1000.0}
    monkeypatch.setattr(mgmt.time, "monotonic", lambda: clock["t"])

    user = _make_user(user_id)
    await ManagementService.ensure_user_registered(user)  # miss → 1 DB hit, memo recorded
    assert spy.count == 1

    # Advance clock beyond the TTL → memo is stale → must re-hit.
    clock["t"] += mgmt.REGISTRATION_TTL_SECONDS + 1
    await ManagementService.ensure_user_registered(user)
    assert spy.count == 2, "expired memo must re-hit the DB (FR-005)"


@pytest.mark.asyncio
async def test_reset_clears_memo(db_setup, monkeypatch):
    user_id = 6262
    db.add_user(user_id, "Repeat", "Sender")

    spy = _CallCounter(db.user_exists)
    monkeypatch.setattr(mgmt.db, "user_exists", spy)

    user = _make_user(user_id)
    await ManagementService.ensure_user_registered(user)  # 1 DB hit
    mgmt.reset_registration_cache()
    await ManagementService.ensure_user_registered(user)  # cache cleared → re-hit

    assert spy.count == 2, "reset_registration_cache() must clear the memo"
