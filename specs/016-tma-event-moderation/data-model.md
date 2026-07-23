# Phase 1 Data Model: TMA event moderation + audit-request queue

No schema migration. This feature reads existing tables (`audit_requests`, `events`, `event_leads`,
`event_participants`) and adds one cross-entity read + presentation DTOs. All display strings cross the
JSON boundary as **plain text**; the frontend renders them escape-by-default (feature-015 invariant).

## Existing entities (reused, unchanged)

### AuditRequest — `audit_requests` (via `AuditRequestDTO`, `database/dtos.py`)

| Field | Meaning |
|---|---|
| `id` | request id (CAS target) |
| `user_id` | requester (applicant / draft author) |
| `entity_type` | `event_approval` \| `event_participation` \| (others out of scope) |
| `entity_id` | target event id for both in-scope types |
| `status` | `pending` → `approved` \| `rejected` |
| `comment` | optional resolver comment |
| `created_at` | submission time (queue ordering key) |

**State transition (unchanged from feature 007 — reused, not re-implemented):**

```text
                 resolve_audit_request(status)   [atomic CAS: WHERE id=? AND status='pending']
pending ─────────────────────────────────────────► approved | rejected   (winner: rowcount==1)
   │                                                       loser: rowcount==0 → no side effects
   └─ side effects gated on the winning transition (management_service.py:704):
        approved + event_approval      → db.approve_event(entity_id) + sheets sync
        approved + event_participation → db.add_event_participant(entity_id, user_id) + sheets sync
                                         + AnnouncementService.refresh_announcements("event", entity_id)   ← [NEW узел-3]
                                         (NEVER notify_organizers_of_direct_join)
        rejected + event_approval      → db.delete_event(entity_id)  (draft removed)
        rejected + event_participation → (no roster change)
   in all approved/rejected cases → single user notification to request.user_id
```

### Event — `db.get_event_details(event_id) -> EventDTO`

Already returns `creator_id`, `leads: List[int]`, `participants: List[int]`, `title`, dates,
`is_approved`. Used as the source for the organizer predicate and the roster view — **no new query**.

## New backend surface

### `db.get_pending_requests() -> List[AuditRequestDTO]` (D4)

All `pending` rows, `ORDER BY created_at ASC`. Dumb read; no authorization, no entity-type filter, no
enrichment (those live in the service). Exported through `database/db.py`.

### `EventService.is_organizer_of_event(user_id, event_id) -> bool` (D2)

`True` iff `user_id == creator_id` **or** `user_id in leads` (from `get_event_details`). Read-only.
Distinct from `can_edit_event` (creator + global-admin, excludes leads).

### `ManagementService.get_moderation_queue(user_id) -> List[QueueItemDTO]` (D5)

Pipeline: `get_pending_requests()` → keep `entity_type ∈ {event_approval, event_participation}` →
authority filter (below) → enrich → return in original `created_at` order. Event details fetched once
per distinct `entity_id` (no per-item N+1).

## Authority matrix (server-side, R-SEC-3 / R-ARCH-7)

| Action | `event_approval` | `event_participation` / roster |
|---|---|---|
| Appears in viewer's queue (`get_moderation_queue`) | `is_global_admin(viewer)` | `is_organizer_of_event(viewer, event_id)` |
| Resolve (`POST /requests/{id}/resolve`) | `is_global_admin(viewer)` | `is_organizer_of_event(viewer, event_id)` |
| View roster (`GET /events/{id}/participants`) | — | `is_organizer_of_event(viewer, event_id)` |
| Remove participant (`DELETE …/participants/{uid}`) | — | `is_organizer_of_event(viewer, event_id)` |

A viewer holding both roles (global admin *and* organizer of some event) sees the union of what each
role authorizes. Identity is always `get_current_user_id` from validated init-data (R-SEC-1); no
client-supplied authority is trusted.

## Presentation DTOs (typed contracts, R-DATA-8)

### QueueItemDTO (queue element)

| Field | Type | Notes |
|---|---|---|
| `request_id` | int | CAS target for resolution |
| `type` | str | `event_approval` \| `event_participation` — drives status-by-shape |
| `event_id` | int | target event |
| `event_title` | str | plain text; frontend escapes on render |
| `requester_id` | int | applicant / draft author |
| `requester_name` | str | plain text; frontend escapes on render |
| `created_at` | str | submission time (display + ordering) |

### ParticipantDTO / roster response

| Field | Type | Notes |
|---|---|---|
| `event_id` | int | |
| `event_title` | str | plain text |
| `participants[]` | list | each: `{user_id, display_name (plain text), is_organizer: bool}` |
| `capacity` | int \| null | **presentational only** — no hard server limit is introduced (spec assumption) |

### ResolveRequest (input) / ResolveResponse

- Input: `{ status: "approved" | "rejected", comment?: string }`. Any other `status` → 400.
- Output: `{ success: bool, message: str }` — the `(bool, str)` contract from `resolve_request`
  surfaced structurally; success is the flag, never a substring of `message`.

### Participant-removal response

`{ success: bool, message: str }` from `apply_participation_change` (feature 014, remove-only).

## Validation & edge rules (from spec)

- Resolve of an already-resolved / vanished request → `resolve_request` returns `(False, …)`; endpoint
  surfaces "уже обработана" (idempotent, fails closed) — HTTP 200 with `success=false` (not a crash).
- Unauthorized resolve / roster / removal → HTTP 403; unauthorized items never appear in the queue.
- Remove a non-participant (stale button) → no-op via `leave_event_action` (no silent enroll).
- `event_title` / `requester_name` / `display_name` bearing markup → rendered as literal text
  (escape-by-default, inherited from 015).
- Queue > 7 items → frontend paginates/scrolls (bot lists > 7 paginate).
