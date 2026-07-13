# Implementation Plan: DB Connection Reuse & Registration Caching

**Branch**: `008-db-connection-caching` | **Date**: 2026-07-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/008-db-connection-caching/spec.md`

## Summary

Eliminate DB connection churn (≈6 `sqlite3.connect` + 2 PRAGMA cycles per incoming message → ≤1) and redundant per-message registration lookups, without changing the `database.db` facade contract, its 77 call-sites, or making any DB call asynchronous. Two localized changes: (1) `database/connection.py` keeps one lazily-created, process-wide connection with WAL + FK applied once; `get_conn()` yields it instead of opening/closing per call. (2) `services/management_service.py` gains a short-TTL in-memory cache for user/topic registration facts so repeated messages skip the DB. Async-driver migration and thread-pool offload are explicitly out of scope (PA-1 Ф3 verdict; Ф2 gated behind profiling).

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: aiogram 3, FastAPI, stdlib `sqlite3` (no new dependency)

**Storage**: SQLite (WAL mode), local file; path overridable via `BOT_DB_PATH`

**Testing**: pytest (isolated per-test DB via autouse `db_setup` fixture in `tests/conftest.py`)

**Target Platform**: Linux/Windows single-process bot, single-threaded asyncio event loop

**Project Type**: Single project (Telegram bot + FastAPI mini-app), layered facade architecture

**Performance Goals**: ≤1 new physical DB connection per message (baseline ≈6); 0 registration DB hits on a repeat message within the cache window

**Constraints**: No change to `database.db` public signatures or call-sites (`R-ARCH-1`); no `await` inside DB operations; integrity guarantees (FK, write-transaction atomicity) preserved; test isolation preserved

**Scale/Scope**: 2 files modified (`database/connection.py`, `services/management_service.py`); no schema change; low-hundreds of users, supergroup message throughput

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Layered Isolation (`R-ARCH-1/2/4`)** — PASS. Change is confined below and within the facade: `connection.py` is the connection provider; the `db.*` facade signatures and all handler/service call-sites are untouched (FR-008). No new cross-layer imports.
- **II. Sterile Interface (`R-UI-1`, `R-FSM-1`)** — N/A. No UI/FSM surface touched.
- **III. Service-Mediated Mutation (`R-DATA-1/4`)** — PASS. Registration still flows through `ManagementService`; cache only short-circuits a read-check, mutation path unchanged.
- **IV. Test-First (`R-PROC-3`, `R-TEST-1/3`)** — PASS by construction: reproducing test counting `sqlite3.connect` per message is written first (US1 P1), on isolated DB fixtures.
- **V. Single Source of Truth (`R-CODE-7`)** — PASS. Plan cites rule IDs; no rule text copied.
- **Static enforcement (`R-ARCH-8`, `R-PROC-10/11`)** — semgrep / import-linter / ruff / AST gates must stay green; no facade-bypass introduced.

**Result**: No violations. Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/008-db-connection-caching/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── internal-interfaces.md   # Facade contract (unchanged) + new internal helpers
├── checklists/
│   └── requirements.md  # Spec quality checklist (from /speckit-specify)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
database/
├── connection.py        # [MODIFY] persistent shared connection; get_conn() yields it;
│                        #          init_db() resets shared connection (test isolation)
└── db.py                # [UNCHANGED] facade re-exports

services/
└── management_service.py # [MODIFY] TTL registration cache in ensure_user_registered
                          #          and register_topic_if_not_exists; cache reset hook

tests/
├── conftest.py          # [MODIFY] db_setup fixture resets registration cache per test
├── test_database/
│   └── test_connection_reuse.py  # [NEW] reproducing test: connect-count per message
└── test_services/
    └── test_registration_cache.py # [NEW] cache hit/expiry/invalidation tests
```

**Structure Decision**: Single-project layout. Two production files change (`database/connection.py`, `services/management_service.py`); the facade `database/db.py` and all 77 call-sites remain byte-identical. Test isolation is preserved by hooking both resets (shared connection + registration cache) into the paths the autouse `db_setup` fixture already exercises (`init_db()` + an explicit cache reset).

## Complexity Tracking

> No Constitution Check violations. Section intentionally empty.
