# Phase 0 Research: TMA event moderation + audit-request queue

All load-bearing claims below are grounded in files read during planning; no unverified external
claims. Decisions resolve the design forks; none remain marked NEEDS CLARIFICATION.

## D1 — Moderation authority per request type (the FR-007 fork)

**Decision**: Authority mirrors the bot per request type. `event_approval` (draft) is resolved by
**global admins only** (parity with `handlers/events.py:461`). `event_participation` is resolved by
**organizers of that event only** (creator + assigned leads); the global admin is **not** a universal
participation resolver unless they are themselves an organizer of that event. The queue is therefore
**viewer-scoped**.

**Rationale**: Decided by Шэф (2026-07-21). It cleanly mirrors the code's existing intent: the
participation-request notification is sent "ТОЛЬКО организаторам (лидам и создателю)… без общего
списка админов" (`services/event_service.py:147`, `:157`). Making participation an organizer concern
closes the dangling promise ("рассмотрите заявку в разделе „Аудит"") for exactly the audience already
notified. Basis: R-SEC-3 (server-side authority, channel parity), R-ARCH-7 (per-action authorization).

**Alternatives considered**: (A) global-admins resolve everything — simplest single global queue, but
organizers are notified yet cannot act → the same orphaned request, relocated. (B) organizers **+**
global admins resolve participation — broader oversight, but dilutes the "organizers own their event"
model Шэф chose and contradicts the "без общего списка админов" comment. Both rejected.

## D2 — Organizer predicate: new `is_organizer_of_event`, not `can_edit_event`

**Decision**: Add a new read-only predicate `EventService.is_organizer_of_event(user_id, event_id)`
returning `user_id == creator_id OR user_id in leads`, computed from `db.get_event_details` (which
already returns `creator_id` and `leads`).

**Rationale**: The existing `EventService.can_edit_event` (`event_service.py:106`) is **creator +
global-admin** and **excludes leads** — wrong on both ends for D1's participation authority (which is
creator + leads, *without* admin override). A distinct predicate keeps the two authority questions
(edit vs. moderate-participation) explicit and independently correct. It is a pure read; no facade or
mutation change.

**Alternatives considered**: Overloading `can_edit_event` — rejected: it would silently grant global
admins participation-resolution power (violates D1) and still miss leads.

## D3 — узел-3 fix: refresh announcements on participation-approve, no direct-join notice

**Decision**: In `ManagementService.resolve_request`, the `status == "approved"` /
`entity_type == "event_participation"` branch (`management_service.py:713`) keeps
`db.add_event_participant` + sheets sync and additionally calls
`await AnnouncementService.refresh_announcements(bot, "event", request["entity_id"])` via a lazy
`from services.announcement_service import AnnouncementService`. It does **not** call
`EventService.notify_organizers_of_direct_join`.

**Rationale**: A moderated approval changes the roster, so the public announcement (participant
count / v2 capacity meter) must refresh to stay truthful (R-CODE-6). But the approval is **not** a
direct join: `notify_organizers_of_direct_join` text is "запись прошла автоматически через анонс"
(`event_service.py:196`) — a lie here — so routing the whole thing through
`apply_participation_change(intent="join")` (which bundles that notice) is wrong. The refresh alone is
the correct shared consequence. The lazy import matches the acyclic pattern already used at
`event_service.py:242`. One fix, both channels (bot approve handler and the new web resolve endpoint).

**Alternatives considered**: (a) route approve through `apply_participation_change` — rejected (false
direct-join notice); (b) duplicate refresh logic in the web endpoint only — rejected (bot approve path
stays broken; drift). Fix at the single resolution seam instead.

**Test-first (R-PROC-3)**: seed an approved event with an active announcement + a pending
`event_participation` request; mock `refresh_announcements` and `notify_organizers_of_direct_join`;
call `resolve_request(…, "approved")`; assert refresh called with `("event", event_id)` and
direct-join notice **not** called. Fails today (no refresh), passes after the fix.

## D4 — Cross-entity pending listing: new `db.get_pending_requests`

**Decision**: Add `database/audit.py::get_pending_requests() -> List[AuditRequestDTO]` returning **all**
pending rows `ORDER BY created_at ASC` (oldest first), exported through `database/db.py`. Viewer
scoping and entity-type restriction happen in the **service** layer, not SQL.

**Rationale**: `database/audit.py` today offers only per-entity/per-user lookups
(`get_pending_requests_by_type`, `get_user_pending_request`) — no cross-entity list with stable order
(FR-012). Keeping the SQL dumb (all pending, ordered) and doing authorization/enrichment in
`ManagementService` keeps the facade a thin data provider (R-ARCH-1/R-DATA-1) and the authority logic
in one testable place. `AuditRequestDTO` already exists (`database/dtos.py`, used by
`get_audit_request`).

**Alternatives considered**: authority-aware SQL (per-viewer WHERE clauses joining events/leads) —
rejected: pushes permission logic into the data layer, hard to test and drifts from the service-owned
authority model.

## D5 — Queue aggregator location: `ManagementService.get_moderation_queue`

**Decision**: `ManagementService.get_moderation_queue(user_id) -> List[QueueItemDTO]` fetches
`db.get_pending_requests()`, keeps only `event_approval` and `event_participation` types (this
feature's scope), filters by D1 authority (admin ⇒ drafts; organizer ⇒ participation for own events),
and enriches each surviving item with `entity_name` (`get_entity_name`, `management_service.py:322`)
and requester display name. Event lookups are grouped by distinct `event_id` to avoid per-item N+1.

**Rationale**: `ManagementService` already owns `resolve_request`, `get_entity_name`, and the
`get_pending_request_id` helpers — the queue is cohesive with them. A dedicated `ModerationService`
would import ManagementService + EventService + PermissionService for no isolation gain (Core
Philosophy V: minimal footprint). The web router is the moderation *domain seam*; the service stays
where the audit logic already lives.

**Alternatives considered**: new `ModerationService` module — deferred; revisit only if 017 grows a
larger moderation surface. Other request types (`group`/`topic`/`user`) are out of 016 scope and are
filtered out here; they belong to the 017 admin domain.

## D6 — Router seam: new `web/routers/moderation.py`

**Decision**: A new domain router `web/routers/moderation.py` mounted at `/api/moderation` with:
`GET /queue`, `POST /requests/{request_id}/resolve`, `GET /events/{event_id}/participants`,
`DELETE /events/{event_id}/participants/{user_id}`. Each endpoint re-checks authority server-side
before acting; identity via the existing `get_current_user_id` (`web/auth.py:61`).

**Rationale**: Router-per-domain (R-ARCH-7); keeps the 015 authoring router (`events.py`) focused on
create/edit. `require_admin` does **not** exist (verified: no `def require_admin` in the tree — it is a
feature-017 plan item), so 016 uses explicit per-action checks, which is exactly what D1's split
authority requires anyway (drafts vs. participation gate differently). Mounting mirrors
`web/main.py:31-33`.

**Alternatives considered**: extend `web/routers/events.py` — rejected: mixes authoring and moderation
concerns and their differing authority models in one file.

## D7 — Roster & removal reuse existing seams

**Decision**: Roster view reuses `db.get_event_details` (already returns `participants` list of
user_ids) + display-name mapping — **no new roster db method**. Participant removal calls
`EventService.apply_participation_change(bot, event_id, participant_id, intent="leave")` (feature 014),
which removes-only and refreshes announcements.

**Rationale**: `get_event_details` (`database/events.py:111-124`) already loads participants; adding a
roster query would duplicate it. `apply_participation_change` with `leave` is exactly the unified
consequence tail (remove-only, no silent enroll — BUG-4/R-SEC-3) and already refreshes announcements,
satisfying US3 without new mutation code.

**Alternatives considered**: a bespoke roster query + a direct `db.remove_event_participant` in the
router — rejected (duplicate read; direct write bypasses the 014 consequence point, R-DATA-1).

## D8 — Exactly-once resolution reused, not re-implemented

**Decision**: The web resolve endpoint calls `resolve_request` unchanged in its concurrency contract;
the feature-007 atomic CAS (`database/audit.py:47`, gated side-effects at `management_service.py:704`)
is the sole race guard. No new locking or transport-level idempotency is added.

**Rationale**: The CAS is transport-agnostic; web exposure does not weaken it (FR-005). Re-implementing
would be change-for-change (Core Philosophy IV). The concurrency test extends the existing
`test_audit_cas` pattern to prove exactly-once holds when invoked via the web path.

## D9 — Deep-link entry to the queue (optional, deferred)

**Decision**: A `start_param` → moderation-queue deep-link (roadmap Фаза-5 point 5) is **optional** and
not a spec requirement; the router MAY map it, but the P1 path is opening the queue via in-app nav.
The 015 `?ann_id=` entry contract is untouched.

**Rationale**: No FR mandates deep-link entry to the queue; keeping it optional avoids scope creep.
Nav-driven access satisfies US1. If added, it is a pure router mapping with no backend change.

**Alternatives considered**: making deep-link a hard requirement — rejected (not in spec; adds a
Telegram-side manual-test surface for no P1 value).
