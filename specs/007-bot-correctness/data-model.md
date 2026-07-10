# Data Model — Feature 007 Bot Correctness

**No schema changes.** All fields and tables already exist. This document describes the entities
these fixes touch and the invariants they must uphold.

## Entity: Hike (`events` table → `EventDTO`)

| Field | Type | Role in this feature |
|---|---|---|
| `event_id` | INTEGER PK | identity |
| `title` | TEXT | — |
| `start_date` | TEXT (raw human) | **BUG-1**: MUST hold the full human start (e.g. `"10 июня"`), never a fragment (`"10"`). Stored raw (R-CODE-6). |
| `end_date` | TEXT (raw human) | **BUG-1**: MUST hold the full human end (e.g. `"15 июня"`) for ranges, else empty. |
| `start_iso` | TEXT `YYYY-MM-DD` \| NULL | **BUG-2**: primary sort key; NULL = undated (always shown). |
| `end_iso` | TEXT `YYYY-MM-DD` \| NULL | **BUG-2**: past-cutoff via `COALESCE(end_iso, start_iso)`. |
| `is_approved` | INTEGER 0/1 | active-list filter (unchanged). |

**Invariants**
- INV-1 (BUG-1): for a recognized range, `(start_date, end_date)` are the two *complete* human
  parts; for a single day, `end_date` is empty and `end_iso` is NULL.
- INV-2 (BUG-2): a hike is "active" iff `is_approved=1` AND
  (`COALESCE(end_iso, start_iso) >= today` OR `start_iso IS NULL`).
- INV-3 (BUG-2): active list ordered by `start_iso ASC`.

## Entity: Participation (`event_participants` table)

| Field | Role |
|---|---|
| `event_id`, `user_id` | membership link |

**Invariants**
- INV-4 (BUG-4): the "leave" operation is monotonic — it may transition
  *participant → non-participant* only, never the reverse. Creating membership is reserved to the
  approved request/audit flow (or the R-SEC-3 guarded direct-join channels).

## Entity: Approval Request (`audit_requests` table → `AuditRequestDTO`)

| Field | Type | Role in this feature |
|---|---|---|
| `id` | INTEGER PK | identity |
| `user_id` | INTEGER | notification target |
| `entity_type` | TEXT | dispatch: `event_approval` / `event_participation` / … |
| `entity_id` | INTEGER | acted-upon entity |
| `status` | TEXT | **BUG-5**: state machine `pending → approved | rejected`. |
| `comment` | TEXT | optional resolution note |
| `updated_at` | TIMESTAMP | set on resolution |

**Status transition (BUG-5)**

```text
        resolve_request(status)               [CAS: WHERE id=? AND status='pending']
pending ───────────────────────────► approved | rejected      (winner: rowcount==1)
   │
   └── any later/concurrent resolve ─► no-op (rowcount==0), reported "already handled"
```

**Invariants**
- INV-5: the `pending → X` transition succeeds for exactly one caller (atomic CAS).
- INV-6: DB side effects (approve event / add participant / delete draft) and the user
  notification fire **only** on the winning transition — zero duplicates.

## Cross-cutting: Message sender (tail)

`AccessGuardMiddleware` operates on `aiogram.types.Message`. `message.from_user` may be `None`
(channel posts / automatic messages). Invariant INV-7: a `None` sender passes through the guard
without raising (access control applies to real users only; consistent with R-DB-1 scope).
