# -*- coding: utf-8 -*-
"""
[Feature 012] Persistent FSM storage — reproducing + contract tests.

Item №16: loader.py wired MemoryStorage, so a bot restart wiped all FSM state.
A restart is modelled here as: write via one SQLiteStorage instance, drop the
in-process shared connection (connection.close_shared_conn), then read via a
FRESH SQLiteStorage instance. Because close_shared_conn() forces the next access
to re-open the connection against the on-disk DB file, a passing read proves the
data survived on disk — not in instance memory (which is exactly what
MemoryStorage kept it in, and lost on restart).

RED-first (R-PROC-3): the restart-survival tests below MUST FAIL until
SQLiteStorage exists (T005/T006). The module-level import of SQLiteStorage is
itself the first RED signal.
"""
import pytest
from aiogram.fsm.storage.base import StorageKey

from database import connection
from database.fsm_storage import SQLiteStorage


def _key(bot_id=42, chat_id=100, user_id=7, thread_id=None, destiny="default"):
    return StorageKey(
        bot_id=bot_id, chat_id=chat_id, user_id=user_id,
        thread_id=thread_id, destiny=destiny,
    )


def _restart() -> SQLiteStorage:
    """Model a process restart: drop the shared in-process connection so the
    next DB access re-opens it against the on-disk file, then hand back a fresh
    storage instance (a new process would be exactly a new instance)."""
    connection.close_shared_conn()
    return SQLiteStorage()


# --- T002 [US1] menu-tracking keys survive a restart -------------------------

@pytest.mark.asyncio
async def test_menu_tracking_keys_survive_restart():
    key = _key()
    storage = SQLiteStorage()
    await storage.set_data(key, {"last_menu_ids": [100, 200], "last_menu_id": 200})

    restarted = _restart()
    data = await restarted.get_data(key)

    assert data["last_menu_ids"] == [100, 200]
    assert data["last_menu_id"] == 200


# --- T003 [US2] input state + typed context survive a restart ----------------

@pytest.mark.asyncio
async def test_input_state_and_context_survive_restart():
    key = _key()
    storage = SQLiteStorage()
    await storage.set_state(key, "waiting_for_topic_name")
    await storage.set_data(key, {"moderator_edit_topic_id": 55})

    restarted = _restart()

    assert await restarted.get_state(key) == "waiting_for_topic_name"
    data = await restarted.get_data(key)
    assert data["moderator_edit_topic_id"] == 55
    assert isinstance(data["moderator_edit_topic_id"], int)


# --- T004 [US3] admin_onboarded survives a restart ---------------------------

@pytest.mark.asyncio
async def test_admin_onboarded_survives_restart():
    key = _key()
    storage = SQLiteStorage()
    await storage.set_data(key, {"admin_onboarded": True})

    restarted = _restart()
    data = await restarted.get_data(key)

    assert data["admin_onboarded"] is True


# --- T008 [I-1] thread_id=None must not duplicate rows -----------------------

@pytest.mark.asyncio
async def test_thread_id_none_does_not_duplicate_rows():
    """SQLite treats NULLs in a composite PK as distinct; the None->0 sentinel is
    what keeps two writes under the same key to one row. This is the private-chat
    main path, so a regression here would silently break every DM."""
    key = _key(thread_id=None)
    storage = SQLiteStorage()
    await storage.set_data(key, {"a": 1})
    await storage.set_data(key, {"a": 2})

    with connection.get_conn() as conn:
        count = conn.execute("SELECT count(*) FROM fsm_storage").fetchone()[0]
    assert count == 1
    assert (await storage.get_data(key))["a"] == 2


# --- T009 [I-3] round-trip preserves types; updated_at is populated ----------

@pytest.mark.asyncio
async def test_round_trip_preserves_types_and_populates_timestamp():
    key = _key()
    storage = SQLiteStorage()
    payload = {
        "last_menu_ids": [100, 200],   # list[int]
        "admin_onboarded": True,        # bool
        "last_menu_id": None,           # None
        "search_query": "тест",         # str (Cyrillic)
        "edit_topic_id": 55,            # int
    }
    await storage.set_data(key, payload)
    got = await storage.get_data(key)

    assert got == payload
    assert all(isinstance(x, int) for x in got["last_menu_ids"])
    assert got["admin_onboarded"] is True
    assert got["last_menu_id"] is None
    assert isinstance(got["edit_topic_id"], int)

    # FR-012: the passive timestamp column is actually written (guards schema drift).
    with connection.get_conn() as conn:
        ts = conn.execute("SELECT updated_at FROM fsm_storage").fetchone()[0]
    assert ts is not None


# --- T010 [I-4] deletion boundary (R-FSM-1) ----------------------------------

@pytest.mark.asyncio
async def test_clearing_state_keeps_tracking_keys_but_empty_drops_row():
    """The R-FSM-1 boundary: set_state(None) alone MUST NOT wipe the row while
    tracking data remains, or the Sterile Interface loses last_menu_ids and leaves
    undeletable menu garbage. Only state-null AND data-empty together drop it."""
    key = _key()
    storage = SQLiteStorage()
    await storage.set_data(key, {"last_menu_ids": [1, 2, 3]})
    await storage.set_state(key, "waiting_for_topic_name")

    await storage.set_state(key, None)  # clear state only — the project's teardown

    with connection.get_conn() as conn:
        count = conn.execute("SELECT count(*) FROM fsm_storage").fetchone()[0]
    assert count == 1  # row survives
    assert (await storage.get_data(key))["last_menu_ids"] == [1, 2, 3]

    await storage.set_data(key, {})  # now data is empty too

    with connection.get_conn() as conn:
        count = conn.execute("SELECT count(*) FROM fsm_storage").fetchone()[0]
    assert count == 0  # row is now gone


# --- T011 [I-2] absent key degrades to None / {} -----------------------------

@pytest.mark.asyncio
async def test_absent_key_returns_none_state_and_empty_data():
    key = _key(user_id=999)
    storage = SQLiteStorage()
    assert await storage.get_state(key) is None
    assert await storage.get_data(key) == {}


# --- T013 [FR-009] corrupted data degrades to {} + log, no crash -------------

@pytest.mark.asyncio
async def test_corrupted_data_degrades_to_empty_and_logs(caplog):
    key = _key()
    storage = SQLiteStorage()
    await storage.set_data(key, {"last_menu_ids": [1, 2]})

    # Inject non-JSON garbage directly into the row's data column. The isolated
    # test DB holds exactly this one row, so no WHERE clause is needed.
    with connection.get_conn() as conn:
        with conn:
            conn.execute("UPDATE fsm_storage SET data = ?", ("{not valid json",))

    with caplog.at_level("WARNING"):
        got = await storage.get_data(key)

    assert got == {}                       # degrades, does not raise
    assert caplog.records                  # a warning was logged

    # Row is NOT auto-deleted on a corrupt read (FR-009).
    with connection.get_conn() as conn:
        count = conn.execute("SELECT count(*) FROM fsm_storage").fetchone()[0]
    assert count == 1


# --- T014 [I-6] owner isolation ----------------------------------------------

@pytest.mark.asyncio
async def test_owners_are_isolated():
    storage = SQLiteStorage()
    alice = _key(user_id=1)
    bob = _key(user_id=2)

    await storage.set_state(alice, "alice_state")
    await storage.set_data(alice, {"secret": "alice"})
    await storage.set_state(bob, "bob_state")
    await storage.set_data(bob, {"secret": "bob"})

    assert await storage.get_state(alice) == "alice_state"
    assert await storage.get_state(bob) == "bob_state"
    assert (await storage.get_data(alice))["secret"] == "alice"
    assert (await storage.get_data(bob))["secret"] == "bob"


# --- T015 [D-5] close() must not close the shared connection -----------------

@pytest.mark.asyncio
async def test_close_leaves_shared_connection_usable():
    key = _key()
    storage = SQLiteStorage()
    await storage.set_data(key, {"a": 1})

    await storage.close()

    # The shared connection must still be alive and usable for the rest of the
    # process (the FastAPI half lives here too) — a read still works.
    assert (await storage.get_data(key))["a"] == 1
    with connection.get_conn() as conn:
        assert conn.execute("SELECT 1").fetchone()[0] == 1
