---
description: "Task list for feature 015 — TMA event authoring + frontend modularization"
---

# Tasks: TMA event authoring + frontend modularization

**Input**: Design documents from `specs/015-tma-event-authoring/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: REQUESTED — the feature is test-first (R-PROC-3 / R-TEST-3). New endpoints ship with
Level-A tests written and failing before implementation.

**Organization**: Phases map to the plan's execution chunks (A1/A2/B1/B2/C/D). Every task carries
its user-story label for traceability. Each chunk ends with a HARD-STOP approval gate (R-PROC-2).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1 create, US2 edit, US3 modular frontend, US4 design system
- Exact file paths are included in each task

## User-story map

- **US1 (P1)**: Create event in the Mini App (backend POST + create form).
- **US2 (P1)**: Edit event with authority-parity (backend PUT + edit form).
- **US3 (P1)**: Modular ES-module frontend, escape-by-default render, `?ann_id=` entry preserved.
- **US4 (P2)**: Design system v2 "Alpine night to dawn".

## Path Conventions

Single project. Backend: `web/routers/`, `web/main.py`, `services/` (reused). Frontend:
`web/frontend/` and new `web/frontend/js/`. Tests: `tests/test_web/`. venv-only execution
(`.\venv\Scripts\python.exe ...`, R-PROC-7).

---

## Phase 1: Setup and Foundational Tests (Chunk A1)

**Purpose**: Establish a green baseline and write the failing endpoint tests before any backend code.

- [x] T001 Run the full suite and record the baseline green count: `.\venv\Scripts\python.exe -m pytest -q` (quickstart prerequisite)
- [x] T002 Sanity-boot the Level-B stand `local_scripts/tma_audit_server.py` (port 8100) and confirm the current frontend serves and prints per-persona URLs
- [x] T003 [P] [US1] Write the failing create test `tests/test_web/test_events_create.py` (positive create via `web_call`+`forge_init_data`; empty-title 400 negative; unrecognized-date returns success with `date_recognized` false) per contracts/events-api.md
- [x] T004 [P] [US2] Write the failing edit test `tests/test_web/test_events_edit.py` (creator-non-admin positive; unrelated-user 403; missing-event 404) — asserts authority-parity per contracts/events-api.md
- [x] T005 [P] [US3] Write the failing server-contract test `tests/test_web/test_frontend_contract.py`: announcement-by-id returns the DTO so the `?ann_id=` target survives; a markup title read back via `GET /api/dashboard/events/{id}` returns the raw human-readable characters (un-escaped, not `&lt;b&gt;`, canonical form per A1); and `can_edit` is true for the creator and false for an unrelated user (D7/U1)
- [x] T005a **HARD STOP**: Report progress to the user (Шэф) in Russian — the three test modules are written and failing (no endpoints yet) — and AWAIT EXPLICIT APPROVAL before implementing the backend. Do not continue on your own judgment. (R-PROC-2)

---

## Phase 2: Backend authoring endpoints (Chunk A2)

**Goal**: The create and edit endpoints exist as thin adapters over existing sanitizing mutations,
turning the Chunk-A1 tests green. Serves US1 and US2.

**Independent Test**: `tests/test_web/test_events_create.py` and `test_events_edit.py` pass; the
full suite stays green.

- [x] T006 [US1] Create `web/routers/events.py` with `POST /api/events` (session-only, `Depends(get_current_user_id)`): parse `date_text`/`end_date_text` via `DateService.parse_smart_date` and `split_human_range`, call `ManagementService.create_event_action(...)`, then on `event_id > 0` call `ManagementService.submit_request(user_id, "event_approval", event_id)` and `EventService.notify_admins_for_approval(bot, event_id)`; return the DTO with structural `success` and `date_recognized`; mount the router in `web/main.py` via `app.include_router(events.router, prefix="/api/events", tags=["Events"])`
- [x] T007 [US2] Add `PUT /api/events/{event_id}` to `web/routers/events.py`: re-check `EventService.can_edit_event(user_id, event_id)` server-side (403 on failure, 404 if absent), parse dates, call `ManagementService.update_event_details(...)`; no approval re-notification (edit parity); return the DTO
- [x] T008 [US1] [US2] [US3] Add a web-layer display serialization helper that un-escapes stored display strings for JSON output (D3, no change to `ManagementService`) and apply it to the reused readers `web/routers/dashboard.py` (`/events`, `/events/{id}`) and `web/routers/announcements.py` (`/{ann_id}`); additionally add a server-computed `can_edit` field to the `GET /api/dashboard/events/{id}` response via `EventService.can_edit_event(user_id, event_id)` (D7/U1) — response shape only, no query/logic change
- [x] T009 [US1] [US2] Run `.\venv\Scripts\python.exe -m pytest tests\test_web -q` then the full suite; confirm the new endpoint tests plus the reused-reader changes (D3 display-serialization + `can_edit`) are green and no existing dashboard/announcements test regressed (assertions check both `args` and `kwargs` on mocked bot calls, R-TEST-3)
- [ ] T009a **HARD STOP**: Report progress to the user (Шэф) in Russian — backend authoring endpoints complete and green — and AWAIT EXPLICIT APPROVAL before starting the frontend modularization. (R-PROC-2)

---

## Phase 3: Frontend core modules (Chunk B1)

**Goal**: Stand up the module skeleton — escape-by-default render, api wrapper, hash router, and
bootstrap with `?ann_id=` mapping. Serves US3.

**Independent Test**: On the Level-B stand, the app boots via the module entry; `?ann_id=` maps to
the announcement card and no-param maps to the dashboard.

- [x] T010 [US3] Create `web/frontend/js/render.js` — escape-by-default DOM helpers (text setter plus a safe list/template builder); no raw-`innerHTML` path for server or user data (FR-013, contracts/frontend-architecture.md)
- [x] T011 [US3] Create `web/frontend/js/api.js` — fetch wrapper attaching the init-data header, treating `success` structurally, surfacing errors uniformly; no date or business logic
- [x] T012 [US3] Create `web/frontend/js/router.js` — hash route table, exact-key lookup (no substring match), back-history stack plus `tg.BackButton`, unknown-route falls back to dashboard
- [x] T013 [US3] Create `web/frontend/js/main.js` — bootstrap: read `?ann_id=` from `location.search`, route to `#/ann/{id}` when present else `#/dashboard`, Telegram SDK glue (FR-014)
- [x] T013a **HARD STOP**: Report progress to the user (Шэф) in Russian — core frontend modules stood up — and AWAIT EXPLICIT APPROVAL before migrating the read screens. (R-PROC-2)

---

## Phase 4: Screen migration and monolith removal (Chunk B2)

**Goal**: Move the existing read screens into modules 1:1 (behavior-preserving) and delete the
monolith. Serves US3.

**Independent Test**: On the stand, all read screens render the same data as before; navigation is
reload-free; a markup title renders as literal text.

- [x] T014 [P] [US3] Migrate read screens into `web/frontend/js/screens/` (dashboard, events-list, event-card, announcement-card, topics/profile/admin/roles) using `render.js` — same data sources (existing dashboard/announcements GETs); behavior-preserving, consuming the D3-serialized (un-escaped) display fields already applied in Chunk A
- [x] T015 [US3] Update `web/frontend/index.html` to load `<script type="module" src="js/main.js">`, remove the `app.js` script, and delete `web/frontend/app.js`
- [x] T016 [US3] Verify on the Level-B stand: `?ann_id=` entry lands on the card, dashboard is the default, navigation is reload-free, and a title containing markup renders as literal characters; then run the full suite green
- [x] T016a **HARD STOP**: Report progress to the user (Шэф) in Russian — modular frontend live, monolith removed, entry and escape verified — and AWAIT EXPLICIT APPROVAL before building the authoring form. (R-PROC-2)

---

## Phase 5: Authoring form (Chunk C)

**Goal**: The create/edit form screen, wired to the Chunk-A endpoints. Serves US1 and US2.

**Independent Test**: On the stand, a non-admin creator creates and edits an event; an unrelated
persona is refused at submit.

- [x] T017 [US1] Create `web/frontend/js/screens/event-form.js` create mode — fields title / date_text / optional end_date_text, submit `POST /api/events` via `api.js`, show the "won't reach the calendar" hint from `date_recognized`; optional UX hints only, no client-side date business logic
- [x] T018 [US2] Extend `web/frontend/js/screens/event-form.js` edit mode — seed from `GET /api/dashboard/events/{id}`, submit `PUT /api/events/{id}`; surface a server 403 as a polite refusal (no client-side gating)
- [x] T019 [US1] [US2] Wire form routes `#/event/new` and `#/event/{id}/edit` into `web/frontend/js/router.js`; add the create affordance on the events-list screen and the edit affordance on the event-card screen shown only when the event-details DTO reports `can_edit true` (D7/U1)
- [x] T020 [US1] [US2] Verify on the Level-B stand: create flow including the unrecognized-date hint; a rejected submit (empty title) preserves the already-entered form fields (FR-006); the edit control appears only for the creator persona and edit succeeds; an unrelated persona sees no edit control and a direct edit call is refused; then run the full suite green
- [ ] T020a **HARD STOP**: Report progress to the user (Шэф) in Russian — authoring form complete, create and edit verified with authority-parity — and AWAIT EXPLICIT APPROVAL before applying the design system. (R-PROC-2)

---

## Phase 6: Design system v2 (Chunk D)

**Goal**: Apply the approved "Alpine night to dawn" v2 tokens and accessibility affordances. Serves US4.

**Independent Test**: On the stand, authoring and list screens use v2 tokens; a status is
distinguishable by shape (not color alone); a multi-day event shows a date range.

- [ ] T021 [US4] Add design-system v2 tokens (color, typography, radius, spacing custom properties) to `web/frontend/style.css`, sourced from the approved v2 mockup `_nogit_tma_mockup_v2.html` (cross-machine fallback: the published artifact)
- [ ] T022 [US4] Implement status-by-shape markers and the date-range chip in `web/frontend/js/ui/components.js` (FR-018) and use them on list, card, and form screens
- [ ] T023 [US4] Apply v2 tokens across the authoring and list/card screens; verify on the stand that tokens are consistent, statuses are distinguishable by shape, and multi-day events show a range
- [ ] T024 [US4] Update `CHANGELOG.md` for feature 015 via the docs-update CMD-4 command (R-PROC-6)
- [ ] T024a **HARD STOP**: Report progress to the user (Шэф) in Russian — design system applied and changelog updated — and AWAIT EXPLICIT APPROVAL before the polish phase. (R-PROC-2)

---

## Phase 7: Polish and Cross-Cutting Concerns

**Purpose**: Final validation and documentation synchronization across the feature.

- [ ] T025 [P] Run the full quickstart.md validation — the backend test table plus the Level-B browser walkthrough (US1 to US4)
- [ ] T026 Route C docs-update sweep: reflect the new `web/routers/events.py` and the `web/frontend/js/` module set in the module registry (`docs/knowledge/module-registry.md`) via CMD-1/CMD-2; no git operations during Route C
- [ ] T027 Final gate: run checklist-linter `.\venv\Scripts\python.exe local_scripts\prompt_linter.py --dir specs/015-tma-event-authoring --stage checklist` and confirm it passes with every box marked `[x]` (R-PROC-4)

---

## Dependencies and Execution Order

### Chunk order (sequential, each behind a HARD-STOP)

- **A1 (Setup + failing tests)**: no dependency; first.
- **A2 (backend endpoints)**: depends on A1 (tests exist and fail).
- **B1 (frontend core modules)**: depends on A2 (endpoints available for the form later); modules
  themselves need only the read GETs, which already exist.
- **B2 (screen migration)**: depends on B1 (render/api/router/main exist).
- **C (authoring form)**: depends on A2 (endpoints) and B2 (modular frontend + router).
- **D (design system)**: depends on C (screens exist to style).
- **Polish**: depends on all chunks.

### User-story dependencies

- **US1 create**: backend (A2) then form (C) then styling (D). MVP-critical.
- **US2 edit**: backend (A2) then form (C); authority-parity asserted in A1/A2 tests.
- **US3 modular frontend**: B1 then B2; the enabling architecture for C and for 016/017.
- **US4 design system**: D, layered on the modular screens; independently testable visually.

### Within a chunk

- Tests (A1) are written and confirmed failing before endpoints (A2).
- Core modules (B1) precede screen migration (B2).
- Create mode (T017) precedes edit mode (T018) in the shared form file (same file — not parallel).

### Parallel opportunities

- T003 / T004 / T005 are different test files — parallelizable [P].
- T014 (screen migration) is a self-contained batch [P] once B1 exists.
- T025 (quickstart validation) is [P] against the finished build.
- Within the shared `event-form.js` file, create and edit modes are sequential (same file).

---

## Implementation Strategy

### MVP scope

US1 (create) plus the US3 modular frontend it rides on: chunks A1 -> A2 -> B1 -> B2 -> C (create
mode). This delivers "create an event from the Mini App on a safe, modular frontend" as the first
demonstrable slice. Edit (US2) is completed in the same form (C), and the design system (US4) is an
incremental visual layer on top.

### Incremental delivery

1. A1 + A2: backend authoring endpoints green (no UI yet).
2. B1 + B2: modular frontend live, monolith gone, read screens preserved.
3. C: authoring form — create and edit usable end to end (functional MVP complete).
4. D: design system v2 applied; changelog updated.
5. Polish: quickstart validation, docs sweep, checklist-linter gate.

---

## Notes

- [P] tasks touch different files with no incomplete-task dependency.
- Every chunk ends in a HARD-STOP; `/speckit-implement` must stop and await approval at each and
  must not proceed on its own judgment (R-PROC-2).
- Participation is untouched — it stays on `EventService.apply_participation_change` (feature 014),
  never re-implemented here (FR-016).
- No new mutation logic — endpoints are thin adapters over existing sanitizing service methods
  (R-DATA-1). Dates only via `DateService` (R-CODE-5). Identity only from init-data (R-SEC-1).
- Keep tasks.md ASCII-plus-Cyrillic with em-dash only (no arrows or emoji) so the cp1251
  checklist-linter stage passes; convert any `[X]` to lowercase `[x]` before the gate.
