---

description: "Task list for DB Connection Reuse & Registration Caching (feature 008)"
---

# Tasks: DB Connection Reuse & Registration Caching

**Input**: Design documents from `/specs/008-db-connection-caching/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: TDD is mandatory for this feature (`R-PROC-3`, `R-TEST-1`). Each user story writes a
failing reproducing test FIRST, before any production change.

**Organization**: Grouped by user story. US1 (P1) and US2 (P2) touch different files
(`database/connection.py` vs `services/management_service.py`) and are independently testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1, US2
- Exact file paths included.

## Approval Gates (R-PROC-2 — MANDATORY)

Execution is chunked 3–5 tasks. Every chunk ends with a **HARD-STOP** gate task.
`/speckit-implement` MUST NOT proceed past an unchecked HARD-STOP task — it stops, reports in
Russian to Шэф, and awaits explicit approval.

## Path Conventions

Single project: production code in `database/`, `services/`; tests under `tests/` at repo root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Minimal scaffolding for the new test module.

- [x] T001 [P] Ensure `tests/test_database/` is a package — create `tests/test_database/__init__.py` if it does not exist (leave existing test packages untouched)
- [x] T002 Confirm baseline suite is green before any change: run `pytest -q` and record the result (regression baseline for SC-003)

- [x] T003 **HARD STOP**: Report progress to the user (Шэф) in Russian — baseline recorded, scaffolding ready — and AWAIT EXPLICIT APPROVAL before starting User Story 1. (R-PROC-2)

---

## Phase 3: User Story 1 - Reuse a single database connection (Priority: P1) 🎯 MVP

**Goal**: Replace per-call connect+2×PRAGMA churn with one persistent shared connection; ≈6 → ≤1 new connections per message, facade and call-sites unchanged.

**Independent Test**: Spy `sqlite3.connect`, drive one message through the full middleware access-check chain; assert ≤1 new connection once warm, with all DB-layer and permission tests green.

### Tests for User Story 1 (write FIRST — must FAIL before implementation) ⚠️

- [x] T004 [P] [US1] Write reproducing test `tests/test_database/test_connection_reuse.py`: patch/spy `sqlite3.connect` to count calls, drive one message through `UserManagerMiddleware` → `ForumUtilityMiddleware` → `AccessGuardMiddleware` using existing journey fixtures; first assert the current churn (≈6) to prove RED, then encode the post-fix target `≤ 1` (SC-001, FR-001). Assert mock `args`/`kwargs` per `R-TEST-3`.

### Implementation for User Story 1

- [x] T005 [US1] In `database/connection.py`: introduce a module-level `_shared_conn: sqlite3.Connection | None`; add a lazy accessor that creates it with `check_same_thread=False` and applies `PRAGMA journal_mode=WAL` + `PRAGMA foreign_keys=ON` **once** (FR-002); make `get_conn()` yield the shared connection and **not** close it on exit (FR-001, FR-003 — nested `with conn:` still commits/rolls back).
- [x] T006 [US1] In `database/connection.py`: make `init_db()` first close+null any existing `_shared_conn`, then (re)create against the current `DB_PATH` (FR-006 test isolation); add best-effort recovery — recreate when `_shared_conn` is `None`/unusable (FR-007); add an optional shutdown close helper.
- [x] T007 [US1] Run `pytest tests/test_database/test_connection_reuse.py -v` (now GREEN, ≤1) and the full DB-layer + permission suites; confirm the integrity/rollback path (`database/permissions.py` duplicate-grant → `IntegrityError`) still rolls back on the reused connection (SC-005, FR-003).

**Checkpoint**: Connection reuse functional and independently verified.

- [x] T008 **HARD STOP**: Report progress to the user (Шэф) in Russian — summarize US1 completion (connect-count result, suite status) — and AWAIT EXPLICIT APPROVAL before starting User Story 2. (R-PROC-2)

---

## Phase 4: User Story 2 - Cache repeated registration lookups (Priority: P2)

**Goal**: Short-TTL in-memory memo for user/topic registration so repeat messages skip the DB; 2 → 0 registration DB hits within the window, name changes reapplied within TTL.

**Independent Test**: Two consecutive identical messages (same user, same topic) → second causes 0 registration DB hits; expired memo re-hits DB; `reset_registration_cache()` clears memos.

### Tests for User Story 2 (write FIRST — must FAIL before implementation) ⚠️

- [x] T009 [P] [US2] Write test `tests/test_services/test_registration_cache.py`: spy `db.user_exists` / `db.register_topic_if_not_exists`; assert (a) second identical message → 0 registration DB hits (SC-002, FR-004), (b) after advancing the monotonic clock past `REGISTRATION_TTL_SECONDS` the memo expires and registration re-hits DB (FR-005), (c) `reset_registration_cache()` clears both memos. Assert mock `args`/`kwargs` per `R-TEST-3`.

### Implementation for User Story 2

- [x] T010 [US2] In `services/management_service.py`: add constant `REGISTRATION_TTL_SECONDS = 300` and two module-level `dict[int, float]` memos (user, topic) keyed on `time.monotonic()`; gate `ensure_user_registered` and `register_topic_if_not_exists` to check freshness first, hit DB on miss/expiry, record timestamp on success (FR-004, FR-005) — cold cache reproduces exact current behavior.
- [x] T011 [US2] In `services/management_service.py`: add `reset_registration_cache()` clearing both memos; wire a one-line call into the autouse `db_setup` fixture in `tests/conftest.py` so each test starts with cold memos (test isolation).
- [x] T012 [US2] Run `pytest tests/test_services/test_registration_cache.py -v` (GREEN) and the full suite `pytest -q` — all green, no changes to business-logic tests (SC-003).

**Checkpoint**: Both stories independently functional.

- [x] T013 **HARD STOP**: Report progress to the user (Шэф) in Russian — summarize US2 completion — and AWAIT EXPLICIT APPROVAL before Polish & Cross-Cutting Concerns. (R-PROC-2)

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Verification, static gates, docs flagging.

- [x] T014 [P] Run `quickstart.md` validation end-to-end (connect-count ≈6→≤1; registration hits 2→0); record measured numbers against SC-001/SC-002.
- [x] T015 Run static architecture gates — semgrep / import-linter / ruff / `pytest tests/test_governance.py` — confirm facade signatures & 77 call-sites unchanged (SC-004, `R-ARCH-8`, `R-PROC-10/11`).
- [x] T016 Flag Route C (docs-update) if the connection/registration behavior warrants a note in `docs/knowledge/` (architecture) or `CHANGELOG.md` (`CMD-4`); no git operations here.

- [x] T017 **HARD STOP**: Report final results to the user (Шэф) in Russian — measured outcomes, suite/gate status — and AWAIT EXPLICIT APPROVAL before any commit (GW-1) or further work. (R-PROC-2)

- [x] T018 Run checklist-linter: `python local_scripts/prompt_linter.py --dir specs/008-db-connection-caching --stage checklist` and confirm it prints "Checklist is valid." (R-PROC-4 completion gate; convert any `[X]` → `[x]` first per linter casing)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **US1 (Phase 3)**: after Setup. Self-contained (`database/connection.py` + reproducing test).
- **US2 (Phase 4)**: after Setup. Self-contained (`services/management_service.py` + `tests/conftest.py`); independent of US1 at the code level — different files.
- **Polish (Phase 5)**: after US1 and US2.

### Within Each User Story

- Reproducing test written and FAILING before implementation (`R-PROC-3`).
- `connection.py` accessor before `init_db()` reset wiring (US1).
- Cache memos before `reset_registration_cache()` + fixture wiring (US2).
- Story complete and green before moving on.

### Parallel Opportunities

- T001 [P] independent of T002.
- T004 [P] (US1 test) and T009 [P] (US2 test) touch different files — writable in parallel.
- US1 and US2 are independent files; if staffed, both stories can proceed in parallel after Setup.
- T014 [P] independent of T015 within Polish.

---

## Parallel Example

```bash
# US1 and US2 reproducing tests target different files — can be authored together:
Task: "Write tests/test_database/test_connection_reuse.py (US1)"
Task: "Write tests/test_services/test_registration_cache.py (US2)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup → 2. Phase 3 US1 (persistent connection) → 3. STOP & VALIDATE connect-count ≤1 → MVP delivers the dominant churn win on its own.

### Incremental Delivery

Setup → US1 (connection reuse, MVP) → US2 (registration cache) → Polish. Each story is an independently green increment; US2 adds the repeat-message win without touching US1's file.

---

## Notes

- [P] = different files, no dependencies.
- Scope frozen: no `aiosqlite`, no thread-pool offload (FR-009 / PA-1 Ф3 verdict).
- Facade `database/db.py` and all 77 call-sites remain byte-identical (FR-008, SC-004).
- Commit only on Шэф's word (GW-1, `R-PROC-5`); graph updated post-commit via headless CLI only.
