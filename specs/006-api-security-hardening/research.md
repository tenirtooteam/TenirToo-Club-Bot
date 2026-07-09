# Phase 0 Research — API Security Hardening (Фаза 1)

Resolves the open technical decisions before design. Each entry: Decision / Rationale / Alternatives.

---

## R1. What is "the event's topic" for the unified participation guard?

**Context**: The spec (US1/FR-001) requires `can_user_write_in_topic` "по топику, к которому привязан поход" across all three paths. But the DB schema has **no direct event→topic link** — events carry `creator_id`, `participants`, `leads`, approval status only. The topic association exists **only through an announcement** (`announcements.topic_id`). The three paths therefore differ in structure:

- **Bot card** (`handlers/events.py::join_event`): NOT a direct join — it creates a participation *audit request* that an organizer approves. No topic context; governed by the audit model.
- **Announcement button** (`handlers/announcements.py::ann_join`): direct join, topic = the announcement's `topic_id`; already checks `can_user_write_in_topic`.
- **Web announcement toggle** (`web/routers/announcements.py`): direct join, topic = announcement's `topic_id`; already checks access.
- **Web dashboard toggle** (`web/routers/dashboard.py::/events/{id}/toggle`): direct join by bare `event_id`, **no topic context and no checks at all**.

**Decision**: Introduce one guard `EventService.check_direct_join_allowed(user_id, event_id, topic_id: Optional[int]) -> tuple[bool, str]` with these rules:
1. Event MUST exist and be **approved** (`is_approved = 1`) — else deny (`FR-002`). Applies to every direct-join path unconditionally.
2. If a **topic context is provided** (announcement paths pass the announcement's `topic_id`), the user MUST pass `PermissionService.can_user_write_in_topic(user_id, topic_id)` — else deny (`FR-001`).
3. The **dashboard path passes no topic context** (a bare event has no single topic), so it enforces rule 1 (approval) plus a valid registered session only. This is consistent with the fact that the dashboard event list (`get_active_events`) is already club-wide and topic-agnostic — gating the *join* by a topic the event isn't bound to would be arbitrary.

All four direct-join call sites are routed through this single method → the three divergent implementations collapse into one (`FR-003`).

**Rationale**: Honestly reflects the schema (topic-scoping only exists where an announcement exists) while still closing the real gap (dashboard could join *pending* events and bypass every check). Reuses the Default-Deny gate (`R-DB-1`) as the topic-access source of truth. Bot-card request model is intentionally left unchanged — it is not a direct join.

**Alternatives considered**:
- *Gate dashboard joins on "any topic where the event is announced"*: rejected — an event may have zero or many announcements; semantics get murky, and the event list is already open club-wide, so it adds complexity without real protection.
- *Add an `events.topic_id` column*: rejected — schema change, out of scope; events are legitimately club-wide, not topic-owned.

**Resolved (Шэф, 2026-07-09)**: interpret "topic of the event" as *the announcement's topic where one exists, else club-wide*. Spec FR-001/US1 were updated to state this explicitly (direct-join channels only; topic check where a topic context exists; bot-card audit path excluded). An explicit event→topic model was declined for Phase 1 (would require a schema change).

---

## R2. `auth_date` freshness — TTL value and clock-skew handling

**Context**: `web/auth.py::validate_webapp_init_data` verifies the HMAC but ignores `auth_date`; a captured init-data string is valid forever (`FR-005/006/007`).

**Decision**:
- Add `config.WEBAPP_SESSION_TTL_SECONDS`, default `86400` (24 h), read from env like other config.
- After HMAC passes, parse `auth_date` (unix seconds). Reject if **missing/unparseable** (`FR-007`), or if `now - auth_date > TTL`.
- Allow a small **future skew tolerance** of 300 s (clock drift): reject only if `auth_date - now > 300`.
- TTL `<= 0` disables the freshness check (escape hatch for tests/local), documented as such.

**Rationale**: 24 h matches Telegram Mini App norms and the club's low-friction UX; env-configurable per `FR-006`. Skew tolerance prevents false rejections from minor drift (edge case in spec).

**Alternatives considered**: 1 h TTL (rejected — too aggressive for a casual club app, forces frequent re-open); no skew tolerance (rejected — brittle against normal drift).

---

## R3. FastAPI global exception handler shape

**Context**: `web/main.py::global_exception_handler` **returns** an `HTTPException` instance. Starlette's exception middleware expects a `Response`; returning a non-Response raises again during error handling (`FR-008`).

**Decision**: Return `starlette.responses.JSONResponse(status_code=500, content={"detail": "Internal Server Error"})` and keep `logger.error(..., exc_info=True)`. Signature stays `(request, exc)`.

**Rationale**: Minimal, correct, framework-idiomatic. Preserves logging with traceback. No behavior change for the success path.

**Alternatives considered**: `raise HTTPException(500)` inside the handler (rejected — re-raising from a catch-all handler is discouraged and can loop); custom error model (rejected — over-scoped for a bugfix).

---

## R4. Callback defense-in-depth — permission resolution shape

**Context**: `handlers/common.py::confirm_execution` (delete group/topic/user/event, revoke role) and `perform_search_pick` (`mod_add`, `dir_add`) live on the unfiltered `common` router and don't re-check permissions before mutating (`FR-009/010`). Actions have **mixed** required privileges — some are admin-only, some are moderator-of-topic.

**Decision**: Add an **action-keyed permission gate** evaluated before the mutation, using `PermissionService` only (per `R-ARCH-7`, no raw `ADMIN_ID`):
- `group_del`, `global_topic_del`, `user_del`, `role_rev*`, `event_del` → require `is_global_admin(user_id)` (note: `event_del` also reachable by creator via `EventService.can_edit_event`, so use `can_edit_event` for `event_del`).
- `topic_del` → require `is_global_admin` (admin group-management context).
- `mod_topic_del`, `mod_rem` → require `can_manage_topic(user_id, extra_id/topic_id)` (moderator or admin).
- For `perform_search_pick` `mod_add` / `dir_add` → require `can_manage_topic(user_id, int(s_context))`.
- On failure: `callback.answer("❌ Доступ запрещён.", show_alert=True)` + `logger.warning` (audit, `FR-011`), no mutation.

**Rationale**: Mirrors the per-action authority already implied by the moderator handlers, keeps the existing UI/confirmation flow (`R-DATA-4`) intact, and hardens against future routing regressions without breaking the legitimate moderator paths.

**Alternatives considered**: Slap an `IsGlobalAdmin` filter on the whole `common` router (rejected — `common` also serves non-admin flows: `close_menu`, `landing`, help, search for members; would break them); blanket `is_global_admin` for all confirm actions (rejected — breaks moderator `mod_topic_del`/`mod_rem`).

---

## R5. Testing strategy (R-PROC-3 / R-TEST-*)

**Decision**: One failing reproducing test per defect first, then fix:
- **US1**: journey test — member without topic access + valid session hits dashboard toggle on a pending and on a topic-restricted-announcement event → asserts denial (args+kwargs) and no participant row; positive path for authorized member.
- **US2**: unit test on `validate_webapp_init_data` — correctly-signed init-data with stale `auth_date` → `None`; fresh → dict; missing `auth_date` → `None`. HMAC computed with the test bot token.
- **US3**: web test — a route patched to raise → client receives 500 JSON, handler does not itself error; assert log captured.
- **US4**: journey test — unauthorized user triggers `confirm_execution` (e.g. `user_del`) and `perform_search_pick` `mod_add` → mutation absent, denial alert; authorized path still succeeds (regression guard).

Tests use `conftest.py` fixtures, isolated `db_setup`, `mock_bot`; no hardcoded entity IDs (use creation return values); frozen-model patching per `R-TEST-2`.

**Rationale**: Satisfies Test-First and journey-coverage rules; negative path is mandatory per `R-TEST-3`.
