---
description: "Task list for feature 014 — backend unification (single-point participation orchestration)"
---

# Tasks: Single-point orchestration of participation change (backend unification)

**Input**: Design documents from `specs/014-backend-unification/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: REQUIRED here — this is a refactor of a guarded write-path, so R-PROC-3
(characterization-first, then failing reproducing tests) governs every phase. Tests are
format-agnostic: drive the real producer (endpoint fn / handler), never assert hard-coded wire
strings.

**Organization**: The unified method is the shared blocking core (Phase 2, Foundational). The
three spec user stories layer assurance on top of it: US1 wires every surface through the
method (MVP), US2 hardens explicit intent and locks the No.7 fix, US3 locks change-gating and
delivery-failure isolation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete-task dependency)
- **[Story]**: US1 / US2 / US3 (Setup, Foundational, Polish carry no story label)
- Exact file paths are in each task.

## Approval Gates (R-PROC-2 — MANDATORY)

Every chunk boundary ends with a HARD-STOP gate. `/speckit-implement` MUST NOT proceed past an
unchecked HARD-STOP; it stops, reports in Russian, and awaits explicit approval.

---

## Phase 1: Setup

**Purpose**: Confirm the test ground before touching the guarded write-path.

- [x] T001 Confirm per-test isolation for participation + announcement state: verify existing
  conftest fixtures give each test a fresh DB and reset service caches (registration, sheets);
  add a reset fixture only if a real gap is found. Files: `tests/conftest.py`,
  `tests/test_web/conftest.py` (if present). (R-TEST-1)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Lock current behavior, then build the one method every surface will call.

**CRITICAL**: No callsite migration (US1+) may begin until T006 is done and its unit tests are
green.

- [x] T002 [P] Characterization test — dashboard toggle endpoint: assert the CURRENT
  consequence set for join and for leave (participant state change; whether
  `refresh_announcements` fired; whether `notify_organizers_of_direct_join` fired). Encode the
  present gap (dashboard leave fires no refresh) as the baseline. Green against current code.
  File: `tests/test_web/test_dashboard_participation.py`. (R-PROC-3, R-TEST-3)
- [x] T003 [P] Characterization test — announcement toggle endpoint: assert CURRENT behavior
  incl. the single-copy refresh gap (only the clicked announcement message is edited). Green
  against current code. File: `tests/test_web/test_announcement_participation.py` [NEW].
  (R-PROC-3)
- [x] T004 [P] Characterization test — bot `ann_join` and `leave_event` handlers: assert
  CURRENT consequence set (guard, mutation, refresh-all, notify-on-join). Green against current
  code. File: `tests/test_journeys/test_participation_parity_journey.py` [NEW] (baseline
  section). (R-PROC-3)
- [x] T005 [P] Unit tests for `EventService.apply_participation_change`, written FIRST and
  FAILING: join changes state (add + notify-once + refresh-all + success); join no-op (no
  notify, no refresh); leave changes state (remove + refresh-all + no notify); leave no-op is
  NOT a join (No.7 core); refresh targets all announcement copies; outcome classification is
  structural not message-text (INV-5); unknown intent returns (False, refusal) with no
  side-effects; a raising `refresh_announcements` does not roll back the mutation nor flip
  success (INV-6). File: `tests/test_services/test_participation_orchestration.py` [NEW].
  (R-PROC-3, R-TEST-3)
- [x] T006 Implement `EventService.apply_participation_change(bot, event_id, user_id, intent)`
  in `services/event_service.py` (no `topic_id` param — guard stays caller-side, D1/I1):
  lazy-import `ManagementService` and
  `AnnouncementService` inside the method (D6); structural before/after `is_event_participant`
  change detection (D3); delegate mutation to `add_event_participation_action` (join) /
  `leave_event_action` (leave) (D4/D5); on change fire join-only
  `notify_organizers_of_direct_join` then `refresh_announcements(bot, "event", event_id)`
  (all copies); return `(success, message)`; unknown intent -> `(False, refusal)`. T005 goes
  green. (R-DATA-1, R-ARCH-4, R-DATA-11, R-SEC-3)

**Checkpoint**: The single orchestration method exists, unit-tested; characterization baselines
are green and protect the refactor.

- [x] T006a **HARD STOP**: Report progress to the user (Шэф) in Russian — метод создан,
  характеризация зелёная, юнит-тесты метода зелёные — и AWAIT EXPLICIT APPROVAL before starting
  User Story 1 (миграция четырёх callsite). (R-PROC-2)

---

## Phase 3: User Story 1 - Same consequences from any surface (Priority: P1) [MVP]

**Goal**: Route all four participation surfaces through `apply_participation_change` so join
and leave yield one identical, complete consequence set everywhere.

**Independent Test**: Drive join then leave through each surface; the consequence set
(participant state, refresh of every announcement copy, join-only organizer notify) is
identical and complete. Fixes the dashboard-leave-no-refresh and announcement-single-copy
drift.

- [x] T007 [P] [US1] Migrate dashboard toggle endpoint to a thin call: accept an explicit
  `action` ("join"/"leave"), keep the `check_direct_join_allowed` guard, call
  `apply_participation_change(bot, event_id, user_id, action)`, keep the
  `{success, message}` response shape. Evolve the T002 characterization into a parity test
  (leave now refreshes). File: `web/routers/dashboard.py` (C2). (R-SEC-3, R-DATA-1)
- [x] T008 [P] [US1] Migrate announcement toggle endpoint to a thin call and DELETE the
  hand-rolled single-message `edit_message_text` block; keep the guard (still uses
  `topic_id`); call `apply_participation_change(bot, target_id, user_id, action)`. Evolve T003
  into a parity test (all copies refresh). File: `web/routers/announcements.py` (C3). (R-SEC-3, R-DATA-1)
- [x] T009 [P] [US1] Migrate bot `ann_join` handler: map action code 1 -> "join", 0 ->
  "leave", call `apply_participation_change`; remove the handler's direct `refresh_announcements`
  and `notify_organizers_of_direct_join` calls (they now live in the method). File:
  `handlers/announcements.py` (C4). (R-DATA-1)
- [x] T010 [P] [US1] Migrate bot `leave_event` handler: keep the admin/creator pending-event
  guard, call `apply_participation_change(callback.bot, event_id, user_id, "leave")`; remove
  the direct `refresh_announcements` call. File: `handlers/events.py` (C5). (R-DATA-1)

- [x] T010a **HARD STOP**: Report progress to the user (Шэф) in Russian — четыре backend
  callsite переведены на единый метод — и AWAIT EXPLICIT APPROVAL before the frontend wiring
  and parity test. (R-PROC-2)

- [x] T011 [US1] Frontend: `toggleParticipation` derives intent from the known
  `is_participant` state and sends `action` on the existing POST to the same `/toggle` path; no
  business logic in JS (server stays sole authority). File: `web/frontend/app.js` (C6).
  (R-SEC-3)
- [x] T012 [US1] Cross-surface parity journey test: for one approved event, run join then leave
  through all four surfaces (dashboard endpoint, announcement endpoint, `ann_join`,
  `leave_event`) and assert the consequence set is identical and complete (participant state;
  `refresh_announcements` on every change; organizer notify on join only). File:
  `tests/test_journeys/test_participation_parity_journey.py`. (SC-001, SC-002, SC-003)

**Checkpoint**: Every surface routes through the one method; parity test green. This is the MVP.

- [x] T012a **HARD STOP**: Report progress to the user (Шэф) in Russian — все поверхности
  унифицированы, паритет-тест зелёный (MVP) — и AWAIT EXPLICIT APPROVAL before User Story 2.
  (R-PROC-2)

---

## Phase 4: User Story 2 - Explicit intent, no silent join (Priority: P2)

**Goal**: Make explicit intent mandatory and lock the No.7 fix so a stale button can never
silently join a non-participant, and a legacy-format action is refused rather than guessed.

**Independent Test**: A "leave" for a non-participant on any web surface is a safe no-op (no
add, no notify); a missing/invalid action is refused (400 on web, polite alert on bot), never
toggled.

- [x] T013 [US2] Remove the legacy toggle fallback in bot `ann_join`: an unrecognized/absent
  action code returns a polite `callback.answer` refusal with no mutation and no side-effects.
  File: `handlers/announcements.py` (D8, FR-011).
- [x] T014 [US2] Web endpoints reject a missing/invalid `action` with a 400 and an informative
  message; no toggle fallback remains. Files: `web/routers/dashboard.py`,
  `web/routers/announcements.py` (FR-011).
- [x] T015 [P] [US2] Tests locking No.7 and refusal: leave-of-non-participant on both web
  endpoints changes nothing and notifies no one; unknown/absent action yields 400 (web) and
  polite refusal (bot), all with no mutation. Add the guard-deny negative (C2): on a denied
  guard (pending event / no topic access) assert neither `refresh_announcements` nor
  `notify_organizers_of_direct_join` is called (zero consequences on deny, FR-006). Files:
  `tests/test_web/test_dashboard_participation.py`,
  `tests/test_web/test_announcement_participation.py`,
  `tests/test_journeys/test_participation_parity_journey.py`. (FR-004, FR-005, FR-006, FR-011)

**Checkpoint**: Intent is mandatory everywhere; the silent-join path is closed and tested.

- [x] T015a **HARD STOP**: Report progress to the user (Шэф) in Russian — явное намерение
  обязательно, тихая запись закрыта и покрыта тестами — и AWAIT EXPLICIT APPROVAL before User
  Story 3. (R-PROC-2)

---

## Phase 5: User Story 3 - Consequences only on real change; failures do not roll back (Priority: P3)

**Goal**: Lock that side-effects fire only on an actual state change, and that a Telegram
delivery failure never rolls back the committed mutation nor turns success into an error.

**Independent Test**: A no-op action (repeat join, leave-of-non-participant) fires neither
notify nor refresh; a raising refresh leaves the mutation persisted and success intact.

- [x] T016 [US3] Tests: no-op paths across surfaces fire no notify and no refresh; a
  side-effect failure (`refresh_announcements` raising) leaves the participant change persisted,
  keeps `success` reflecting end state, and raises nothing to the caller. Files:
  `tests/test_services/test_participation_orchestration.py`,
  `tests/test_journeys/test_participation_parity_journey.py`. (FR-007, FR-008)
- [x] T017 [US3] Update `test_tma_bridge_journey.py` to the new endpoint signature (pass
  `action`) and assert refresh-all behavior. File: `tests/test_journeys/test_tma_bridge_journey.py`.
  (SC-005)

**Checkpoint**: Change-gating and failure-isolation are locked; all three stories independently
verified.

- [x] T017a **HARD STOP**: Report progress to the user (Шэф) in Russian — гарантии US3
  зафиксированы тестами — и AWAIT EXPLICIT APPROVAL before Polish. (R-PROC-2)

---

## Phase 6: Polish & Cross-Cutting

**Purpose**: Green gates, docs sync, final completion gate.

- [x] T018 [P] Run the full suite and static gates green: `venv\Scripts\python.exe -m pytest`;
  `venv\Scripts\lint-imports.exe`; ruff; the semgrep lint tests
  (`tests/test_services/test_{import,ruff,semgrep}_lint.py`); governance
  (`tests/test_governance.py`, `tests/test_knowledge_bundle.py`). (SC-005, R-ARCH-4)
- [x] T019 Route C docs-update: add the CHANGELOG.md entry (CMD-4) and, if the service registry
  or documented behavior changed, refresh the knowledge bundle (`docs/knowledge/`) for the new
  orchestration method. No git operations in this task. (Route C)

- [x] T019a **HARD STOP**: Report progress to the user (Шэф) in Russian — гейты зелёные, доки
  обновлены — и AWAIT EXPLICIT APPROVAL before the final checklist gate and GW-1 commit.
  (R-PROC-2)

- [x] T020 Run checklist-linter (the checklist-stage prompt-linter) over
  `specs/014-backend-unification`
  (`venv\Scripts\python.exe local_scripts/prompt_linter.py --dir specs/014-backend-unification
  --stage checklist`): keep every task line ASCII-safe (no arrows or emoji glyphs) and ensure
  all task checkboxes are lowercase `[x]` before running. This is the R-PROC-4 completion gate
  and the final task. GW-1 local commit follows only on explicit approval (push needs a separate
  explicit request, R-PROC-5).

---

## Dependencies & Execution Order

### Phase order

- Setup (P1) -> Foundational (P2, blocks everything) -> US1 (P3) -> US2 (P4) -> US3 (P5) ->
  Polish (P6).
- Foundational T006 (the method) blocks all callsite migrations. Characterization T002-T004
  must be green BEFORE T006 changes anything.

### Within stories

- US1: T007-T010 (backend migrations) are mutually independent [P] but all depend on T006;
  T011 (frontend) and T012 (parity) come after the migrations they exercise.
- US2 depends on US1 (it hardens the migrated callsites).
- US3 depends on US1 (it locks the method's behavior as exercised through the surfaces).

### Parallel opportunities

- T002, T003, T004, T005 (all different new/existing test files) run in parallel.
- T007, T008, T009, T010 (four different source files) run in parallel once T006 is done.

---

## Implementation Strategy

- **MVP = Setup + Foundational + US1**: after T012 every surface is unified and the parity test
  passes; the two drift defects (dashboard-leave-no-refresh, announcement-single-copy) are gone.
- **US2** then closes the silent-join path and makes intent mandatory.
- **US3** locks change-gating and failure isolation.
- Commit at milestones per GW-1 (explicit approval); push only on explicit request (R-PROC-5).

## Notes

- [P] = different files, no incomplete-task dependency.
- Characterization tests are format-agnostic — driven through the real producer, no hard-coded
  wire strings (so a later format change does not force test edits).
- No schema change; no new module; no framework/bundler added (R-PROC-7).
- Keep task lines ASCII-safe for the checklist-stage linter (cp1251 console).
