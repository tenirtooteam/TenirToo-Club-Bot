# Implementation Plan: Single-point orchestration of participation change (backend unification)

**Branch**: `014-backend-unification` | **Date**: 2026-07-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/014-backend-unification/spec.md`

## Summary

Four surfaces mutate event participation today, each re-implementing the "mutation + side
effects" chain differently, which has already produced observable drift (dashboard leave
refreshes no announcements; the announcement-card TMA endpoint refreshes only the clicked
copy; two web endpoints still toggle and can silently join a non-participant — the №7 bug).
This feature introduces one orchestration method, `EventService.apply_participation_change`,
that owns the full consequence set (delegated mutation via `ManagementService`, targeted
organizer notification on join, refresh of **all** published announcements), and rewires the
four surfaces to thin calls carrying an explicit `join`/`leave` intent. The guard
(`check_direct_join_allowed` / the event-card admin-creator check) stays at each callsite —
only the mutation-and-side-effects tail is unified, which is exactly where the drift lives.
"Change happened" is derived structurally (participant-state before/after), retiring the
Russian-substring success test. Import-cycle safety (R-ARCH-4) is preserved by lazily importing
`ManagementService` and `AnnouncementService` inside the new method, matching the existing
lazy-import convention in the event-announcement-management triangle.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: aiogram 3, FastAPI, aiosqlite/sqlite3 (WAL), pytest, pytest-asyncio (strict)

**Storage**: SQLite (WAL); participation lives in event-participant tables accessed only via `database.db`

**Testing**: pytest; endpoints exercised in-process (no httpx/TestClient — R-TEST-2); mocks assert `args`/`kwargs` (R-TEST-3)

**Target Platform**: Linux server (bot long-poll + FastAPI web app serving the Telegram Mini App)

**Project Type**: Single project — Telegram bot + FastAPI web backend + vanilla-JS Mini App frontend

**Performance Goals**: No new latency budget; one extra in-memory `is_event_participant` read per change (indexed, negligible)

**Constraints**: No import cycles (R-ARCH-4); all mutation through `ManagementService` (R-DATA-1); server-side authority (R-SEC-3); no framework/bundler added (Footprint 0, R-PROC-7)

**Scale/Scope**: One new service method; four migrated callsites (2 web endpoints, 2 bot handlers); minimal frontend intent wiring; ~5 characterization + parity test modules

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **III. Service-Mediated Mutation (R-DATA-1)**: PASS — the mutation stays inside
  `ManagementService` action methods; the new orchestration method lives in `EventService`
  and calls those methods, performing no direct `db.*` writes (only GET-only participant
  reads for structural change detection, which R-DATA-1 permits).
- **I. Layered Isolation (R-ARCH-4)**: PASS — `EventService` gains no top-level service
  imports; `ManagementService` and `AnnouncementService` are imported lazily inside the
  method, mirroring the existing lazy imports at `management_service.py:455` and
  `announcement_service.py:21`. import-linter has no inter-service contract; the concern is a
  runtime cycle, and lazy import inside the method resolves it.
- **IV. Test-First (R-PROC-3)**: PASS — characterization tests for all four callsites are
  written and green against current behavior before any migration, then evolve into parity
  tests. Documented behavior changes (№7 fix, announcement-refresh completeness, legacy-format
  refusal) get their own asserting tests.
- **R-SEC-3 (single guarded write-path, server-side authority)**: PASS — the guard remains
  server-side and runs before the method; explicit intent replaces the toggle so a stale
  client button cannot flip a leave into a join.
- **R-DATA-11 (targeted participation notifications)**: PASS — organizer notification is
  emitted only on an actual join, only to leads+creator, via the existing
  `notify_organizers_of_direct_join`.
- **R-CODE-4 (production code in tilde blocks)** and **R-CODE-7 (cite IDs, no rule-text
  copy)**: honored in this plan and downstream artifacts.

No violations — Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/014-backend-unification/
├── plan.md              # This file
├── spec.md              # Feature spec (already written)
├── research.md          # Phase 0 — decisions (intent model, change detection, guard placement)
├── data-model.md        # Phase 1 — method contract, intent value, consequence rules
├── contracts/
│   └── participation-orchestration.md   # apply_participation_change + migrated callsite contracts
├── quickstart.md        # Phase 1 — validation scenarios + named tests
├── checklists/
│   └── requirements.md  # Spec quality checklist (already passed)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
services/
├── event_service.py            # [MODIFY] add apply_participation_change(bot, event_id, user_id, intent)
├── management_service.py       # [UNCHANGED] mutation action methods reused as-is
└── announcement_service.py     # [UNCHANGED] refresh_announcements reused as-is

web/routers/
├── dashboard.py                # [MODIFY] toggle endpoint -> thin call with explicit action; guard kept
└── announcements.py            # [MODIFY] toggle endpoint -> thin call; drop manual single-message edit; guard kept

handlers/
├── announcements.py            # [MODIFY] ann_join handler -> thin call; drop legacy toggle fallback (polite refusal)
└── events.py                   # [MODIFY] leave_event handler -> thin call; guard kept

web/frontend/
└── app.js                      # [MODIFY] toggleParticipation sends explicit action from known is_participant state

tests/
├── test_services/
│   └── test_participation_orchestration.py   # [NEW] unit tests for apply_participation_change
├── test_web/
│   ├── test_dashboard_participation.py       # [MODIFY] characterization -> parity; explicit intent + №7 no-silent-join
│   └── test_announcement_participation.py     # [NEW] characterization + parity for announcements toggle endpoint
└── test_journeys/
    ├── test_tma_bridge_journey.py            # [MODIFY] follow endpoint signature; assert refresh-all
    └── test_participation_parity_journey.py  # [NEW] cross-surface parity: same consequence set on all four surfaces
```

**Structure Decision**: Single-project layout (services / web / handlers / frontend / tests).
The change is concentrated in `services/event_service.py` (one new method) plus four thin
callsite migrations and their tests; no new modules, packages, or build steps.

## Complexity Tracking

No constitution violations — section intentionally empty.
