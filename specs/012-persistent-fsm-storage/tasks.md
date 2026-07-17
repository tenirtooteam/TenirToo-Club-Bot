---
description: "Task list for feature 012 — persistent FSM storage"
---

# Tasks: Persistent FSM Storage

**Input**: Design documents from `/specs/012-persistent-fsm-storage/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/storage-contract.md](contracts/storage-contract.md), [quickstart.md](quickstart.md)

**Tests**: REQUIRED. Item №16 is a defect (a restart loses state), so `R-PROC-3` mandates a failing reproducing test before the fix. TDD is not optional here.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies). Note: all storage unit tests share one file (`tests/test_database/test_fsm_storage.py`), so they are **not** [P] among themselves.
- **[Story]**: US1 (menu garbage), US2 (input survival), US3 (onboarding).

## Why there are no per-story implementation phases

This feature's three user stories are one bug with one fix: `MemoryStorage` loses everything on restart. The moment `SQLiteStorage` persists state, US1, US2 and US3 are all satisfied at once — they are three observable *consequences* of a single mechanism, not independently shippable slices. Forcing three implementation phases would be dishonest padding. Story traceability is preserved instead through three focused RED repro tests (T002/T003/T004), one per consequence. **MVP = the storage mechanism itself** (through the Phase 2 gate); it lights up all three stories together.

## Approval Gates (R-PROC-2)

Every chunk boundary ends with a HARD-STOP task. `/speckit-implement` MUST NOT proceed past an unchecked HARD-STOP — it stops, reports in Russian to Шэф, and waits.

---

## Phase 1: Setup & Baseline

- [x] T001 Record a known-good baseline: run `venv\Scripts\python.exe -m pytest` and confirm the full corpus is green; confirm the Docker daemon is up so the semgrep gate runs for real (a `skip` is not a green). See [quickstart.md](quickstart.md) sections 0-1. No files changed.

---

## Phase 2: RED repro then the storage mechanism (Foundational — blocks everything)

**Purpose**: Reproduce the defect first (`R-PROC-3`), then build the shared mechanism that makes all three stories pass.

### RED — write these first, they MUST FAIL (SQLiteStorage does not exist yet)

- [x] T002 [US1] RED test in `tests/test_database/test_fsm_storage.py`: write `last_menu_ids=[100, 200]` and `last_menu_id=200` via a `SQLiteStorage` instance, then read them back through a **new** `SQLiteStorage` instance over the same temp DB (restart model); assert the menu-tracking keys survive. MUST FAIL now. (FR-001, US1, [quickstart.md](quickstart.md) section 2)
- [x] T003 [US2] RED test in `tests/test_database/test_fsm_storage.py`: set an input state plus context keys (`state="waiting_for_topic_name"`, `moderator_edit_topic_id=55`), read back through a new instance; assert both the state and the typed context survive the restart model. MUST FAIL now. (FR-001, FR-004, US2)
- [x] T004 [US3] RED test in `tests/test_database/test_fsm_storage.py`: write `admin_onboarded=True`, read back through a new instance; assert it survives the restart model. MUST FAIL now. (FR-001, US3)

### GREEN — implement the mechanism

- [x] T005 Add the schema in `database/connection.py` `init_db()`: `CREATE TABLE IF NOT EXISTS fsm_storage` per [data-model.md](data-model.md) — composite PK `(bot_id, chat_id, user_id, thread_id, destiny)`, `thread_id INTEGER NOT NULL DEFAULT 0`, `state TEXT` nullable, `data TEXT NOT NULL DEFAULT '{}'`, `updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`, no foreign keys. Idempotent, placed alongside the existing tables. (FR-007, D-2, D-7)
- [x] T006 Implement `SQLiteStorage(BaseStorage)` in `database/fsm_storage.py` per [contracts/storage-contract.md](contracts/storage-contract.md): the five methods (`set_state`/`get_state`/`set_data`/`get_data`/`close`), `State`-vs-`str` unwrap, `None -> 0` thread_id sentinel, JSON serialize (raise on non-serializable write), `INSERT ... ON CONFLICT DO UPDATE`, deletion gated on `state IS NULL` AND `data == {}`, `close()` no-op, connection only via `get_conn()`, constructor touches no DB. Inherit `update_data`. After this, T002/T003/T004 go GREEN. (FR-001/003/004/005/006/009/010, D-1/D-3/D-4/D-5/D-6/D-8)
- [x] T007 **HARD STOP**: Report progress to Шэф in Russian — RED repro reproduced then made green, storage mechanism built, MVP works in isolation (still on MemoryStorage in production) — and AWAIT EXPLICIT APPROVAL before hardening invariants. (R-PROC-2)

---

## Phase 3: Lock the invariants (contract tests)

**Purpose**: Prove each invariant with a test before any real user reaches the code. All in `tests/test_database/test_fsm_storage.py`.

- [x] T008 Invariant I-1 (the NULL-in-PK trap) in `tests/test_database/test_fsm_storage.py`: write twice under one key with `thread_id=None`; assert `SELECT count(*) FROM fsm_storage == 1`. (I-1, [research.md](research.md) section 2)
- [x] T009 Invariant I-3 round-trip in `tests/test_database/test_fsm_storage.py`: store the real key inventory (`list[int]`, `bool`, `None`, `str`, `int`) and assert values return with types intact; additionally assert a freshly written row has a non-null `updated_at` (guards the FR-012 passive-timestamp column against silent schema drift). (FR-004, FR-012, I-3, [research.md](research.md) section 3)
- [x] T010 Invariant I-4 (the R-FSM-1 deletion boundary) in `tests/test_database/test_fsm_storage.py`: assert `set_state(None)` with non-empty data KEEPS the row (tracking keys survive), and `state=None` + `data={}` DROPS the row. This is the highest-value test in the feature. (R-FSM-1, FR-010, I-4, D-4)
- [x] T011 Invariant I-2 absent-key semantics in `tests/test_database/test_fsm_storage.py`: unknown key returns `get_state() -> None` and `get_data() -> {}` without raising. (I-2)
- [x] T012 **HARD STOP**: Report progress to Шэф in Russian — the four core invariants incl. the R-FSM-1 deletion boundary are locked — and AWAIT EXPLICIT APPROVAL before the remaining resilience tests. (R-PROC-2)

- [x] T013 FR-009 corruption in `tests/test_database/test_fsm_storage.py`: put non-JSON garbage in a row's `data`; assert `get_data()` returns `{}` plus a logged warning, without raising and without dropping the row. (FR-009)
- [x] T014 Invariant I-6 owner isolation in `tests/test_database/test_fsm_storage.py`: two different `(bot_id, chat_id, user_id)` keys never read each other's state. (FR-002, I-6)
- [x] T015 Decision D-5 in `tests/test_database/test_fsm_storage.py`: `await storage.close()` leaves the shared `database/connection.py` connection alive and usable. (D-5)
- [x] T016 **HARD STOP**: Report progress to Шэф in Russian — all invariants and resilience cases green on the unwired storage — and AWAIT EXPLICIT APPROVAL before wiring it into production. (R-PROC-2)

---

## Phase 4: Wire it into production

**Purpose**: The one-line switch, with the blast radius already measured.

- [x] T017 Re-export the `SQLiteStorage` class through the facade `database/db.py` (class only — no FSM data operations on the facade). (I-5, D-1)
- [x] T018 In `loader.py`, replace `MemoryStorage()` with `SQLiteStorage()` imported via `from database.db import SQLiteStorage`. This is the only wiring change. (SC-006, D-1)
- [x] T019 Run the full corpus `venv\Scripts\python.exe -m pytest` and confirm it is green **without a single edit** to the existing test files. A needed edit is a stop-and-investigate signal, not a fix. (SC-006, [quickstart.md](quickstart.md) section 1)
- [x] T020 **HARD STOP**: Report progress to Шэф in Russian — feature is live, full corpus green unedited (SC-006 proven) — and AWAIT EXPLICIT APPROVAL before the Route C documentation update. (R-PROC-2)

---

## Phase 5: Route C documentation (same commit)

**Purpose**: Keep the knowledge bundle in sync; the import-graph edit is the one no machine gate catches.

- [x] T021 [P] In `docs/knowledge/architecture.md` (section Import Dependency Graph) add the arrow `loader.py -> database/db.py (SQLiteStorage)`. Verify by eye — import-linter does not cover root modules. (D-1, [research.md](research.md) D-1)
- [x] T022 [P] In `docs/knowledge/fsm-protocol.md` record that FSM state now persists across restarts, name the SQLite backend, and note the no-expiry decision (FR-012).
- [x] T023 [P] In `docs/knowledge/db-patterns.md` document the `fsm_storage` table: its absence of foreign keys and the `thread_id` sentinel rationale. (D-2)
- [x] T024 Keep the bundle atomic: update `docs/knowledge/index.md`, append to `docs/knowledge/log.md`, and bump the touched concept files' `timestamp` front-matter; then run `venv\Scripts\python.exe -m pytest tests/test_governance.py tests/test_knowledge_bundle.py` green (12 checks).
- [x] T025 **HARD STOP**: Report progress to Шэф in Russian — Route C bundle updated and governance green — and AWAIT EXPLICIT APPROVAL before the final gate run. (R-PROC-2)

---

## Phase 6: Gates

**Purpose**: Machine gates all green (`R-ARCH-8`, `R-PROC-10/11`).

- [x] T026 Run static gates: `venv\Scripts\python.exe -m pytest tests/test_services/test_import_lint.py tests/test_services/test_ruff_lint.py tests/test_services/test_semgrep_lint.py` (Docker up) and `venv\Scripts\lint-imports.exe`; all green, no new violations. ([quickstart.md](quickstart.md) section 3)
- [x] T027 Run the full suite `venv\Scripts\python.exe -m pytest` one final time; confirm green.
- [x] T028 Mark every checkbox in this file `[x]` (ASCII-safe, lowercase x), then run the checklist-linter: `venv\Scripts\python.exe local_scripts\prompt_linter.py --dir specs\012-persistent-fsm-storage --stage checklist` (run checklist-linter). Must report the checklist valid. (R-PROC-4)

---

## Dependencies & Execution Order

- **Phase 1** (T001): no dependencies.
- **Phase 2** (T002-T006): RED tests T002-T004 before the implementation T005-T006 (`R-PROC-3`). T006 depends on T005 (needs the table). Blocks everything downstream.
- **Phase 3** (T008-T015): depends on T006. Sequential — one shared test file.
- **Phase 4** (T017-T019): depends on the storage being proven (Phase 3). T018 depends on T017. T019 depends on T018.
- **Phase 5** (T021-T024): depends on the feature being live (Phase 4). T021/T022/T023 are [P] (different files); T024 depends on them.
- **Phase 6** (T026-T028): depends on everything. T028 is strictly last.

## Parallel Opportunities

- Only the Route C doc edits are genuinely parallel: T021, T022, T023 touch three different files.
- All storage tests share `tests/test_database/test_fsm_storage.py` and run sequentially.

## Implementation Strategy

MVP is the storage mechanism through the Phase 2 gate (T007): at that point state persists across a restart and US1/US2/US3 are all satisfied. Phases 3-6 harden, wire, document, and gate — they do not add user-visible scope, they make the MVP safe to ship. Local commit at the Phase 6 completion (`GW-1`); push only on Шэф's explicit word (`R-PROC-5`).
