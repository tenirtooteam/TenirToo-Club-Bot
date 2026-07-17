# Implementation Plan: Persistent FSM Storage

**Branch**: `012-persistent-fsm-storage` | **Date**: 2026-07-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/012-persistent-fsm-storage/spec.md`

**Note**: Supporting artifacts ([research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/storage-contract.md), [quickstart.md](quickstart.md)) are written in Russian per the project's response protocol; this plan is English per AGENTS.md § PLAN CONTENT.

## Summary

Replace `MemoryStorage` in `loader.py` with `SQLiteStorage` — a custom `BaseStorage` implementation living in `database/fsm_storage.py`, persisting FSM state and data in the project's existing SQLite database through the shared connection from `database/connection.py`. Backend approved up front by the user under `R-PROC-1`: no new dependencies, no new infrastructure, explicitly not Redis and not a third-party package. No expiry — state restores verbatim at any age (FR-012). Consumers are untouched: `handlers/*` and `services/ui_service.py` keep their current FSM calls, zero call-site edits (SC-006).

**Discovered during planning — a defect the naive schema would have shipped.** `StorageKey.thread_id` defaults to `None` `[VERIFIED: aiogram/fsm/storage/base.py:18]`, and SQLite treats NULLs in a composite PRIMARY KEY as **distinct** — an executable probe on the bundled sqlite 3.45.1 inserted `(1, NULL)` twice and got two rows ([research.md](research.md) §2). Since `thread_id=None` is the **main** path (every private-message chat, which is where this bot's entire FSM lives), the obvious schema would have created a duplicate row on every write and made reads nondeterministic — silently, on the primary scenario. Resolution: `thread_id INTEGER NOT NULL DEFAULT 0` with a `None → 0` sentinel at the storage boundary (invariant I-1, locked by a test). The sentinel is safe because Telegram thread ids are message ids, always positive.

**The second trap is `R-FSM-1` itself.** "State cleared, so drop the row" is the natural reading of FR-010 and it would destroy the Sterile Interface: the project's standard teardown is `state.set_state(None)` **plus** `clear_fsm_data_safely`, which deliberately preserves `last_menu_ids` / `last_menu_id` / `admin_onboarded` `[VERIFIED: services/ui_service.py:71-81]`. Dropping the row on a null state would wipe those tracking keys and leave undeletable menu garbage — reintroducing, inside the new storage, the exact consequence of item №16 this feature exists to remove. Deletion is therefore gated on `state IS NULL` **and** `data == {}` together (invariant I-4, D-4).

## Technical Context

**Language/Version**: Python 3.11 (`venv` mandatory, `R-PROC-7`)

**Primary Dependencies**: aiogram 3.4.1 `[VERIFIED: requirements.txt]`. **No new dependencies** (FR-008, SC-005): `BaseStorage` is a stock aiogram ABC, `json` and `sqlite3` are stdlib.

**Storage**: SQLite (WAL), one process-wide shared `sqlite3` connection via `database/connection.py` `get_conn()` — the feature 008 №15 pattern. There is no async SQLite driver in the project and adding one stays out of scope (spec Assumptions; `docs/knowledge/architecture.md` gates it behind profiling). New table `fsm_storage`, created inside the existing `init_db()` flow, idempotent, safe on existing databases (FR-007).

**Testing**: pytest, pytest-asyncio 0.23.6 (strict). The autouse `db_setup` fixture already rebinds `connection.DB_PATH` to a temp file and calls `init_db()` per test `[VERIFIED: tests/conftest.py:26-37]`, so the new table exists per test for free. The existing `storage` fixture stays `MemoryStorage` `[VERIFIED: tests/conftest.py:80-83]` — handler tests test handlers, and the storage is irrelevant to them. **No reset fixture is needed**: unlike `reset_registration_cache` / `reset_sheets_sync_state`, `SQLiteStorage` holds no in-process state — there is nothing to reset (D-10).

**Target Platform**: Telegram bot (long polling) plus FastAPI mini-app in the same process; Linux/Windows.

**Project Type**: Monolithic Telegram bot, layered architecture (`handlers` → `services` → `database` facade).

**Performance Goals**: none set. Two extra local SQLite round-trips per `update_data` (inherited default implementation, D-6) against a WAL database on the same host, at a scale of ~200 users, is not a subject for optimization. `MemoryStorage` was never the bottleneck; it was the bug.

**Constraints**:

- `BaseStorage` requires exactly five abstract methods — `set_state`, `get_state`, `set_data`, `get_data`, `close`; `update_data` ships with a default implementation `[VERIFIED: aiogram/fsm/storage/base.py]`;
- `StorageKey` in 3.4.1 is `(bot_id, chat_id, user_id, thread_id=None, destiny="default")` — **no `business_connection_id`** `[VERIFIED]`; the schema does not pre-build for it, so the aiogram upgrade in Phase 4 is not silently pulled into this feature;
- absent-record semantics are part of the contract: `get_state → None`, `get_data → {}`, never raising `[VERIFIED: memory.py:33 defaultdict]`;
- `storage.close()` is really called on dispatcher shutdown `[VERIFIED: aiogram/fsm/middleware.py:110]`, and must stay a no-op — the shared connection belongs to `database/connection.py` and is also serving the FastAPI half of the same process (D-5);
- `loader.py` builds the Dispatcher at **import** time while `init_db()` runs later inside `main()` `[VERIFIED: loader.py, main.py:49]` — so the storage constructor must not touch the database at all (D-8);
- SQLite NULL is distinct inside a composite PK `[VERIFIED by probe, sqlite 3.45.1]` — see Summary and I-1;
- UPSERT (`ON CONFLICT DO UPDATE`) is available `[VERIFIED: sqlite 3.45.1 >> 3.24]`.

**Key risks**:

- *Silently breaking the Sterile Interface via the deletion rule.* This is the highest-value risk in the feature: it fails without any error, exactly like the `state.clear()` bug `R-FSM-1` was written for. Mitigated by I-4 plus a dedicated test asserting that `set_state(None)` with non-empty data keeps the row.
- *Duplicate rows on the private-chat path.* Mitigated by the `thread_id` sentinel (I-1) and a conflict test; found by probe before any code was written.
- *Type drift through JSON.* The full inventory of FSM values is `None`/`int`/`str`/`bool`/`list[int]` — all JSON-safe `[VERIFIED: 19 production call sites]`. Mitigated by a round-trip test over that real inventory rather than a comment; the JSON edges (`tuple → list`, non-string dict keys) are unreachable today and the test is what keeps them that way.
- *Import-graph drift.* The new `loader.py → database/db.py` arrow is invisible to import-linter, whose `root_packages` cover only `handlers`/`middlewares`/`services`/`database` `[VERIFIED: .importlinter]`. Mitigated by a Route C update to `docs/knowledge/architecture.md` in the same commit, verified by eye — no machine gate will catch this one.

**Scale/Scope**: one new module (~120 lines), one new table, one line changed in `loader.py`, one import added to the facade, one `CREATE TABLE` added to `init_db()`. Storage rows are O(users) — hundreds. Zero changes to handlers, services, keyboards, or the existing test corpus.

**Out of scope**: async driver / `to_thread` for database calls (gated behind profiling since 008); event isolation — `events_isolation` stays at the aiogram default `DisabledEventIsolation` (D-9), since serializing concurrent updates is a different problem from surviving a restart; any TTL / expiry mechanism (FR-012, rationale in spec Assumptions); `business_connection_id` support.

## Constitution Check

*GATE: passed before Phase 0; re-checked after Phase 1.*

| Principle | Status | Justification |
|---|---|---|
| **I. Layered Isolation** (`R-ARCH-1/2/4`) | PASS | `database/fsm_storage.py` is an internal module of the `database` package and imports `.connection` exactly as its siblings (`members.py`, `topics.py`) do. `loader.py` reaches it **through the facade** (`from database.db import SQLiteStorage`), so no consumer bypasses `database/db.py` (`R-ARCH-1`). Re-exporting a class is not domain data access: the facade gains **zero** operations over FSM state, and no service or handler can read or write it (I-5). Handlers keep importing nothing from `database` (`R-ARCH-2`). The new arrow `loader.py → database/db.py` mirrors the existing `main.py → database/db.py (init_db only)` and flows consumer-to-provider (`R-ARCH-4`). |
| **II. Sterile Interface** (`R-UI-1`, `R-FSM-1`, `R-UI-2`) | PASS | The feature changes only *where* state lives. `sterile_show` remains the transition gateway, the navigator's FSM-reset asymmetry is untouched, and `state.clear()` is neither introduced nor enabled. The one real hazard — a deletion rule that would eat the tracking keys — is closed by I-4 and its test. This principle is the reason the feature exists: US1 is the Sterile Interface finally surviving a restart. |
| **III. Service-Mediated Mutation** (`R-DATA-1/4`) | PASS | No entity mutation is touched. FSM state is transport for the UI, not domain data — which is exactly why it stays off the facade and carries no foreign keys (D-2). |
| **IV. Test-First** (`R-PROC-3`, `R-TEST-1/3`) | PASS | Item №16 is a defect ("a restart loses state"), so `R-PROC-3` requires a failing reproducing test first: it asserts the loss on `MemoryStorage` and turns green on `SQLiteStorage` (D-10). Tests use the existing autouse `db_setup` isolated temp database (`R-TEST-1`); `bot.db` is never written during tests. |
| **V. Single Source of Truth** (`R-CODE-7`) | PASS | This plan cites rule IDs instead of restating them. The storage stays key-agnostic (FR-003): it holds no knowledge of what `last_menu_ids` or `admin_onboarded` mean — that knowledge stays solely in `UIService`. |
| **`R-DATA-2`** (FK enforcement) | PASS | `PRAGMA foreign_keys=ON` and the `init_db()` runtime fuse are untouched. `fsm_storage` declares no foreign keys — deliberately (D-2): state exists before a user is registered, `chat_id` is not a user, and `ON DELETE CASCADE` would silently wipe state. A table with no FK does not weaken FK enforcement. |
| **`R-ARCH-8`, `R-PROC-10/11`** | PASS | semgrep / ruff / import-linter must show no new violations. Docker must be up: a `skip` is not a green. Note the honest gap: import-linter cannot see the `loader.py` arrow (root modules are outside its `root_packages`), so the graph update in `docs/knowledge/architecture.md` is checked by eye, not by machine. |
| **`R-PROC-5`** (Git) | PASS | Local commit at the milestone; push only on explicit request. |

**Gate verdict**: PASS on all principles. Complexity Tracking is not filled in — there are no violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/012-persistent-fsm-storage/
├── plan.md              # This file
├── spec.md              # Spec (FR-012 resolved: no expiry — see Assumptions)
├── research.md          # Phase 0: aiogram contract, the NULL-in-PK probe, decisions D-1..D-10
├── data-model.md        # Phase 1: fsm_storage schema, invariants I-1..I-6, record lifecycle
├── quickstart.md        # Phase 1: how to validate, including the manual restart checks
├── checklists/
│   └── requirements.md  # Spec quality checklist (green)
├── contracts/
│   └── storage-contract.md  # Phase 1: the two-sided BaseStorage contract
└── tasks.md             # Phase 2 (/speckit-tasks — NOT created by this command)
```

### Source Code (repository root)

```text
database/
├── fsm_storage.py                    # [NEW] SQLiteStorage(BaseStorage): the five contract methods.
│                                     #       Imports .connection like its siblings; imports no
│                                     #       services/handlers. Constructor touches no database (D-8).
│                                     #       None -> 0 thread_id sentinel (I-1); JSON serialization (D-3);
│                                     #       deletion gated on state IS NULL AND data == {} (I-4);
│                                     #       close() is a no-op (D-5); update_data inherited (D-6).
├── connection.py                     # [MODIFY] init_db(): add CREATE TABLE IF NOT EXISTS fsm_storage,
│                                     #          alongside the existing tables (FR-007).
└── db.py                             # [MODIFY] Re-export the SQLiteStorage class only — no FSM data
                                      #          operations reach the facade (I-5, D-1).

loader.py                             # [MODIFY] MemoryStorage() -> SQLiteStorage(), imported via the
                                      #          facade. The only wiring change in the feature.

tests/
└── test_database/
    └── test_fsm_storage.py           # [NEW] RED repro first (R-PROC-3): restart loses state on
                                      #       MemoryStorage, survives on SQLiteStorage. Then the
                                      #       contract: round-trip over the real key inventory (I-3),
                                      #       thread_id=None conflict (I-1), the R-FSM-1 deletion
                                      #       boundary (I-4), absent-key semantics (I-2), corrupted
                                      #       JSON degradation (FR-009), owner isolation (I-6),
                                      #       close() leaves the shared connection alive (D-5).
                                      # NOTE: tests/conftest.py is NOT modified — db_setup already
                                      #       gives per-test isolation, and the storage fixture stays
                                      #       MemoryStorage for the existing corpus (D-10).

docs/knowledge/
├── architecture.md                   # [MODIFY] Route C, same commit: the import graph gains
│                                     #          loader.py -> database/db.py (SQLiteStorage only).
│                                     #          No machine gate covers this — verify by eye.
├── fsm-protocol.md                   # [MODIFY] Route C: state now persists across restarts; record
│                                     #          the storage backend and the no-expiry decision.
└── db-patterns.md                    # [MODIFY] Route C: the fsm_storage table, its lack of FKs,
                                      #          and the thread_id sentinel rationale.
```

**Structure Decision**: The storage lives **inside `database/`**, not at the repository root next to `callbacks.py`. Reason: it is persistence, and persistence is what that package is. The root alternative would have had to reach the connection through `db.get_conn()` — legal, but it would place a persistence module outside the persistence layer purely to dodge a question the facade already answers. `R-ARCH-1` is satisfied by routing `loader.py` through `db.py`, not by relocating the module. What must **not** happen is the facade growing FSM read/write functions: the class re-export is the whole of the public surface (I-5).

## Execution Order (realized in `tasks.md`)

Chunks of 3-5 steps with a HARD-STOP gate at every boundary (`R-PROC-2`). Standing invariant: the existing test corpus stays green **without edits** at every step — needing to touch it signals unplanned behavior drift, which is a stop-and-investigate signal, not a fix (SC-006).

| Phase | Content | Exit condition |
|---|---|---|
| **1** | Baseline: full pytest green recorded; Docker up for the semgrep gate | Known-good starting point |
| **2** | RED repro (`R-PROC-3`): restart loses state on `MemoryStorage`. Then the schema in `init_db()` + `SQLiteStorage` with the five methods; repro turns GREEN | FR-001/FR-006/FR-007 closed; the feature works in isolation, still unwired |
| **3** | Contract tests: I-1 conflict, I-3 round-trip over the real inventory, I-4 deletion boundary, I-2 absent keys, FR-009 corruption, I-6 isolation, D-5 close | Every invariant locked by a test before a single user reaches the code |
| **4** | Wire it: facade re-export + the `loader.py` one-liner. Full corpus green **unedited** | SC-006 proven; the feature is live |
| **5** | Route C in the same commit: `architecture.md` import graph, `fsm-protocol.md`, `db-patterns.md`; governance suite | Bundle atomic (concept + `index.md` + `log.md` + timestamp bump) |
| **6** | Gates: ruff, import-linter, semgrep (Docker up), full pytest; checklist-linter as the final item | `R-ARCH-8`, `R-PROC-10/11` |

**Why the wiring comes last.** Phases 2-3 build and prove the storage while the bot still runs on `MemoryStorage`, so every invariant — above all the `R-FSM-1` deletion boundary — is locked before a single real user's state depends on it. Phase 4 is then a one-line switch whose blast radius is already measured, and the rollback posture is trivial: revert one line to `MemoryStorage` and the bot is back on the known-good path, with the new table sitting harmlessly unused.

## Complexity Tracking

Not applicable: the Constitution Check has no violations requiring justification.
