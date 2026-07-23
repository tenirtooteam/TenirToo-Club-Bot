---
description: "Task list for feature 016 — TMA event moderation + audit-request queue"
---

# Tasks: TMA event moderation + audit-request queue

**Input**: Design documents from `specs/016-tma-event-moderation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: REQUESTED — this feature is test-first (R-PROC-3, Constitution IV). Every backend change
lands its failing test first, verified red before the fix.

**Organization**: Grouped by the plan's execution chunks (A–E). Each chunk is 3–5 tasks with a TDD
sub-step and closes with a **HARD-STOP** approval gate (R-PROC-2). Story labels map tasks to spec.md
user stories (US1 queue, US2 trustworthy resolution, US3 roster, US4 design).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1 / US2 / US3 / US4 (from spec.md)

## Approval Gates (R-PROC-2 — MANDATORY)

`/speckit-implement` MUST NOT proceed past an unchecked **HARD STOP** task. It stops, reports to Шэф
in Russian, and awaits explicit approval.

## Path Conventions

Single project (bot + FastAPI web bridge + vanilla-JS Mini App). Real paths from plan.md are used
verbatim below.

---

## Phase 1: Setup

**Purpose**: Establish a clean, green baseline before any change (Constitution IV, R-TEST-1).

- [x] T001 Confirm baseline: run `.\venv\Scripts\python.exe -m pytest -q` and record the suite green before edits (no code change).

---

## Phase 2: Chunk A — node-3 announcement-truth fix (backend correctness)

**Story**: US2 (trustworthy resolution — announcements stay truthful after a moderated approval).

**Goal**: Approving an `event_participation` request refreshes the event's public announcements and
never emits the false direct-join notice. Blocking correctness: every approval path (bot + future web)
depends on it.

**Independent Test**: `resolve_request(..., "approved")` on a pending participation calls
`refresh_announcements("event", id)` and does NOT call `notify_organizers_of_direct_join`.

- [x] T002 [US2] Write FIRST failing repro `tests/test_services/test_participation_approve_refresh.py`: seed approved event + active announcement + pending `event_participation`; mock `AnnouncementService.refresh_announcements` and `EventService.notify_organizers_of_direct_join`; assert refresh called once with args `("event", event_id)`, direct-join notice NOT called, applicant added, one user notification (R-PROC-3, R-TEST-3).
- [x] T003 [US2] Run the new test; confirm it FAILS today (approval never refreshes).
- [x] T004 [US2] MODIFY `services/management_service.py::resolve_request` approved/`event_participation` branch: after `db.add_event_participant` + sheets sync, add lazy `from services.announcement_service import AnnouncementService` and `await AnnouncementService.refresh_announcements(bot, "event", request["entity_id"])`; do NOT call `notify_organizers_of_direct_join` (R-CODE-6, R-ARCH-4, R-DATA-1).
- [x] T005 [US2] Run `test_participation_approve_refresh` + `test_audit_cas` + full suite; all green.
- [x] T005a **HARD STOP**: Report progress to Шэф in Russian — Chunk A (node-3 fix) done, next is Chunk B (queue data + service) — and AWAIT EXPLICIT APPROVAL. (R-PROC-2)

---

## Phase 3: Chunk B — Queue data + service (backend foundation for the queue)

**Story**: US1 (moderation queue). Foundational reads/predicate the endpoints depend on.

**Goal**: A cross-entity pending listing, an organizer predicate, and a viewer-scoped enriched queue
aggregator — all through the facade, authority in the service.

**Independent Test**: `get_moderation_queue(admin)` returns drafts only; `get_moderation_queue(organizer)`
returns own-event participation only; non-event types excluded; oldest-first order.

- [x] T006 [P] [US1] Add `get_pending_requests() -> List[AuditRequestDTO]` (all pending, `ORDER BY created_at ASC`) in `database/audit.py` (FR-012, R-ARCH-1).
- [x] T007 [US1] Re-export `get_pending_requests` through the `database/db.py` facade (R-ARCH-2) — depends on T006.
- [x] T008 [P] [US1] Add `is_organizer_of_event(user_id, event_id) -> bool` (creator OR lead, from `get_event_details`) in `services/event_service.py` (D2, read-only).
- [x] T009 [US1] Write FIRST failing `tests/test_services/test_moderation_queue_service.py`: scoping (admin↔drafts, organizer↔own participation, foreign items excluded), non-event types excluded, oldest-first ordering (R-PROC-3, R-TEST-3); confirm FAIL (method missing).
- [x] T010 [US1] Implement `ManagementService.get_moderation_queue(user_id)` in `services/management_service.py` (filter to `event_approval`|`event_participation` → authority filter via `is_global_admin`/`is_organizer_of_event` → enrich with `get_entity_name` + requester name, grouping event lookups) (D5, R-DATA-8); confirm T009 green + suite green — depends on T006–T008.
- [x] T010a **HARD STOP**: Report to Шэф in Russian — Chunk B (queue data + service) done, next is Chunk C (router: queue + resolve) — and AWAIT EXPLICIT APPROVAL. (R-PROC-2)

---

## Phase 4: Chunk C — Moderation router: queue + resolve endpoints

**Story**: US1 (queue view) + US2 (authority-parity resolve + exactly-once via web).

**Goal**: `web/routers/moderation.py` exposes the viewer-scoped queue and per-type authorized
resolution, delegating to the existing atomic-CAS `resolve_request`.

**Independent Test**: Level-A `web_call` — admin GET /queue sees drafts not foreign participation;
organizer sees own participation not foreign drafts; non-authorized resolve → 403; already-resolved →
`success:false`; two concurrent approves → exactly one action.

- [x] T011 [US1] Write FIRST Level-A test `tests/test_web/test_moderation_queue.py`: GET `/api/moderation/queue` scoping (admin positive/negative, organizer positive/negative) via `web_call` + `forge_init_data` (R-TEST-2).
- [x] T012 [US2] Write FIRST Level-A test `tests/test_web/test_moderation_resolve.py`: POST resolve authority-parity per type (403 for wrong role), already-resolved → `success:false`, exactly-once via web path (two concurrent approves → one side effect + one notification), **and reject-path semantics (FR-003): reject `event_approval` deletes the draft; reject `event_participation` leaves the roster unchanged** (R-PROC-3, R-TEST-3).
- [x] T013 [US1] Create `web/routers/moderation.py`: GET `/queue` (→ `get_moderation_queue`) and POST `/requests/{request_id}/resolve` (load request → per-type server-side authority: `is_global_admin` for `event_approval`, `is_organizer_of_event` for `event_participation` → `ManagementService.resolve_request`); identity via `get_current_user_id` (R-SEC-1, R-SEC-3, R-ARCH-7, R-ARCH-4).
- [x] T014 [US1] Register the router: export in `web/routers/__init__.py` and `app.include_router(moderation.router, prefix="/api/moderation", tags=["Moderation"])` in `web/main.py`.
- [x] T015 [US1] Run `test_moderation_queue` + `test_moderation_resolve` + full suite; all green.
- [x] T015a **HARD STOP**: Report to Шэф in Russian — Chunk C (queue + resolve endpoints) done, next is Chunk D (roster + participant removal) — and AWAIT EXPLICIT APPROVAL. (R-PROC-2)

---

## Phase 5: Chunk D — Roster view + participant removal

**Story**: US3 (participant management).

**Goal**: Organizers view an event roster and remove a participant through the feature-014 consequence
point (remove-only, announcement refresh).

**Independent Test**: organizer GET participants → roster; non-organizer → 403; DELETE participant →
removed + announcement refreshed; stale remove of a non-participant → no-op (no silent enroll).

- [x] T016 [US3] Write FIRST Level-A test `tests/test_web/test_moderation_participants.py`: roster (organizer positive, non-organizer 403), removal refreshes announcement, stale-remove no-op (BUG-4) (R-PROC-3, R-TEST-3).
- [x] T017 [US3] Add GET `/api/moderation/events/{event_id}/participants` to `web/routers/moderation.py` (`is_organizer_of_event` gate; roster + display names from `get_event_details`; `capacity` presentational) (R-ARCH-7, R-DATA-8).
- [x] T018 [US3] Add DELETE `/api/moderation/events/{event_id}/participants/{user_id}` to `web/routers/moderation.py` (`is_organizer_of_event` gate → `EventService.apply_participation_change(bot, event_id, user_id, intent="leave")`, feature 014) (R-DATA-1, R-SEC-3).
- [x] T019 [US3] Run `test_moderation_participants` + full suite; all green.
- [x] T019a **HARD STOP**: Report to Шэф in Russian — Chunk D (roster + removal) done, next is Chunk E (frontend screens + design v2) — and AWAIT EXPLICIT APPROVAL. (R-PROC-2)

---

## Phase 6: Chunk E — Frontend moderation screens + design v2

**Story**: US1 (queue screen) + US3 (participants screen) + US4 (design system).

**Goal**: Additive moderation screen-modules in the feature-015 architecture (escape-by-default, no
framework/build), design-v2 request card with Approve/Reject and status-by-shape.

**Independent Test**: Level-B stand (port 8100) — queue renders request cards; a markup-bearing title
shows as literal text; status distinguishable by shape; unrelated screen modules untouched.

- [x] T020 [P] [US1] Add `web/frontend/js/screens/moderation-queue.js`: fetch `/api/moderation/queue` via `api.js`, render request cards via `render.js` (escape-by-default), Approve/Reject → POST resolve (structural success), empty-state, paginate/scroll > 7 (FR-014).
- [x] T021 [P] [US3] Add `web/frontend/js/screens/participants.js`: roster view + participant removal (DELETE) **behind an explicit confirm step before the DELETE fires (R-DATA-4; cancel = no roster change)**, escape-by-default names, graceful stale-remove.
- [x] T022 [US1] Wire routing/nav: add moderation routes in `web/frontend/js/router.js`, screen containers in `web/frontend/index.html`, authorized-only nav affordance; leave the 015 `?ann_id=` entry contract untouched (D6/D9).
- [x] T023 [US4] Design v2: add moderation tokens/components in `web/frontend/style.css` + request-card & status-by-shape widgets in `web/frontend/js/ui/components.js`, per the approved v2 mockup (reuse 015 tokens, no redefinition) (FR-015).
- [x] T024 [US1] Verify on the Level-B stand (`local_scripts/tma_audit_server.py`, port 8100): queue renders, markup title is literal text, status-by-shape distinct; run quickstart Scenario 5.
- [x] T024a **HARD STOP**: Report to Шэф in Russian — Chunk E (frontend + design v2) done, next is Polish (full validation, CHANGELOG, docs flag, checklist linter) — and AWAIT EXPLICIT APPROVAL. (R-PROC-2)

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation, changelog, docs flag, and the mandatory checklist gate.

- [x] T025 Run full `quickstart.md` validation (Scenarios 1–5) and `.\venv\Scripts\python.exe -m pytest -q`; confirm the whole suite is green.
- [x] T026 Add a `CHANGELOG.md` entry for feature 016 (moderation queue, node-3 fix, roster) (CMD-4; no git operations).
- [x] T027 [P] Flag Route C docs-update (CMD-2) for the registry additions: `web/routers/moderation.py`, `db.get_pending_requests`, `EventService.is_organizer_of_event`, `ManagementService.get_moderation_queue` (note only; do not run git).
- [x] T028 запуск линтера-чеклиста: run `.\venv\Scripts\python.exe local_scripts/prompt_linter.py --dir specs/016-tma-event-moderation --stage checklist` (with `$env:PYTHONIOENCODING='utf-8'`) and confirm it passes once all tasks above are marked `[x]`.

---

## Dependencies & Execution Order

### Chunk order (sequential — each ends in a HARD STOP)

1. **Setup (Phase 1)** → **Chunk A (Phase 2)**: node-3 correctness lands before any moderation UI exposes approval.
2. **Chunk B (Phase 3)**: queue data + service — depends on nothing in A but is grouped after it per plan order.
3. **Chunk C (Phase 4)**: router queue + resolve — depends on B (needs `get_moderation_queue`, `is_organizer_of_event`) and benefits from A (correct approve).
4. **Chunk D (Phase 5)**: roster + removal — depends on C (same `moderation.py` router file) and feature-014 enabler.
5. **Chunk E (Phase 6)**: frontend — depends on C + D endpoints existing.
6. **Polish (Phase 7)**: depends on all chunks complete.

### Within each chunk

- Test written and confirmed FAILING before the implementation task (Constitution IV, R-PROC-3).
- Facade read (`database/audit.py`, `db.py`) before the service that consumes it; service before the endpoint; endpoint before the frontend screen.

### Parallel Opportunities

- **T006** (audit.py) and **T008** (event_service.py) are `[P]` — different files, no mutual dependency.
- **T020** (moderation-queue.js) and **T021** (participants.js) are `[P]` — different screen modules.
- **T027** (docs flag) is `[P]` — independent of the changelog edit.
- Cross-chunk parallelism is intentionally NOT used: the HARD-STOP gates serialize chunks by design (R-PROC-2).

---

## Parallel Example: Chunk B foundation reads

```bash
# Independent-file primitives can be built together, then joined by get_moderation_queue:
Task: "T006 Add get_pending_requests in database/audit.py"
Task: "T008 Add is_organizer_of_event in services/event_service.py"
```

---

## Implementation Strategy

### MVP scope

- **Phase 1 + Chunk A + Chunk B + Chunk C** delivers the MVP: the node-3 correctness fix plus a
  working, viewer-scoped moderation queue with authorized approve/reject (US1 + US2) served to the
  Mini App. Chunk E's queue screen makes it visible; roster (US3) and full design polish (US4) are
  incremental.

### Incremental delivery

1. Chunk A → announcement truth restored (bot immediately benefits).
2. Chunk B + C → queue + resolve API (validated via Level-A harness, no Telegram).
3. Chunk D → roster management.
4. Chunk E → Mini App screens + design v2.
5. Polish → full quickstart validation + changelog + checklist gate.

---

## Notes

- `[P]` = different files, no dependency on an incomplete task.
- `[Story]` maps each task to a spec.md user story for traceability.
- Every backend test is written FIRST and confirmed red before the fix (R-PROC-3); mocks assert
  `args`/`kwargs` (R-TEST-3); Level-A endpoints use `web_call` + `forge_init_data`, no httpx/TestClient
  (R-TEST-2).
- The final task (T028) is the mandatory checklist-linter gate; it passes only when every task above
  is marked `[x]` (lowercase). Commit at logical groups; `git push` only on Шэф's explicit request
  (R-PROC-5).
