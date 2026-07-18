# Implementation Plan: Broadcast Rate-Limiting & Reliability

**Branch**: `013-broadcast-rate-limiting` | **Date**: 2026-07-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/013-broadcast-rate-limiting/spec.md`

## Summary

Feature 008 №18 + Phase-4 №5. Three latent data/memory defects in `services/notification_service.py`
plus an authorization gap on the `@all` trigger:

1. **`send_to_users`** sends PMs in a tight loop with no pacing and no handling of Telegram
   `429`/`TelegramRetryAfter`; the first flood-wait drops the tail of the recipient list silently
   (audit-result notifications lost).
2. **`send_native_all`** hard-slices `authorized_users[:50]`; on topics with 51+ authorized members
   everyone past the 50th is silently dropped from the mass-ping.
3. **`_alert_cache`** (class-level dict) accumulates one `(user_id, topic)` timestamp per pair forever;
   monotonic memory growth over process lifetime.
4. **`@all`** (`handlers/user.py:handle_all_mention`) performs no role check and no rate-limit — any
   write-capable member can ping up to 50 people, arbitrarily often.

**Technical approach** (Task RNA):
- Introduce a single flood-wait-aware send helper `_send_message_resilient(...)` inside
  `NotificationService`: on `TelegramRetryAfter`, `await asyncio.sleep(min(e.retry_after, cap))` then
  retry (bounded); on other `TelegramAPIError`, log and skip. Both `send_to_users` and the batched
  `send_native_all` route every outbound message through it, with a small cooperative pause between
  sends/batches. One mechanism, no duplicated logic.
- Rewrite `send_native_all` to chunk `authorized_users` into batches of `MENTION_BATCH_SIZE` and emit
  one message per batch, covering every authorized user; no silent truncation.
- Add `sender_id` to `send_native_all` and centralize the `@all` gate in the service: role check via
  `PermissionService` (`is_moderator_of_topic ∪ ADMIN_ID`) + a per-sender in-memory cooldown
  (superadmin exempt). Unauthorized/too-frequent calls return without broadcasting; the handler still
  deletes the trigger message (silent, stealth-moderation style).
- Bound `_alert_cache`: prune entries older than `ALERT_CACHE_TTL_SECONDS` on each alert call, with a
  hard-ceiling safety cap; observable dedup semantics (60 s / 3600 s windows) unchanged.
- Promote every timing/size literal to a named module constant (pacing, flood-wait cap/retries, batch
  size, cooldown, alert windows, TTL, cap).
- Add `reset_notification_state()` and wire it into the `db_setup` conftest fixture so the class-level
  caches (`_alert_cache`, cooldown store) are isolated per test.

Consumers outside the broadcast path are untouched: `send_to_users`'s call site in
`ManagementService` (audit approval) and the two `access_check` alert call sites keep their signatures.
`send_native_all` gains one required argument (`sender_id`) with exactly one call site
(`handlers/user.py`).

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: aiogram 3 (`Bot`, `TelegramRetryAfter`/`TelegramAPIError` from
`aiogram.exceptions`), asyncio, pytest / pytest-asyncio 0.23.6 (strict)

**Storage**: N/A for this feature — the `@all` cooldown and the alert dedup cache are deliberately
in-memory (soft anti-abuse and soft anti-spam; not required to survive restart, unlike FSM state in
feature 012). No schema change, no DB access added.

**Testing**: pytest with isolated temp DB (`db_setup`), `mock_bot`, journey tests in
`tests/test_journeys/`. Flood-wait simulated by a mock `bot.send_message` that raises
`TelegramRetryAfter` on selected calls then succeeds.

**Target Platform**: Linux/Windows single-host, single-process Telegram bot

**Project Type**: Single project (aiogram bot + FastAPI mini-app); this feature lives entirely in the
services + handlers layers.

**Performance Goals**: Correctness/reliability, not throughput. Club scale: recipient lists in the
hundreds, topics up to a few hundred authorized members. Pacing must not block the event loop
(cooperative `asyncio.sleep`, per R-DATA-7).

**Constraints**: No new external dependency, no new infra service (SC — reuse aiogram + asyncio only).
No blocking sleeps. Alert-dedup windows (60 s / 3600 s) observable behavior must not change.

**Scale/Scope**: 4 defects, 1 service module (`notification_service.py`), 1 handler
(`handlers/user.py`), 1 conftest fixture wire-up, new test module(s). One added parameter on one
service method with one call site.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Contextual Constraints (cited by ID per R-CODE-7; full text in `RULES.md`):

- **R-ARCH-1 (Database Facade)**: PASS — no new direct DB access; handler continues to reach data only
  through services (`PermissionService`, `NotificationService`). Broadcast authority stays behind the
  service facade (FR-014).
- **R-DATA-7 (Non-blocking targeted background I/O)**: PASS — pacing uses cooperative
  `asyncio.sleep`; the event loop is never blocked. Sends stay targeted (no `"all"` fan-out added).
- **R-DATA-9 (Strict ID hardening)**: PASS — `send_to_users` continues to `set()`-dedup after casting
  recipient IDs to `int`; the cooldown store keys on `int` sender IDs.
- **R-DATA-11 (Targeted notifications)**: N/A-aligned — this feature does not broaden any notification
  fan-out; it makes existing broadcasts complete and rate-limited.
- **R-PROC-3 (TDD for bug fixes)**: PASS by construction — all four items are defects; each gets a
  failing reproducing test before the fix (truncation-at-50, drop-on-429, unbounded-cache,
  ungated-@all). Reproducing tests named in `quickstart.md` and per-task in `tasks.md`.
- **R-TEST-1 (Fixture isolation)**: PASS — new `reset_notification_state()` wired into `db_setup`
  clears class-level caches per test; no writes to `bot.db`.
- **R-TEST-2 (No real network)**: PASS — all Telegram calls mocked via `mock_bot`; frozen-model rules
  respected.
- **R-TEST-3 (Journey coverage & mock-assertion parity)**: PASS — journey test covers
  Input(`@all`)→Gate→Broadcast with a negative (non-moderator) path; assertions check both `args` and
  `kwargs` of `bot.send_message`.
- **R-CODE-4 (Tilde code blocks)**: PASS — production code delivered in `~~~` blocks.
- **R-CODE-7 (Universal indexing)**: PASS — plan cites rule IDs; new/changed behavior gets in-code
  markers; no rule text copied.
- **R-PROC-2 (Blueprint before multi-file change)**: PASS — this plan is the blueprint; execution is
  chunked 3–5 steps with HARD-STOP gate tasks at chunk boundaries (generated by `/speckit-tasks`).
- **R-PROC-4 (Prompt-linter gates)**: this `plan.md` must pass the plan stage; `tasks.md` the
  checklist stage.

No principle violations. **Complexity Tracking is intentionally empty.**

Post-Design re-check (after Phase 1): still PASS — no new dependency, no new infra, no schema change,
no import-direction violation (`notification_service` → `permission_service` is acyclic:
`permission_service` does not import `notification_service`). Recorded in `research.md`.

## Project Structure

### Documentation (this feature)

```text
specs/013-broadcast-rate-limiting/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (in-memory entities)
├── quickstart.md        # Phase 1 output (validation guide)
├── contracts/
│   └── notification_service.md   # Service method + handler contracts
└── checklists/
    └── requirements.md  # Spec quality checklist (from /speckit-specify)
```

### Source Code (repository root)

Proposed Changes:

```text
services/
└── notification_service.py   # [MODIFY]
      - [NEW] module constants: BROADCAST_PACING_SECONDS, FLOOD_WAIT_CAP_SECONDS,
        FLOOD_WAIT_MAX_RETRIES, MENTION_BATCH_SIZE, ALL_MENTION_COOLDOWN_SECONDS,
        DEFAULT_DENY_WINDOW_SECONDS (=60), MEMBER_DENY_WINDOW_SECONDS (=3600),
        ALERT_CACHE_TTL_SECONDS (=3600), ALERT_CACHE_MAX_ENTRIES
      - [NEW] _send_message_resilient(bot, **kwargs): flood-wait-aware single send (429 → sleep(cap)
        → bounded retry; other TelegramAPIError → log+skip)
      - [NEW] _prune_alert_cache(now): drop entries older than ALERT_CACHE_TTL_SECONDS; enforce cap
      - [NEW] _all_cooldown: dict[int, float] + internal cooldown check (superadmin exempt)
      - [NEW] reset_notification_state(): clear _alert_cache and _all_cooldown (test isolation)
      - [MODIFY] send_to_users: route through _send_message_resilient, cooperative pacing, keep dedup
      - [MODIFY] send_native_all: add sender_id param; role+cooldown gate; batch by MENTION_BATCH_SIZE
        (no [:50] truncation); pace + resilient send per batch
      - [MODIFY] send_default_deny_alert / send_member_deny_alert: prune-on-call; use window constants

handlers/
└── user.py                   # [MODIFY]
      - [MODIFY] handle_all_mention: pass sender_id (message.from_user.id) to send_native_all; keep
        trigger deletion first (silent gate lives in the service)

tests/
├── conftest.py               # [MODIFY] call reset_notification_state() inside db_setup (isolation)
├── test_services/
│   └── test_notification_service.py   # [NEW] unit: 429 retry, pacing, dedup, batching, cache prune,
│                                       #       @all role gate, cooldown, superadmin exemption
└── test_journeys/
    └── test_all_mention_journey.py    # [NEW] journey: @all Input→Gate→Broadcast, negative path,
                                        #       args/kwargs parity (R-TEST-3)
```

**Structure Decision**: Single project. The entire change is confined to `services/notification_service.py`
(the broadcast facade), one call-site edit in `handlers/user.py`, one conftest wire-up, and new tests.
No new module or package is introduced; timing/size constants live as module-level names in the service
module (the project has no shared `constants.py`; this mirrors how feature 010 keeps its debounce state
and reset hook in `management_service`).

## Complexity Tracking

> No Constitution Check violations — this section is intentionally empty.
