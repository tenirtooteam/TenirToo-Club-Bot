# Implementation Plan: API Security Hardening (Phase 1)

**Branch**: `006-api-security-hardening` | **Date**: 2026-07-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-api-security-hardening/spec.md`

## Summary

Close the one genuinely exploitable authorization gap (web participation endpoint accepts joins without access/approval checks) and three related hardening defects: no `auth_date` freshness check on WebApp sessions, a broken FastAPI global exception handler, and bot deletion/grant callbacks that trust button delivery instead of re-checking permissions server-side.

Technical approach: introduce a **single participation-guard method in the service layer** (`EventService`) that both the announcement paths and the web dashboard path call before any mutation, eliminating the three divergent implementations. Add `auth_date` TTL validation inside the existing `validate_webapp_init_data` trust boundary. Replace the returned `HTTPException` in `web/main.py` with a proper `JSONResponse`. Add an action-keyed server-side permission re-check inside `handlers/common.py::confirm_execution` and `perform_search_pick`. Every defect is driven by a failing reproducing test first (R-PROC-3).

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: aiogram 3.4.1 (bot), FastAPI 0.109 / Starlette / uvicorn (web bridge), stdlib `hmac`/`hashlib` (init-data), pytest 8 + pytest-asyncio (tests)

**Storage**: SQLite (WAL) via `database/db.py` facade — **no schema changes in this feature**

**Testing**: pytest with `conftest.py` fixtures, isolated temp DB (`db_setup`), mocked Telegram (`mock_bot`) per R-TEST-1/2/3

**Target Platform**: Linux server (bot polling + FastAPI on the same event loop, `asyncio.gather` in `main.py`)

**Project Type**: Telegram Access-Control bot + FastAPI Mini-App bridge (layered: handlers/middlewares → services → db facade; web/routers → services → db facade)

**Performance Goals**: No new hot-path cost; the participation guard adds at most the two reads already performed elsewhere (topic-access + event lookup). No event-loop blocking introduced.

**Constraints**: Preserve existing behavior for authorized users (zero functional regressions, SC-003); changes confined to `web/`, `middlewares`/`handlers`, `services`, `config.py`, and `tests/`.

**Scale/Scope**: Club-scale (tens–hundreds of users). Four defects, four independently testable user stories (P1/P2/P2/P3).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Rule | Impact & Compliance |
|---|---|
| **I. Layered Isolation** (`R-ARCH-2`, `R-ARCH-4`) | Participation guard lives in `EventService`; handlers/web-routers call the service, never re-implement access logic or write to `db.*` directly. Web mutation stays `web/routers → services → db`. ✅ |
| **III. Service-Mediated Mutation** (`R-DATA-1`) | The guard gates the existing `ManagementService.toggle_event_participation` / `add_event_participation_action`; no new direct writes in handlers. ✅ |
| **IV. Test-First** (`R-PROC-3`, `R-TEST-1/2/3`) | Each of the 4 defects gets a failing reproducing test before the fix; journey tests include the negative (unauthorized) path with args+kwargs assertions. ✅ |
| **Access control** (`R-ARCH-7`) | Callback defense-in-depth uses `PermissionService.is_global_admin` / `can_manage_topic` — **no inline `if user_id != ADMIN_ID`** checks. ✅ |
| **WebApp trust boundary** (`R-SEC-1`) | `auth_date` TTL check is added *inside* `validate_webapp_init_data`, preserving it as the single trust boundary; identity still from `get_current_user_id`. ✅ |
| **Security fallback** (`R-SEC-2`) | Unchanged; global unhandled-callback fallback remains. ✅ |
| **Announcement indirection** (`R-UI-10`) | Unchanged; join still routes via `ann_join:{announcement_id}`. ✅ |
| **Default-Deny** (`R-DB-1`) | Guard reuses `PermissionService.can_user_write_in_topic` (the Default-Deny gate) as the topic-access source of truth. ✅ |
| **Linter parity** (`R-PROC-10/11`) | No new module/layer/directory added → no `.ruff.toml`/`.importlinter`/`semgrep-rules.yaml` changes required. ✅ |
| **Changelog** (`R-PROC-6`) | `CHANGELOG.md` update deferred to Route C after implementation (not a plan-phase git op). ⏳ |

**Gate result: PASS** — no violations; Complexity Tracking not required.

**Post-Phase-1 re-check**: design keeps all mutation behind services, adds no cross-layer imports, introduces one config constant and one service method — Constitution Check still **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/006-api-security-hardening/
├── plan.md              # This file
├── research.md          # Phase 0 — decisions (topic semantics, TTL, skew, handler shape)
├── data-model.md        # Phase 1 — logical entities & config (no DB schema change)
├── quickstart.md        # Phase 1 — how to validate each story
├── contracts/
│   └── interfaces.md     # Phase 1 — affected web endpoints + service/auth/config contracts
├── checklists/
│   └── requirements.md   # Spec quality checklist (from /speckit-specify)
└── tasks.md             # Phase 2 — generated by /speckit-tasks (NOT here)
```

### Source Code (repository root — affected paths only)

```text
config.py                              # [MODIFY] add WEBAPP_SESSION_TTL_SECONDS (default ~86400)

web/
├── auth.py                            # [MODIFY] auth_date freshness (TTL + skew) inside validate_webapp_init_data
├── main.py                            # [MODIFY] global_exception_handler → JSONResponse(500)
└── routers/
    └── dashboard.py                  # [MODIFY] /events/{id}/toggle calls EventService participation guard

services/
├── event_service.py                  # [MODIFY] add participation guard (approval + optional topic access)
└── permission_service.py             # [reuse] can_user_write_in_topic, is_global_admin, can_manage_topic

handlers/
├── common.py                         # [MODIFY] confirm_execution + perform_search_pick server-side perm re-check
├── announcements.py                  # [MODIFY] route direct-join through the shared guard
└── events.py                         # [reuse] request-based join unchanged (audit model, not direct-join)

tests/
├── test_web/                         # [NEW] auth_date TTL, dashboard toggle guard, 500 handler
├── test_journeys/                    # [NEW/EXTEND] direct-join guard parity; callback defense-in-depth negative path
└── test_services/                    # [NEW/EXTEND] EventService participation-guard unit tests
```

**Structure Decision**: Existing layered layout is kept as-is. The only new abstraction is one guard method in `EventService`; no new modules, layers, or directories — hence no linter-config churn (`R-PROC-10/11`).

## Complexity Tracking

> Not applicable — Constitution Check passed with no violations to justify.
