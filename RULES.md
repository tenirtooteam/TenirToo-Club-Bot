# RULES — Tenir-Too Bot Unified Rulebook

Single source of truth for every behavioral rule. Each rule has a stable ID `R-<DOMAIN>-<n>`, a statement, a rationale (`Why`), a tier, and the legacy anchors it absorbs. **Tier A** = agent judgment required (full text). **Tier B** = enforced by CI/tooling (one line + `Enforced by`). Legacy `PL-x.y`/`CP-x.y` citations resolve here via [docs/knowledge/rule-map.md](docs/knowledge/rule-map.md).

Domains: ARCH (layers/facades/imports), DB, UI, FSM, CODE (coding & response mechanics), DATA (service/mutation/query flow), TEST, PROC (routes/process/git), SEC.

---

## ARCH — Architecture, Facades, Imports

### R-ARCH-1 [A] Database Facade is the exclusive data interface
**Rule**: All data operations MUST pass through `database/db.py` (`from database import db`). Direct imports from internal DB modules (`database/topics.py`, `database/members.py`, etc.) bypassing the facade are a critical architectural violation.
**Why**: A single data boundary keeps persistence swappable and testable; bypasses create hidden coupling.
**Legacy**: PL-2.4, PL-6.1, CP-3.7.1, CP-2.2(facade)

### R-ARCH-2 [A] Handler sterile isolation
**Rule**: Handlers (`handlers/*.py`) are strictly prohibited from importing the database facade. All data interaction MUST go through a service layer (`PermissionService`, `ManagementService`, `EventService`).
**Why**: Handlers manage UI/routing only; moving data logic to services keeps them thin, testable, reusable.
**Legacy**: PL-6.2, PL-2.1.1, CP-3.7.2, CP-3.57, CP-2.21

### R-ARCH-3 [A] Keyboard facade & sanctioned DB exception
**Rule**: `keyboards/__init__.py` is the exclusive import point for keyboard builders (`import keyboards as kb`). Keyboard modules (`keyboards/*_kb.py`) MAY import `database.db` directly for live rendering — the only sanctioned exception to R-ARCH-2. Never import an internal `keyboards/*_kb.py` module directly from any layer.
**Why**: Mirrors the DB facade at the keyboard layer; the render exception avoids a pointless service passthrough for read-only menu data.
**Legacy**: PL-2.5, PL-6.18, PL-2.1.4, CP-3.7.3, CP-3.8

### R-ARCH-4 [A] Import direction is one-way
**Rule**: Imports flow consumers→providers only: `handlers → services → database/db.py → database/*`; `keyboards/__init__.py → keyboards/*_kb.py → database/db.py`; `middlewares → services/permission_service.py → database/db.py`; `web/routers → services → database/db.py`. Any arrow reversal is an architectural violation.
**Why**: Acyclic layering prevents import cycles and keeps responsibilities separable.
**Legacy**: PL-2.3

### R-ARCH-5 [A] Keyboard import order is an invariant
**Rule**: The wildcard import order in `keyboards/__init__.py` (`admin_kb → user_kb → moderator_kb`) MUST NOT change — later imports shadow identically named functions.
**Why**: Wildcard re-export means order determines which duplicate-named builder wins; reordering silently swaps UI.
**Legacy**: PL-6.20

### R-ARCH-6 [A] Middleware private-chat guard; GROUP_ID is never a guard
**Rule**: `ForumUtilityMiddleware` and `AccessGuardMiddleware` MUST begin with `if event.chat.type == "private": return await handler(event, data)`. `UserManagerMiddleware` is exempt (operates on all chat types by design). `GROUP_ID` MUST NOT be used as a middleware guard — it is reserved for Telegram API calls in `handlers/admin.py`/`handlers/moderator.py`.
**Why**: The two group-branching middlewares need the guard; UserManager legitimately runs everywhere; GROUP_ID as a guard would wrongly restrict the bot.
**Legacy**: PL-4.5, CP-3.6, PL-7.3(guard clause)

### R-ARCH-7 [A] Access control via IsGlobalAdmin filter, no inline admin checks
**Rule**: Admin access is controlled by the router-level `IsGlobalAdmin` filter (`router.message.filter(...)` + `router.callback_query.filter(...)`), or `PermissionService.is_global_admin(user_id)`. Do NOT add inline `if user_id != ADMIN_ID: return` checks in handlers.
**Why**: One authoritative access gate; hardcoded ID checks in presentation code violate encapsulation and drift.
**Legacy**: PL-6.12, CP-3.16(access part)

### R-ARCH-8 [B] Handler DB-import boundary
**Rule**: Handlers importing `database/*` directly are prohibited. **Enforced by** `semgrep-rules.yaml` (`ban-db-in-handlers`), `.importlinter`, `tests/test_services/test_import_lint.py`, `tests/test_services/test_ruff_lint.py`.
**Legacy**: PL-6.24, CP-3.57(enforcement)

### R-ARCH-9 [A] Middleware pipeline order invariant
**Rule**: The sequential middleware pipeline is registered as `outer_middleware` on `dp.message` — the order (UserManager → ForumUtility → AccessGuard) is fixed and MUST NOT be changed.
**Why**: Later stages assume earlier guarantees (registration before access checks).
**Legacy**: PL-4.1

---

## DB — Database & Data Integrity

### R-DB-1 [A] Default-Deny access model
**Rule**: A topic is Closed unless present in `direct_topic_access`; in Closed state unauthorized messages are silently deleted. Once configured, access is strictly limited to listed users/groups. Global admins bypass only if `config.IMMUNITY_FOR_ADMINS` is True. UI showing topic status MUST indicate Default-Deny mode.
**Why**: Fail-safe security posture — access is never implicit.
**Legacy**: PL-3.2.1, PL-3.2.2, PL-3.2.4, CP-3.52

### R-DB-2 [A] Groups are non-runtime templates
**Rule**: The `groups` table is a template toolset for bulk-copying users into a topic's `direct_topic_access`; it is not a runtime permission source.
**Why**: Decouples runtime permissions from group membership — permissions stay explicit per topic.
**Legacy**: PL-3.2.3, CP-2.4

### R-DB-3 [A] Topic-rename dual sync
**Rule**: An admin topic rename MUST be applied to both the local DB (`db.update_topic_name`) and the Telegram API (`bot.edit_forum_topic`).
**Why**: A DB-only rename diverges from Telegram and confuses users.
**Legacy**: PL-6.11, CP-3.10

### R-DB-4 [A] Virtual superadmin encapsulation
**Rule**: The virtual `superadmin` role (from `config.ADMIN_ID`) is resolved inside `database/roles.py::get_user_roles`. UI/keyboard code MUST NOT manipulate `ADMIN_ID` to append the role manually — the DB response is pre-enriched.
**Why**: One place owns privilege derivation; duplicating it in UI causes audit sprawl if rules change.
**Legacy**: PL-6.19, CP-3.16(role part)

### R-DB-5 [B] Foreign-key integrity fuse
**Rule**: `PRAGMA foreign_keys = ON` on every connection; `init_db()` aborts with `RuntimeError` if FK support returns 0. Do not weaken this check. **Enforced by** `init_db` runtime fuse (`database/connection.py`); `tests/test_database/test_integrity_suite.py`.
**Legacy**: PL-3.1.1, CP-3.18

---

## UI — Sterile Interface, Navigation, Presentation

### R-UI-1 [A] sterile_show is the single UI gateway
**Rule**: All menu transitions MUST use `UIService.sterile_show(state, event, text, reply_markup)`. Direct `callback.message.edit_text(...)`, `message.answer(...)`, `edit_reply_markup(...)` from handlers are prohibited. Never edit a menu message into a status/log message — use `delete_msg` + `NotificationService` for feedback. (Announcement refresh via `edit_text` + `AnnouncementService.format_announcement_text` is the sanctioned dynamic exception.)
**Why**: One gateway owns `last_menu_id` tracking, cleanup, and state protection; manual API calls create "dirty chat".
**Legacy**: PL-6.4, PL-6.9, CP-3.19, PL-5.1.8

### R-UI-2 [A] FSM menu tracking
**Rule**: Every handler that sends a new menu MUST record its message ID in FSM `last_menu_ids`. Using `UIService.sterile_show` does this automatically.
**Why**: Untracked menus become undeletable "zombie" interfaces.
**Legacy**: PL-6.3

### R-UI-3 [A] Unified navigator for standard transitions
**Rule**: Standard UI returns/transitions SHOULD use `UIService.generic_navigator(state, event, callback_data)` rather than direct `sterile_show`. The navigator MUST use Defensive Routing (verify the route/keyboard exists before dispatch).
**Why**: Centralizes routing, prevents UI-logic leak and `NoneType` crashes on incomplete route maps.
**Legacy**: PL-6.5, CP-3.23, PL-5.1.10, PL-5.1.15

### R-UI-4 [A] Orphan message termination
**Rule**: Messages sent via direct `bot.send_message` outside FSM tracking (audit/participation notifications) MUST be finalized with `UIService.delete_msg(callback.message)` on interaction. Using `sterile_show` for orphan messages is a violation (risks zombie buttons).
**Why**: Orphans have no `last_menu_id`; `sterile_show` would mistrack state and strand buttons.
**Legacy**: PL-6.10, CP-3.37, PL-5.1.13

### R-UI-5 [A] Standardized navigation footer
**Rule**: Every keyboard MUST provide a navigation footer via `add_nav_footer` or `build_paginated_menu`: `[ ⬅️ Назад ] [ ❌ Закрыть ] [ ❓ ]`. The help button uses `help:{key}:{back_data}`; `back_data` MUST point to the current screen (defaults to `landing`).
**Why**: Consistent ergonomics; separates navigation from functional buttons.
**Legacy**: PL-5.1.14, CP-3.12

### R-UI-6 [A] Close-menu behavior
**Rule**: The `close_menu` handler MUST call `UIService.delete_msg(callback.message)` and clear tracking (`last_menu_id=None`, `last_menu_ids=[]`).
**Why**: Leaves the chat clean and keeps the sterile protocol synchronized.
**Legacy**: PL-5.4, CP-2.35(close)

### R-UI-7 [A] User-card consistency
**Rule**: All profile displays (admin/user/search) MUST use `UIService.format_user_card`.
**Why**: One formatter prevents UI drift across role/topic renderings.
**Legacy**: CP-3.17

### R-UI-8 [A] Heartfelt, content-isolated UI text
**Rule**: User-facing text MUST be community-oriented (avoid "management system", "entities", "permissions"). All long static/help strings MUST live in `services/help_service.py`; handlers MUST NOT hardcode help text.
**Why**: Warm tone fits the club; centralizing text simplifies localization and keeps handlers lean.
**Legacy**: CP-3.14, CP-3.36, PL-5.1.16

### R-UI-9 [A] Global handler uniqueness
**Rule**: Do not duplicate global callback handlers (e.g. `close_menu`) across handler files — place them only in `handlers/common.py`.
**Why**: Duplicate global handlers cause router dispatch conflicts and arbitrary double-execution.
**Legacy**: CP-3.15

### R-UI-10 [A] Announcement dispatcher indirection
**Rule**: Interactive buttons in broadcast announcements MUST route through the `announcements` registry (`ann_join:{announcement_id}`), never link directly to entity IDs (`event_join:42`).
**Why**: Indirection enables context-aware permission checks and uniform handling.
**Legacy**: CP-3.41, PL-5.1.17

### R-UI-11 [B] WebApp button & callback hardening
**Rule**: `web_app` buttons MUST be gated on non-empty `config.WEBAPP_URL`; colon-callback parsers MUST split defensively; `sterile_show` MUST catch `BUTTON_TYPE_INVALID` and fall back to a new message. **Enforced by** `tests/test_services/test_ui_integrity.py`, `tests/test_services/test_ui_fuzzer.py`.
**Legacy**: CP-3.53, PL-5.1.21

### R-UI-12 [A] Sterile input entry points
**Rule**: Every transition between independent FSM flows, disambiguation steps, or generation of new interactive elements MUST be preceded by `await UIService.terminate_input(state, message)`. Every FSM entry point that requires text input MUST use an isolated cancel keyboard (e.g., `get_event_cancel_kb`, `get_admin_cancel_kb`). Command-level handlers use the `@UIService.sterile_command` decorator.
**Why**: Centralizes redirect/cleanup/tracking; isolated cancel keyboards prevent bypass via functional buttons.
**Legacy**: CP-3.11

### R-UI-13 [A] Admin-creation UX branching
**Rule**: When an entity creation triggers an automatic audit notification to admins, the creation handler MUST NOT immediately show the final entity card to an admin creator — show a clean success message instead.
**Why**: Prevents double-notification clutter for admins.
**Legacy**: CP-3.47

---

## FSM — State Machine Hygiene

### R-FSM-1 [A] Never state.clear()
**Rule**: `state.clear()` is forbidden — it destroys `last_menu_id` and breaks the Sterile Interface silently. Use `state.set_state(None)` to nullify state and `UIService.clear_fsm_data_safely(state)` to purge custom keys (preserving `last_menu_ids`, `last_menu_id`, `admin_onboarded`).
**Why**: Clearing wipes UI-tracking keys with no runtime error — the next menu deploys without cleaning the previous.
**Legacy**: PL-5.3, CP-3.3, PL-5.1.23, CP-2.35

### R-FSM-2 [A] Don't reset state mid-chain
**Rule**: During multi-step input (e.g. Title→Dates) state MUST NOT be reset prematurely; `sterile_show` handles this by calling `terminate_input(reset_state=False)` for message events.
**Why**: Aggressive resets make the bot "forget" the flow, causing silent failures on the next input.
**Legacy**: CP-3.4, PL-5.1.4

### R-FSM-3 [B] State-parameter signature rule
**Rule**: Every handler calling a `UIService` method that needs `state` MUST declare `state: FSMContext`. **Enforced by** `semgrep-rules.yaml` (`missing-state-parameter`).
**Legacy**: PL-6.6, CP-3.20

### R-FSM-4 [B] state.clear ban
**Rule**: `state.clear()` calls are rejected statically. **Enforced by** `semgrep-rules.yaml` (`ban-state-clear`).
**Legacy**: PL-5.3(enforcement)

### R-FSM-5 [A] State-class scope
**Rule**: `AdminStates` is defined/used only in `handlers/admin.py`; `ModeratorStates` only in `handlers/moderator.py`. Never reference them from outside their file.
**Why**: Local state classes keep flows encapsulated and prevent cross-handler coupling.
**Legacy**: PL-6.16, PL-6.17

---

## DATA — Service, Mutation & Query Flow

### R-DATA-1 [A] All mutations traverse ManagementService
**Rule**: All entity mutations MUST go through `ManagementService` (contract `(bool, str)`). Handlers MUST NOT perform input validation (regex, string-splitting) or direct `db.*` writes. GET-only reads for keyboard rendering may stay direct via `database.db`. Every event creation MUST auto-register the creator as participant and lead.
**Why**: One layer sanitizes intent and applies business rules consistently; validation in handlers duplicates logic.
**Legacy**: PL-6.7, CP-3.21, CP-3.48, CP-2.19

### R-DATA-2 [A] Search delegation via SEARCH_REQUIRED
**Rule**: Handlers MUST honor the `"SEARCH_REQUIRED"` signal from `ManagementService` and delegate disambiguation to the shared search router in `handlers/common.py`. Fetching MUST use the `_fetch_search_results(s_type, query)` helper — do not inline per-type branches.
**Why**: Shared search prevents duplicated disambiguation logic across admin/moderator flows.
**Legacy**: PL-6.8, CP-3.22, PL-6.21

### R-DATA-3 [A] By-ID preference
**Rule**: When an integer entity ID is already known, handlers MUST use `*_by_id` service methods instead of string-parsing equivalents.
**Why**: Avoids redundant parsing/validation in hot routing paths.
**Legacy**: CP-3.33

### R-DATA-4 [A] Destructive confirmation protocol
**Rule**: Destructive operations (`delete_group`, `delete_user`, `revoke_role`, etc.) MUST pass a confirmation step via `UIService.get_confirmation_ui` and execute through `ManagementService.execute_deletion` in `handlers/common.py`.
**Why**: Telegram has no undo; forced confirmation prevents accidental data loss.
**Legacy**: PL-6.14, CP-3.9

### R-DATA-5 [A] Polymorphic cascade cleanup
**Rule**: When deleting any entity, verify both native FK cascades and polymorphic cleanups — services deleting a target MUST call `delete_announcements_by_target` (announcements use polymorphic links without native FKs).
**Why**: Polymorphic links bypass FK protection; missing cleanup rots data and strands buttons.
**Legacy**: PL-5.1.19, CP-3.43

### R-DATA-6 [A] Roles separation of concerns
**Rule**: Role information uses the Dashboard Pattern (FAQ/global lists in `common.py`); role management uses the Context Pattern (per-user actions in `admin.py`/`user_edit_kb`).
**Why**: Separating read-dashboards from write-actions keeps role flows predictable.
**Legacy**: PL-6.15

### R-DATA-7 [A] Non-blocking targeted background I/O
**Rule**: Network I/O (Google Sheets, webhooks) MUST run asynchronously; user-triggered syncs not needing immediate feedback SHOULD use `asyncio.create_task`. Use Targeted Sync modes (`"users"`, `"groups"`, `"events"`) over `"all"`.
**Why**: Blocking the event loop freezes the bot for all users.
**Legacy**: CP-3.27, PL-3.5

### R-DATA-8 [A] DTO contracts
**Rule**: Queries returning events/audit requests MUST return `EventDTO`/`AuditRequestDTO`; handlers access fields via property access with dict-fallback for legacy code.
**Why**: Typed models prevent field-shape errors while keeping backward compatibility.
**Legacy**: CP-3.56, CP-2.33

### R-DATA-9 [A] Strict ID hardening
**Rule**: User IDs from DB/config MUST be cast to `int` before set operations or collection logic.
**Why**: Mixed str/int from SQLite silently breaks dedup and membership checks.
**Legacy**: CP-3.39

### R-DATA-10 [B] No N+1 queries in UI
**Rule**: Keyboard builders iterating entity lists MUST batch-fetch (`get_topic_names_by_ids`) and use set lookups; direct `db.*` calls inside loops are prohibited. **Enforced by** `tests/test_services/test_ui_integrity.py`; performance-critical [PL-HI].
**Legacy**: PL-6.22, CP-3.31, CP-2.9, CP-2.18

### R-DATA-11 [A] Participation notifications are targeted
**Rule**: New participation requests (Audit) or direct joins (Quick Announcements) MUST notify only the event leads and creator — never broadcast to all global admins.
**Why**: Targeted alerts eliminate notification noise for uninvolved admins.
**Legacy**: PL-5.1.13(targeted), CP-3.49, CP-2.23

---

## CODE — Coding & Editing Mechanics

### R-CODE-1 [A] Full-block delivery
**Rule**: Always provide the FULL BLOCK of a function or logic section — never partial snippets.
**Why**: Partial snippets create integration ambiguity and silent insertion errors.
**Legacy**: CP-3.1

### R-CODE-2 [A] Precise, anchored replacement
**Rule**: When editing, target via unique anchors or approximate line numbers with the directive «Замените весь этот блок». Match targets MUST include the section header and ≥2 lines of surrounding context; simplifying anchors away is prohibited.
**Why**: Deterministic placement; high-fidelity anchoring prevents deleting neighboring structural lines.
**Legacy**: CP-3.2, CP-3.32

### R-CODE-3 [A] Verify before change
**Rule**: BEFORE any code change, view the target file and all related signatures (methods, keyboards, DB tables). AFTER modifying a strategic file (`.md`, `db.py`, `UIService`), re-view the whole modified section for truncation/logic drift. Writing calls without confirming their existence is prohibited.
**Why**: Memory-based edits cause phantom-call bugs and greedy-match deletions.
**Legacy**: PL-6.23, CP-3.24

### R-CODE-4 [A] Tilde code blocks only
**Rule**: Use only tilde code blocks (`~~~`). Triple backticks are forbidden.
**Why**: Backticks conflict with the internal documentation tooling's output format.
**Legacy**: CP-3.5

### R-CODE-5 [A] Smart date protocol
**Rule**: All date inputs MUST be processed via `DateService.parse_smart_date`; never ad-hoc regex/splitting for dates in handlers.
**Why**: Centralized parsing keeps natural-language support and ISO-8601 normalization consistent.
**Legacy**: CP-3.45

### R-CODE-6 [A] Presentation/data separation
**Rule**: Strings stored in the DB (`start_date`, `end_date`) MUST stay in raw human-entered form; all UI decorations (weekday suffixes, etc.) applied only at the presentation layer (`EventService.format_event_card`).
**Why**: Prevents data pollution and cumulative decoration on re-edit/re-display.
**Legacy**: CP-3.46

### R-CODE-7 [A] Universal indexing protocol
**Rule**: Every rule/pattern in governance files MUST carry a stable ID (`R-<DOMAIN>-<n>`; legacy `PL-x`/`CP-x` resolve via rule-map). IDs are used in the spec-kit `plan.md`/`tasks.md` and as in-code markers for traceability.
**Why**: Indexing lets plans cite by ID instead of copying text, saving context and enabling lookups.
**Legacy**: CP-3.40, PL-2.1.7, PL-2.1.8(index)

---

## TEST — Testing Standards

### R-TEST-1 [A] Declarative fixture-based testing
**Rule**: All tests MUST use `pytest` fixtures from `conftest.py` (no direct mocking in test bodies) and an isolated temporary DB via `db_setup`. Writing to `bot.db` during tests is strictly prohibited.
**Why**: Fixture isolation guarantees a clean schema per run and reproducibility.
**Legacy**: PL-2.2.50, PL-8.2.1, PL-8.5.1, PL-8.5.2

### R-TEST-2 [A] No real network in tests
**Rule**: All external (Telegram) calls MUST be mocked via `mock_bot`. aiogram 3 models are frozen — never assign `callback.answer = AsyncMock()`; use `patch("aiogram.types.CallbackQuery.answer", ...)` and attach `._bot = mock_bot`. Mocked `Message`/`Update` MUST include valid data (`date=datetime.now()`) for Pydantic V2.
**Why**: Deterministic offline tests; respects aiogram's frozen-model constraints.
**Legacy**: PL-8.5.3, PL-8.5.5, PL-8.5.6, PL-8.2.2

### R-TEST-3 [A] Journey coverage & mock-assertion parity
**Rule**: Cross-service/notification features MUST have journey tests (`tests/test_journeys/`) covering Input→Mutation→Notification→FSM transition, including a negative (unauthorized) path. Assertions on `bot.send_message`/UI feedback MUST check both positional `args` and keyword `kwargs`. Never hardcode entity IDs under `db_setup` — use the ID returned by creation.
**Why**: Unit tests miss integration bugs; args/kwargs parity avoids false negatives; isolated-DB IDs are non-deterministic.
**Legacy**: PL-8.3.1, PL-8.3.2, PL-8.3.3, CP-3.34, CP-3.50, CP-3.51, CP-3.44

### R-TEST-4 [A] Test after core changes
**Rule**: All modifications to core logic (Database/Services/Handlers) MUST be verified against the suite via `pytest`; new features/critical fixes MUST add tests in `tests/`.
**Why**: The suite is the single source of functional truth against regressions.
**Legacy**: CP-3.25, PL-8.1

### R-TEST-5 [B] Router detach & mocking sterility
**Rule**: Global routers in integration tests set `router._parent_router = None`; `callback.answer`/`sterile_show` are patched to avoid unmounted RuntimeError. **Enforced by** the passing state of `tests/test_journeys/` and `tests/test_handlers/`.
**Legacy**: PL-8.5.4, PL-8.3.4

---

## PROC — Process, Routes, Git, Environment

*(Full process narrative lives in AGENTS.md; these are the imperative rules it cites.)*

### R-PROC-1 [A] Route discipline (no conversational architecture)
**Rule**: Architectural/logic proposals MUST trigger Route B (PA-1/APA-1) and MUST NOT be answered conversationally. Implementation planning starts only via `/speckit-plan` following an approved audit (the legacy RNA-1 trigger was retired in feature 004). For any global/architectural feature, options and system impact MUST be aligned with the user (Шэф) before planning.
**Why**: Prevents protocol drift and unvetted changes to the Optimality Standard.
**Legacy**: CP-3.35, CP-3.30, CP-3.58, GEMINI§Route-B, GEMINI§Route-A(align)

### R-PROC-2 [A] RNA-Blueprint before multi-file change
**Rule**: Any feature/refactor/bugfix touching >1 file MUST have a blueprint plan: Base DNA, Task RNA, Contextual Constraints (indexed), Proposed Changes, numbered Execution Steps (TDD sub-step each), Verification. The sole canonical plan artifact is the spec-kit `plan.md` (blueprint content mapped per AGENTS.md § PLAN CONTENT) and the sole canonical checklist is `tasks.md`; the legacy `implementation_plan.md`/`task.md` were retired in feature 004 (historical specs 001–003 keep theirs as read-only records only). Execution runs 3–5 steps per chunk, then reports and awaits approval — `tasks.md` MUST contain an explicit HARD-STOP gate task at each chunk boundary. For bugs, the plan MUST name the reproducing test file/case. Plans are updated incrementally: do not rewrite the entire plan for a correction; update only the affected parts.
**Why**: Externalizing strategy before action prevents instruction drift and enforces TDD; incremental updates keep plan diffs reviewable; a gate task in the artifact itself makes the approval pause mechanical instead of relying on the plan author's memory.
**Legacy**: CP-3.28, GEMINI§RNA-BLUEPRINT, CP-3.28.2

### R-PROC-3 [A] TDD for bug fixes
**Rule**: A reported bug MUST first get a failing test reproducing it (verified failing), then the fix. Fixing without a reproducing test first is a process failure.
**Why**: Proves the bug exists and that the fix addresses it; guards against regression.
**Legacy**: GEMINI§Route-A(debugging), CP-3.28(bug)

### R-PROC-4 [B] Prompt-linter gates
**Rule**: Plan/checklist/report artifacts MUST pass their stage. Plan stage validates `plan.md`; checklist stage validates `tasks.md`; report stage validates `walkthrough.md`. The legacy `implementation_plan.md`/`task.md` fallbacks were removed in feature 004 — the linter now rejects them. **Enforced by** `local_scripts/prompt_linter.py --stage {plan|checklist|report}`.
**Legacy**: CP-2.36, GEMINI§Route-A(linter)

### R-PROC-5 [A] Git workflow GW-1
**Rule**: The AI MAY create local commits at milestones (`git add .`, concise English message). Automatic `git push` is strictly forbidden — push only on explicit user request. No git operations during documentation-update (Route C).
**Why**: Clean traceable local history; remote state stays under user control.
**Legacy**: CP-3.29, GEMINI§GIT-WORKFLOW

### R-PROC-6 [A] Changelog on every shipped change
**Rule**: Every feature/refactor/documentation shift MUST update root `CHANGELOG.md` (public) via the `tenirtoo-docs-update` CMD-4 command.
**Why**: Centralized, consistent version history without cluttering pre-reads.
**Legacy**: CP-3.54

### R-PROC-7 [A] venv isolation & local aux files
**Rule**: All development/testing/execution MUST use the `venv` (`.\venv\Scripts\python.exe`); commands assume an active environment. Files prefixed `_nogit_` are local-only scratch and are git-ignored.
**Why**: Environment parity prevents version conflicts; scratch stays out of history.
**Legacy**: CP-3.26, CP-3.55, PL-1.3

### R-PROC-8 [A] Response protocol
**Rule**: Respond in Russian; address the user as «Шэф»; be concise, no preamble, no restating code; if files were modified via tools, summarize rather than paste. Provide production-ready code in tilde blocks (R-CODE-4).
**Why**: Consistent, token-efficient interaction the user relies on.
**Legacy**: CP-6, GEMINI§RESPONSE-RULES

### R-PROC-9 [A] UI-transition trace discipline
**Rule**: When analyzing/changing UI transitions, perform a step-by-step trace of `last_menu_ids`, naming which method (`sterile_ask`/`terminate_input`/`sterile_show`) deletes which message ID at each stage.
**Why**: Prevents shallow "cleanup by magic" assumptions that cause double-deletion/regressions.
**Legacy**: CP-3.38

### R-PROC-10 [B] Linter configuration parity
**Rule**: When adding a module/layer/directory, update `.ruff.toml`, `.importlinter`, `semgrep-rules.yaml`. **Enforced by** the Docker `semgrep` service and `tests/test_services/test_import_lint.py` / `test_ruff_lint.py` / `test_semgrep_lint.py`.
**Legacy**: PL-6.25, CP-3.59

### R-PROC-11 [B] Architecture enforcement ruleset
**Rule**: Five semgrep rules enforce architecture: `ban-dynamic-imports`, `ban-db-in-handlers`, `ban-state-clear`, `ban-direct-ui-calls` (excludes `errors.py`, `announcements.py`), `missing-state-parameter`. **Enforced by** `semgrep-rules.yaml` via `docker-compose --profile lint run --rm semgrep` and `tests/test_services/test_semgrep_lint.py`.
**Legacy**: PL-6.26, CP-3.60

### R-PROC-12 [A] Graph-first for structural questions
**Rule**: When `graphify-out/` exists, questions about architecture, file relationships, call graphs, or data flow MUST be answered with a `graphify query`/`path`/`explain` first; opening source files is for verifying and detailing what the graph returned, not for first-pass discovery. If the graphify CLI is unavailable, fall back to reading source directly and STATE that degradation explicitly. Graph currency rides on two channels — code via the post-commit git hook, documentation/semantic layer via the docs-update skill (see `docs/knowledge/graph.md`); do not trust the graph when you have reason to believe both are stale.
**Why**: The graph is the cheapest correct map of the repository — querying first saves context and surfaces cross-module links a source dive misses; the explicit fallback keeps the rule from becoming a hazard when the tool is missing.
**Legacy**: —

---

## SEC — Security

### R-SEC-1 [A] WebApp init-data validation
**Rule**: TMA requests MUST validate Telegram init data via `web/auth.py::validate_webapp_init_data` (HMAC-SHA256); user identity comes from `get_current_user_id` (FastAPI dependency), never from client-supplied fields. Validation MUST additionally enforce `auth_date` freshness (reject sessions older than `config.WEBAPP_SESSION_TTL_SECONDS`, default 24h, with a small future clock-skew tolerance) — a valid HMAC alone is NOT sufficient (anti-replay).
**Why**: HMAC validation is the trust boundary for Mini App requests; without a freshness bound a captured init-data string is replayable forever.
**Legacy**: PL-2.2.51(auth), CP-2.28(secure)

### R-SEC-2 [A] Security fallback for unhandled callbacks
**Rule**: A global fallback handler MUST catch unhandled callback queries and show a warning alert, preventing infinite button loading for unauthorized users.
**Why**: Avoids stuck UI and information leakage on unrouted callbacks.
**Legacy**: CP-2.34, PL-5.5(resilience), CP-3.13

### R-SEC-3 [A] Single guarded write-path & server-side callback authority
**Rule**: Direct participation (event join/leave outside the audit-request flow) MUST pass through the single guard `EventService.check_direct_join_allowed` (event approved + topic-write access where an announcement topic exists, reusing `R-DB-1`); the direct channels (bot `ann_join`, web announcement toggle, web dashboard toggle) MUST NOT re-implement divergent checks. The bot event-card join stays a request/audit flow and is exempt. Destructive/grant callbacks that live on unfiltered routers (`handlers/common.py::confirm_execution`, `perform_search_pick`) MUST re-verify authority server-side via `PermissionService` (`is_global_admin`/`can_manage_topic`) or `EventService.can_edit_event` before mutating — never trusting which user received the button (`R-ARCH-7`).
**Why**: One guarded write-path prevents approval/access bypass drifting across channels; a button reaching a client is not proof of authority, so the mutation site must re-check.
**Legacy**: —

---

## Notes on merged duplicates (audit F1)

The following pre-consolidation duplicate pairs collapsed into single entries (most-restrictive text retained): PL-6.4↔CP-3.19→R-UI-1; PL-6.6↔CP-3.20→R-FSM-3; PL-6.7↔CP-3.21→R-DATA-1; PL-6.22↔CP-3.31→R-DATA-10; PL-6.14↔CP-3.9→R-DATA-4; PL-6.11↔CP-3.10→R-DB-3; PL-6.8↔CP-3.22→R-DATA-2; CP-3.28↔GEMINI§RNA→R-PROC-2; CP-3.29↔GEMINI§GW-1→R-PROC-5; CP-3.35↔GEMINI§Route-B→R-PROC-1; CP-6↔GEMINI§RESPONSE→R-PROC-8. Full anchor→ID resolution: [docs/knowledge/rule-map.md](docs/knowledge/rule-map.md).
