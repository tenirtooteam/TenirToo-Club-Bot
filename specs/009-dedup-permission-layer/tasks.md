---

description: "Task list — Dedup Permission Layer (feature 008 №20)"
---

# Tasks: Dedup Permission Layer (feature 008 №20)

**Input**: Design documents from `specs/009-dedup-permission-layer/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, quickstart.md ✅

**Tests**: REQUESTED (R-PROC-3 / Constitution IV — Test-First). Characterization tests
capture current observable behavior; they are GREEN on the current code as a baseline and
MUST stay green after the edits (no behavior change).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 = remove dead duplicate; US2 = honest `is_superadmin`

## Approval Gates (R-PROC-2 — MANDATORY)

`/speckit-implement` MUST NOT proceed past an unchecked **HARD STOP** task. It stops,
reports in Russian to Шэф, and awaits explicit approval.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Test scaffold for the characterization suite.

- [x] T001 Create `tests/test_permission_layer_dedup.py` with pytest imports and reuse of the
  existing isolated-DB fixtures (`R-TEST-1`); patch `ADMIN_ID` via the project's config seam
  for US2 cases (mock assertions check `args`/`kwargs`, `R-TEST-3`).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: None beyond Setup — this is a localized cleanup; no shared schema/framework
changes. DB schema and public contract of the permission layer are unchanged.

**Checkpoint**: Scaffold ready — characterization stories can begin.

- [x] T002 **HARD STOP**: Report progress to Шэф in Russian (scaffold ready) and AWAIT
  EXPLICIT APPROVAL before starting User Story 1. (R-PROC-2)

---

## Phase 3: User Story 1 - Single point of direct-access check (Priority: P1) 🎯 MVP

**Goal**: Remove the dead duplicate `has_direct_access`; `can_write` is the sole
direct-access check. No behavior change.

**Independent Test**: Full permission suite green; `has_direct_access` definition/import
gone; `can_write` behavior identical for access/no-access inputs.

### Tests for User Story 1 (write FIRST, run GREEN on current code as baseline)

- [x] T003 [P] [US1] In `tests/test_permission_layer_dedup.py` add characterization tests for
  `database/permissions.py::can_write`: user WITH a `direct_topic_access(user_id, topic_id)`
  row → `True`; user WITHOUT → `False`. Run and confirm GREEN on unmodified code (baseline).
- [x] T004 [US1] In the same file add a pre-removal equivalence test asserting
  `has_direct_access(u, t) == can_write(u, t)` for both inputs (documents the duplication).
  Run GREEN on current code. (This test is deleted in T006 together with the function.)

### Implementation for User Story 1

- [x] T005 [US1] Remove `has_direct_access` (lines ~74-78) from `database/permissions.py`,
  and drop `has_direct_access` from the import in `database/db.py` (line 27). (R-ARCH-1/2/4)
- [x] T006 [US1] Delete the now-obsolete equivalence test (T004) from
  `tests/test_permission_layer_dedup.py`; retain the `can_write` behavior tests (T003).
- [x] T007 [US1] Run `venv/Scripts/python.exe -m pytest tests/test_permission_layer_dedup.py
  tests/test_journeys -q`; confirm GREEN (behavior preserved, `can_write` intact).

**Checkpoint**: US1 complete — dead duplicate gone, behavior unchanged.

- [x] T008 **HARD STOP**: Report US1 completion to Шэф in Russian and AWAIT EXPLICIT
  APPROVAL before starting User Story 2. (R-PROC-2)

---

## Phase 4: User Story 2 - Honest `is_superadmin` semantics (Priority: P1)

**Goal**: Remove the dead DB branch in `services/permission_service.py::is_superadmin` whose
result does not depend on its condition; preserve observable semantics
(`True` for `ADMIN_ID` / `False` otherwise). Optional diagnostic warning may stay but MUST
NOT affect the result.

**Independent Test**: Behavior cases (True/True/False) green before and after; the function
no longer contains a branch that is dead-by-result.

### Tests for User Story 2 (write FIRST, run GREEN on current code as baseline)

- [x] T009 [P] [US2] In `tests/test_permission_layer_dedup.py` add characterization tests for
  `services/permission_service.py::PermissionService.is_superadmin`:
  (a) `user_id == ADMIN_ID` WITH `superadmin` role in DB → `True`;
  (b) `user_id == ADMIN_ID` WITHOUT the role in DB → `True` (key case: result independent of
  DB); (c) `user_id != ADMIN_ID` → `False`. Run GREEN on unmodified code (baseline).

### Implementation for User Story 2

- [x] T010 [US2] Simplify `is_superadmin` to the authoritative check
  (`user_id == ADMIN_ID`), removing the DB role loop from the result path; keep an OPTIONAL
  diagnostic `logger.warning` on role mismatch that does not change the return. Update the
  docstring to reflect the true semantics (ADMIN_ID is source of truth; log is diagnostic).
  (R-CODE-4, R-CODE-7)
- [x] T011 [US2] Run `venv/Scripts/python.exe -m pytest tests/test_permission_layer_dedup.py
  -q`; confirm the three US2 cases stay GREEN (semantics preserved).

**Checkpoint**: US2 complete — control flow honest, behavior unchanged.

- [x] T012 **HARD STOP**: Report US2 completion to Шэф in Russian and AWAIT EXPLICIT
  APPROVAL before Polish. (R-PROC-2)

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T013 Run the full suite `venv/Scripts/python.exe -m pytest -q` and the architecture
  gates (ruff, import-linter, semgrep — needs live Docker daemon) per `R-ARCH-8`,
  `R-PROC-10/11`; confirm no new violations.
- [x] T014 Flag Route C docs check: the permission-layer registry entry may reference
  `has_direct_access` — if so, update via `tenirtoo-docs-update` (CMD-1/CMD-2). Add a
  `CHANGELOG.md` entry (CMD-4).
- [x] T015 **HARD STOP**: Report final status to Шэф in Russian (tests, gates, docs) and
  AWAIT EXPLICIT APPROVAL before any commit (GW-1; push only on explicit request, R-PROC-5).
- [x] T016 запуск линтера-чеклиста (run checklist-linter): completion gate — convert any
  speckit `[X]` → `[x]`, then run `venv/Scripts/python.exe local_scripts/prompt_linter.py
  --dir specs/009-dedup-permission-layer --stage checklist` and confirm it passes (all boxes
  `[x]`, this line last).

---

## Dependencies & Execution Order

- **Setup (T001)** → **Gate T002** → **US1 (T003–T007)** → **Gate T008** →
  **US2 (T009–T011)** → **Gate T012** → **Polish (T013–T014)** → **Gate T015** →
  **completion-gate T016 (checklist-linter, last)**.
- US1 and US2 are independent (different files: `database/*` vs `services/permission_service.py`)
  and could run in parallel, but sequential P1→P1 order is used to honor per-chunk gates.
- Within each story: characterization tests FIRST (baseline green), then the edit, then re-run.

### Parallel Opportunities

- T003 and T009 ([P]) touch the same test file → do NOT run concurrently (same-file conflict);
  the [P] marks story-independence, not file-independence here.
- T005 (database layer) and T010 (services layer) are file-independent and could be authored
  in parallel if gates were relaxed — they are not, so keep sequential.

---

## Implementation Strategy

**MVP = US1** (removing the dead duplicate). US2 is an independent second increment. Each
story is a complete, independently testable slice; behavior is preserved throughout. Commit
after each approved chunk (GW-1); push only when Шэф explicitly asks (R-PROC-5).

## Notes

- Characterization (not failing-repro) tests: they encode EXISTING behavior and stay green —
  the change is a cleanup, so green-before/green-after is the correctness signal (R-PROC-3
  satisfied by the test-first baseline + no-regression guarantee).
- Line numbers are indicative; confirm against the current files before editing.
