# Phase 1 Data Model: DB Connection Reuse & Registration Caching

No database schema changes. This feature introduces only in-memory process state. Entities below are runtime structures, not persisted tables.

## Entity: Shared Connection (module state in `database/connection.py`)

| Attribute | Type | Description |
|---|---|---|
| `_shared_conn` | `sqlite3.Connection \| None` | The single process-wide connection; `None` until first use or after reset. |
| bound path | derived from `DB_PATH` | The DB file the shared connection is attached to. Changing `DB_PATH` requires a reset. |

**Lifecycle / state transitions**:

- `None → open`: lazy creation on first `get_conn()` (or on `init_db()`), applying `journal_mode=WAL` and `foreign_keys=ON` once.
- `open → None`: on `init_db()` (test DB switch / reinit) or on process shutdown — connection closed then nulled.
- `open → None → open`: recovery path — if the shared connection is unusable, it is dropped and recreated on next access (FR-007).

**Invariants**:

- Applied-once PRAGMAs (WAL, FK) hold for the connection's whole lifetime (FR-002).
- Only accessed from the asyncio loop thread; no `await` occurs between acquiring and releasing it within a DB operation (safety basis, FR-001).
- `get_conn()` yields this connection and MUST NOT close it on context exit.

## Entity: Registration Memo (module state in `services/management_service.py`)

Two independent short-TTL caches.

| Attribute | Type | Description |
|---|---|---|
| user memo | `dict[int, float]` | `user_id → monotonic timestamp of last confirmed registration`. |
| topic memo | `dict[int, float]` | `topic_id → monotonic timestamp of last confirmed registration`. |
| `REGISTRATION_TTL_SECONDS` | `int` (const = 300) | Freshness window; entries older than this are treated as absent. |

**Read rule**: an id is "fresh" iff present AND `monotonic() - ts < REGISTRATION_TTL_SECONDS`.

**State transitions**:

- miss (absent or expired) → DB check/insert as today → record `id = monotonic()`.
- hit (fresh) → skip DB entirely.
- reset → both dicts cleared (via `reset_registration_cache()`), invoked on `init_db()`/per-test fixture.

**Invariants**:

- A stale registration fact lives at most `REGISTRATION_TTL_SECONDS` (FR-005): name updates and delete/rename are re-picked-up within the window.
- Cache is advisory: correctness never depends on it — a cold cache reproduces exact current behavior.

## Validation rules mapped to requirements

| Rule | Requirement |
|---|---|
| PRAGMAs applied once per connection lifetime | FR-002 |
| `with conn:` still commits/rolls back write transactions | FR-003 |
| Fresh memo skips DB; expired memo re-hits DB | FR-004, FR-005 |
| `DB_PATH` change resets shared connection | FR-006 |
| Unusable connection recreated, no permanent failure | FR-007 |
| Facade signatures & call-sites unchanged | FR-008 |
