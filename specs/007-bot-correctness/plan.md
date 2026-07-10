# Implementation Plan: Bot Correctness (Correctness Fixes)

**Branch**: `007-bot-correctness` | **Date**: 2026-07-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-bot-correctness/spec.md`

## Summary

Feature 007 fixes five confirmed correctness bugs plus a small dead-code/None-guard tail,
all within the existing layered architecture — no schema changes. Each bug (BUG-1..BUG-5)
gets a failing reproducing test first (R-PROC-3), then a minimal localized fix that stays
inside its proper layer:

- **BUG-1** (date-range corruption): the naive `dates.split("-")` reconstruction in
  `handlers/events.py` is replaced by a new `DateService` helper that decomposes a human
  range into start/end parts with month-inheritance, honoring R-CODE-5 (no ad-hoc date
  splitting in handlers).
- **BUG-2** (list order/filter): `database/events.py::get_active_events` sorts by `start_iso`
  and filters out fully-past hikes, keeping undated and ongoing hikes visible.
- **BUG-3** (None-guard): five FSM input handlers gain the existing "please send text"
  graceful guard before `.strip()`.
- **BUG-4** (audit bypass): `leave_event` switches from `toggle_event_participation` to a new
  remove-only `ManagementService` action (R-DATA-1, R-SEC-3 single write-path intent).
- **BUG-5** (TOCTOU): `database/audit.py::resolve_audit_request` becomes a conditional
  compare-and-swap (`WHERE id=? AND status='pending'`, return `rowcount>0`); `resolve_request`
  gates all side effects on the CAS result.
- **Tail**: remove dead expressions (`events.py`, `ui_service.py`), and add a `from_user is
  None` guard in `AccessGuardMiddleware`.

Technical approach: TDD per bug, layer-respecting minimal edits, full suite green at the end.

## Technical Context

**Language/Version**: Python 3.11 (mandatory `venv`, R-PROC-7)

**Primary Dependencies**: aiogram 3, FastAPI, dateparser, pytest, pytest-asyncio

**Storage**: SQLite (WAL); existing columns only — `events.start_date/end_date/start_iso/end_iso`,
`audit_requests.status`. **No migration.**

**Testing**: pytest with `conftest.py` fixtures (`db_setup`, `mock_bot`, `create_context`,
`create_callback`), isolated temp DB (R-TEST-1). Date determinism via the existing
`mock_dateparser_now` pattern (`RELATIVE_BASE = 2026-01-01`).

**Target Platform**: Linux/Windows server (Telegram bot long-poll + FastAPI Mini App)

**Project Type**: Single-project layered app (handlers → services → database facade)

**Performance Goals**: N/A (correctness feature; no hot-path change beyond an indexed-free
`ORDER BY start_iso` on a small events table)

**Constraints**: Single-process asyncio over SQLite/WAL — BUG-5 "concurrency" is `await`-point
interleaving, so a DB-level atomic conditional UPDATE fully serializes the transition.

**Scale/Scope**: Club-scale (tens–hundreds of users/events). Scope = 5 bugs + tail; ~6 source
files touched, ~5 new/extended test files.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Rule | Relevance | Compliance in this plan |
|---|---|---|
| **IV. Test-First** — R-PROC-3, R-TEST-1/3/4 | Every bug needs a failing repro test first | Each chunk starts with a repro test task (named below); tests use `conftest` fixtures + isolated DB; mock assertions check `args`+`kwargs` (R-TEST-3) |
| **I. Layered Isolation** — R-ARCH-1/2/4 | Fixes span handlers/services/db | BUG-2/BUG-5 edits live in `database/*` (facade-internal); handlers never gain a `db` import; BUG-1 date logic moves *into* `DateService`, not handler |
| **III. Service-Mediated Mutation** — R-DATA-1 | BUG-4 changes a mutation path | Leave routed through a new `ManagementService` remove-only action with `(bool,str)` contract; handler does no direct write/validation |
| **Smart-date protocol** — R-CODE-5 | BUG-1 root cause is ad-hoc splitting in a handler | New `DateService.split_human_range` centralizes decomposition; handler stops splitting on `-` |
| **Presentation/data separation** — R-CODE-6 | BUG-1 writes `start_date`/`end_date` | Stored human parts stay raw (no decoration); month-inheritance produces a *complete* human start, not a UI decoration |
| **DTO contracts** — R-DATA-8 | BUG-2 returns `EventDTO` list | `get_active_events` keeps returning `EventDTO`; only ORDER/WHERE change |
| **Single guarded write-path** — R-SEC-3 | BUG-4 is an approval-bypass | Remove-only semantics ensure leave can never become a back-door join; card join stays request/audit flow (exempt) |
| **V. Traceability** — R-CODE-7 | — | Plan/tasks cite `R-*` IDs; in-code markers where a fix embodies a rule |

**Gate result: PASS.** No architectural boundary is crossed; no new module/layer (so R-PROC-10/11
linter-parity untouched). No `state.clear()`, no direct UI calls introduced.

## Project Structure

### Documentation (this feature)

```text
specs/007-bot-correctness/
├── plan.md              # This file
├── research.md          # Phase 0 — design decisions per bug
├── data-model.md        # Phase 1 — affected entities/fields, status transition
├── quickstart.md        # Phase 1 — validation/run guide
├── contracts/
│   └── internal-signatures.md   # Phase 1 — changed/new function contracts
└── tasks.md             # Phase 2 (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
handlers/
├── events.py            # [MODIFY] BUG-1 (process_date_confirm, process_editing_dates),
│                        #          BUG-3 (editing title/dates None-guard), BUG-4 (leave_event),
│                        #          tail dead code (lines ~352, ~364-372)
├── moderator.py         # [MODIFY] BUG-3 None-guard (rename topic ~99, direct-access ~220)
└── common.py            # [MODIFY] BUG-3 None-guard (search query ~170)

services/
├── date_service.py      # [MODIFY] BUG-1 — add split_human_range() helper
├── management_service.py# [MODIFY] BUG-4 leave action; BUG-5 resolve_request CAS gating
└── ui_service.py        # [MODIFY] tail — remove dead expressions (~115-116)

database/
├── events.py            # [MODIFY] BUG-2 — get_active_events ORDER BY start_iso + past filter
└── audit.py             # [MODIFY] BUG-5 — resolve_audit_request conditional CAS + rowcount

middlewares/
└── access_check.py      # [MODIFY] tail — from_user None guard (~68)

tests/
├── test_services/test_date_logic.py          # [MODIFY] BUG-1 range decomposition cases
├── test_handlers/test_event_edit_collision.py# [MODIFY] BUG-1 editing-path regression
├── test_database/test_event_contracts.py     # [MODIFY] BUG-2 order+filter cases
├── test_handlers/test_fsm_nontext_guard.py    # [NEW] BUG-3 non-text guard across 5 handlers
├── test_services/test_participation_guard.py  # [MODIFY] BUG-4 leave remove-only
└── test_services/test_audit_cas.py            # [NEW] BUG-5 compare-and-swap idempotency
```

**Structure Decision**: Reuse the existing single-project layout; no new directories.
Repro tests are placed with their nearest existing peers (date logic, event contracts,
participation guard) and two focused new files for BUG-3 and BUG-5.

## Execution Blueprint (Task RNA → chunked, TDD, HARD-STOP gates)

Chunks are ordered by spec priority. Each fix step is preceded by its failing-repro step
(R-PROC-3). `/speckit-tasks` expands these into numbered tasks with a HARD-STOP gate at each
chunk boundary (R-PROC-2).

**Chunk A — BUG-1 (P1, data corruption)** · rules R-CODE-5, R-CODE-6, R-DATA-1
1. Repro: extend `test_date_logic.py` + `test_event_edit_collision.py` to assert full human
   start/end (e.g. `"10 июня"`/`"15 июня"`) persisted on both create and edit ranges — verify FAIL.
2. Fix: add `DateService.split_human_range(text) -> (start_human, end_human|None)` reusing the
   existing separator + month-inheritance logic.
3. Fix: replace the inline `split("-")` in `process_date_confirm` and rewrite the dead branch in
   `process_editing_dates` to use the helper; remove tail dead code at ~352/~364-372.
4. HARD-STOP gate.

**Chunk B — BUG-2 (P2, list order/filter)** · rules R-DATA-8, R-CODE-6
1. Repro: extend `test_event_contracts.py` — seed past/ongoing/future/undated hikes; assert
   ISO-ordering and past-exclusion; verify FAIL.
2. Fix: `get_active_events(today: str|None=None)` → `ORDER BY start_iso`, filter
   `COALESCE(end_iso, start_iso) >= today OR start_iso IS NULL`; keep `EventDTO`.
3. HARD-STOP gate.

**Chunk C — BUG-3 + BUG-5 (P2, crash + race)** · rules R-PROC-3, R-DATA-1
1. Repro (BUG-3): NEW `test_fsm_nontext_guard.py` — non-text message into each of the 5 states
   returns a graceful prompt, no raise; verify FAIL.
2. Fix (BUG-3): add `if not message.text: return await UIService.show_temp_message(...)` guard in
   moderator rename, moderator direct-access, common search, events editing-title, events editing-dates.
3. Repro (BUG-5): NEW `test_audit_cas.py` — two resolutions on one pending request; assert exactly
   one side-effect+notification, second reports already-handled; verify FAIL.
4. Fix (BUG-5): `resolve_audit_request` → `UPDATE ... WHERE id=? AND status='pending'`, return
   `rowcount>0`; `resolve_request` reads request, gates ALL side effects on the CAS boolean.
5. HARD-STOP gate.

**Chunk D — BUG-4 + Tail (P3 + cleanup)** · rules R-DATA-1, R-SEC-3
1. Repro (BUG-4): extend `test_participation_guard.py` — non-participant "leave" creates no
   participation; participant "leave" still removes; verify FAIL.
2. Fix (BUG-4): add `ManagementService.leave_event_action(event_id, user_id) -> (bool,str)`
   (remove-only); point `leave_event` at it.
3. Fix (Tail): remove dead expressions in `ui_service.py` (~115-116); add `from_user is None`
   pass-through guard in `AccessGuardMiddleware`.
4. Full-suite run (`pytest`) — all green (R-TEST-4). HARD-STOP gate.

**Verification**: reproducing tests named per chunk above; `quickstart.md` lists the exact
`pytest` invocations proving each bug fixed and the suite green.

## Complexity Tracking

> No Constitution Check violations — section intentionally empty.
