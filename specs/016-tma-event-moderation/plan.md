# Implementation Plan: TMA event moderation + audit-request queue

**Branch**: `016-tma-event-moderation` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/016-tma-event-moderation/spec.md`

## Summary

Move event moderation — draft approve/reject, participation-request review, and participant-roster
management — from scattered bot callback chains into the Telegram Mini App, and add the consolidated
audit-request queue that today's code *promises* (the participation notice directs organizers to a
review "Audit" section — `services/event_service.py:166`) but never implemented:
`event_participation` requests can be created (`handlers/events.py:393`) yet have **no in-UI
resolution path** at all today.

The backend adds exactly one new data-layer primitive — a cross-entity pending-request listing
`db.get_pending_requests()` (FR-012) — and one read-only predicate
`EventService.is_organizer_of_event` (creator + leads; distinct from `can_edit_event`, which is
creator + global-admin and excludes leads). A new domain router `web/routers/moderation.py` carries
per-action authority — **no blanket `require_admin`** (that dependency does not exist yet; it is a
feature-017 concern) — and returns typed DTOs (R-DATA-8). Resolution reuses the existing atomic
compare-and-swap `ManagementService.resolve_request` (feature 007) unchanged in its concurrency
contract; the **only** mutation change is a localized `[MODIFY]` to its participation-approve branch
so it refreshes the event's public announcements (fixes the latent node-3 staleness at
`management_service.py:714`) **without** emitting the false "direct join" organizer notice
(`notify_organizers_of_direct_join`, whose text claims an automatic self-service join through the
announcement — a lie for a moderated approval). Participant removal reuses
`EventService.apply_participation_change(intent="leave")` (feature 014) — remove-only, announcement
refresh included.

Authority mirrors the bot per request type (Шэф's decision 2026-07-21): **drafts (`event_approval`)
→ global admin only**; **participation (`event_participation`) & roster → organizers of that event
(creator + leads)**, with the global admin *not* a universal participation resolver. The queue is
therefore **viewer-scoped**. The frontend adds moderation screen-modules inside the feature-015
architecture (escape-by-default render, no framework/build step, R-PROC-7); design-system v2 supplies
the request card with explicit Approve/Reject actions and status-by-shape encoding.

## Technical Context

**Language/Version**: Python 3.11 (backend), native browser ES modules (frontend, no transpile)

**Primary Dependencies**: FastAPI (web bridge), aiogram 3 (shared `bot` for notifications), sqlite3
(WAL) via `database.db`, pytest / pytest-asyncio (strict); no frontend framework or bundler added
(Footprint 0, R-PROC-7)

**Storage**: SQLite (WAL); `audit_requests`, `events`, `event_leads`, `event_participants` accessed
through `database.db`; writes only via `ManagementService` / feature-014 consequence point

**Testing**: pytest; new endpoints exercised in-process through the Level-A harness
(`tests/test_web/conftest.py::web_call` + `forge_init_data`, no httpx/TestClient — R-TEST-2); mocks
assert `args`/`kwargs` (R-TEST-3). Frontend developed against the Level-B browser stand
(`local_scripts/tma_audit_server.py`, port 8100)

**Target Platform**: Linux server (FastAPI serving the Mini App static frontend + JSON API); client
is the Telegram in-app webview

**Project Type**: Single project — Telegram bot + FastAPI web bridge + vanilla-JS Mini App frontend

**Performance Goals**: No new latency budget. The queue reads the pending set (small at club scale)
and enriches each item; event lookups are grouped by distinct `event_id` to avoid per-item N+1.
Lists over 7 items remain paginable/scrollable

**Constraints**: Server-side authority per request type (R-SEC-3); per-action authorization, no
blanket admin gate (R-ARCH-7); all mutation through `ManagementService` / feature-014 point
(R-DATA-1); atomic-CAS resolution reused, never re-implemented (feature 007); escape-by-default
render + init-data identity only (R-SEC-1); one-way imports `web/routers → services → database/db.py`
(R-ARCH-4); announcement truthfulness after resolution (R-CODE-6); no framework/bundler (R-PROC-7)

**Scale/Scope**: One new backend router (queue GET, resolve POST, roster GET, participant removal),
one new db read (`get_pending_requests`) + facade export, one new service predicate
(`is_organizer_of_event`), one new service aggregator (`get_moderation_queue`), one localized
`resolve_request` `[MODIFY]` (node-3), ~2 new frontend screen modules + router/nav wiring + design-v2
request card, ~4 new `tests/` modules (node-3 repro, queue scoping, resolve authority + exactly-once,
roster + removal)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **III. Service-Mediated Mutation (R-DATA-1)**: PASS — resolution goes through the existing
  `ManagementService.resolve_request`; participant removal through
  `EventService.apply_participation_change` (feature 014). The router performs no direct `db.*`
  writes. `db.get_pending_requests` is a GET-only read; the node-3 change adds a presentation
  refresh (`AnnouncementService.refresh_announcements`), not a data bypass.
- **I. Layered Isolation (R-ARCH-4)**: PASS — `web/routers/moderation.py` imports services only
  (`ManagementService`, `EventService`, `PermissionService`), mirroring `web/routers/dashboard.py`.
  The node-3 refresh uses a lazy `from services.announcement_service import AnnouncementService`
  inside `resolve_request` (announcement_service imports ManagementService), keeping the import
  graph acyclic — the exact pattern already used at `event_service.py:242`.
- **IV. Test-First (R-PROC-3 / R-TEST-3)**: PASS — node-3 ships a failing reproducing test first
  (approve participation ⇒ `refresh_announcements(bot, "event", id)` called, `notify_organizers…`
  NOT called); each endpoint ships a Level-A positive + negative (unauthorized / already-resolved /
  vanished) path; exactly-once is pinned by a concurrency test reusing the feature-007 CAS pattern.
  Mocks assert `args`/`kwargs`.
- **R-SEC-3 / R-ARCH-7 (authority-parity, per-action authority)**: PASS — resolution re-checks
  authority server-side per request type before calling `resolve_request`: `event_approval` requires
  `PermissionService.is_global_admin`; `event_participation` requires
  `EventService.is_organizer_of_event`. Roster view/removal require `is_organizer_of_event`. No
  blanket `require_admin` is attached; the queue GET returns only items the viewer may resolve.
- **R-SEC-1 (init-data identity + freshness)**: PASS — every endpoint depends on the existing
  `get_current_user_id`; no client-supplied identity or authority field is trusted.
- **R-DATA-8 (DTO contracts)**: PASS — queue items and resolution responses are typed, structurally
  successful payloads (`{success, message, …}`); success is derived structurally, never by
  substring-matching a human message.
- **R-CODE-6 (presentation ≠ data)**: honored — the node-3 refresh keeps the public announcement
  (roster/capacity) truthful after a moderated approval; this is a correctness fix, not cosmetics.
- **R-PROC-10 (linter configuration parity)**: PASS — a new file inside the existing `web/routers/`
  package: `.ruff.toml` already globs `web/**/*.py`; `.importlinter` / `semgrep-rules.yaml` define no
  web-layer contracts (`ban-db-in-handlers` targets `handlers/`, not `web/`). No config change
  needed — asserted, not assumed.
- **R-UI-8 (heartfelt, content-isolated UI text)**: PASS — moderation strings stay warm and
  community-oriented; no "management system" vocabulary leaks into the Mini App.
- **R-CODE-4 / R-CODE-7**: honored — production code in tilde blocks; rules cited by ID, never
  restated.

No violations — Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/016-tma-event-moderation/
├── plan.md              # This file
├── spec.md              # Feature spec (already written)
├── research.md          # Phase 0 — decisions (authority model, queue shape/scoping, node-3 fix, router seam)
├── data-model.md        # Phase 1 — audit-request queue model, organizer predicate, DTO shapes, state
├── contracts/
│   ├── moderation-api.md         # GET queue, POST resolve, GET participants, DELETE participant — DTO + error + authority contract
│   └── frontend-moderation.md    # Moderation screen modules, router/nav entries, request-card + status-by-shape contract
├── quickstart.md        # Phase 1 — validation scenarios + named tests + stand/harness commands
├── checklists/
│   └── requirements.md  # Spec quality checklist (already passed)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
database/
├── audit.py                     # [MODIFY] add get_pending_requests() → List[AuditRequestDTO], all pending, ORDER BY created_at (FR-012)
└── db.py                        # [MODIFY] re-export get_pending_requests through the facade

services/
├── event_service.py             # [MODIFY] add is_organizer_of_event(user_id, event_id) — creator OR lead (read-only predicate)
└── management_service.py        # [MODIFY] node-3: resolve_request participation-approve branch refreshes announcements (lazy import), never notify-direct-join;
                                 #          [NEW] get_moderation_queue(user_id) — viewer-scoped, enriched pending list (event_approval|event_participation only)

web/routers/
├── moderation.py                # [NEW] moderation domain: GET /queue, POST /requests/{id}/resolve, GET /events/{id}/participants, DELETE /events/{id}/participants/{uid}; per-action authority
└── __init__.py                  # [MODIFY] export moderation router

web/
└── main.py                      # [MODIFY] include_router(moderation.router, prefix="/api/moderation")

web/frontend/
├── index.html                   # [MODIFY] moderation screen containers + nav affordance (visible when authorized)
├── style.css                    # [MODIFY] design-v2 moderation tokens: request card, status-by-shape, capacity/roster
└── js/
    ├── router.js                # [MODIFY] add moderation routes (+ optional start_param → queue deep-link)
    ├── screens/
    │   ├── moderation-queue.js  # [NEW] viewer-scoped queue; request card Approve/Reject (US1/US2/US4)
    │   └── participants.js      # [NEW] event roster view + participant removal (US3)
    └── ui/
        └── components.js        # [MODIFY] request-card + status-by-shape widgets (extends 015 kit)

tests/
├── test_services/
│   └── test_participation_approve_refresh.py  # [NEW] node-3 repro (write FIRST, verify FAIL): approve participation ⇒ refresh, no direct-join notice
├── test_web/
│   ├── test_moderation_queue.py               # [NEW] viewer-scoping: admin sees drafts not foreign participation; organizer sees own participation not foreign drafts
│   ├── test_moderation_resolve.py             # [NEW] resolve positive/negative: authority-parity per type + already-resolved + exactly-once via web path
│   └── test_moderation_participants.py        # [NEW] roster view + removal (organizer positive, non-organizer negative), removal refreshes announcement
└── test_web/conftest.py         # [UNCHANGED] Level-A harness reused (web_call, forge_init_data, seed_*)

local_scripts/
└── tma_audit_server.py          # [UNCHANGED] Level-B stand serves the new module frontend at port 8100
```

**Structure Decision**: Single-project layout. The moderation domain gets its own thin router
(`web/routers/moderation.py`) rather than overloading the 015 authoring router — router-per-domain
(R-ARCH-7). The only mutation touch is the localized node-3 `[MODIFY]` inside `resolve_request` (both
bot and web benefit — one fix, both channels). The queue aggregator lives in `ManagementService`
(cohesion with `resolve_request` / `get_entity_name`, avoids a fourth service just to join
audit+events+permissions). Roster reuses `get_event_details` (already returns `participants`,
`leads`, `creator_id`) — no new roster db method. Removal reuses the feature-014 consequence point.
Frontend adds two screen modules under the existing `web/frontend/js/` architecture without touching
unrelated screens (FR-014) and without a framework or build step (R-PROC-7).

## Execution chunking (HARD-STOP boundaries for tasks.md)

Chunk boundaries are materialized as HARD-STOP gate tasks by `/speckit-tasks`; each chunk is 3–5
steps with a TDD sub-step and closes with an approval pause (R-PROC-2). Chunk A ships the node-3
correctness fix first so the announcement-truth invariant holds before any moderation UI exposes
approval.

1. **Chunk A — node-3 announcement-truth fix (test-first).** Failing repro
   (`test_participation_approve_refresh`); `[MODIFY]` `resolve_request` participation-approve branch
   to refresh announcements via lazy `AnnouncementService` import, never `notify_organizers_of_direct_join`;
   confirm bot + (future) web parity. HARD-STOP.
2. **Chunk B — Queue data + service (test-first).** `db.get_pending_requests` + facade export;
   `EventService.is_organizer_of_event`; `ManagementService.get_moderation_queue(user_id)`
   (viewer-scoped, enriched, event types only, grouped event lookups); service-level tests for
   scoping and ordering. HARD-STOP.
3. **Chunk C — Moderation router: queue + resolve (test-first).** `web/routers/moderation.py` GET
   `/queue` + POST `/requests/{id}/resolve` with per-type server-side authority re-check before
   `resolve_request`; mount in `main.py`; Level-A positive/negative (authority-parity, already-resolved,
   exactly-once via web). HARD-STOP.
4. **Chunk D — Roster view + participant removal (test-first).** GET `/events/{id}/participants` +
   participant removal via `apply_participation_change(intent="leave")`, both gated by
   `is_organizer_of_event`; Level-A tests incl. removal-refreshes-announcement and stale-remove no-op.
   HARD-STOP.
5. **Chunk E — Frontend moderation screens + design v2.** `moderation-queue.js` (request card
   Approve/Reject) + `participants.js`; router/nav entries (authorized-only); status-by-shape +
   capacity/roster tokens per the approved v2 mockup; escape-by-default reused from 015; CHANGELOG
   (CMD-4). HARD-STOP.

## Complexity Tracking

No constitution violations — section intentionally empty.
