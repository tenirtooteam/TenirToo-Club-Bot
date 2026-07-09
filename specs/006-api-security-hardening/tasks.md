---

description: "Task list — API Security Hardening (Phase 1)"
---

# Tasks: API Security Hardening (Phase 1)

**Input**: Design documents from `specs/006-api-security-hardening/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/interfaces.md, quickstart.md

**Tests**: REQUIRED. This project is Test-First (`R-PROC-3`, `R-TEST-1/2/3`, spec FR-012) - every defect gets a failing reproducing test before its fix. All tests use `conftest.py` fixtures, isolated `db_setup`, and `mock_bot`; no hardcoded entity IDs; frozen-model patching for aiogram (`R-TEST-2`).

**Organization**: Grouped by user story (US1-US4) in spec priority order. Each story is an independent, testable increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1-US4 (setup/foundational/polish carry no story label)

## Approval Gates (R-PROC-2 - MANDATORY)

Execution is chunked into groups of 3-5 tasks. Every chunk boundary ends with a **HARD STOP**. `/speckit-implement` MUST NOT proceed past an unchecked HARD-STOP task - it stops, reports in Russian to Шэф, and awaits explicit approval.

## Checklist-linter note

The checklist stage of `local_scripts/prompt_linter.py` is a COMPLETION gate: it passes only when every item is `[x]` and the final item is "run checklist-linter". During `/speckit-implement`, flip each task to `[x]` as it is finished; run the gate at the end. Invoke it UTF-8-safe to avoid the cp1251 print bug:

~~~
$env:PYTHONIOENCODING="utf-8"; .\venv\Scripts\python.exe local_scripts/prompt_linter.py --dir specs/006-api-security-hardening --stage checklist
~~~

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Test scaffolding shared by the web-facing stories.

- [x] T001 [P] Create web test package `tests/test_web/__init__.py` (new dir; `tests/test_services/`, `tests/test_journeys/` already exist)
- [x] T002 [P] Confirm reusable fixtures in `tests/conftest.py` (`db_setup`, `mock_bot`) and note the `BOT_TOKEN` used for signing WebApp init-data in tests; do not add real network or write to `bot.db` (`R-TEST-1/2`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The four defects are independent; no cross-story blocking logic exists. This phase only certifies the baseline before changes.

- [x] T003 Capture baseline: run `.\venv\Scripts\python.exe -m pytest -q` and record current green count (126 passed, 0 failed at implement time — semgrep green with Docker up) so regressions are detectable (`R-TEST-4`)

**Checkpoint**: Baseline known - user story implementation can begin.

- [x] T004 **HARD STOP**: Report progress to Шэф in Russian - baseline captured, setup done - and AWAIT EXPLICIT APPROVAL before starting User Story 1. (R-PROC-2)

---

## Phase 3: User Story 1 - Unified direct-join guard (Priority: P1) MVP

**Goal**: One service-layer guard enforces "event approved + (topic access when a topic context exists)" for every direct-join path (web dashboard, web announcement, bot announcement); joining a pending event or a topic-restricted announcement without access is denied.

**Independent Test**: A valid member joining a pending event via `POST /api/dashboard/events/{id}/toggle` is denied with no participant row; a member without topic access joining via announcement is denied; an authorized member on an approved event still joins (parity, SC-003).

### Tests for User Story 1 (write FIRST, ensure they FAIL)

- [x] T005 [P] [US1] Unit test `EventService.check_direct_join_allowed` in `tests/test_services/test_participation_guard.py`: pending event -> `(False, ...)`; approved + no topic ctx -> `(True, "")`; approved + topic ctx without access -> `(False, ...)`; approved + topic ctx with access -> `(True, "")` (use IDs returned by creation, `R-TEST-3`)
- [x] T006 [P] [US1] Web test in `tests/test_web/test_dashboard_participation.py`: member toggles a PENDING event -> HTTP 403, no `event_participants` row; authorized member + approved -> 200 toggled
- [x] T007 [P] [US1] Journey test in `tests/test_journeys/test_announcement_join_guard.py`: `ann_join` on an UNAPPROVED event -> deny alert, no mutation (approval now enforced), asserting `callback.answer` args+kwargs; member without topic access -> deny (negative path, `R-TEST-3`)

### Implementation for User Story 1

- [x] T008 [US1] Add `check_direct_join_allowed(user_id, event_id, topic_id: Optional[int]) -> tuple[bool, str]` to `services/event_service.py` per data-model.md (event exists and approved; if `topic_id` given -> `PermissionService.can_user_write_in_topic`); makes T005 green (`R-DATA-1`, reuses Default-Deny gate `R-DB-1`)

- [x] T009 [US1] **HARD STOP**: Report to Шэф in Russian - US1 tests written and failing, guard implemented (unit green, journey/web still red pending wiring) - and AWAIT APPROVAL before wiring call sites. (R-PROC-2)

- [x] T010 [US1] Gate `web/routers/dashboard.py::toggle_event_participation_direct` with `EventService.check_direct_join_allowed(user_id, event_id, topic_id=None)` before mutation; deny -> `logger.warning` (user_id/event_id/reason, FR-011) + `HTTPException(403, reason)`, no mutation; authorized path unchanged; makes T006 green
- [x] T011 [P] [US1] Replace the inline access check in `web/routers/announcements.py::toggle_participation` with `EventService.check_direct_join_allowed(user_id, target_id, topic_id=ann.topic_id)` (adds approval enforcement); deny -> `logger.warning` (FR-011) + 403, no mutation
- [x] T012 [P] [US1] Gate `handlers/announcements.py::ann_join` direct join through `EventService.check_direct_join_allowed(user_id, target_id, topic_id=topic_id)`; deny -> `logger.warning` (FR-011) + `callback.answer(reason, show_alert=True)`, no mutation; makes T007 green (bot-card `event_join` audit path stays untouched)
- [x] T013 [US1] Run `.\venv\Scripts\python.exe -m pytest tests/test_services/test_participation_guard.py tests/test_web/test_dashboard_participation.py tests/test_journeys/test_announcement_join_guard.py -q` - all green; confirm SC-001/002/003

**Checkpoint**: US1 (MVP) fully functional and independently testable.

- [x] T014 [US1] **HARD STOP**: Report US1 completion to Шэф in Russian and AWAIT APPROVAL before starting User Story 2. (R-PROC-2)

---

## Phase 4: User Story 2 - Session freshness / anti-replay (Priority: P2)

**Goal**: WebApp sessions older than a configurable TTL are rejected; missing/unparseable `auth_date` is rejected; small future clock skew tolerated.

**Independent Test**: Correctly-signed init-data with stale `auth_date` -> rejected (401); fresh -> accepted; missing `auth_date` -> rejected.

### Tests for User Story 2 (write FIRST, ensure they FAIL)

- [x] T015 [P] [US2] Unit test in `tests/test_web/test_auth_freshness.py`: sign init-data with test `BOT_TOKEN`; `auth_date = now-(TTL+60)` -> `validate_webapp_init_data` returns `None`; `auth_date = now` -> dict; missing `auth_date` -> `None`; `auth_date = now+600` (beyond skew) -> `None` (`R-SEC-1`)

### Implementation for User Story 2

- [x] T016 [US2] Add `WEBAPP_SESSION_TTL_SECONDS = int(os.getenv("WEBAPP_SESSION_TTL_SECONDS", "86400"))` to `config.py` (`<=0` disables check)
- [x] T017 [US2] In `web/auth.py::validate_webapp_init_data`, after HMAC passes, enforce `auth_date` freshness: missing/unparseable -> `None`; `now-auth_date > TTL` (TTL>0) -> `None`; `auth_date-now > 300` (module-level skew const) -> `None`; makes T015 green
- [x] T018 [US2] Run `.\venv\Scripts\python.exe -m pytest tests/test_web/test_auth_freshness.py -q` - green; confirm SC-004

**Checkpoint**: US1 + US2 both work independently.

- [x] T019 [US2] **HARD STOP**: Report US2 completion to Шэф in Russian and AWAIT APPROVAL before starting User Story 3. (R-PROC-2)

---

## Phase 5: User Story 3 - Correct global error handler (Priority: P2)

**Goal**: Any unhandled web exception returns a proper HTTP 500 JSON response; the handler never raises again.

**Independent Test**: A route patched to raise -> client gets 500 JSON `{"detail": "Internal Server Error"}`, error logged, no secondary failure.

### Tests for User Story 3 (write FIRST, ensure they FAIL)

- [x] T020 [P] [US3] Web test in `tests/test_web/test_error_handler.py`: mount/patch a route to raise `Exception` -> response status 500 with JSON body; assert handler returns a `Response` (no re-raise) and `logger.error` fired with `exc_info`

### Implementation for User Story 3

- [x] T021 [US3] Change `web/main.py::global_exception_handler` to `return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})` (import from `starlette.responses`/`fastapi.responses`), keep `logger.error(..., exc_info=True)`; makes T020 green
- [x] T022 [US3] Run `.\venv\Scripts\python.exe -m pytest tests/test_web/test_error_handler.py -q` - green; confirm SC-005

**Checkpoint**: US1-US3 independently functional.

- [x] T023 [US3] **HARD STOP**: Report US3 completion to Шэф in Russian and AWAIT APPROVAL before starting User Story 4. (R-PROC-2)

---

## Phase 6: User Story 4 - Callback defense-in-depth (Priority: P3)

**Goal**: Deletion/grant callbacks re-check authority server-side before mutating, using `PermissionService` only (no raw `ADMIN_ID`, `R-ARCH-7`); legitimate admin/moderator paths unchanged.

**Independent Test**: A non-admin triggering `confirm_execution` (`user_del`) performs no deletion; a non-manager triggering `perform_search_pick` `mod_add` grants no role; authorized users still succeed.

### Tests for User Story 4 (write FIRST, ensure they FAIL)

- [x] T024 [P] [US4] Journey test in `tests/test_journeys/test_callback_defense.py`: non-admin -> `confirm_execution` with `confirm_exe_user_del:{id}:0` -> `ManagementService.execute_deletion` NOT called + deny alert (args+kwargs); admin -> executes (regression guard)
- [x] T025 [P] [US4] In the same file: non-manager -> `perform_search_pick` `mod_add`/`dir_add` for a topic -> no role/access granted + deny alert; topic-manager -> succeeds

### Implementation for User Story 4

- [x] T026 [US4] In `handlers/common.py::confirm_execution`, add an action-keyed authority gate before `execute_deletion` per research.md R4: `group_del`/`global_topic_del`/`topic_del`/`user_del`/`role_rev*` -> `PermissionService.is_global_admin`; `mod_topic_del`/`mod_rem` -> `PermissionService.can_manage_topic(user_id, extra_id)`; `event_del` -> `EventService.can_edit_event`; deny -> `callback.answer("Доступ запрещён.", show_alert=True)` + `logger.warning`, no mutation
- [x] T027 [US4] In `handlers/common.py::perform_search_pick`, require `PermissionService.can_manage_topic(user_id, int(s_context))` before `mod_add`/`dir_add`; deny -> deny alert + `logger.warning`, no mutation; makes T024/T025 green
- [x] T028 [US4] Run `.\venv\Scripts\python.exe -m pytest tests/test_journeys/test_callback_defense.py -q` - green; confirm SC-007

**Checkpoint**: All four stories independently functional.

- [x] T029 [US4] **HARD STOP**: Report US4 completion to Шэф in Russian and AWAIT APPROVAL before Polish. (R-PROC-2)

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T030 Run full suite `.\venv\Scripts\python.exe -m pytest -q` - no regressions vs T003 baseline (`R-TEST-4`); pre-existing `test_semgrep_lint` (Docker) failure remains out of scope
- [x] T031 [P] Verify no architecture/lint regressions: `tests/test_services/test_import_lint.py`, `test_ruff_lint.py` green (no new modules/layers added, so no `.ruff.toml`/`.importlinter`/`semgrep-rules.yaml` change expected, `R-PROC-10/11`)
- [x] T032 [P] Flag Route C docs update (deferred): `CHANGELOG.md` (CMD-4, `R-PROC-6`) and check whether `R-SEC-1` text in `RULES.md` should note `auth_date` freshness; do via `tenirtoo-docs-update`, not inline
- [x] T033 Produce `walkthrough.md` (Changes made / What was tested / Validation results, in Russian) for the report-stage linter (`R-PROC-4`)
- [x] T034 **HARD STOP**: Final report to Шэф in Russian - all stories done, suite green - and AWAIT APPROVAL before any commit (GW-1; push only on explicit request, `R-PROC-5`). (R-PROC-2)
- [x] T035 запуск линтера-чеклиста (run checklist-linter): `$env:PYTHONIOENCODING="utf-8"; .\venv\Scripts\python.exe local_scripts/prompt_linter.py --dir specs/006-api-security-hardening --stage checklist` - must report "Checklist is valid."

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no deps.
- **Foundational (Phase 2)**: after Setup; only certifies baseline, blocks nothing logically.
- **US1-US4 (Phases 3-6)**: each depends only on Setup+Foundational; mutually independent, executed in priority order P1, P2, P2, P3.
- **Polish (Phase 7)**: after all stories.

### User Story Dependencies

- **US1 (P1)**: independent. Guard method (T008) is created here and reused by its own wiring tasks.
- **US2 (P2)**: independent (`config.py` + `web/auth.py`).
- **US3 (P2)**: independent (`web/main.py`).
- **US4 (P3)**: independent (`handlers/common.py`).

### Within Each User Story

- Tests written and failing before implementation (`R-PROC-3`).
- Guard/service before endpoint/handler wiring.
- Story verified green before the next story.

### Parallel Opportunities

- Setup: T001, T002 in parallel.
- US1 tests T005/T006/T007 in parallel (different files); wiring T011/T012 in parallel, T010 first as it also proves guard integration.
- US4 tests T024/T025 in parallel.
- Polish T031/T032 in parallel.
- Stories touch disjoint files (US1: services/event_service, web/routers, handlers/announcements; US2: config, web/auth; US3: web/main; US4: handlers/common), so they can be parallelized across developers after Foundational.

---

## Parallel Example: User Story 1

```bash
# Write US1 tests together (all must FAIL first):
Task: "Unit test guard in tests/test_services/test_participation_guard.py"
Task: "Web test in tests/test_web/test_dashboard_participation.py"
Task: "Journey test in tests/test_journeys/test_announcement_join_guard.py"

# After guard + HARD STOP approval, wire the two independent call sites together:
Task: "Wire web/routers/announcements.py toggle"
Task: "Wire handlers/announcements.py ann_join"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 Setup -> Phase 2 Foundational (baseline) -> Phase 3 US1.
2. STOP and validate US1 independently (closes the one exploitable gap, SC-001/002).
3. Deploy/demo if ready.

### Incremental Delivery

US1 (MVP) -> US2 -> US3 -> US4, each an independently testable, non-breaking increment, with a HARD-STOP approval gate between every story.

---

## Notes

- [P] = different files, no incomplete-task dependency.
- Every story ends in a HARD-STOP gate (`R-PROC-2`); executor never self-continues past one.
- No DB schema change; no new module/layer, so no linter-config churn.
- Commit only at milestones on explicit approval; never auto-push (`R-PROC-5`).
