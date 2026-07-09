# Phase 1 Data Model — API Security Hardening (Фаза 1)

**No database schema changes.** This feature adds no tables, columns, or indexes. The entities below are *logical* — a config value, a derived policy, and existing records read by the guard.

## Configuration

### `WEBAPP_SESSION_TTL_SECONDS`
- **Home**: `config.py`, read from env `WEBAPP_SESSION_TTL_SECONDS`.
- **Type**: int (seconds). **Default**: `86400` (24 h).
- **Semantics**: max age of a WebApp `auth_date`. `<= 0` disables the freshness check.
- **Companion constant**: future-skew tolerance = `300` s (module-level in `web/auth.py`, not env).

## Logical Policy: Direct-Join Access Rule

Encapsulated in `EventService.check_direct_join_allowed(user_id, event_id, topic_id)`.

| Input | Source | Meaning |
|---|---|---|
| `user_id` | authenticated caller (`get_current_user_id` / `callback.from_user.id`) | who wants to join |
| `event_id` | path / callback | target event |
| `topic_id` | announcement record (`announcements.topic_id`), or `None` for the dashboard path | topic context, if any |

**Decision function** (returns `(allowed: bool, reason: str)`):
1. `event = db.get_event_details(event_id)`; if `None` → `(False, "❌ Поход не найден.")`
2. if `not event.is_approved` → `(False, "❌ Запись закрыта. Поход на модерации.")`
3. if `topic_id is not None` and `not PermissionService.can_user_write_in_topic(user_id, topic_id)` → `(False, "🚫 У вас нет доступа к этому разделу клуба.")`
4. else → `(True, "")`

Idempotency of the actual join/leave stays in `ManagementService.toggle_event_participation` / `add_event_participation_action` (unchanged), which already guard duplicates.

## Session Freshness (validation-time entity)

`auth_date` field inside Telegram init-data (already parsed by `validate_webapp_init_data`, currently unused):
- **Type**: unix seconds (string in init-data).
- **Validation**: present ∧ parseable ∧ `now - auth_date <= TTL` ∧ `auth_date - now <= 300`.
- **On failure**: `validate_webapp_init_data` returns `None` → `get_current_user_id` raises 401 (existing behavior, `R-SEC-1`).

## Existing records read (no writes beyond current behavior)

- `events` (via `db.get_event_details`) — approval status.
- `direct_topic_access` (via `PermissionService.can_user_write_in_topic` → `db.is_topic_restricted` + `db.can_write`) — Default-Deny topic access (`R-DB-1`).
- `announcements` (via `db.get_announcement`) — supplies `topic_id` on announcement paths.
- `user_roles`/`roles` (via `PermissionService.is_global_admin` / `can_manage_topic`) — callback defense-in-depth authority.

## State transitions

None changed. Participation add/remove and audit-request lifecycle are untouched; this feature only adds *pre-mutation gates*.
