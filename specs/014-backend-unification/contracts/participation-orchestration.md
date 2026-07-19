# Contract: Participation orchestration + migrated callsites (feature 014)

Internal service + endpoint contracts. No public HTTP schema change beyond one added request
parameter (`action`) on the two toggle endpoints.

## C1 — `EventService.apply_participation_change`

**Kind**: internal async service method (the single participation-change orchestrator).

**Inputs**: `bot`, `event_id: int`, `user_id: int`, `intent: "join" | "leave"`. No `topic_id`
parameter — the caller runs the topic-aware guard before calling (D1); the method never
re-checks access.

**Preconditions (caller-enforced, NOT re-checked here)**:
- The caller has already run its access guard and only calls on allow (D1, FR-006):
  - Dashboard / Announcement TMA / Announcement bot button → `check_direct_join_allowed`.
  - Event card leave → admin/creator-aware inline check (unchanged).

**Behavior**: per `data-model.md` algorithm — structural before/after change detection,
intent-directed mutation via `ManagementService`, join-only organizer notify, all-copies
announcement refresh, side effects gated on `changed`.

**Outputs**: `(success: bool, message: str)`.

**Postconditions**:
- On `changed` join: participant added, leads+creator notified once, every announcement copy
  rebuilt.
- On `changed` leave: participant removed, every announcement copy rebuilt, no notify.
- On no-op (repeat join / leave-of-non-participant): no notify, no refresh, informative
  `message`, `success` reflects end state (join-already → True; leave-already-out → True).
- On unknown `intent`: no mutation, no side effects, `(False, refusal)`.

**Errors**: side-effect (Telegram) failures are logged and do not raise out of the method, do
not roll back the mutation, do not flip `success` (FR-008).

## C2 — Endpoint `POST /api/dashboard/events/{event_id}/toggle`

**Change**: accepts an explicit `action` (`"join" | "leave"`) — request body field or query
param — replacing the implicit toggle.

- Guard `check_direct_join_allowed(user_id, event_id, topic_id=None)` unchanged; 403 on deny.
- Body: `success, message = await EventService.apply_participation_change(bot, event_id,
  user_id, action)`.
- Response unchanged in shape: `{"success": success, "message": message}`.
- Missing/invalid `action` → 400 with informative message (FR-011); no toggle fallback.
- Path unchanged for 014 (frontend route churn is 015 scope); the intent lives in `action`.

## C3 — Endpoint `POST /api/announcements/{ann_id}/toggle`

**Change**: accepts explicit `action`; the hand-rolled single-message `edit_message_text`
block (current lines ~67–83) is **removed** — all-copies refresh now happens inside C1.

- Resolve announcement → `ann_type`, `target_id`, `topic_id`; 404 if missing; 400 if not
  `event`.
- Guard `check_direct_join_allowed(user_id, target_id, topic_id=topic_id)` unchanged; 403 on
  deny (the caller still resolves and uses `topic_id` for the guard).
- Body: `success, message = await EventService.apply_participation_change(bot, target_id,
  user_id, action)`.
- Response: `{"success": success, "message": message}`.
- Missing/invalid `action` → 400 (FR-011).

## C4 — Bot handler `ann_join` (`handlers/announcements.py`)

**Change**: map the callback action code to intent, drop the legacy toggle fallback.

- Guard `check_direct_join_allowed` unchanged.
- `action_code == "1"` → intent `"join"`; `action_code == "0"` → intent `"leave"`.
- Any other/absent code → polite `callback.answer` refusal, no mutation (FR-011; D8).
- On a valid code: `success, message = await EventService.apply_participation_change(
  callback.message.bot, target_id, user_id, intent)`; then
  `callback.answer(message, show_alert=True)`. The guard above still uses `topic_id`.
- The handler no longer calls `refresh_announcements` or `notify_organizers_of_direct_join`
  directly — those move inside C1.

## C5 — Bot handler `leave_event` (`handlers/events.py`)

**Change**: replace the `leave_event_action` + manual `refresh_announcements` pair with one
call.

- Existing admin/creator-aware guard (pending-event block) unchanged.
- `success, message = await EventService.apply_participation_change(callback.bot, event_id,
  user_id, "leave")`; then `callback.answer(message)` and `view_event`.
- Handler no longer calls `refresh_announcements` directly.

## C6 — Frontend `web/frontend/app.js`

**Change**: `toggleParticipation` sends explicit intent derived from known state.

- The button already reflects `is_participant` (`updateButton`). On click, send
  `action = currentIsParticipant ? "leave" : "join"` in the POST to the same `/toggle` path.
- No business logic in JS (R-SEC-3); the server remains sole authority. Stale state is safe:
  a wrong `action` becomes a no-op server-side (D5), never a silent flip.
