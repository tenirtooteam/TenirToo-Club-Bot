# Tenir-Too Club Bot Changelog

All notable changes to the Tenir-Too Club Bot project are documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.15.2] - 2026-07-19

### Removed (dead code)
- **`ManagementService.toggle_event_participation`** (`services/management_service.py`) — the blind
  state-toggle that feature 014 superseded with the explicit-intent orchestrator
  (`EventService.apply_participation_change` + `add_event_participation_action` /
  `leave_event_action`). It had zero production and test callers (feature 007 moved `leave_event`
  off it; feature 014 unified the remaining surfaces), so removal is behavior-neutral. Module
  registry (`docs/knowledge/module-registry.md`, `PL-2.2.19`) updated to match. Full suite 429 green.

## [1.15.1] - 2026-07-19

### Added (web-bridge / TMA E2E test coverage without Telegram — Phase 5 groundwork)
- **In-process ASGI E2E harness for the web bridge** (`tests/test_web/conftest.py`): drives the
  real FastAPI app through the ASGI interface with no sockets and no `httpx` (unavailable — pip is
  SSL-intercepted in this env, and Starlette's `TestClient` requires it), so it stays within
  `R-TEST-2` ("no real network"). `forge_init_data` signs Telegram WebApp initData with a real
  HMAC-SHA256 test token, so `web.auth.validate_webapp_init_data` is exercised for real rather than
  bypassed; the `web_app` fixture patches the import-bound `web.auth.BOT_TOKEN`.
- **25 new web E2E tests** closing the two coverage gaps left after feature 014 (the crypto helper
  and both toggle endpoints were already covered):
  - auth wiring through a live endpoint — `X-TG-Init-Data` → `get_current_user_id` → route → HTTP
    status — valid plus seven rejection paths incl. anti-replay (`test_e2e_auth.py`, 8);
  - every previously-uncovered GET endpoint — dashboard init/topics/profile/events/event-view/
    admin-gates/roles-faq and announcement details 200/403/404/400 (`test_e2e_read.py`, 15);
  - a thin auth→toggle end-to-end cap that does not duplicate the feature-014 logic tests
    (`test_e2e_toggle.py`, 2).
- Full suite 404 to 429 green.
- (Local, gitignored) `local_scripts/tma_audit_server.py`: a browser dev/audit stand serving the
  real API + frontend with an injected `window.Telegram.WebApp` shim (offline; real Telegram SDK
  and web fonts stripped) and printing per-persona forged-initData URLs — the development vehicle
  for the feature-015 frontend rewrite.

## [1.15.0] - 2026-07-19

### Added (feature 014 — Backend unification: single participation orchestrator, Phase 5 enabler)
- **One method owns every consequence of a participation change** (`services/event_service.py`,
  new `EventService.apply_participation_change(bot, event_id, user_id, intent)`): the mutation is
  delegated to `ManagementService` (`R-DATA-1`), and on an actual state change it notifies
  organizers (join only, `R-DATA-11`) and refreshes ALL published announcement copies of the
  event. "Changed" is derived structurally (participant state before/after), not by matching the
  human message text. `ManagementService`/`AnnouncementService` are imported lazily inside the
  method to keep the event/announcement/management import triangle acyclic (`R-ARCH-4`).

### Changed (feature 014 — four surfaces unified onto the orchestrator)
- **All four direct-participation surfaces are now thin callers** carrying an explicit
  `join`/`leave` intent: the dashboard toggle endpoint (`web/routers/dashboard.py`), the
  announcement toggle endpoint (`web/routers/announcements.py`), the `ann_join` bot handler
  (`handlers/announcements.py`) and the event-card `leave_event` handler (`handlers/events.py`).
  Their access guards stay at the callsite; only the consequence tail is unified. The frontend
  (`web/frontend/app.js`) sends the explicit intent derived from the rendered participation state.

### Fixed (feature 014 — side-effect drift between web flows)
- **A dashboard "leave" now refreshes announcements** — previously it updated nothing, leaving
  every published copy stale.
- **An announcement-card change refreshes EVERY copy of the event**, not just the clicked message:
  the endpoint's hand-rolled single-message edit is gone (refresh fans out via
  `refresh_announcements`).
- **The web toggle can no longer silently join a non-participant** (bug №7, previously fixed only
  in bot handlers): both web endpoints dropped the toggle for explicit intent, so a stale "leave"
  button is a safe no-op, never an implicit join. Leave is remove-only everywhere (`R-SEC-3`).
- **A no-intent action is refused, not guessed**: an old-format announcement button (no explicit
  action code) gets a polite refusal with no mutation; the web endpoints reject a missing/invalid
  `action` with `400`.
- 13 new tests (method unit tests + per-surface characterization-to-parity + a cross-surface
  parity journey), format-agnostic (driven through the real producers). Full suite 391 to 404 green.

## [1.14.0] - 2026-07-18

### Fixed (feature 013 №18 — Broadcast Rate-Limiting & Reliability, Phase 3)
- **Mass PM broadcasts no longer drop recipients under flood-wait** (`services/notification_service.py`,
  `send_to_users`, FR-001..004): sends now route through a shared `_send_message_resilient` helper that
  honors Telegram `429`/`TelegramRetryAfter` (waits `min(retry_after, FLOOD_WAIT_CAP_SECONDS)` and
  retries) and paces sends with a cooperative `asyncio.sleep` (`R-DATA-7`). Previously the loop caught
  every exception and moved on, so the first flood-wait silently lost the tail of the list — an
  audit-result notification could never reach the admins it concerned. Unreachable recipients (blocked
  bot) are logged and skipped without aborting the run.
- **@all reaches every authorized member, not just the first 50** (`send_native_all`, FR-005..008): the
  authorized list is split into batches of `MENTION_BATCH_SIZE` and one message is sent per batch, each
  through the flood-wait-aware helper. The silent `authorized_users[:50]` truncation is gone — on a
  topic with 51+ authorized users, everyone past the 50th used to receive no push and nobody was told.
- **Anti-spam alert cache is bounded** (`_alert_cache`, `_prune_alert_cache`, FR-012/FR-013): the
  moderation PM-alert de-dup map now drops entries older than `ALERT_CACHE_TTL_SECONDS` (plus a
  hard-ceiling safety cap) on each alert, instead of accumulating one `(user, topic)` timestamp forever.
  The observable de-dup windows (60 s default-deny, 3600 s member-deny, now named constants) are
  unchanged.

### Added (feature 013 №5 — @all abuse guard)
- **@all is gated by role and rate-limited per sender** (`send_native_all` + `handlers/user.py`,
  FR-009..011): a mass ping now runs only for a moderator of the topic (`is_moderator_of_topic`) or the
  superadmin (`is_superadmin`/`ADMIN_ID`); other senders' `@all` broadcasts nothing while the trigger
  message is still deleted (silent, stealth-moderation style). A moderator's `@all` is limited to once
  per `ALL_MENTION_COOLDOWN_SECONDS`; the superadmin is exempt. Previously any write-capable member
  could ping up to 50 people, arbitrarily often, with no role or frequency check.
- Test isolation hook `reset_notification_state()` wired into the `db_setup` fixture (`R-TEST-1`); 16
  new unit/journey tests covering flood-wait retry, batching, the @all gate/cooldown, and cache bounding.

## [1.13.0] - 2026-07-17

### Added (feature 012 №16 — Persistent FSM Storage, Phase 3)
- **FSM state survives bot restarts** (`database/fsm_storage.py`, new `SQLiteStorage(BaseStorage)`):
  the dispatcher is now built on a custom aiogram storage backed by the shared SQLite connection
  instead of the in-process `MemoryStorage`. State (`state`) and data (all FSM keys, JSON-encoded) live
  in a new `fsm_storage` table created idempotently by `init_db`; `loader.py` wires
  `Dispatcher(storage=SQLiteStorage())`. Previously every restart wiped all FSM state — mid-input flows
  (topic rename, group add, search, date entry) broke silently, and the sterile-UI tracking keys
  (`last_menu_ids`, `last_menu_id`, `admin_onboarded`) were lost, leaving un-clearable menu clutter and
  re-triggering admin onboarding.
- **Composite-key isolation with a thread_id sentinel** (`fsm_storage.py`, `_pk`): the storage key
  (bot/chat/user/thread) is the primary key; `thread_id None` is normalized to `0` because SQLite treats
  `NULL` components of a composite PK as distinct, which otherwise produced duplicate rows on the main DM
  path (caught by a probe).
- **Deletion boundary preserves tracking keys** (`R-FSM-1`): a row is removed only when it is fully empty
  (`state IS NULL AND data == {}`); clearing state alone does not drop the row, so whitelisted tracking
  keys that outlive `clear_fsm_data_safely` are not destroyed. No TTL — records are restored verbatim
  regardless of age (a timestamp column is carried as passive metadata for future TTL only).
- **Facade boundary intact** (`database/db.py` re-exports `SQLiteStorage`; `R-ARCH-1`): services gain no
  domain access to FSM state; the schema stays an implementation detail. 10 new tests
  (`tests/test_database/test_fsm_storage.py`); the existing corpus passed unchanged (SC-006).

## [1.12.0] - 2026-07-14

### Changed (feature 011 №19 — Typed Callback Routing, Phase 3)
- **Single source of truth for callback format** (`callbacks.py`, new root module, `R-UI-14`):
  every parameterized callback route is now declared exactly once as an aiogram `CallbackData`
  factory. Keyboards build via `.pack()`, handlers match via `Factory.filter()`, and
  `UIService.generic_navigator` resolves via an exact-match registry — all three read the same
  declaration. Previously the format lived in two hand-written copies: `keyboards/*` assembled
  strings with f-strings while the navigator took them apart with substring checks, and nothing
  detected drift between them until a user clicked. The module is a leaf node (`R-ARCH-4`):
  it imports only `aiogram` and `enum`.
- **Declarative navigator dispatch** (`services/ui_service.py`, `R-UI-3`): the ~139-line chain of
  substring branches (`if "user_info" in cmd`) and positional extraction (`int(p[-1])`,
  `int(p[3])`) is replaced by an 89-line resolution path over a
  `{prefix: (Factory, render_fn)}` registry — serving 22 routes where the chain served ~15.
  Route lookup is exact `dict` access; parameters are read by field name. Signature widened to
  `generic_navigator(state, event, callback_data: str | CallbackData)`; the parameter name is
  unchanged.
- **Pagination is a declared field, not a string suffix** (`R-UI-14`, FR-005):
  `build_paginated_menu` now takes a `page_cb: CallbackData` instead of an opaque
  `callback_prefix: str`, building arrows via `page_cb.model_copy(update={"page": n}).pack()`.
  The parallel `UIService.PAGINATED_CMDS` name registry — a second source of truth for which
  routes "support" a page — was deleted; paginability now follows from a factory owning a `page`
  field.
- **Callback overflow fails loudly** (`keyboards/pagination_util.py`, `R-UI-11`): the manual
  `cb_data[:64]` truncation was removed. Telegram's 64-byte limit is enforced by `pack()`, which
  raises at keyboard-build time. Truncating mid-string used to emit a syntactically valid but
  semantically broken route that silently fell through to the navigation-error fallback; the
  overflow is now a test-time failure instead of a user-facing surprise. The realistic worst case
  measures 49 bytes of 64.
- **Defensive parsing moved into the filter** (`handlers/common.py`, `R-UI-11`): the hand-rolled
  `split(":")` ladder in `universal_help_handler`, which guessed among three legacy formats, is
  gone. `HelpCB.filter()` rejects malformed data via `(TypeError, ValueError)` — the same tuple
  aiogram's own `CallbackQueryFilter` catches, so "the filter accepted it but the navigator
  choked" is structurally impossible.

### Fixed (feature 011 — three live defects found while planning №19)
- **Paginated routes took the page number as the entity ID**: `p = callback_data.split("_")` ran
  over the full string including the `_pg_{n}` tail, so `int(p[-1])` returned the page. Clicking
  "next page" on the group list of topic 55 opened **topic 3**. Affected `mod_topic_groups`,
  `mod_gr_addlist`, `mod_users_manage`, `mod_topic_moderators`, `group_topics_list`. Two sibling
  routes had been silently patched around this with hardcoded positional indices (`p[3]`, `p[4]`)
  — inconsistently, 2 of 7.
- **The role-assignment topic picker was unroutable**: the prefix `topic_assign_pg_` itself
  contained `_pg`, which `split("_pg_")[0]` ate, so the route matched nothing and threw the admin
  back to the main menu. Its prefix is now `topic_assign`; the route name no longer carries a
  paginability marker.
- **Topic cards opened the wrong topic**: buttons were built as
  `topic_in_group_{t_id}_{group_id}` but consumed as
  `show_topic_detail(int(p[-1]), int(p[-2]))` against a `(topic_id, group_id)` signature —
  inverted. A topic opened from a group's list showed the card of whichever topic's ID matched
  the group's.
- **Pagination silently ignored on three screens**: "Мои топики" (`user_topics`), the moderator
  panel (`moderator`) and topic moderators (`mod_topic_moderators`) emitted page arrows whose
  page number was discarded — the list re-rendered page 1 forever. All three now honor it.

### Added (feature 011)
- `tests/test_services/test_callback_contract.py` — format invariants: registry completeness,
  prefix uniqueness, `pack()` inside 64 bytes at maximum field values, `unpack(pack(x)) == x`.
- `tests/test_services/test_callback_routing_characterization.py` — behavior lock for
  "button → screen", deliberately format-agnostic (drives real keyboards, never hardcodes a wire
  string). It caught a real `R-FSM-1` regression mid-migration: six top-level list screens lost
  their FSM reset when moving from the old `simple` dict into the registry.
- `tests/test_services/test_callback_routing_defects.py` — reproducing tests for the three
  defects above (`R-PROC-3`): red before, green after.
- `tests/test_services/test_callback_static_guard.py` — AST gate preventing the old mechanism
  from returning: no substring route matching, no positional extraction, no hand-built
  parameterized `callback_data`.
- `tests/test_journeys/test_callback_routing_journey.py` — the three scenarios end-to-end through
  a real `Dispatcher`, exercising the full keyboard → filter → navigator → screen chain.

### Notes (feature 011)
- **Scope**: the `event_*` / `ann_*` / `date_*` families and the `search_start_*` /
  `search_pick_*` parsing are **not** migrated — same defect class, tracked separately. The
  boundary is enforced by a test, not by convention.
- **`HelpCB` uses `sep="|"`, not the default `:`** — deliberately. It stores a *packed* return
  route in `back_data` (e.g. `group_topics_list:5:1`), and `pack()` forbids a factory's own
  separator inside a value; with `:` it would raise on every parameterized return. Do not unify
  the separator.
- The roadmap's claim that this work "removes a class of permission bugs" **was not substantiated**
  and was cut from scope. Value delivered is parse-safety; authority re-verification (`R-SEC-3`,
  `R-ARCH-7`) is untouched and remains mandatory. Typing guarantees `topic_id` is an integer, not
  that the user may see it.

## [1.11.0] - 2026-07-14

### Changed (feature 010 №17 — Sheets Sync Debounce & Task Ownership, Phase 3)
- **Owned, debounced background sync** (`services/management_service.py`): `_trigger_sheets_sync`
  no longer fires a bare `asyncio.create_task` (which could be GC'd mid-flight and swallow
  errors — the root cause behind the historical "Task was destroyed" test warnings and the
  007 test-patch). It now computes a per-type sync key (`mode`, or
  `event_participants:{entity_id}`), schedules an owned `asyncio.Task` held in the module-level
  `_pending_syncs` registry, and removes it via `add_done_callback`. A per-key debounce
  (`SHEETS_SYNC_DEBOUNCE_SECONDS = 2.0`) coalesces a burst of mutations into a single export:
  a new trigger for the same key cancels the prior pending task during its wait phase; the
  surviving task reads fresh DB state at export time. Export logic was extracted into
  `_run_sheets_export`. The `_trigger_sheets_sync(mode, entity_id)` signature and all ~77
  call-sites are unchanged.
- **Graceful shutdown flush** (`main.py`, `services/management_service.py`): new
  `ManagementService.flush_pending_syncs()` runs every pending export immediately (cancelling
  the wait phase) and is registered as a `dp.shutdown` hook, so the last coalesced change is
  not lost when the bot stops.
- **N+1 roles fetch removed** (`database/roles.py`, `database/db.py`): user export now uses the
  new batched facade method `get_roles_for_users(user_ids)` (single `WHERE user_id IN (...)`
  query, preserving the `superadmin` synthesis for `ADMIN_ID`) instead of a per-user
  `get_user_roles` loop.

### Out of scope (gated behind profiling, as in feature 008)
- Making the in-task `db.*` calls non-blocking (`to_thread`); full broadcast rate-limiting (№18).

### Tests
- New `tests/test_sheets_sync_debounce.py` (`R-PROC-3` TDD, RED→GREEN): batched roles fetch,
  task ownership + error logging, burst coalescing (one export per key), independent keys /
  distinct `event_participants` entities, and shutdown flush. Added
  `reset_sheets_sync_state()` and an async autouse drain fixture in `tests/conftest.py` for
  registry isolation and zero "Task was destroyed" warnings suite-wide (SC-006).
  Suite: 187 passed; semgrep / import-linter / ruff / governance gates green.

## [1.10.0] - 2026-07-14

### Changed (feature 008 №20 — Dedup Permission Layer, Phase 3)
- **Single point of direct-access check** (`database/permissions.py`, `database/db.py`):
  removed the dead duplicate `has_direct_access` — an identical
  `SELECT 1 FROM direct_topic_access WHERE user_id=? AND topic_id=?` to `can_write` with zero
  live callers (only an unused re-export in the `database.db` facade). `can_write` is now the
  sole direct-access predicate; the facade import and the `module-registry.md` entry were
  updated to match. Behavior of `can_write` is unchanged.
- **Honest `is_superadmin` semantics** (`services/permission_service.py`): the method now
  returns `user_id == ADMIN_ID` directly. The previous DB role loop was dead-by-result — for
  `ADMIN_ID` it always returned `True` (and its `logger.warning` + fallback `return True` were
  unreachable, since `database/roles.py::get_user_roles` synthesizes the `superadmin` role for
  `ADMIN_ID`). ADMIN_ID is the authoritative source of truth; the misleading docstring and the
  now-unused `logging` import/logger were removed. Observable result (`True` for `ADMIN_ID` /
  `False` otherwise) is preserved.

### Tests
- Characterization tests (`tests/test_permission_layer_dedup.py`, `R-PROC-3`): `can_write`
  access/no-access, duplicate-removed invariant, and `is_superadmin` (admin+role / admin
  without role / non-admin) — green before and after the cleanup (no behavior change).
  Suite: 176 passed; semgrep / import-linter / ruff / governance gates green.

## [1.9.0] - 2026-07-13

### Changed (feature 008 — DB Connection Reuse & Registration Caching, Phase 3)
- **Persistent DB connection** (`database/connection.py`): `get_conn()` now yields one
  process-wide reusable `sqlite3` connection (`_shared_conn`, lazily created) instead of
  opening + `PRAGMA journal_mode=WAL` + `PRAGMA foreign_keys=ON` + closing on every call. WAL
  and FK pragmas are applied once at creation; `get_conn()` no longer closes on exit and rolls
  back any dangling transaction if the body raises. Safe because all `db.*` operations are
  synchronous with no `await` inside a transaction — under the single-threaded asyncio loop no
  pool or lock is required. Cuts connection churn from ≈6 `connect`+PRAGMA cycles per incoming
  message to ≤1 (measured 5 → 1). New `close_shared_conn()` (shutdown / reinit); `init_db()`
  resets the shared connection first so a `DB_PATH` switch (tests) rebinds cleanly. The
  `database.db` facade signatures and all 77 call-sites are unchanged.
- **Registration cache** (`services/management_service.py`): `ensure_user_registered` and
  `register_topic_if_not_exists` consult a short-TTL in-memory memo
  (`REGISTRATION_TTL_SECONDS = 300`, `time.monotonic`) before hitting the DB, so a repeat
  message from an already-registered user/topic performs 0 registration lookups (was 2).
  Staleness is bounded by the TTL (name changes / external deletions re-applied within the
  window). `reset_registration_cache()` clears both memos; the `db_setup` fixture calls it for
  per-test isolation. Out of scope (PA-1 Ф3 verdict, gated behind profiling): `aiosqlite`
  migration and thread-pool offload.

### Tests
- TDD per `R-PROC-3`: failing reproducing tests written first. New
  `tests/test_database/test_connection_reuse.py` (connect-count per message ≤1) and
  `tests/test_services/test_registration_cache.py` (repeat-skip, TTL expiry re-hit, reset).
  Suite: 170 passed (was 165); semgrep / import-linter / ruff / governance gates green.

## [1.8.0] - 2026-07-09

### Fixed (feature 007 — Bot Correctness, Phase 2)
- **Date-range corruption** (`handlers/events.py`): confirming a multi-day hike like "10-15 июня" no longer truncates the stored start to a fragment ("10"). Decomposition of a human range into start/end parts now lives in `DateService.split_human_range` (month-inheritance, `R-CODE-5/6`) and is applied on both the create and edit confirmation paths. The edit path previously computed the split into throwaway variables and discarded it (dead branch removed).
- **Active-hikes list order & filtering** (`database/events.py`): `get_active_events(today=None)` now sorts by `start_iso` (ISO date) instead of raw human text, and excludes fully-past hikes (`COALESCE(end_iso, start_iso) >= today`), while keeping ongoing (started/not-ended) and undated (`start_iso IS NULL`) hikes visible. `EventService.get_active_events` forwards the optional `today`.
- **Non-text input crash** (`handlers/moderator.py`, `handlers/common.py`, `handlers/events.py`): five FSM input handlers (topic rename, direct-access search, entity search, hike editing title/dates) now guard `message.text` before `.strip()` — a photo/sticker/voice reply yields a graceful "введите текст" prompt instead of `AttributeError`.
- **Leave-hike audit bypass** (`services/management_service.py`, `handlers/events.py`): "Leave" now uses remove-only semantics via `ManagementService.leave_event_action` — a non-participant tapping a stale "Leave" button is no longer silently enrolled in bypass of the request→approval flow (`R-DATA-1`, `R-SEC-3`). The bot `ann_join` toggle channel is unchanged.
- **Request-resolution race (TOCTOU)** (`database/audit.py`, `services/management_service.py`): `resolve_audit_request` is now an atomic compare-and-swap (`UPDATE … WHERE id=? AND status='pending'`, returns `rowcount>0`); `resolve_request` gates all side effects and the user notification on the winning transition, so two concurrent admin resolutions produce exactly one action + one notification (idempotent; fails closed if the request vanished mid-flight).
- **Dead code & anonymous-sender guard**: removed no-effect expressions in `handlers/events.py` and `services/ui_service.py`; `AccessGuardMiddleware` now guards `event.from_user is None` (channel/anonymous posts) instead of crashing on `.id`.

### Tests
- TDD per bug (`R-PROC-3`): failing reproducing tests written first. New `tests/test_services/test_audit_cas.py`, `tests/test_handlers/test_fsm_nontext_guard.py`; extended `test_date_logic.py`, `test_event_edit_collision.py`, `test_event_contracts.py`, `test_participation_guard.py`, `test_middleware_pipeline_journey.py`. Suite: 165 passed (was 146).

## [1.7.0] - 2026-07-09

### Security (feature 006 — API Security Hardening, Phase 1)
- **Unified direct-join guard** (`EventService.check_direct_join_allowed`): all direct participation paths — web dashboard (`POST /api/dashboard/events/{id}/toggle`), web announcement toggle, and the bot `ann_join` button — now enforce a single rule (event approved + topic access where a topic context exists, reusing the Default-Deny gate `R-DB-1`). Closes the exploitable gap where any member with a valid session could join a *pending* event or one in a topic they cannot write to. The bot-card audit/request flow is intentionally unchanged.
- **WebApp anti-replay** (`web/auth.py`): `validate_webapp_init_data` now enforces `auth_date` freshness after the HMAC check — missing/unparseable or stale sessions (older than `config.WEBAPP_SESSION_TTL_SECONDS`, default 86400) are rejected, with a 300 s future clock-skew tolerance. A captured `initData` string is no longer valid indefinitely.
- **Callback defense-in-depth** (`handlers/common.py`): `confirm_execution` (delete group/topic/user/event, revoke role) and `perform_search_pick` (`mod_add`/`dir_add`) now re-check authority server-side before mutating — per-action via `PermissionService.is_global_admin` / `can_manage_topic` / `EventService.can_edit_event` (`R-ARCH-7`, no inline `ADMIN_ID`) — instead of trusting button delivery.

### Fixed
- **FastAPI global exception handler** (`web/main.py`): now returns a proper `JSONResponse(500, …)` instead of *returning* an `HTTPException` instance (which would itself raise during error handling).

### Changed
- **New config** `WEBAPP_SESSION_TTL_SECONDS` (env, default 86400; `<= 0` disables the freshness check).
- `perform_search_pick` parameter renamed `event` → `event_or_msg` (aligns with the `ban-direct-ui-calls` semgrep whitelist and the codebase convention).
- Two pre-existing tests updated to reflect the new (correct) behavior: `test_fsm_reset_after_search_pick` (actor made authorized) and `test_web/test_auth.py` (dynamic fresh `auth_date`). Suite: 146 passed, semgrep SAST gate green.

## [1.6.0] - 2026-07-06

### Added
- **Canonical pytest invocation** (`pytest.ini`): `pythonpath = .` + `testpaths = tests` make the bare `.\venv\Scripts\pytest` form work from the repo root (previously only `python -m pytest` collected — `tests/conftest.py` failed to import `database`). A subprocess collection smoke test (`tests/test_services/test_collection_smoke.py`) guards it (failing-first per `R-PROC-3`). `docs/knowledge/testing.md` gains a "Running the Suite" section.
- **`tenirtoo-plugin` registration**: the workspace engines are now a real Claude Code plugin (`.claude-plugin/plugin.json` manifest, repo-root `.claude-plugin/marketplace.json` `tenirtoo-local`, `enabledPlugins` in `.claude/settings.json`). Route B/C skills (`tenirtoo-proposal-analysis`, `tenirtoo-docs-update`) and the three subagents (`proposal-auditor`, `test-runner-and-debugger`, `cognitive-ux-auditor`, generated from `docs/knowledge/subagents.md`) are discoverable/delegable in fresh sessions. All Local-tier.
- **Semgrep SAST gate verified**: `docker compose --profile lint run --rm semgrep` runs green (5 rules, 46 files, 0 findings); `docs/knowledge/testing.md` documents the Docker channel as canonical and the host-side Windows skip as intended.

### Changed
- **Prompt linter false-positive fix** (`local_scripts/prompt_linter.py`): the plan-stage Cyrillic check now flags a token only when it contains ≥1 Cyrillic letter, so hyphens/dashes in `spec-kit`/`2026-07-04` no longer warn. Three regression cases added to `tests/test_prompt_linter.py`.
- **`requirements-dev.txt`**: `semgrep` pinned with `; sys_platform != "win32"` (no native Windows wheels) so dev-deps install cleanly on the Windows dev host.
- **Dead reference removed**: the `graphify-out/wiki/index.md` bullet dropped from `CLAUDE.md` (graphify CLI 0.8.49 produces no wiki). `AGENTS.md` § FILE REGISTRY row updated for the plugin.

## [1.5.0] - 2026-07-04

### Added
- **R-PROC-12 graph-first rule**: `RULES.md` gains a governed mandate — when `graphify-out/` exists, architecture/relationship/data-flow questions are answered via `graphify query`/`path`/`explain` before source reads, with an explicit CLI-absent fallback and the two-channel freshness contract.
- **`docs/knowledge/graph.md`**: knowledge-graph concept file (query/rebuild commands, freshness channels, model configuration, auth note) — future sessions of any assistant need nothing beyond the repository. Registered in `index.md`/`log.md` (bundle atomicity).
- **Graphify native integration**: `graphify claude install` (a `## graphify` section in `CLAUDE.md` + PreToolUse hooks in `.claude/settings.json`, `@AGENTS.md` shim intact) and `graphify hook install` (post-commit/post-checkout auto-rebuild of the code layer). Semantic extraction runs headlessly via the DeepSeek backend (`DEEPSEEK_API_KEY` in the `.claude/settings.json` `env` block, ~$0.02/pass); the `claude-cli`/Haiku backend is also wired but does not authenticate from sandboxed agent shells.
- **Docs-update graph refresh step**: the `tenirtoo-docs-update` skill now ends CMD-1/CMD-2 with `graphify extract . --backend deepseek` + `graphify cluster-only . --backend deepseek` (semantic layer) and its Output Validation checklist gained a "graph refreshed" item; Route C stays git-free.

### Changed
- **Spec-kit is the sole Route A**: the legacy RNA path is fully retired — `RNA-1` removed from `AGENTS.md` § COMMAND REGISTRY (recorded as retired in § INDEXING and `rule-map.md`), `R-PROC-1`/`R-PROC-2`/`R-PROC-4` name `plan.md`/`tasks.md` as the only canonical artifacts, and historical specs 001–003 keep their legacy artifacts as read-only records.
- **Prompt linter v3 (spec-kit-only)**: `PLAN_LEGACY_REQUIRED_H2S` and the `implementation_plan.md`/`task.md` fallbacks removed from `local_scripts/prompt_linter.py`; legacy filenames are now rejected. Linter unit/journey tests rewritten TDD-first (legacy-rejection red → green); code-layer graph rebuilt (1796 nodes, 3151 edges, 174 communities).

## [1.4.0] - 2026-07-03

### Added
- **Content-level rule retention guard**: `test_imperatives_map_to_rules` in `tests/test_governance.py` — every imperative legacy anchor must resolve to a real rule ID in `RULES.md` or carry an explicit `descriptive`/`retired` disposition in the new `tests/fixtures/imperative_dispositions.txt`; catches silent rule loss during future governance consolidations automatically.
- **Mandatory approval-gate template**: `.specify/templates/tasks-template.md` now requires a `HARD STOP` gate task at every chunk boundary (Foundational → US1, US1 → US2, etc.), citing `R-PROC-2`, so `/speckit-implement` cannot legally run past an approval point even if the plan author forgets one.

### Changed
- **Restored 3 rules lost during the 002 consolidation**, verbatim from git history (`8280d6f^`): `R-ARCH-9` (middleware pipeline order invariant, was PL-4.1), `R-UI-12` (sterile input entry points / isolated cancel keyboards, was CP-3.11), `R-UI-13` (admin-creation UX branching, was CP-3.47); `R-PROC-2` amended with the incremental plan-update principle (was CP-3.28.2).
- **Repaired `docs/knowledge/rule-map.md`**: 30 rows fixed (24 curated dispositions + 6 additional fallback rows found during repair); zero rows now target the generic `docs/knowledge/index.md` (was 10).
- **Prompt linter v2**: `local_scripts/prompt_linter.py` now prefers spec-kit artifacts (`plan.md`, `tasks.md`) with full backward-compatible fallback to the legacy RNA artifacts (`implementation_plan.md`, `task.md`) — kills the double-artifact-set problem for new features while historical features (001, 002) keep linting unchanged.
- **Canonized spec-kit as the Route A engine**: `AGENTS.md` registers the `speckit-*` command chain, marks `RNA-1` as a legacy alias, and retitles § RNA-BLUEPRINT to § PLAN CONTENT with an explicit RNA-Blueprint → `plan.md` section mapping. `RULES.md` `R-PROC-2`/`R-PROC-4` updated to name the canonical artifacts.

## [1.3.1] - 2026-07-02

### Removed
- **Legacy redirect files deleted**: `PROJECT_LOGIC.md` and `CONTEXT_PROMPT.md` (kept as thin redirect indexes in 1.3.0) are removed entirely — no industry convention defines these names, and legacy `PL-x.y`/`CP-x.y` anchor resolution is already fully served by `docs/knowledge/rule-map.md`. The obsolete `test_cp_corruption_absent` test (guarding a file that no longer exists) is removed; the governance duplicate-text scan and the bundle anchor-survival test now target `RULES.md` + `AGENTS.md`. README directory tree and AI Quick Start updated to the standard entry points (`AGENTS.md`, `RULES.md`, `docs/knowledge/`).

## [1.3.0] - 2026-07-02

### Changed
- **Governance Consolidation**: Replaced the three-file scattered governance (`GEMINI.md` + `PROJECT_LOGIC.md` + `CONTEXT_PROMPT.md`) with the industry-standard layout: a single tracked constitution at `AGENTS.md` (open agent-instructions standard; previously an ignored subagent registry), a unified rulebook `RULES.md` (60 rules across 9 domains, stable `R-<DOMAIN>-<n>` IDs, Tier A/B taxonomy with enforcement pointers, 16 duplicate rule groups merged), and full dissolution of descriptive content into `docs/knowledge/` (7 new concept files: architecture, middleware, fsm-protocol, db-patterns, constants, testing, features-overview). `PROJECT_LOGIC.md`/`CONTEXT_PROMPT.md` are now thin retired redirect indexes; `CLAUDE.md`/`GEMINI.md` are pure compatibility shims. Every historical `PL-x.y`/`CP-x.y` anchor resolves via `docs/knowledge/rule-map.md` (295 anchors). Route A pre-read reduced 89.8 → 35.1 KB (-61%) with zero rule loss.
- **Workflow Sync**: Updated `tenirtoo-docs-update` (producer contract v2: rules → RULES.md, description → bundle, process → AGENTS.md) and `tenirtoo-proposal-analysis` (ground truth: RULES.md + docs/knowledge/) skills. Filled the spec-kit constitution (`.specify/memory/constitution.md`).

### Added
- **Governance Validation Suite**: `tests/test_governance.py` (6 contract tests: rule-ID uniqueness, no duplicated rule text, rule-map completeness, Tier-B enforcement pointer existence, shim purity, constitution filled) plus the frozen rule inventory fixture `tests/fixtures/rules_inventory_baseline.txt`.
- **Knowledge Graph Update**: Rebuilt via `graphify --update` — 1195 nodes, 2536 edges, 135 communities (up from 1002/2309/66), now indexing governance content by rule ID.

## [1.2.0] - 2026-07-02

### Changed
- **Two-Tier Documentation Architecture**: Split the monolithic pre-read files into a thin normative core (`PROJECT_LOGIC.md`, `CONTEXT_PROMPT.md` — imperative rules only) and an OKF-style reference bundle (`docs/knowledge/`). Extracted the DDL schema (`[PL-3.1]` → `db-schema.md`), the module registry (`[PL-2.2]` → `module-registry.md`), and the design system (`[CP-4]` → `features/design-system.md`) into concept files with YAML front matter, an on-demand `index.md`, and a `log.md`. Route A pre-read reduced ~23% (89.8 → 69.5 KB) with zero imperative rules removed; all 250 `PL-x.y` anchors preserved.
- **Core Repair & Deduplication**: Fixed a merge corruption at the `[CP-2]`/`[CP-3]` boundary in `CONTEXT_PROMPT.md`, deduplicated `[CP-3.6]`/`[CP-3.7]` against their `PROJECT_LOGIC.md` homes via index citations, and compressed the `[CP-2]` feature list to one line per feature.
- **Workflow Sync**: Updated `GEMINI.md` (Route A pre-read, File Registry, Content Ownership, graphify onboarding) and the `tenirtoo-docs-update` skill (CMD-1/CMD-2 bundle routing with atomic index/log maintenance).

### Added
- **Knowledge-Bundle Validation Suite**: `tests/test_knowledge_bundle.py` (6 contract tests: front matter, index consistency, anchor survival, no dangling references, corruption absence, non-empty log) plus the frozen anchor fixture `tests/fixtures/pl_anchors_baseline.txt`.
- **Graphify Knowledge Graph**: Built a repository knowledge graph (1002 nodes, 2309 edges, 66 communities) into `graphify-out/` (git-ignored); onboarding now directs architecture questions to graphify queries first.

## [1.1.7] - 2026-06-19

### Added
- **Refinement Journey Test Suite**: Added a TDD journey test file `tests/test_journeys/test_ux_refinement_journey.py` validating onboarding loop protection, onboarding close button, search back navigation, moderator redirects, and terminology parity.

### Fixed
- **Admin Onboarding Loop**: Whitelisted `"admin_onboarded"` state key in `UIService.clear_fsm_data_safely` to prevent FSM clear from re-triggering onboarding welcome screens after entity updates.
- **Onboarding Escape Hatch**: Added a close button with `close_menu` callback to the admin onboarding welcome screen.
- **Search Results Escape Hatch**: Injected a back button (`⬅️ НАЗАД`) into `search_results_kb` using `search_context` (casted to string to satisfy Pydantic validations).
- **Moderator Toggle Redirect**: Changed the target redirect path in `mod_tgl_dir_` callback query handler to return to the active topic screen (`mod_topic_select_{topic_id}`) instead of the user list dashboard.
- **Terminology Alignment**: Replaced "Мероприятия Клуба" with "Походы Клуба" in help screens, menus, buttons, and web pages to unify terms.

## [1.1.6] - 2026-06-19

### Added
- **Artifact Prompt Linter**: Added a local command-line validation script `local_scripts/prompt_linter.py` to audit agent-developer plan structure (English language), task checklists (completion status), and walkthrough reports (Russian language).
- **Linter Test Suites**: Added unit tests in `tests/test_prompt_linter.py` and journey/integration tests in `tests/test_journeys/test_prompt_linter_journey.py` to verify prompt linter behavior and command-line execution return codes.

## [1.1.5] - 2026-06-19

### Added
- **Comprehensive E2E Journey Tests**: Introduced 6 new journey test files in `tests/test_journeys/` to close all 10 priority gaps: `/start` role-based routing, event lifecycle rejections/deletions/leaves, admin entity CRUD and template sync, moderator scoped flows, full middleware pipeline execution (UserManager, ForumUtility, AccessGuard, FsmButtonGuard), TMA FastAPI endpoints with bot reactivity, and UX Escape Hatch/fallback handlers.

### Fixed
- **WebApp Button AttributeError**: Fixed a bug in `build_paginated_menu` within `keyboards/pagination_util.py` where buttons using `web_app` (which have `callback_data=None`) caused an AttributeError due to missing guard checks before `callback_data.startswith("help:")` calls.

## [1.1.4] - 2026-06-19

### Added
- **Semgrep Architecture Enforcement**: Introduced 5 custom Semgrep rules in `semgrep-rules.yaml` enforcing: ban on dynamic imports, handler DB isolation, `state.clear()` prohibition, direct UI call ban in handlers, and mandatory `state: FSMContext` parameter detection. `[CP-3.60]` `[PL-6.26]`
- **Docker Compose Semgrep Service**: Added `semgrep` service (profile: `lint`) in `docker-compose.yml` using `returntocorp/semgrep` image for containerized architecture scans. Run via: `docker-compose --profile lint run --rm semgrep`.
- **Pytest Semgrep Wrapper**: Created `tests/test_services/test_semgrep_lint.py` with graceful skip when semgrep is not locally installed.

### Changed
- **Handler UI Sterility**: Refactored `handlers/admin.py` (sheets export/import) and `handlers/events.py` (date validation) to use `UIService.show_temp_message` instead of direct `callback.message.answer()` / `message.answer()` calls, eliminating `ban-direct-ui-calls` violations.
- **Linter Config Sync Rule**: Updated `[CP-3.59]` / `[PL-6.25]` to include `semgrep-rules.yaml` alongside `.ruff.toml` and `.importlinter` in the mandatory synchronization checklist.

## [1.1.3] - 2026-06-19

### Added
- **Ruff Banned API Verification**: Integrated flake8-tidy-imports (`TID251`) rule in Ruff configuration (`.ruff.toml`) to enforce handler layer separation by banning `aiogram.Router` imports in service/database layers and `aiogram.types` in `main.py`.
- **Architectural Rules**: Established rule `[CP-3.59]` / `[PL-6.25]` to require automatic linter configuration synchronization (`.ruff.toml`, `.importlinter`) when new features/layers are added in the future.

### Changed
- **Relocated Fallback Handler**: Decoupled catch-all `default_callback_handler` out of `main.py` into [handlers/errors.py](file:///c:/TenirTooClub_Bot/handlers/errors.py) to preserve bot entry point sterility.

## [1.1.2] - 2026-06-19

### Added
- **Rate-Limited PM Alerts for Members**: Added `send_member_deny_alert` in `NotificationService` to send a soft rate-limited (1 hour) warning to ordinary members when their messages are stealth-deleted.
- **Cognitive UX Audit Expansion**: Prepopulated test database with new mock roles (`moderator`, `direct_member`, `group_member`) and added 8 new scenarios for message moderation (admin immunity, unconfigured Default Deny, private chat bypass, and moderator permissions).
- **Security Fallback Handler**: Registered a global fallback callback query handler in `main.py` to intercept and answer unhandled callbacks (such as unauthorized clicks on admin options), preventing infinite loading indicators.

### Changed
- **Admin Default Deny Navigation**: Enhanced the default deny PM alert keyboard by replacing the generic close button with a direct link to the topic access settings interface (`all_topics_list`).
- **Explicit Search Confirmations**: Removed implicit search auto-picking upon single matches in `handlers/common.py` to enforce explicit confirmations and prevent accidental permissions assignment.

### Fixed
- **FSM State & Data Hygiene**:
  - Added FSM state reset (`await state.set_state(None)`) in `handlers/admin.py:process_group_add` immediately after group template creation.
  - Added FSM state reset in `handlers/common.py:perform_search_pick` after role or access assignment to prevent search state hangs.
  - Implemented `UIService.clear_fsm_data_safely` which strips user-defined context keys while retaining Sterile UI menu tracking stack, and expanded its usage across all major menu entry points.
  - Added FSM state reset in `handlers/admin.py:process_topic_name_save` upon successfully editing a topic name.
- **Search Picker Callback Parsing**: Fixed `search_pick_handler` parsing algorithm in `handlers/common.py` to correctly extract action names containing underscores (e.g., `dir_add` or `mod_add`).
- **Navigator Route Fix**: Fixed a navigation routing leak in `handlers/common.py:perform_search_pick` where moderators were incorrectly routed using admin-only dashboard buttons.
- **Pydantic Validation Error in Journey Tests**: Fixed mutating frozen Pydantic instances in journey tests by defining the test message content within the context initialization block.



## [1.1.1] - 2026-06-18

### Added
- `cancel_participation_request_action` in `ManagementService` and `delete_audit_request` in `database/audit.py` allowing users to cancel their pending participation requests.
- Interactive `[🚶 Отменить заявку]` button on event cards for pending requests.
- E2E and integration tests in `tests/test_handlers/test_ux_audited_flows.py` verifying access controls and cancellation flows.

### Fixed
- FSM state clearance: Replaced `state.clear()` with `state.set_state(None)` in `handlers/events.py` to preserve tracking metadata keys (`last_menu_ids`).
- Term Parity: Replaced all occurrences of "мероприятие" with "поход" in user-facing texts and notifications.
- UI Deadlocks: Added standard navigation footers to the date confirmation keyboard. Parametrized `get_date_picker_kb` and `get_event_cancel_kb` to allow dynamic back navigation.
- Access Control: Restricted viewing and participation actions for non-approved events to only admins and event creators.

## [1.1.0] - 2026-06-18

### Added
- Domain data transfer objects (`EventDTO`, `AuditRequestDTO`) to enforce strict type contracts in database queries.
- Global dispatcher error handler (`handlers/errors.py`) to intercept, log, and report unhandled exceptions.
- Static AST-based import boundary validator (`tests/test_services/test_import_lint.py`) to prevent direct database imports in presentation layers.
- In-memory `UserSessionSimulator` test helper with automated UX assertions (markup balance, anti-spam, and navigation footers).
- E2E event creation journey TDD test verifying the entire interactive creation flow.
- `FsmButtonGuardMiddleware` (`middlewares/fsm_button_guard.py`) to prevent execution of obsolete callbacks during active FSM states.
- Default Deny PM alerting system for administrators with 60-second rate-limiting in `services/notification_service.py`.
- Soft close stub logic in `handlers/common.py` providing seamless PM navigation recovery.
- Session-based onboarding screen for administrators inside `services/ui_service.py` to prevent UX confusion.
- Comprehensive E2E journey tests validating new UX and FSM protection features.

### Changed
- Refactored `database/events.py` and `database/audit.py` to return DTO instances instead of dict primitives (with backward-compatible dict interface).
- Eliminated direct `database.db` imports in handlers, delegating operations to `ManagementService` and `AnnouncementService`.
- Expanded autonomous UI fuzzer with unexpected command injection stress-tests during FSM states.

### Fixed
- Fixed relative date parsing unit tests failing due to system year mismatch by introducing static base date mock fixture.


## [1.0.0] - 2026-06-18

### Changed
- **Prompt Architecture Restructuring**: Migrated static orchestrators and prompts to workspace-local plugin/skills architecture.
  - Relocated proposal audit prompt to `.agents/plugins/tenirtoo-plugin/skills/proposal-analysis/SKILL.md` as `tenirtoo-proposal-analysis`.
  - Relocated documentation maintenance prompt to `.agents/plugins/tenirtoo-plugin/skills/docs-update/SKILL.md` as `tenirtoo-docs-update` with command `CMD-4` support for `CHANGELOG.md`.
  - Created `AGENTS.md` specifying `proposal-auditor` and `test-runner-and-debugger` subagents.
  - Created `CLAUDE.md` to automate agent onboarding and rule references.
  - Updated `GEMINI.md` and `CONTEXT_PROMPT.md` to coordinate routes, commands, automated local commits, and TDD error-debugging.
