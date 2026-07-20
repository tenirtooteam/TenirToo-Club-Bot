# Implementation Plan: TMA event authoring + frontend modularization

**Branch**: `015-tma-event-authoring` | **Date**: 2026-07-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/015-tma-event-authoring/spec.md`

## Summary

Move event creation and editing — today a six-state `EventCreation` FSM in the bot
(`handlers/events.py:19`, the historical source of the №11 date-entry bug) — into the Telegram
Mini App as single-screen forms, and modularize the 346-line monolithic `web/frontend/app.js`
into a file-per-screen ES-module architecture with a hash router. No new backend mutation logic
is written: the endpoints are thin adapters over the existing sanitizing mutations
(`ManagementService.create_event_action`, `ManagementService.update_event_details`) and the
existing edit-authority check (`EventService.can_edit_event`), exactly mirroring the bot's own
authority so a plain creator can still edit their own event from the Mini App (authority-parity
invariant, R-SEC-3 / R-ARCH-7). A new domain router `web/routers/events.py` carries per-action
dependencies — **no blanket `require_admin`** on the events domain — and returns typed DTO
payloads (R-DATA-8). Date parsing stays server-side via `DateService.parse_smart_date`
(R-CODE-5); the client only shows optional UX hints. The rewritten render layer is
escape-by-default: server strings reach the DOM as text, never as executable markup, closing the
existing `innerHTML` XSS surface (`app.js:149`, `app.js:172`) that becomes session theft while
`tg.initData` shares the JS scope (R-SEC-1). The `?ann_id=` entry contract is preserved: the
router maps the query parameter to the announcement screen on first load so live in-chat
announcement buttons keep working. Participation changes remain routed through the single
consequence point from feature 014 (`EventService.apply_participation_change`) — this feature
adds an authoring domain, it does not touch participation.

## Technical Context

**Language/Version**: Python 3.11 (backend), native browser ES modules (frontend, no transpile)

**Primary Dependencies**: FastAPI (web bridge), aiogram 3 (shared `bot` for notifications), sqlite3 (WAL) via `database.db`, pytest / pytest-asyncio (strict); no frontend framework or bundler is added (Footprint 0, R-PROC-7)

**Storage**: SQLite (WAL); events accessed through `database.db`; writes only via `ManagementService`

**Testing**: pytest; new endpoints exercised in-process through the Level-A harness (`tests/test_web/conftest.py::web_call` + `forge_init_data`, no httpx/TestClient — R-TEST-2); mocks assert `args`/`kwargs` (R-TEST-3). Frontend developed against the Level-B browser stand (`local_scripts/tma_audit_server.py`, port 8100)

**Target Platform**: Linux server (FastAPI serving the Mini App static frontend + JSON API); client is the Telegram in-app webview

**Project Type**: Single project — Telegram bot + FastAPI web bridge + vanilla-JS Mini App frontend

**Performance Goals**: No new latency budget; authoring endpoints are single-mutation calls; list endpoints already exist. Lists over 7 items must remain paginable/scrollable

**Constraints**: Server-side authority (R-SEC-3); per-action authorization, no blanket admin gate on events (R-ARCH-7); all mutation through `ManagementService` (R-DATA-1); dates through `DateService` (R-CODE-5); escape-by-default render; init-data identity only (R-SEC-1); one-way imports `web/routers → services → database/db.py` (R-ARCH-4); no framework/bundler (R-PROC-7)

**Scale/Scope**: One new backend router (2 authoring endpoints + supporting GET reads reused from dashboard), a frontend split into ~8 screen modules + a router module + a safe-render utility, design-system v2 tokens, ~3 new `tests/test_web` modules (create positive/negative, edit positive/negative, entry-mapping/escape characterization)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **III. Service-Mediated Mutation (R-DATA-1)**: PASS — creation and editing call the existing
  `ManagementService.create_event_action` / `update_event_details`, which own sanitization and
  the creator-as-participant+lead registration. The router performs no validation and no direct
  `db.*` writes; only GET-only reads for rendering, which R-DATA-1 permits.
- **I. Layered Isolation (R-ARCH-4)**: PASS — `web/routers/events.py` imports services only
  (`EventService`, `ManagementService`, `DateService`, `PermissionService`); it mirrors the
  existing `web/routers/dashboard.py` pattern. No new inter-layer arrow is introduced.
- **IV. Test-First (R-PROC-3 / R-TEST-3)**: PASS — each new endpoint ships with a Level-A test
  (positive + a negative unauthorized/invalid path) written against the harness before the
  frontend consumes it; a characterization test pins the `?ann_id=` entry mapping and the
  escape-by-default rendering of a markup-bearing title.
- **R-SEC-3 / R-ARCH-7 (authority-parity, server-side authority)**: PASS — create requires only
  a valid session (the bot's `event_create` has no admin gate); edit re-checks
  `EventService.can_edit_event` server-side per event. No blanket `require_admin` is attached to
  the events domain. Identity comes only from validated init-data (R-SEC-1).
- **R-SEC-1 (init-data validation + freshness)**: PASS — endpoints depend on the existing
  `get_current_user_id`; no client-supplied identity field is trusted.
- **R-CODE-5 (smart-date protocol)**: PASS — all date normalization is delegated to
  `DateService.parse_smart_date` / `split_human_range` on the server; the client carries no date
  business logic.
- **R-DATA-8 (DTO contracts)**: PASS — authoring responses use typed, structurally-successful
  payloads (`{success, message, ...}` / event DTO shape); success is derived structurally, never
  by substring-matching a human message.
- **R-PROC-10 (linter configuration parity)**: PASS — `.ruff.toml` already globs
  `web/**/*.py`; `.importlinter` and `semgrep-rules.yaml` define no web-layer contracts (semgrep
  `ban-db-in-handlers` targets `handlers/`, not `web/`). A new file inside the existing
  `web/routers/` package needs no config change; this is asserted, not assumed.
- **R-UI-8 (heartfelt, content-isolated UI text)**: PASS — user-facing strings stay warm and
  community-oriented; no "management system" vocabulary leaks into the Mini App.
- **R-CODE-4 / R-CODE-7**: honored — production code in tilde blocks; rules cited by ID, never
  restated.

No violations — Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/015-tma-event-authoring/
├── plan.md              # This file
├── spec.md              # Feature spec (already written)
├── research.md          # Phase 0 — decisions (authority model, date/form shape, escape reconciliation, router)
├── data-model.md        # Phase 1 — event authoring fields, authority rule, screen/route model, DTO shapes
├── contracts/
│   ├── events-api.md            # POST /api/events, PUT /api/events/{id}, reused GET reads, DTO + error contract
│   └── frontend-architecture.md # Module boundaries, hash router + ?ann_id= mapping, safe-render contract
├── quickstart.md        # Phase 1 — validation scenarios + named tests + stand/harness commands
├── checklists/
│   └── requirements.md  # Spec quality checklist (already passed)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
web/routers/
├── events.py                    # [NEW] authoring domain: POST create (session-only), PUT edit (can_edit_event); DTO responses
├── dashboard.py                 # [MODIFY] reused GET reads: un-escape display fields for JSON (D3) + add server-computed can_edit to event-details DTO (U1)
└── announcements.py             # [MODIFY] reused ?ann_id= card: un-escape display fields for JSON (D3); participation toggle unchanged

web/
└── main.py                      # [MODIFY] include_router(events.router, prefix="/api/events")

web/frontend/
├── index.html                   # [MODIFY] host module entry; screen containers; design-system v2 markup hooks
├── style.css                    # [MODIFY] design-system v2 tokens (Alpine night → dawn), status-by-shape, date-range chip
├── app.js                       # [DELETE] monolith replaced by module entry
└── js/                          # [NEW] file-per-screen ES modules
    ├── main.js                  # [NEW] bootstrap: read ?ann_id=, init router, Telegram SDK glue
    ├── router.js                # [NEW] hash router + entry-param → route mapping (preserves ?ann_id=)
    ├── api.js                   # [NEW] fetch wrapper: init-data header, structural success, error surfacing
    ├── render.js                # [NEW] escape-by-default DOM helpers (text nodes / safe templating)
    ├── screens/
    │   ├── dashboard.js         # [NEW] migrated dashboard screen
    │   ├── events-list.js       # [NEW] migrated events list
    │   ├── event-card.js        # [NEW] migrated event/announcement card
    │   ├── event-form.js        # [NEW] create/edit authoring form (US1/US2)
    │   ├── topics.js            # [NEW] migrated topics/profile/admin/roles screens
    │   └── ...                  # [NEW] remaining migrated read screens
    └── ui/
        └── components.js        # [NEW] shared badges, date-range chip, status-by-shape widgets

tests/test_web/
├── conftest.py                  # [UNCHANGED] Level-A harness reused (web_call, forge_init_data, seed_*)
├── test_events_create.py        # [NEW] create: positive + negative (invalid payload) via web_call
├── test_events_edit.py          # [NEW] edit: positive (creator, non-admin) + negative (no rights) — authority-parity
└── test_frontend_contract.py    # [NEW] ?ann_id= entry mapping + escape-by-default (markup title renders as text)

local_scripts/
└── tma_audit_server.py          # [UNCHANGED] Level-B stand serves the new module frontend at port 8100
```

**Structure Decision**: Single-project layout. The backend change is one new thin router plus a
one-line mount, and a small display-serialization `[MODIFY]` on the two reused readers
(`dashboard.py` / `announcements.py`): un-escape display fields for the JSON boundary (D3) and add
a server-computed `can_edit` flag to the event-details DTO (U1, drives the edit affordance). No new
mutation logic, no new service. The frontend is split under
`web/frontend/js/` (file-per-screen modules + router + api + escape-by-default render), replacing
the monolith without adding any framework or build step (R-PROC-7). Design-system v2 lands as
CSS tokens in the existing `style.css` alongside the module split.

## Execution chunking (HARD-STOP boundaries for tasks.md)

Chunk boundaries are materialized as HARD-STOP gate tasks by `/speckit-tasks`; each chunk is
3–5 steps with a TDD sub-step and closes with an approval pause (R-PROC-2).

1. **Chunk A — Backend authoring endpoints (test-first).** New `web/routers/events.py` create +
   edit; mount in `main.py`; Level-A tests first (create positive/negative; edit
   creator-positive / no-rights-negative — authority-parity). No frontend yet. HARD-STOP.
2. **Chunk B — Frontend modularization skeleton.** Extract router + api + escape-by-default
   render + bootstrap; migrate existing read screens 1:1 (no behavior change); preserve
   `?ann_id=` entry; `test_frontend_contract` pins entry mapping + escape. HARD-STOP.
3. **Chunk C — Authoring form screen.** `event-form.js` create/edit wired to Chunk-A endpoints;
   optional client UX hints only; server remains sole validator. HARD-STOP.
4. **Chunk D — Design-system v2.** Tokens in `style.css`, status-by-shape, date-range chip,
   applied to authoring + list screens per the approved v2 mockup. HARD-STOP + CHANGELOG (CMD-4).

## Complexity Tracking

No constitution violations — section intentionally empty.
