# Phase 1 Contracts — API Security Hardening (Фаза 1)

Behavioral contracts for the interfaces touched. No new endpoints or routes are added; existing ones gain guards. Signatures shown for orientation — final code lives in implementation.

## 1. Service contract — participation guard (new)

`services/event_service.py`

~~~
EventService.check_direct_join_allowed(user_id: int, event_id: int, topic_id: int | None) -> tuple[bool, str]
~~~

- **Precondition**: caller is authenticated.
- **Postcondition**: no side effects (pure read). Returns `(True, "")` when a direct join is permitted, else `(False, <user-facing reason>)`.
- **Rules**: see `data-model.md` → Direct-Join Access Rule (event exists ∧ approved; if `topic_id` given → `can_user_write_in_topic`).
- **Callers**: `web/routers/dashboard.py` (topic_id=None), `web/routers/announcements.py` (topic_id=ann.topic_id), `handlers/announcements.py::ann_join` (topic_id=ann.topic_id). Bot-card `event_join` is **not** a caller (request/audit model, unchanged).

## 2. Web endpoint — `POST /api/dashboard/events/{event_id}/toggle`

`web/routers/dashboard.py`

- **Auth**: `Depends(get_current_user_id)` (unchanged).
- **New behavior**: BEFORE mutation, call `EventService.check_direct_join_allowed(user_id, event_id, topic_id=None)`.
  - allowed → proceed with `ManagementService.toggle_event_participation` (unchanged), then existing organizer notify + announcement refresh.
  - denied → HTTP `403` with `{"detail": <reason>}` (approval failure may use `403`; keep single deny status for simplicity) and **no mutation**.
- **Response (success)**: `{ "success": bool, "message": str }` (unchanged shape).

## 3. Web endpoint — `POST /api/announcements/{ann_id}/toggle`

`web/routers/announcements.py`

- **Change**: replace the inline `can_user_write_in_topic` check with `EventService.check_direct_join_allowed(user_id, target_id, topic_id=ann.topic_id)` so approval is also enforced (currently only topic access is checked).
- Deny → `403 {"detail": <reason>}`, no mutation. Success shape unchanged.

## 4. Bot callback — `ann_join:{announcement_id}:{code}`

`handlers/announcements.py`

- **Change**: gate the direct join through `EventService.check_direct_join_allowed(user_id, target_id, topic_id=ann_topic_id)` (adds approval enforcement to the existing topic check).
- Deny → `callback.answer(<reason>, show_alert=True)`, no mutation. Allowed path (join/leave + refresh + organizer notify) unchanged.

## 5. Auth boundary — `validate_webapp_init_data`

`web/auth.py`

~~~
validate_webapp_init_data(init_data: str) -> dict | None
~~~

- **Unchanged**: HMAC-SHA256 verification, identity extraction (`R-SEC-1`).
- **Added**: after HMAC passes, enforce `auth_date` freshness:
  - missing/unparseable `auth_date` → `None`
  - `now - auth_date > config.WEBAPP_SESSION_TTL_SECONDS` (and TTL > 0) → `None`
  - `auth_date - now > 300` (future skew) → `None`
  - otherwise → existing dict.
- **Downstream**: `get_current_user_id` still raises `401 Invalid session` on `None` (unchanged).

## 6. Web error handler — `global_exception_handler`

`web/main.py`

~~~
@app.exception_handler(Exception)
async def global_exception_handler(request, exc) -> JSONResponse
~~~

- **Change**: return `JSONResponse(status_code=500, content={"detail": "Internal Server Error"})` instead of returning an `HTTPException` instance. Keep `logger.error(..., exc_info=True)`.
- **Contract**: any unhandled exception on any route → HTTP 500 with a JSON body; the handler itself never raises.

## 7. Bot callbacks — deletion & grant defense-in-depth

`handlers/common.py`

- **`confirm_execution`** (`confirm_exe_{action}:{target}:{extra}`): before `ManagementService.execute_deletion`, resolve required authority by `action` (see `research.md` R4) using `PermissionService` (`is_global_admin` / `can_manage_topic` / `EventService.can_edit_event`). Denied → `callback.answer("❌ Доступ запрещён.", show_alert=True)` + `logger.warning`, no mutation.
- **`perform_search_pick`** (`mod_add`, `dir_add`): before granting, require `PermissionService.can_manage_topic(user_id, int(s_context))`. Denied → deny alert + log, no mutation.
- **Authorized paths unchanged** (regression guard, SC-007 positive case).

## Contract test matrix

| Contract | Negative (must deny/500) | Positive (must pass) |
|---|---|---|
| §1/§2 dashboard toggle | member, pending event → 403, no row | authorized member, approved event → toggled |
| §3/§4 announcement join | member without topic access → deny | member with access, approved → joined |
| §5 auth | stale `auth_date` / missing → None→401 | fresh `auth_date` → 200 |
| §6 error handler | route raises → 500 JSON, no secondary error | normal route → unaffected |
| §7 callbacks | non-admin `user_del` / non-manager `mod_add` → no mutation | admin/manager → executes |
