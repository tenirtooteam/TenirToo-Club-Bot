# -*- coding: utf-8 -*-
"""
[Feature 008 / US1] Reproducing test for DB connection churn.

Baseline (before fix): one authorized group message drives ≈6 full
`sqlite3.connect` + PRAGMA cycles through the middleware access-check chain
(UserManager → ForumUtility → AccessGuard). Target (after fix): the shared
connection is already warm, so processing a message opens ZERO new physical
connections — asserted here as ≤ 1 (SC-001, FR-001).

This test MUST fail before the persistent-connection change and pass after it.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from database import connection, db
from middlewares.access_check import (
    UserManagerMiddleware,
    ForumUtilityMiddleware,
    AccessGuardMiddleware,
)


class _ConnectCounter:
    """Wraps sqlite3.connect, counting real invocations while delegating."""

    def __init__(self, real_connect):
        self._real = real_connect
        self.count = 0

    def __call__(self, *args, **kwargs):
        self.count += 1
        return self._real(*args, **kwargs)


@pytest.mark.asyncio
async def test_message_opens_at_most_one_connection(db_setup, mock_bot, monkeypatch):
    topic_id = 55
    user_id = 8888  # != ADMIN_ID (999999999) → exercises full DB access-check path

    # Authorized sender: user exists, topic is restricted, user has direct access.
    db.add_user(user_id, "Authorized", "User")
    db.update_topic_name(topic_id, "Secret Topic")
    db.grant_direct_access(user_id, topic_id)  # makes topic restricted AND grants access

    # Build one supergroup message from the authorized user (MagicMock, matching the
    # existing middleware journey tests — a real aiogram Message trips on unset
    # optional forum_topic_* fields in this version).
    mock_bot.id = 123456789  # bot id, != user_id

    message = MagicMock()
    message.chat = MagicMock()
    message.chat.type = "supergroup"
    message.from_user = MagicMock()
    message.from_user.id = user_id
    message.from_user.is_bot = False
    message.from_user.first_name = "Authorized"
    message.from_user.last_name = "User"
    message.message_thread_id = topic_id
    message.bot = mock_bot
    message.forum_topic_edited = None
    message.forum_topic_deleted = None
    message.forum_topic_created = None
    message.delete = AsyncMock()

    async def terminal_handler(event, data):
        return "delivered"

    # Warm-up: ensure any lazy shared connection is established BEFORE counting,
    # so we measure steady-state churn, not first-touch initialization.
    db.user_exists(user_id)

    counter = _ConnectCounter(connection.sqlite3.connect)
    monkeypatch.setattr(connection.sqlite3, "connect", counter)

    # Drive the full middleware chain for a single message.
    async def guard_stage(event, data):
        return await AccessGuardMiddleware()(terminal_handler, event, data)

    async def forum_stage(event, data):
        return await ForumUtilityMiddleware()(guard_stage, event, data)

    result = await UserManagerMiddleware()(forum_stage, message, {})

    assert result == "delivered", "authorized message must reach the handler"
    assert counter.count <= 1, (
        f"Expected ≤1 new sqlite3.connect per message once warm, got {counter.count} "
        f"(pre-fix baseline ≈6 — connection churn not yet eliminated)"
    )
