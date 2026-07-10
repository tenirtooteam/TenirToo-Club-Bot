---
description: "Task list for feature 007 — Bot Correctness"
---

# Tasks: Bot Correctness (Correctness Fixes)

**Input**: Design documents from `/specs/007-bot-correctness/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/internal-signatures.md, quickstart.md

**Tests**: REQUIRED — this is a bug-fix feature under R-PROC-3 (TDD): every bug gets a failing
reproducing test written and verified FAILING before its fix.

**Organization**: Grouped by user story (BUG-1..BUG-5) in the plan's chunk order
(A: US1 → B: US2 → C: US3+US5 → D: US4+Tail). HARD-STOP gates sit at each chunk boundary.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1=BUG-1, US2=BUG-2, US3=BUG-3, US4=BUG-4, US5=BUG-5
- Exact file paths included per task

## Approval Gates (R-PROC-2)

HARD-STOP tasks (T006, T010, T018, T026) mark the plan's four chunk boundaries.
`/speckit-implement` MUST stop at each, report to Шэф in Russian, and await explicit approval
before continuing. Do not remove or skip them.

## Checklist-linter note

The `checklist` stage of `local_scripts/prompt_linter.py` is a COMPLETION gate: it passes only
when every item is `[x]` and the final item is "run checklist-linter". Do NOT run it at
generation time (it will report every `[ ]` as incomplete — expected). During
`/speckit-implement`, flip each task to `[x]` as finished (lowercase `[x]`; convert any speckit
`[X]`→`[x]`), then run the gate at the very end. Invoke it UTF-8-safe to avoid the cp1251 print
crash on non-ASCII output: prefix `$env:PYTHONIOENCODING="utf-8";`.

---

## Phase 1: Setup (baseline)

**Purpose**: Establish a green baseline before touching anything. No new infrastructure or
Foundational phase is needed — this feature only edits existing layered code with no schema
change.

- [x] T001 Confirm `venv` active and capture a baseline run of `.\venv\Scripts\python.exe -m pytest -q` (record currently-passing state) per R-PROC-7 / R-TEST-4.

---

## Phase 2: User Story 1 — Multi-day dates keep real values (Priority: P1) 🎯 MVP · BUG-1

**Goal**: Ranges like "10-15 июня" persist full human start/end (`"10 июня"`/`"15 июня"`) and ISO
dates on both create and edit; date decomposition lives in `DateService` (R-CODE-5/6).

**Independent Test**: `tests/test_services/test_date_logic.py` + `tests/test_handlers/test_event_edit_collision.py` prove complete human parts persisted, no fragment.

### Tests (write FIRST, verify FAIL)

- [x] T002 [P] [US1] In `tests/test_services/test_date_logic.py`, add cases asserting `DateService.split_human_range` returns complete parts (`"10-15 июня"`→`("10 июня","15 июня")`, `"10 - 15 мая"`→`("10 мая","15 мая")`, `"15 мая"`→`("15 мая", None)`); verify FAIL (helper absent).
- [x] T003 [P] [US1] In `tests/test_handlers/test_event_edit_collision.py`, add a range regression for both `process_date_confirm` (create path) and the editing path asserting persisted `start_date="10 июня"`, `end_date="15 июня"` (args+kwargs, R-TEST-3); verify FAIL.

### Implementation

- [x] T004 [US1] Implement `DateService.split_human_range(text) -> tuple[str, Optional[str]]` in `services/date_service.py` per contracts/internal-signatures.md (reuse separator + month-inheritance logic).
- [x] T005 [US1] In `handlers/events.py`, replace inline `dates.split("-")` in `process_date_confirm` with `DateService.split_human_range`; rewrite the discarded split branch in `process_editing_dates` to use it; remove dead expressions at ~L352 (`data['new_title']`) and the `_s_human/_e_human/pass` block ~L364-372.

**Checkpoint**: BUG-1 tests green; single-date path unchanged.

- [x] T006 **HARD STOP**: Report BUG-1 completion to Шэф in Russian (what changed, tests green) and AWAIT EXPLICIT APPROVAL before Chunk B. (R-PROC-2)

---

## Phase 3: User Story 2 — Active list ordered & current (Priority: P2) · BUG-2

**Goal**: Active hikes sorted by `start_iso`, fully-past hikes excluded, ongoing/undated kept.

**Independent Test**: `tests/test_database/test_event_contracts.py` seeds past/ongoing/future/undated and asserts order + filtering.

### Tests (write FIRST, verify FAIL)

- [x] T007 [US2] In `tests/test_database/test_event_contracts.py`, add cases: ISO-ordering of a mixed set, exclusion of a fully-past hike, inclusion of an ongoing (started/not-ended) and an undated (`start_iso IS NULL`) hike, using an injected `today`; verify FAIL.

### Implementation

- [x] T008 [US2] In `database/events.py`, change `get_active_events` to `get_active_events(today: Optional[str] = None)` — `WHERE is_approved = 1 AND (COALESCE(end_iso, start_iso) >= :today OR start_iso IS NULL) ORDER BY start_iso ASC`, `today` defaulting to `datetime.date.today().isoformat()`; keep returning `EventDTO` (R-DATA-8).
- [x] T009 [US2] In `services/event_service.py`, forward the optional `today` param in `get_active_events(today=None)`.

**Checkpoint**: BUG-2 tests green; `get_active_events()` no-arg call sites unaffected.

- [x] T010 **HARD STOP**: Report BUG-2 completion to Шэф in Russian and AWAIT EXPLICIT APPROVAL before Chunk C. (R-PROC-2)

---

## Phase 4: User Story 3 — Non-text input never crashes (Priority: P2) · BUG-3

**Goal**: A non-text message in any of the 5 awaiting states yields a graceful "введите текст"
prompt, no crash, state preserved.

**Independent Test**: `tests/test_handlers/test_fsm_nontext_guard.py` drives each handler with `text=None`.

### Tests (write FIRST, verify FAIL)

- [x] T011 [US3] Create `tests/test_handlers/test_fsm_nontext_guard.py` — for each of the 5 handlers (moderator rename, moderator direct-access, common search, events editing-title, events editing-dates), send a `text=None` message (via `create_context(text=None)`) and assert a graceful `show_temp_message` response with no exception; verify FAIL.

### Implementation

- [x] T012 [P] [US3] In `handlers/moderator.py`, add `if not message.text: return await UIService.show_temp_message(...)` before `.strip()` in the topic-rename handler (~L99) and the direct-access-user-search handler (~L220).
- [x] T013 [P] [US3] In `handlers/common.py`, add the same guard before `.strip()` in the search-query handler (~L170).
- [x] T014 [US3] In `handlers/events.py`, add the same guard before `.strip()` in `process_editing_title` (~L328) and `process_editing_dates` (~L346).

**Checkpoint**: BUG-3 tests green. (No gate yet — Chunk C continues into BUG-5.)

---

## Phase 5: User Story 5 — Request resolved exactly once (Priority: P2) · BUG-5

**Goal**: Atomic compare-and-swap on request resolution; side effects + notification fire only
for the winning transition.

**Independent Test**: `tests/test_services/test_audit_cas.py` simulates a double-resolve and an already-resolved re-resolve.

### Tests (write FIRST, verify FAIL)

- [x] T015 [US5] Create `tests/test_services/test_audit_cas.py` — with one pending request: (a) two `resolve_request` attempts → exactly one side effect + one notification, second returns `(False, "…уже была обработана…")`; (b) re-resolving an already-resolved request is a no-op; (c) [C1, spec BUG-5 edge case] request deleted/cancelled after the initial read but before the CAS → `resolve_audit_request` returns `False` (`rowcount==0`), zero side effects, zero notification (fail-closed); verify FAIL.

### Implementation

- [x] T016 [US5] In `database/audit.py`, change `resolve_audit_request` to `UPDATE ... WHERE id=? AND status='pending'` and return `cursor.rowcount > 0` (atomic CAS) per contracts/internal-signatures.md.
- [x] T017 [US5] In `services/management_service.py::resolve_request`, read the request first, then gate ALL side effects (approve / add participant / delete draft) and the single notification on the CAS boolean returned by `db.resolve_audit_request`; keep the friendly pre-check as fast-fail.

**Checkpoint**: BUG-3 AND BUG-5 tests green (Chunk C complete).

- [x] T018 **HARD STOP**: Report BUG-3 + BUG-5 completion to Шэф in Russian and AWAIT EXPLICIT APPROVAL before Chunk D. (R-PROC-2)

---

## Phase 6: User Story 4 — Leave is remove-only (Priority: P3) · BUG-4

**Goal**: "Leave" can only remove participation, never enroll a non-participant (no audit bypass).

**Independent Test**: `tests/test_services/test_participation_guard.py` — non-participant leave creates nothing; participant leave removes.

### Tests (write FIRST, verify FAIL)

- [x] T019 [US4] In `tests/test_services/test_participation_guard.py`, add: non-participant `leave_event_action` → no participation row, `(False, …)`; participant → removed, `(True, …)`; verify FAIL.

### Implementation

- [x] T020 [US4] Implement `ManagementService.leave_event_action(event_id, user_id) -> tuple[bool, str]` (remove-only) in `services/management_service.py` per contracts/internal-signatures.md.
- [x] T021 [US4] In `handlers/events.py::leave_event`, replace `toggle_event_participation(...)` with `leave_event_action(...)`; keep announcement refresh + `callback.answer(msg)` unchanged.

**Checkpoint**: BUG-4 tests green. (No gate yet — Tail cleanup completes Chunk D.)

---

## Phase 7: Polish & Tail (Cross-cutting cleanup)

**Purpose**: Dead-code removal, anonymous-sender guard, full-suite verification, docs flag.

- [x] T022 [P] In `services/ui_service.py`, remove the two evaluated-and-discarded ternary expressions in `show_temp_message` (~L115-116).
- [x] T022a [C2] Repro (write FIRST, verify FAIL) in `tests/test_journeys/test_middleware_pipeline_journey.py` — a group `Message` with `from_user=None` (channel/anonymous post) passed through `AccessGuardMiddleware` must NOT raise `AttributeError` and must pass through to the handler; verify it FAILS on current `event.from_user.id` access.
- [x] T023 [P] [C2] In `middlewares/access_check.py::AccessGuardMiddleware`, guard the sender: `if event.from_user is None or event.chat.type == "private" or event.from_user.id == event.bot.id: return await handler(event, data)` (~L68) — makes T022a pass.
- [x] T024 Run full suite `.\venv\Scripts\python.exe -m pytest -q` — all green (R-TEST-4); run quickstart.md per-bug commands.
- [x] T025 Flag Route C docs sync: update `CHANGELOG.md` for feature 007 via `tenirtoo-docs-update` CMD-4 (R-PROC-6). No git ops here (Route C rule).
- [x] T026 **HARD STOP**: Report full feature-007 completion to Шэф in Russian (all 5 bugs + tail, suite green) and AWAIT EXPLICIT APPROVAL before any commit (GW-1; push only on explicit request, R-PROC-5). (R-PROC-2)
- [x] T027 запуск линтера-чеклиста (run checklist-linter): `$env:PYTHONIOENCODING="utf-8"; .\venv\Scripts\python.exe local_scripts/prompt_linter.py --dir specs/007-bot-correctness --stage checklist` — must report "Checklist is valid." (R-PROC-4)

---

## Dependencies & Execution Order

### Phase / chunk order (matches plan.md)

- **Setup (T001)**: baseline, no dependencies.
- **Chunk A / US1 (T002–T006)**: after Setup. → HARD STOP.
- **Chunk B / US2 (T007–T010)**: after A approval. → HARD STOP.
- **Chunk C / US3+US5 (T011–T018)**: after B approval. → HARD STOP.
- **Chunk D / US4+Tail (T019–T026)**: after C approval. → HARD STOP (final, T026); then T027 runs the checklist-linter completion gate.

### Within each story

- Repro test(s) MUST be written and verified FAILING before the fix (R-PROC-3).
- BUG-1: T004 (helper) before T005 (handler uses it).
- BUG-2: T008 (db) before T009 (service passthrough).
- BUG-5: T016 (db CAS) before T017 (service gating).
- BUG-4: T020 (service method) before T021 (handler repoint).

### Cross-file note

BUG-1 (T005) and BUG-3 (T014) both edit `handlers/events.py` editing handlers, but in different
phases and non-overlapping lines — T005 rewrites the range-split body, T014 adds the None-guard
at the top. Sequential order (US1 before US3) avoids conflict.

## Parallel Opportunities

- T002 ‖ T003 (different test files, US1).
- T012 ‖ T013 (moderator.py ‖ common.py, US3).
- T022 ‖ T023 (ui_service.py ‖ access_check.py, tail).

## Implementation Strategy

- **MVP** = Chunk A (US1 / BUG-1): stops the persistent data corruption — highest value alone.
- Then B → C → D incrementally; each chunk is independently testable and ends at a HARD-STOP for
  Шэф's approval before the next.

## Notes

- [P] = different files, no dependency.
- Verify every repro test FAILS before implementing its fix.
- Mock assertions check both `args` and `kwargs` (R-TEST-3).
- No `state.clear()`, no direct UI calls, no `db` import in handlers introduced.
