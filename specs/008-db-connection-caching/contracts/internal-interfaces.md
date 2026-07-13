# Internal Interface Contracts

This feature exposes **no external/public API changes**. The `database.db` facade contract
is unchanged (FR-008). Documented here are the internal contracts that must hold.

## Unchanged (contract-frozen)

- **`database.db` facade**: every re-exported function keeps its exact signature and
  behavior. All 77 `get_conn()` call-sites across 9 `database/*.py` modules remain
  byte-identical. Handlers and services calling `db.*` require no edits.
- **`get_conn()` usage idiom**: `with get_conn() as conn:` and the nested `with conn:`
  write-transaction idiom continue to work identically from the caller's viewpoint.

## Modified internal contracts

### `database/connection.py`

- `get_conn()` — still a `@contextmanager` yielding a `sqlite3.Connection`. **Behavior
  change**: yields the shared process-wide connection and does **not** close it on exit.
  Callers observe no API difference.
- `init_db()` — additionally resets (closes + nulls) any existing shared connection before
  (re)initializing, so a subsequent `get_conn()` binds to the current `DB_PATH`.
- *(new, internal)* a shutdown-time close of the shared connection SHOULD be wired where the
  bot stops (best-effort; not required for correctness).

### `services/management_service.py`

- `ensure_user_registered(user)` — unchanged signature; internally checks the user memo
  before `db.user_exists`, records on registration. Cold-cache behavior identical to today.
- `register_topic_if_not_exists(topic_id)` — unchanged signature; internally checks the
  topic memo before delegating to `db.register_topic_if_not_exists`.
- *(new, internal)* `reset_registration_cache()` — clears both memos; called from
  `init_db()` path and the `db_setup` test fixture.

## Contract tests (map to acceptance scenarios)

| Test | Asserts | Spec ref |
|---|---|---|
| connect-count per message ≤ 1 | US1 AS-1, SC-001 | FR-001 |
| write rollback on IntegrityError leaves connection usable | US1 AS-3, SC-005 | FR-003 |
| second identical message → 0 registration DB hits | US2 AS-1/2, SC-002 | FR-004 |
| expired memo → registration re-hits DB | US2 AS-3 | FR-005 |
| `DB_PATH` switch → queries hit new DB, no bleed | Edge: test isolation | FR-006 |
| facade signatures unchanged (AST/import gates green) | SC-004 | FR-008 |
