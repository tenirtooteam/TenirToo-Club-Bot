# Contract: Moderation API (`web/routers/moderation.py`, prefix `/api/moderation`)

All endpoints depend on `get_current_user_id` (`web/auth.py:61`) for identity from validated init-data
(R-SEC-1). Authority is re-checked server-side per action (see data-model authority matrix). No blanket
`require_admin`. Responses are typed DTOs; success is a structural flag, never a message substring
(R-DATA-8). Mutations traverse existing service seams only (R-DATA-1): resolution →
`ManagementService.resolve_request`; removal → `EventService.apply_participation_change`.

Import direction: `web/routers/moderation.py → services/* → database/db.py` (one-way, R-ARCH-4).

---

## GET `/api/moderation/queue`

Returns the viewer-scoped list of pending requests the caller may resolve.

- **Auth**: any valid session; content is filtered by `get_moderation_queue(user_id)`.
- **200** → `{ "items": QueueItemDTO[] }`, ordered oldest-first (`created_at ASC`).
  - Global admin: sees `event_approval` items; not `event_participation` of events they don't organize.
  - Organizer: sees `event_participation` items for their own events; not foreign `event_approval`.
- **401** → missing/invalid init-data.

`QueueItemDTO`: `{ request_id, type, event_id, event_title, requester_id, requester_name, created_at }`
(plain-text display fields; frontend escapes on render).

---

## POST `/api/moderation/requests/{request_id}/resolve`

Approve or reject one pending request.

- **Body**: `{ "status": "approved" | "rejected", "comment"?: string }`.
- **Authority** (server-side, before calling `resolve_request`): load the request; if
  `entity_type == "event_approval"` require `PermissionService.is_global_admin(user_id)`; if
  `entity_type == "event_participation"` require `EventService.is_organizer_of_event(user_id, entity_id)`.
- **Effect**: delegates to `ManagementService.resolve_request(bot, request_id, status, comment)` — the
  feature-007 atomic CAS gates all side effects and the single user notification (exactly-once under
  concurrency, FR-005). On approved participation, `resolve_request` refreshes the event's
  announcements (узел-3) and does **not** send the direct-join notice.
- **200** → `{ "success": true, "message": string }` (resolved), or `{ "success": false, "message":
  string }` when the request was already handled / vanished (idempotent fail-closed — not an error).
- **400** → `status` not in `{approved, rejected}`.
- **403** → caller lacks authority for this request's type/event.
- **401** → missing/invalid init-data.

---

## GET `/api/moderation/events/{event_id}/participants`

Roster of an event for its organizers.

- **Authority**: `is_organizer_of_event(user_id, event_id)` → else **403**.
- **200** → `{ event_id, event_title, capacity: int|null, participants: [{ user_id, display_name,
  is_organizer }] }` (plain-text names). `capacity` is presentational; no hard limit enforced.
- **404** → event not found. **401** → bad session.

Source: `db.get_event_details` (`participants`, `leads`, `creator_id`) — no new query.

---

## DELETE `/api/moderation/events/{event_id}/participants/{user_id}`

Remove a participant (organizer action).

- **Authority**: `is_organizer_of_event(caller_id, event_id)` → else **403**.
- **Effect**: `EventService.apply_participation_change(bot, event_id, user_id, intent="leave")`
  (feature 014) — remove-only (a non-participant target is a no-op, never silently enrolled, BUG-4),
  announcements refreshed on actual change.
- **200** → `{ "success": true|false, "message": string }` (success reflects the intended end state).
- **403** / **401** as above.

---

## Cross-cutting

- **Identity**: only `get_current_user_id`; the `{user_id}` path param names the *target*, never the
  caller.
- **Errors**: `HTTPException` for 400/401/403/404; business "already handled" is a **200** with
  `success:false` (mirrors the bot's callback answer, not a transport error).
- **Test harness**: every route is exercised via `tests/test_web/conftest.py::web_call` +
  `forge_init_data` (Level A, no Telegram, no httpx — R-TEST-2), positive + negative each; mocks assert
  `args`/`kwargs` (R-TEST-3).
