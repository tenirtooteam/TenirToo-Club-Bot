# Phase 0 Research: DB Connection Reuse & Registration Caching

## R1. Single shared sqlite3 connection under single-threaded asyncio

- **Decision**: Keep one module-level `sqlite3.Connection` in `database/connection.py`, created lazily, with `PRAGMA journal_mode=WAL` and `PRAGMA foreign_keys=ON` applied once at creation. `get_conn()` becomes a context manager that **yields the shared connection and does NOT close it** on exit.
- **Rationale**: Every `db.*` function is fully synchronous — grounded in reading `database/permissions.py`, `database/members.py` et al.: each opens `with get_conn() as conn:`, does work, returns, with **no `await` inside the `with` block**. Under a single-threaded asyncio loop, two DB operations can never interleave mid-statement, so a single shared connection needs no lock and no pool. This removes the connect + 2×PRAGMA cost (≈6×/message) while preserving exact behavior.
- **Transaction semantics**: Existing write paths use the nested `with conn:` idiom (e.g. `permissions.grant_direct_access`). `with conn:` commits/rolls back a transaction on the *connection* without closing it — fully compatible with a persistent connection. `get_conn()`'s own `finally` must **stop calling `conn.close()`**; the outer `with get_conn() as conn:` remains a no-op context that just hands over the shared connection. Call-sites are unchanged.
- **Alternatives considered**:
  - *Connection pool*: needed only if operations run in threads; out of scope (FR-009), rejected as unnecessary footprint.
  - *thread-local connection*: only relevant with `to_thread`; not now.
  - *`aiosqlite`*: rejected by PA-1 (Ф1, footprint 0 — ripples async through 77 call-sites + all service methods).

## R2. `check_same_thread` and safety boundary

- **Decision**: Create the shared connection with `check_same_thread=False` (as today), but rely on the single-loop-thread invariant for correctness rather than on cross-thread support.
- **Rationale**: `check_same_thread=False` is already set in the current code. Keeping it avoids surprises if any startup/shutdown code touches the connection from a different thread (e.g. `init_db` at boot). The real safety guarantee is the "no `await` inside a transaction" invariant (R1), documented as an Assumption in the spec. **[Guarded]**: if a future change offloads DB to threads (Ф2), this invariant breaks and a pool becomes mandatory — that transition is deliberately gated behind profiling (FR-009).

## R3. Broken/closed connection recovery (FR-007)

- **Decision**: On acquiring the shared connection, if it is `None` (never created or reset), create it. Detecting a corrupted live connection is best-effort: wrap creation so that a failed shared connection can be dropped (`_shared = None`) and recreated on next access. Keep it minimal — no health-check ping on the hot path.
- **Rationale**: SQLite connections rarely go bad in-process; adding a per-call `SELECT 1` liveness probe would reintroduce overhead we are removing. A lazy "create if None" plus reset-on-`init_db` covers the practical cases (test DB switch, shutdown) without hot-path cost.
- **Alternatives considered**: per-call liveness probe — rejected (defeats the optimization).

## R4. Test isolation with a persistent connection (FR-006)

- **Decision**: `init_db()` first closes and nulls any existing shared connection, then (re)creates it against the current `DB_PATH`. The autouse `db_setup` fixture in `tests/conftest.py` already sets `connection.DB_PATH = <tmp>` and calls `connection.init_db()` per test, so hooking the reset into `init_db()` makes each test transparently get a fresh connection to its own temp DB.
- **Rationale**: Zero change to individual tests; the reset rides the path the fixture already uses. Grounded in reading `tests/conftest.py:29-35`.
- **Alternatives considered**: exposing a separate `reset_connection()` the fixture must call explicitly — rejected as it would require touching the fixture more than necessary and risks new tests forgetting it. (Fixture still gains one line to reset the registration cache — see R5.)

## R5. Registration cache design (FR-004/005)

- **Decision**: Two module-level TTL caches in `services/management_service.py` — a set/dict of `user_id -> inserted_at` and `topic_id -> inserted_at`. `ensure_user_registered` / `register_topic_if_not_exists` check the cache first; on miss they hit the DB as today and record the timestamp; on a fresh hit they skip the DB. Entries expire after **TTL = 300 s** (5 min).
- **Rationale**: TTL bounds staleness (name-change reapplied within ≤5 min, FR-005) while covering bursty repeat traffic. 5 min is a conservative default balancing DB-hit savings against timeliness; it is a single named constant, tunable later. A monotonic clock (`time.monotonic()`) avoids wall-clock jumps.
- **Cache invalidation on delete/rename**: Rather than wiring cache-busting into every admin mutation (footprint creep), rely on TTL as the staleness upper bound (documented Assumption). Exception: the reset hook (R4) clears both caches on `init_db()` so tests never see cross-test bleed. A `reset_registration_cache()` helper is exposed and called from `db_setup`.
- **Alternatives considered**:
  - *Unbounded cache*: rejected — memory growth + never picks up name changes (relates to roadmap №18 `_alert_cache` growth concern).
  - *Explicit invalidation on every mutation*: rejected for footprint; TTL is sufficient within this feature's scope.
  - *LRU with size cap*: unnecessary at this user scale; TTL alone is simpler and time-bounded.

## Resolved unknowns

| Unknown | Resolution |
|---|---|
| Does reuse break `with conn:` transactions? | No — `with conn:` commits without closing (R1). |
| Concurrency safety without a lock? | Yes, under single-loop-thread + no-await-in-txn invariant (R1/R2). |
| Test isolation across DB switches? | Reset shared connection + caches inside `init_db()` (R4). |
| Cache TTL value? | 300 s, single tunable constant (R5). |
| Cache staleness on delete/rename? | Bounded by TTL; no per-mutation busting in scope (R5). |
