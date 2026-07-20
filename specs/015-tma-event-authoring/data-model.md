# Phase 1 Data Model: TMA event authoring + frontend modularization

This feature introduces **no new persisted schema**. It reuses the existing `events`
participation/lead tables through `database.db` and the existing sanitizing mutations. The "model"
here is the authoring request/response shape, the authority rule, and the frontend screen/route
model.

## Entities & shapes

### Event (authoring view)

Reuses the stored event. Fields relevant to authoring (all owned by existing mutations):

| Field | Type | Source of truth | Notes |
|---|---|---|---|
| `event_id` | int | `db.create_event` return | Assigned on create |
| `title` | string | user input | Sanitized in `create_event_action` / `update_event_details` (`html.escape`, ≤100) |
| `start_date` | string (human) | user input | Raw human form kept (R-CODE-6); e.g. "15 мая" |
| `end_date` | string (human) or "" | user input | Optional; range end |
| `start_iso` | ISO date or null | `DateService.parse_smart_date` | null when unrecognized → no calendar |
| `end_iso` | ISO date or null | `DateService.parse_smart_date` / `split_human_range` | null unless a range/end given |
| `creator_id` | int | validated init-data | Auto-registered as participant + lead on create |
| `is_approved` | int (0/1) | system | Create always `0` (moderation), parity with bot |

**Validation rules** (all server-side, no client business logic):
- `title` non-empty after trim → else reject with a clear message (FR-006).
- `date_text` parsed by `DateService.parse_smart_date`; unrecognized start is allowed but flagged
  "won't reach the calendar" (parity with bot), not a hard reject (FR-004).
- All sanitization (escape, length cap) happens inside `ManagementService` methods (R-DATA-1) — the
  router passes raw human strings straight through.

**Lifecycle (create)**: `create_event_action(...)` → (auto) add creator participant + lead →
`submit_request(creator, "event_approval", event_id)` → `notify_admins_for_approval(bot, event_id)`.
The endpoint reproduces this exact tail so a TMA-created event is indistinguishable from a
bot-created one (FR-002, SC-002).

**Lifecycle (edit)**: authority check (`can_edit_event`) → `update_event_details(...)`. No audit
notification on edit (parity with bot: editing does not re-trigger approval — `handlers/events.py:202`).

### Event-edit authority (derived rule, not stored)

`can_edit(user_id, event_id)` ≡ `db.is_global_admin(user_id)` OR `event.creator_id == user_id`
(`EventService.can_edit_event`). Recomputed server-side on every edit request; never sent by the
client. This rule is the authority-parity invariant made concrete. It is **also** serialized as a
derived, non-authoritative `can_edit` boolean in the event-details DTO (`GET /api/dashboard/events/{id}`)
so the UI can hide the edit control from users who cannot use it (D7 / U1); the true gate stays on
the `PUT`, which re-checks regardless of the flag.

### Mini App screen / route model (frontend)

| Screen | Route | Entry | Data source (existing GET) |
|---|---|---|---|
| Dashboard | `#/dashboard` | default (no query) | `GET /api/dashboard/init` |
| Events list | `#/events` | menu | `GET /api/dashboard/events` |
| Event card | `#/event/{id}` | list click | `GET /api/dashboard/events/{id}` |
| Announcement card | `#/ann/{id}` | **`?ann_id=` at bootstrap** | `GET /api/announcements/{id}` |
| Event form (create) | `#/event/new` | list "create" action | — (submits `POST /api/events`) |
| Event form (edit) | `#/event/{id}/edit` | card "edit" action | `GET /api/dashboard/events/{id}` seed |
| Topics / Profile / Admin / Roles | `#/topics` … | menu | existing dashboard GETs |

**Route invariants**:
- Bootstrap reads `?ann_id=` once; present → announcement card, absent → dashboard (FR-014).
- Every screen is a module owning its own render; back-navigation uses the history stack +
  `tg.BackButton` (FR-012).
- The edit control is shown only when the event-details DTO reports `can_edit true` (D7); this is a
  UX affordance, not the gate. The server is the sole authority (FR-008/009) — a user who reaches
  the form anyway (stale flag, direct call) is refused at submit with a 403.

## Data flow (authoring)

```text
TMA form
  → api.js (init-data header)
    → POST /api/events            (session-only)   ── create ──┐
    → PUT  /api/events/{id}        (can_edit_event) ── edit  ──┤
                                                               ▼
                     web/routers/events.py (thin adapter, DTO out)
                                                               ▼
        DateService.parse_smart_date / split_human_range  (R-CODE-5)
                                                               ▼
   ManagementService.create_event_action / update_event_details  (R-DATA-1, sanitizes)
                                                               ▼
                            database.db  (SQLite WAL)
   create tail: submit_request + notify_admins_for_approval(bot)   (parity)
```

## Non-goals (explicit)

- No participation-consequence code here — participation stays on
  `EventService.apply_participation_change` (feature 014, FR-016).
- No schema migration, no new table/column.
- No moderation/audit-queue screens (016), no admin/roles screens (017).
