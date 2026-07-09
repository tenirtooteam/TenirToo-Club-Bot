# Tenir-Too Club Bot Changelog

All notable changes to the Tenir-Too Club Bot project are documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
