# Tenir-Too Club Bot Changelog

All notable changes to the Tenir-Too Club Bot project are documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
