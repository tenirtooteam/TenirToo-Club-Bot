# Implementation Plan: Dedup Permission Layer (feature 008 №20)

**Branch**: `009-dedup-permission-layer` | **Date**: 2026-07-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/009-dedup-permission-layer/spec.md`

## Summary

Remove two nodes of technical debt in the permission layer without changing observable behavior:
1. Delete the dead duplicate `has_direct_access` (identical query to `can_write`, 0 live callers) and its import in the DB aggregator `database/db.py`; `can_write` remains the single point of direct-access checking.
2. Make the control flow of `is_superadmin` in `services/permission_service.py` honest: remove the dead DB branch whose result does not depend on its condition (when `user_id == ADMIN_ID` the result is always `True`); preserve the external semantics (`True` for `ADMIN_ID` / `False` otherwise) and, optionally, keep the diagnostic warning as observability.

**Approach (TDD, R-PROC-3)**: characterization tests first, capturing current behavior of both functions, then minimal edits. Base DNA — Python 3.11 / SQLite(WAL) / pytest inside venv.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: aiogram 3, sqlite3 (stdlib), pytest — no new dependencies introduced

**Storage**: SQLite (WAL); table `direct_topic_access`, roles in DB — schema UNCHANGED

**Testing**: pytest, isolated test DB via fixtures (`R-TEST-1`); mock assertions check `args`/`kwargs` (`R-TEST-3`)

**Target Platform**: Linux/Windows server (Telegram bot)

**Project Type**: Single project (facade-layered bot)

**Performance Goals**: N/A — behavior and query cost unchanged (an unused function is removed; the second edit is control-flow only)

**Constraints**: Public contract of the permission layer unchanged; footprint ≤ 3 source files + tests; end-user bot behavior identical

**Scale/Scope**: Local edit of 3 permission-layer files; risk — low (one function is dead, the other preserves its observable result)

## Constitution Check

*GATE: Must pass before Phase 0. Re-check after Phase 1.*

- **I. Layered Isolation (`R-ARCH-1/2/4`)**: PASS. Edits stay within layers (`database/*` provider, `services/permission_service.py` consumer); import direction unchanged; handlers untouched. Removing the `has_direct_access` import from `db.py` narrows the facade surface without crossing a boundary.
- **II. Sterile Interface (`R-UI-1/FSM-1`)**: PASS. UI/FSM untouched.
- **III. Service-Mediated Mutation (`R-DATA-1/4`)**: PASS. No entity mutations; only permission checks (read path) and dead-code removal.
- **IV. Test-First (`R-PROC-3/R-TEST-1/3`)**: PASS. Characterization tests written FIRST, capturing pre-edit behavior; isolated DB via fixtures.
- **V. Single Source of Truth (`R-CODE-7`)**: PASS. Plan cites IDs, does not copy rule text. The dedup directly serves the single-source-of-truth principle at code level.

**Gate result**: PASS — no violations, Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/009-dedup-permission-layer/
├── plan.md              # This file
├── research.md          # Phase 0 (no unknowns — records decisions)
├── quickstart.md        # Phase 1 (validation)
├── checklists/
│   └── requirements.md  # spec-quality checklist (done)
└── tasks.md             # Phase 2 (/speckit-tasks — NOT created here)
```

data-model.md and contracts/ are NOT created: DB schema is unchanged, the edit introduces no external interfaces, and the public contract of the permission layer is preserved (purely internal cleanup).

### Source Code (repository root)

```text
database/
├── permissions.py       # [MODIFY] remove has_direct_access (lines 74-78)
└── db.py                # [MODIFY] drop has_direct_access from the import (line 27)

services/
└── permission_service.py # [MODIFY] honest control flow for is_superadmin (lines 12-26)

tests/
└── test_permission_layer_dedup.py  # [NEW] characterization tests (US1/US2)
```

**Structure Decision**: Single project, facade-layered. Changes are localized to the permission layer (`database/`, `services/`) and its tests; handlers, UI, and DB schema are not touched.

## Complexity Tracking

> Not filled — Constitution Check passed without violations.
