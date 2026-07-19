# Research: Backend unification (feature 014)

Phase 0 decisions. Each records what was chosen, why, and the alternatives rejected.

## D1 — What the unified method owns (scope of unification)

**Decision**: `EventService.apply_participation_change` owns only the tail: delegated
mutation (via `ManagementService`), organizer notification on join, and refresh of all
announcements. The access **guard stays at each callsite**.

**Rationale**: The observed drift is entirely in the side-effect tail (dashboard leave
refreshes nothing; announcement TMA refreshes one copy; success detected by substring). The
guard was already consistent across A/B/C (`check_direct_join_allowed`) and deliberately
different for D (event card allows admin/creator to leave a pending event). Pulling the guard
into the method would erase D's admin/creator escape — a behavior regression — for no benefit,
since guard failure already means "return without mutating." FR-006 is satisfied because each
caller runs its guard before the call and never invokes the method on denial.

**Alternatives considered**:
- *Guard inside the method*: rejected — regresses D's admin/creator leave-on-pending path and
  couples topic-context resolution into a method whose callers already hold it.
- *Guard as an injected callback*: rejected — adds indirection with no drift it prevents; the
  guards are short and already live correctly at the callsites.

## D2 — Explicit intent vs toggle

**Decision**: The method takes an explicit `intent` value, `"join"` or `"leave"`. No toggle
anywhere, including the two web endpoints. The frontend derives intent from the
already-loaded `is_participant` state and sends it.

**Rationale**: The toggle is the mechanism of bug №7 — a stale client button flips a leave
into a join. Explicit intent + remove-only leave (D5) means a stale button can at worst be a
safe no-op, never a silent state flip. The frontend already knows `is_participant`
(`app.js:updateButton`), so supplying intent is a one-line change, not new state.

**Alternatives considered**:
- *Keep toggle on web, fix only bot*: rejected — leaves №7 live on exactly the surfaces Phase
  5 is about to expand.
- *Infer intent server-side from current state*: rejected — that **is** a toggle; it cannot
  distinguish "user meant to leave but is already out" from "user meant to join."

## D3 — Structural change detection (retire the substring test)

**Decision**: The method reads `db.is_event_participant` before and after the delegated
mutation; `changed = before != after`. Side effects fire only when `changed` is true.
`success = (after == (intent == "join"))`.

**Rationale**: FR-009 forbids deciding "a join happened" by searching the human message for
"записаны" (today's logic in `dashboard.py:94` and `announcements.py:86`). A before/after
participant read is structural, idempotent, and works uniformly for both intents. The
underlying `ManagementService` action methods already no-op safely on repeats, so the extra
read only classifies the outcome; it does not gate the mutation. GET-only participant reads
from a service are permitted by R-DATA-1.

**Alternatives considered**:
- *Add `(bool, str)`-returning join/leave action pair to `ManagementService`*: viable and
  slightly more symmetric (`leave_event_action` already returns `(bool, str)`), but changing
  `add_event_participation_action`'s return type ripples into its callers and tests for no
  behavioral gain. The before/after read achieves the same structural signal with zero
  signature churn. Deferred as an optional cleanup, not required here.
- *Parse the message*: rejected outright — it is the exact anti-pattern FR-009 removes.

## D4 — Mutation delegation (which ManagementService methods)

**Decision**: Reuse existing action methods unchanged — `add_event_participation_action` for
`join`, `leave_event_action` for `leave`. Both already encapsulate their own no-op guard and
`_trigger_sheets_sync` (R-DATA-1). The method returns the underlying human message to the
caller.

**Rationale**: R-DATA-1 keeps mutations in `ManagementService`. These methods already exist,
are already the correct write path, and already emit the Sheets side effect internally; the
orchestration method must not duplicate or bypass them.

## D5 — Remove-only leave everywhere (№7 invariant)

**Decision**: `leave` always routes through `leave_event_action`, which removes a participant
and no-ops (never adds) for a non-participant. This invariant, previously only in the bot
handler, now holds on every surface because every surface goes through this method.

**Rationale**: Directly implements FR-005. Combined with D2, it closes the silent-join path on
web.

## D6 — Import-cycle safety (R-ARCH-4)

**Decision**: Inside `apply_participation_change`, lazily import both `ManagementService` and
`AnnouncementService` (function-body imports). `EventService` gains no new top-level service
import.

**Rationale**: import-linter defines no inter-service contract (only handlers/middlewares →
database is forbidden), so this is a runtime-cycle question, not a static one. The triangle
already resolves cycles by lazy import (`management_service.py:455` lazily imports
`EventService`; `announcement_service.py:21` lazily imports `EventService`). Matching that
convention keeps module import order robust regardless of which service loads first and keeps
the pattern uniform for the next reader.

**Alternatives considered**:
- *Top-level import of `ManagementService` in `event_service`*: technically acyclic today
  (`ManagementService` does not import `EventService` at top level), but rejected to avoid a
  latent trap if a future top-level import is added on either side, and to keep one convention.

## D7 — Announcement refresh: all copies, via the existing method

**Decision**: The method calls `AnnouncementService.refresh_announcements(bot, "event",
event_id)`, which already iterates **all** announcements of the event
(`get_announcements_by_target`) and rebuilds each message. The announcement TMA endpoint's
current hand-rolled single-message `edit_message_text` block is deleted.

**Rationale**: `refresh_announcements` is already the correct all-copies refresh; the TMA
endpoint's bespoke single-message edit is the source of the "only the clicked copy updates"
drift (SC-003). Routing through the shared method fixes it for free and removes duplicated
Telegram-edit code.

## D8 — Legacy-format callback refusal (bot ann button)

**Decision**: The `ann_join` handler's current `else: toggle_event_participation(...)`
fallback for an unrecognized action code is removed. Unknown/absent action → polite refusal,
no state change, no guessing.

**Rationale**: FR-011 — a legacy button without explicit intent must not be resolved by
guessing direction. The fallback is the last toggle path in the bot; removing it makes intent
mandatory everywhere.

## D9 — Delivery-failure isolation

**Decision**: Side effects (`notify_organizers_of_direct_join`, `refresh_announcements`) run
after the committed mutation and their failures are caught/logged (both already swallow
per-recipient/per-message errors internally); a delivery failure never rolls back the mutation
or converts success into an error for the user.

**Rationale**: FR-008. The mutation is the source of truth; Telegram availability is not. The
existing methods already log-and-continue on send/edit failure, so the isolation is largely
inherited; the method must not wrap them in a way that re-raises.
