# Data Model: Backend unification (feature 014)

No schema changes. This feature adds no tables, columns, or migrations. It defines one
service-method contract and the consequence rules around it. Entities below are existing
domain concepts, restated only where the method interacts with them.

## Value: Participation intent

A required, explicit direction for every participation change.

| Value | Meaning | Underlying mutation |
|---|---|---|
| `join` | User wants to be a participant | `ManagementService.add_event_participation_action` |
| `leave` | User wants to not be a participant | `ManagementService.leave_event_action` (remove-only) |

- Represented as a plain string constant (`"join"` / `"leave"`); no enum dependency is
  required, but the method MUST reject any other value with a no-op refusal (FR-011).
- Callers supply the value explicitly; it is never inferred from current state (D2).

## Method: `EventService.apply_participation_change`

**Signature (intent-carrying orchestration)**

`async apply_participation_change(bot, event_id: int, user_id: int, intent: str) -> tuple[bool, str]`

- `bot` — aiogram Bot, needed for the two Telegram side effects.
- `event_id`, `user_id` — target of the change.
- `intent` — `"join"` or `"leave"` (see Value above).
- No `topic_id` parameter: the access **guard is applied by the caller** (D1), which already
  holds the topic context, so the method never re-runs the guard and would only carry an unused
  argument. A future caller that needs topic-aware behavior inside the method can add a named
  parameter then (non-breaking).

**Returns** `(success, message)`:
- `success` — `True` when the user ends in the intended state (`after == (intent == "join")`),
  including the idempotent no-op case (join when already in; leave when already out).
- `message` — the human-readable string from the underlying `ManagementService` action,
  surfaced unchanged to preserve existing user-facing text (FR-010).
- Unknown `intent` → `(False, <polite refusal message>)`, no mutation, no side effects.

**Algorithm (consequence rules)**

1. `before = db.is_event_participant(event_id, user_id)` (GET-only read).
2. Delegate mutation by intent (lazy-import `ManagementService`):
   - `join` → `message = add_event_participation_action(event_id, user_id)`
   - `leave` → `_, message = leave_event_action(event_id, user_id)`
   - other → return `(False, refusal)`.
3. `after = db.is_event_participant(event_id, user_id)`; `changed = before != after`.
4. If `changed`:
   - If `intent == "join"`: `await notify_organizers_of_direct_join(bot, event_id, user_id)`
     (targeted, leads+creator — R-DATA-11).
   - `await AnnouncementService.refresh_announcements(bot, "event", event_id)` (lazy-import;
     refreshes **all** announcement copies — D7).
5. `success = (after == (intent == "join"))`; return `(success, message)`.

**Invariants**

- INV-1 (FR-001/002/003): the only place the full consequence set is assembled.
- INV-2 (FR-005): `leave` never adds a participant (remove-only via `leave_event_action`).
- INV-3 (FR-007): side effects fire only when `changed` is true; no-op changes are silent but
  still return an informative `message`.
- INV-4 (FR-002/003): organizer notification fires on join only, never on leave.
- INV-5 (FR-009): `changed`/`success` derived from participant state, never from `message`.
- INV-6 (FR-008): a raised error from a side effect must not roll back the committed mutation
  nor flip `success`; side-effect failures are logged and swallowed (inherited behavior).

## Entity interactions (existing, unchanged)

- **Event (поход)**: `is_approved` gates direct join at the caller's guard, not in this method.
- **Participation**: the single mutable relation; only `join`/`leave` change it.
- **Announcement**: 0..N per event; all copies refreshed on any change (D7).
- **Organizers**: leads + creator; recipients of the join-only notification.

## Callsite contract deltas (see contracts/ for full per-surface detail)

| Surface | Before | After |
|---|---|---|
| Dashboard toggle (`web/routers/dashboard.py`) | guard → `toggle` → notify(if "записаны") → refresh; **no refresh on leave** | guard → `apply_participation_change(intent)`; refresh on both directions |
| Announcement TMA (`web/routers/announcements.py`) | guard → `toggle` → **edit one message** → notify(if "записаны") | guard → `apply_participation_change(intent)`; all copies refreshed, bespoke edit removed |
| Announcement bot button (`handlers/announcements.py`) | guard → action by code, **legacy toggle fallback** → refresh | guard → `apply_participation_change(intent)`; legacy fallback removed (polite refusal) |
| Event card leave (`handlers/events.py`) | admin/creator guard → `leave_event_action` → refresh | admin/creator guard → `apply_participation_change("leave")` |
