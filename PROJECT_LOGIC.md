# PROJECT_LOGIC: Tenir-Too Access Control Bot

## [PL-1] PROJECT IDENTITY & STACK
- [PL-1.1] **System Name**: Tenir-Too Access Control Bot.
- [PL-1.2] **Python Version**: 3.11 (Required for optimal stability and dependency compatibility).
- [PL-1.3] **Virtual Environment**: Mandatory `venv` isolation to prevent dependency conflicts and ensure consistent environment across development and production.
- [PL-1.4] **Framework**: aiogram 3.4.1 (Asynchronous Python framework).
- [PL-1.5] **Testing Suite**: pytest 8.1.1 with pytest-asyncio, pytest-mock and pytest-cov.
- [PL-1.6] **Database Engine**: SQLite 3 with Write-Ahead Logging (WAL).
- [PL-1.7] **Core Purpose**: Granular access control and stealth moderation for Telegram Forum Topics within a Supergroup.
- [PL-1.8] **Web Bridge**: FastAPI with uvicorn for Telegram Mini Apps (TMA) integration.

---

## [PL-2] ARCHITECTURAL OVERVIEW

### [PL-2.1] Layered Architecture
Decoupled concerns across five layers:
- [PL-2.1.1] **Handlers** — UI and command routing. **Sterile Isolation**: prohibited from importing `database.db`.
- [PL-2.1.2] **Middlewares** — Logic interception pipeline.
- [PL-2.1.3] **Services** — Business logic. Gateway for all handler-to-DB interactions.
- [PL-2.1.4] **Keyboards** — Inline keyboard builders. Import from `database.db` directly to render data-driven menus. Exposed via wildcard re-export facade (`keyboards/__init__.py`).
- [PL-2.1.5] **Database** — Persistence via Facade pattern.
- [PL-2.1.6] **Tests** — Automated test suite using in-memory database and mocks.
- [PL-2.1.7] **Indexing Protocol** — Universal addressing system (`CP-x`, `PL-x`) for all rules and patterns. Used to minimize context bloat and ensure precise execution via Main AI.
- [PL-2.1.8] **Web Bridge** — FastAPI backend for Telegram Mini Apps. Shared service layer access with the bot.

### [PL-2.2] Module Registry
Complete file list with individual responsibilities and full function inventory:

- [PL-2.2.1] **main.py** — Entry point: `setup_logging`, DB initialization, router registration, outer middleware chaining, and concurrent execution of WebApp (uvicorn) and Bot polling via `asyncio.gather`. [CC-3]

- [PL-2.2.2] **loader.py** — Initializes `Bot` and `Dispatcher` with `MemoryStorage`.
- [PL-2.2.3] **config.py** — Environment variable loader and global constants definition. Centralizes all magic numbers, logging parameters, and WebApp configurations.
- [PL-2.2.4] **database/__init__.py** — Package initializer for DB facade pattern.
- [PL-2.2.5] **database/connection.py** — Connection context manager, WAL activation, and Foreign Key enforcement.
- [PL-2.2.6] **database/audit.py** — Audit requests management: `create_audit_request`, `get_audit_request`, `resolve_audit_request`, `get_pending_requests_by_type`, `get_user_pending_request`.
- [PL-2.2.7] **database/members.py** — User entity management: `add_user`, `user_exists`, `get_all_users`, `get_user_name`, `get_user_names_by_ids` (Batch-Fetch, N+1 fix), `update_user_name`, `delete_user`, `find_users_by_query`.
- [PL-2.2.8] **database/topics.py** — Forum topic management: `add_topic`, `rename_topic`, `get_topic_name`, `get_all_unique_topics`, `get_topic_names_by_ids` (Batch-Fetch), `delete_topic`.
- [PL-2.2.9] **database/groups.py** — Global templates management: `create_group`, `delete_group`, `get_all_groups`, `get_group_name`, `add_topic_to_group`, `remove_topic_from_group`, `get_topics_of_group`, `get_group_ids_by_topic`, `get_group_template_members`, `add_to_group_template`, `remove_from_group_template`.
- [PL-2.2.10] **database/roles.py** — Roles definitions and scoping: `get_role_id`, `grant_role`, `revoke_role`, `get_user_roles`, `get_moderators_of_topic`, `is_global_admin`, `is_moderator_of_topic`, `get_all_roles`, `get_role_name_by_id`, `get_global_admin_ids`.
- [PL-2.2.11] **database/permissions.py** — Direct access management: `grant_direct_access`, `grant_direct_access_bulk`, `revoke_direct_access`, `revoke_all_direct_access`, `get_direct_access_users`, `has_direct_access`, `can_write`, `get_topic_authorized_users`, `get_user_available_topics`, `get_direct_access_user_ids`, `get_topic_authorized_user_ids`.
- [PL-2.2.12] **database/events.py** — Expedition management: `create_event`, `update_event_details`, `approve_event`, `set_event_sheet_url`, `delete_event`, `add_event_lead`, `add_event_participant`, `remove_event_participant`, `is_event_participant`, `get_event_details`, `get_active_events`, `get_pending_events`. (Supports ISO-8601 storage with contract validation).
- [PL-2.2.13] **database/db.py** — Single facade re-exporting all database functions (including audit.py). **The only permitted import point for data operations.**
- [PL-2.2.14] **services/ui_service.py** — Централизованный UI lifecycle via `UIService`: `delete_tracked_ui`, `delete_msg`, `terminate_input`, `sterile_redirect`, `sterile_show`, `generic_navigator`, `get_landing_data(user_id, role_override)` (Traffic Controller), `show_admin_dashboard`, `show_moderator_dashboard`, `sterile_ask`, `show_temp_message`, `show_user_detail`, `show_group_detail`, `show_topic_detail`, `show_moderator_groups`, `show_moderator_moderators`, `sterile_command`, `get_confirmation_ui`, `format_user_card`.
- [PL-2.2.15] **services/event_service.py** — Expedition business logic: `format_event_card`, `notify_admins_for_approval`, `can_edit_event`, `get_active_events`, `get_pending_events`, `get_event_details`, `is_event_participant`.
- [PL-2.2.16] **services/google_sheets_service.py** — Asynchronous Google Sheets API integration via `GoogleSheetsService`. Methods: `export_users`, `export_groups`, `export_events`, `export_event_participants`, `import_users`, `import_groups`.
- [PL-2.2.17] **services/help_service.py** — Centralized help content registry and tooltip logic via `HelpService`. Methods: `get_help`.
- [PL-2.2.18] **services/management_service.py** — Domain Service for entity management. All methods return `(bool, str)`. Functions: `ensure_user_registered`, `add_user`, `create_group`, `assign_moderator_role`, `grant_direct_access`, `toggle_user_group_template`, `apply_group_to_topic`, `sync_group_to_topic`, `copy_topic_to_topic`, `grant_role`, `execute_deletion`, `update_user_name`, `create_event_action` (Internal Sanitization [PL-6.7]), `toggle_event_participation`, `add_event_participation_action`, `remove_event_participation_action`, `approve_event_action`, `submit_request`, `resolve_request` (Atomic Audit), `get_pending_request_id`, `get_user_pending_request_id`, `get_entity_name`, `search_entities`, `_trigger_sheets_sync`.
- [PL-2.2.19] **services/permission_service.py** — Unified Authorization Service: `is_superadmin`, `is_global_admin`, `is_moderator_of_topic`, `can_manage_topic`, `can_manage_user_roles`, `get_manageable_topics`, `can_user_write_in_topic`, `get_user_display_name`, `get_role_name`, `get_role_id`, `get_access_sets`.
- [PL-2.2.20] **services/notification_service.py** — Notification logic: `send_native_all`, `send_to_users` (Targeted Broadcast).
- [PL-2.2.21] **services/callback_guard.py** — `safe_callback()` decorator factory.
- [PL-2.2.22] **handlers/common.py** — Shared logic & search. Functions: `cmd_help`, `close_menu_handler`, `roles_dashboard_menu`, `roles_faq_view`, `list_users_with_roles`, `search_start_handler`, `search_query_handler`, `search_results_pagination`, `search_pick_handler`, `perform_search_pick`, `confirm_execution`, `universal_help_handler` (Robust Parsing [G-DNA]), `show_help_view`. **Decoupled**: Uses `ManagementService.search_entities`.
- [PL-2.2.23] **handlers/admin.py** — Superadmin flows. FSM: `waiting_for_group_name`, `waiting_for_topic_name`, `waiting_for_user_data`, `waiting_for_new_name`.
- [PL-2.2.24] **handlers/moderator.py** — Moderator flows. FSM: `waiting_for_topic_name`, `waiting_for_user_data`, `waiting_for_direct_access_user`.
- [PL-2.2.25] **handlers/events.py** — Expedition flows (Events). FSM: `waiting_for_title`, `waiting_for_dates`, `confirm_date`, `waiting_for_end_date`. Functions: `show_events_list`, `show_pending_events`, `start_event_creation`, `process_event_title`, `process_event_dates`, `process_date_preset`, `process_date_retry`, `process_date_confirm`, `process_date_add_end_start`, `process_event_end_date`, `view_event`, `join_event`, `leave_event`, `delete_event_init`, `approve_event_handler`, `reject_event_handler`, `show_event_card`.
- [PL-2.2.26] **handlers/user.py** — User flows: Unified `/start` (Traffic Controller), profile, topics.
- [PL-2.2.27] **middlewares/access_check.py** — Sequential chain: `UserManagerMiddleware` → `ForumUtilityMiddleware` → `AccessGuardMiddleware`.
- [PL-2.2.28] **keyboards/admin_kb.py** — Admin keyboards: `main_admin_kb`, `get_admin_cancel_kb`, `all_topics_kb`, `group_topics_list_kb`, `available_topics_kb`, `groups_list_kb`, `group_edit_kb`, `template_action_topic_select_kb`, `users_list_kb`, `user_edit_kb`, `user_groups_edit_kb`, `roles_dashboard_kb`, `role_selection_kb`, `user_roles_manage_kb`, `topic_selection_for_role_kb`, `back_to_roles_dashboard_kb`, `search_results_kb`, `confirmation_kb`, `simple_back_kb`.
- [PL-2.2.29] **keyboards/moderator_kb.py** — Moderator keyboards: `get_mod_cancel_kb`, `moderator_topics_list_kb`, `moderator_topic_menu_kb`, `topic_moderators_kb`, `moderator_search_kb`, `moderator_topic_groups_kb`, `moderator_unattached_groups_kb`.
- [PL-2.2.30] **keyboards/pagination_util.py** — Universal keyboard utilities: `build_paginated_menu` (Paginated lists with search support), `add_nav_footer(builder, back_data=None, include_close=True, help_key=None)` (Split footer protocol [PL-5.1.14]).
- [PL-2.2.31] **database/announcements.py** — Dispatcher registry for broadcasted interactions (Events, Gear, Fees). Methods: `create_announcement`, `get_announcement`, `delete_announcements_by_target`, `update_announcement_metadata` (Linking record to physical Telegram message).
- [PL-2.2.32] **services/announcement_service.py** — Logic for quick announcements and unified dispatcher processing. Methods: `create_quick_event`, `format_announcement_text` (Dynamic UI builder), `broadcast_event_announcement`.
- [PL-2.2.33] **handlers/announcements.py** — Command-level entry for `/an` and unified callback `ann_join`.
- [PL-2.2.34] **keyboards/event_kb.py** — Expedition keyboards: `get_events_list_kb`, `get_event_card_kb`, `get_event_moderation_kb`, `get_event_cancel_kb`, `get_date_picker_kb`, `get_date_confirm_kb`, `get_audit_log_kb`.
- [PL-2.2.35] **keyboards/user_kb.py** — User keyboards: `user_main_kb`, `user_topics_list_kb`, `user_profile_kb`, `user_topic_detail_kb`.
- [PL-2.2.36] **local_scripts/dev_run.py** — Developer-only hot-reload runner.
- [PL-2.2.37] **local_scripts/Gemini_maker.py** — Developer-only AI context packager. Regenerates `local_scripts/full_project_code.txt`.
- [PL-2.2.38] **tests/conftest.py** — Global test infrastructure: isolated DB (`db_setup`), mock bot, and context factories (`create_context`, `create_callback`). [PL-HI]
- [PL-2.2.39] **tests/test_database/test_event_contracts.py** — Contract tests ensuring DB-to-Dict mapping consistency.
- [PL-2.2.40] **tests/test_database/test_integrity_suite.py** — Integrity tests for DB relations (FK Cascade and manual cleanup).
- [PL-2.2.41] **tests/test_handlers/test_event_edit_collision.py** — Regression suite for FSM bypass and collision prevention.
- [PL-2.2.42] **tests/test_handlers/test_permission_scenarios.py** — Declarative security boundary tests (Admin/Moderator).
- [PL-2.2.43] **tests/test_handlers/test_admin_flow.py** — Integration tests for Admin CRUD operations (Groups/Topics).
- [PL-2.2.44] **tests/test_handlers/test_announcement_logic.py** — Logic tests for quick announcements and dispatching.
- [PL-2.2.45] **tests/test_journeys/test_default_deny_journey.py** — Verification of "Closed by Default" logic, including admin immunity bypass.
- [PL-2.2.46] **tests/test_services/test_date_logic.py** — Deep unit tests for DateService parsing edge cases.
- [PL-2.2.46] **tests/test_services/test_sheets_sync.py** — Resilience tests for Google Sheets API error handling.
- [PL-2.2.47] **tests/test_services/test_ui_fuzzer.py** — Autonomous Deep-UI Fuzzer for recursive menu exploration.
- [PL-2.2.48] **tests/test_services/test_ui_integrity.py** — UI Integrity and Hardening tests: callback length, WebApp URL safety, HelpService coverage.
- [PL-2.2.49] **obsolete_tests/** — Directory containing legacy and broken tests moved for reference during the 'Total Shield' transition.
- [PL-2.2.50] **[PL-HI] Declarative Testing Standard**: All tests MUST use `pytest` fixtures for setup. Direct mocking in test functions is deprecated in favor of `conftest.py` factories. Every test run MUST use an isolated temporary database (`db_setup` fixture).
- [PL-2.2.51] **web/auth.py** — Security layer: `validate_webapp_init_data` (HMAC-SHA256 validation), `get_current_user_id` (FastAPI dependency for user auth). [CC-3]
- [PL-2.2.52] **web/main.py** — FastAPI application: Unified logging, router inclusion (`announcements`, `dashboard`).
- [PL-2.2.53] **web/routers/announcements.py** — Web API for announcements: `get_announcement_details`, `toggle_participation`. [CC-1]
- [PL-2.2.54] **web/routers/dashboard.py** — Web API for personal cabinet: `get_dashboard_init`, `get_user_topics`, `get_user_profile`, `get_all_events`, `get_event_view`, `toggle_event_participation_direct`.
- [PL-2.2.55] **web/frontend/** — Static assets for Mini App: `index.html` (Multi-view UI), `style.css` (Premium Grid/Glassmorphism), `app.js` (Navigation & API Bridge).
- [PL-2.2.56] **tests/test_web/test_auth.py** — Unit tests for Web Bridge authentication (HMAC-SHA256).
- [PL-2.2.57] **tests/test_journeys/test_tma_integration.py** — Journey test for WebApp-to-Bot reactivity.
- [PL-2.2.58] **tests/test_web/** — Directory for Web Bridge layer tests.

### [PL-2.3] Import Dependency Graph
Permitted import direction — top consumers to bottom providers. Any arrow reversal is an architectural violation.

~~~
handlers/*              →  services/*                    →  database/db.py  →  database/(members|topics|groups|roles|permissions).py
keyboards/__init__.py   →  keyboards/*_kb.py             →  database/db.py  →  database/(members|topics|groups|roles|permissions).py
middlewares/*           →  services/permission_service.py →  database/db.py
web/routers/*           →  services/*                    →  database/db.py
main.py                 →  handlers/*, middlewares/*, database/db.py (init_db only), web/main.py
database/__init__.py    →  database/db.py
database/db.py          →  database/connection.py (init_db, get_conn re-export)
                        →  database/(members|topics|groups|roles|permissions).py
~~~

### [PL-2.4] Database Facade
[PL-2.4.1] `database/db.py` is the exclusive interface for all data operations. Direct imports from files like `database/topics.py` or `database/members.py` are a critical architectural violation.

### [PL-2.5] Keyboard Facade
[PL-2.5.1] `keyboards/__init__.py` is the exclusive import point for all keyboard builders. Handlers must use `import keyboards as kb` and access all functions via `kb.*`. This mirrors the Database Facade pattern at the keyboard layer. The strict top-down wildcard import order within `__init__.py` determines conflict resolution.

### [PL-2.6] Context Manager Connectivity
[PL-2.6.1] `database/connection.py` uses a custom `@contextmanager` (`get_conn`) for deterministic connection handling and guaranteed closure on both success and exception. WAL mode is activated on every individual connection open, not globally at startup. `DB_PATH` is resolved relative to `connection.py`'s own location, always placing `bot.db` inside the `database/` directory regardless of the working directory at launch.
[PL-2.6.2] `loader.py` initializes the `Bot` instance with `DefaultBotProperties(parse_mode="HTML")`. This ensures that all messages sent via the bot (including direct `bot.send_message` calls) support HTML formatting by default, providing a systemic safety net for UI decorations.

---

## [PL-3] DATABASE SCHEMATICS & INTEGRITY

### [PL-3.1] Entity Relationship Model — DDL

~~~sql
CREATE TABLE IF NOT EXISTS roles (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id  INTEGER,
    role_id  INTEGER,
    topic_id INTEGER NULL,
    PRIMARY KEY (user_id, role_id, topic_id),
    FOREIGN KEY (user_id)  REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id)  REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES topic_names(topic_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS direct_topic_access (
    user_id  INTEGER,
    topic_id INTEGER,
    PRIMARY KEY (user_id, topic_id),
    FOREIGN KEY (user_id)  REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES topic_names(topic_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS groups (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS group_topics (
    group_id INTEGER,
    topic_id INTEGER,
    PRIMARY KEY (group_id, topic_id),
    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS group_members (
    group_id INTEGER,
    user_id  INTEGER,
    PRIMARY KEY (group_id, user_id),
    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)  REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS topic_names (
    topic_id INTEGER PRIMARY KEY,
    name     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_group_topics_topic_id ON group_topics(topic_id);
CREATE INDEX IF NOT EXISTS idx_group_members_user_id ON group_members(user_id);

CREATE TABLE IF NOT EXISTS events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    start_iso TEXT,
    end_iso TEXT,
    creator_id INTEGER,
    is_approved INTEGER DEFAULT 0,
    sheet_url TEXT,
    FOREIGN KEY (creator_id) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS event_leads (
    event_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    PRIMARY KEY (event_id, user_id),
    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS event_participants (
    event_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    PRIMARY KEY (event_id, user_id),
    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
~~~

- [PL-3.1.1] **Transactional Integrity**: Native `ON DELETE CASCADE` is enforced at the database level via `PRAGMA foreign_keys = ON;` executed on every connection open. **Strict Enforcement**: `init_db()` performs a runtime check at startup; if `PRAGMA foreign_keys` returns `0`, the bot throws a `RuntimeError` and terminates immediately to prevent data corruption.

### [PL-3.2] Access Control Logic (Default Deny Model)
- [PL-3.2.1] **Default State**: A topic is "Closed" (Restricted to Admins) if absent from the `direct_topic_access` registry — unauthorized users' messages are silently deleted.
- [PL-3.2.2] **Configured State**: A topic becomes "Active" once it appears in `direct_topic_access`. Access is then strictly limited to the users/groups explicitly listed.
- [PL-3.2.3] **Groups as Templates**: The `groups` table serves as a **template toolset**. Admins use templates to bulk-copy users into a topic's `direct_topic_access`.
- [PL-3.2.4] **Authorization**: Access is evaluated against `direct_topic_access` and user roles. Global Admins are exempt only if `config.IMMUNITY_FOR_ADMINS` is True.

### [PL-3.3] Upsert Pattern
- [PL-3.3.1] `update_topic_name(topic_id, name)` uses `INSERT OR REPLACE INTO topic_names` — an upsert pattern. This means the function both inserts new topic name records and updates existing ones atomically. This is the only function in the codebase that uses this pattern; all other mutations use standard `INSERT` or `UPDATE`.

### [PL-3.4] Indexes
- [PL-3.4.1] `idx_group_members_user_id ON group_members(user_id)` — hot path for template member lookups.
- [PL-3.4.2] `idx_group_topics_topic_id ON group_topics(topic_id)` — hot path for topic template lookups.

### [PL-3.5] Background Sync Pattern
- [PL-3.5.1] To ensure the bot remains responsive during network I/O with Google Sheets, all synchronization tasks are executed in the background using `asyncio.create_task`.
- [PL-3.5.2] **Trigger**: Any data mutation in `ManagementService`. Specifically, the call is placed inside deletion branches, mutation methods like `create_event_action`, `toggle_event_participation`, and `resolve_request` (upon approval).
- [PL-3.5.3] **Mechanism**: `_trigger_sheets_sync(mode)` calls `GoogleSheetsService` asynchronously.
- [PL-3.5.4] **Error Handling**: Failures in background tasks are logged but do not interrupt the main execution flow.

---

## [PL-4] MIDDLEWARE EXECUTION LOGIC
- [PL-4.1] Sequential 3-stage pipeline registered as `outer_middleware` on `dp.message` — order is fixed and must not be changed.

### [PL-4.2] Stage 1 — UserManagerMiddleware
- [PL-4.2.1] Operates on all chat types (no private-chat guard — intentional, registration is useful from any chat context). Guard: skips processing if `event.from_user` is absent or is a bot (`event.from_user.is_bot`). For all real users: calls `AccessService.ensure_user_registered(event.from_user)` — auto-registers the user in `users` table if not present. Naming fallback hierarchy: (1) if no name at all → `Пользователь_{user_id}`; (2) if only `last_name` present → promoted to `first_name`. Always passes to the next handler regardless of registration outcome.

### [PL-4.3] Stage 2 — ForumUtilityMiddleware
- [PL-4.3.1] Guard: if `event.chat.type == "private"` → passes. Branching logic for groups:
- [PL-4.3.2] `forum_topic_edited` event → sync new name to DB + delete service message → **early return**.
- [PL-4.3.3] `forum_topic_created` event → delete service message → **early return**.
- [PL-4.3.4] Normal message → auto-register topic → pass to next handler.

### [PL-4.4] Stage 3 — AccessGuardMiddleware
- [PL-4.4.1] Guard: if `event.chat.type == "private"` or `event.from_user.id == event.bot.id` → passes. If user is global admin and `config.IMMUNITY_FOR_ADMINS` is True, passes. For all other messages: resolves `topic_id`, calls `PermissionService.can_user_write_in_topic`. If access denied → silently deletes message and returns. All decisions logged: denied messages at `INFO` (❌), permitted messages at `INFO` (✅).

### [PL-4.5] Private Chat Guard Pattern
- [PL-4.5.1] `ForumUtilityMiddleware` and `AccessGuardMiddleware` use `event.chat.type == "private"` as an early pass-through guard. `UserManagerMiddleware` is exempt from this guard — it operates on all chat types by design. The `GROUP_ID` constant is used only in `handlers/admin.py` and `handlers/moderator.py` for API calls (`bot.edit_forum_topic`), never as a middleware guard condition.

### [PL-4.6] Error Handling
- [PL-4.6.1] All three stages follow a **fail-open** strategy: non-critical exceptions are caught, logged, and the pipeline continues.
- [PL-4.6.2] **Critical exception** (fail-closed): `init_db()` in `connection.py` re-raises any exception after logging — a DB initialization failure must halt the bot immediately.

---

## [PL-5] UI/UX & STATE MANAGEMENT (FSM)

### [PL-5.1] The "Sterile Interface" Protocol
- [PL-5.1.1] **last_menu_id**: FSM key tracking the message ID of the currently active inline keyboard or system message. Set via `state.update_data(last_menu_id=sent_message.message_id)` immediately after every menu deployment.
- [PL-5.1.2] **last_menu_ids**: FSM key holding a list (stack) of message IDs for transient alerts, error messages, or multi-step menus that require bulk deletion.
- [PL-5.1.3] **UIService.delete_tracked_ui**: Reads `last_menu_id` and `last_menu_ids` from FSM state, deletes all tracked messages, nullifies FSM data in a `finally` block (guaranteed even if deletion fails).
- [PL-5.1.4] **UIService.terminate_input**: Atomic sequence: (1) `delete_tracked_ui`, (2) `delete_msg` (user's trigger message), (3) `state.set_state(None)` IF `reset_state=True`. **Systemic Guard**: To maintain FSM chains (like Title -> Dates), `terminate_input` must be called with `reset_state=False` in intermediate steps.
- [PL-5.1.5] **UIService.sterile_ask**: Clears previous menu, deletes trigger message if in group, sends prompt, tracks it as `last_menu_id`, sets FSM state. Used for all FSM text-input initiation flows.
- [PL-5.1.6] **UIService.delete_tracked_ui**: Физически удаляет массив сообщений из `last_menu_ids`. Единственная точка физического уничтожения интерфейса в БД.
- [PL-5.1.7] **UIService.sterile_ask**: Первичный терминатор. Используется ПЕРЕД запросом текстовых данных у пользователя. Удаляет предыдущее меню (`delete_tracked_ui`), шлет промпт (например, "Введите название") и ставит его на слежение.
- [PL-5.1.8] **UIService.sterile_show**: Основной шлюз UI-переходов. Если вызван из колбэка — редактирует текущее сообщение (Swap). Если вызван из Message-хендлера (после ввода пользователя) — вызывает `terminate_input(reset_state=False)`, что удаляет промпт (созданный через `sterile_ask`) и сообщение пользователя, после чего шлет новое чистое меню. **Hardening**: Включает try-except для обработки `BUTTON_TYPE_INVALID` и автоматический fallback на `answer` (новое сообщение), если редактирование невозможно. [G-DNA]
- [PL-5.1.9] **UIService.terminate_input**: Полная зачистка следов ввода. Удаляет tracked_ui (промпт) и само сообщение пользователя, опционально сбрасывая FSM-состояние.
- [PL-5.1.10] **UIService.generic_navigator**: Unified entry point for all UI transitions. Maps callback data strings to specific `UIService` show methods or keyboard builders. Supports global panels (Admin, Moderator, User), profile views, topic details, and **Help Infrastructure** (prefix `help:`). Decoupled help text via `HelpService` using `help:{key}:{back_data}` format. Uses the `PAGINATED_CMDS` class constant to explicitly determine if a keyboard requires the `page` argument. Includes fallback logging for unknown commands. `[AI-1]` Standard: All standard UI returns and transitions MUST traverse this router.
- [PL-5.1.11] **UIService.show_admin_dashboard / show_moderator_dashboard**: Wrappers for main panels that support optional custom feedback text while maintaining layout integrity and superadmin visibility.
- [PL-5.1.12] **UIService.sterile_command**: Decorator factory applied to `@router.message(Command(...))` handlers. Decorated handler returns `(text, reply_markup)` tuple. Decorator intercepts and delegates to `sterile_redirect`, handling group-to-PM redirect, error fallback, cleanup, and `last_menu_id` tracking automatically.
- [PL-5.1.13] **Orphan Notification Protocol**: Any message sent via direct `bot.send_message` (e.g., from `EventService.notify_admins_for_approval` or participation alerts) is considered an "Orphan Notification". These messages MUST be terminated via `UIService.delete_msg(callback.message)` upon user interaction (CallbackQuery) to ensure buttons are removed and the UI remains sterile. **Participation Alerts**: Admins and organizers MUST be notified of all participation requests (Audit) or direct joins (Quick Announcements) via `EventService`.
- [PL-5.1.14] **Split Navigation Footer**: Every keyboard must use `add_nav_footer` or `build_paginated_menu` to ensure consistent navigation.
    - **Buttons**: `[ ⬅️ Назад ] [ ❌ Закрыть ] [ ❓ ]`
    - **Help Logic**: The `❓` button uses format `help:{key}:{back_data}`.
    - **Navigation Safety**: `back_data` (for the help button) must point to the CURRENT screen to ensure the user returns to where they were. If not provided, defaults to `landing`.
- [PL-5.1.15] **Systemic Landing Entry**: The `landing` callback is a mandatory system-wide entry point that triggers the `UIService.get_landing_data` controller. It serves as the ultimate fallback for navigation returns.
- [PL-5.1.16] **Heartfelt UI Principle**: All user-facing strings must use welcoming, community-oriented language. Includes the **Smart Hybrid Date Flow**: preset buttons (Today, Sat) + natural language parsing with confirmation. [RA-7.1/2]
- [PL-5.1.17] **Universal Announcement Dispatcher**: A systemic pattern where interactive buttons in broadcast messages do not link directly to entities, but to an `announcements` registry. This allows a single callback handler to manage diverse interaction types (Participation, Payments, Gear) and enforces context-aware access control.
- [PL-5.1.18] **Quick Announcement Protocol**: Support for `/an` command in forum topics. Automatically creates a "Rapid Event" (date set to 'Оперативно') and posts a rich announcement. **Dynamic Reactivity**: Any interaction with the announcement (joining/leaving) triggers a real-time text update with the current participant list. Original command message is deleted to maintain thread sterility.
- [PL-5.1.19] **Polymorphic Cascade Cleanup**: Since the `announcements` table uses polymorphic links (linking to various entity types by ID without native FKs), any service responsible for deleting a target entity (Events, etc.) MUST manually invoke `delete_announcements_by_target` to prevent data rot.
- [PL-5.1.20] **Telegram Mini App (TMA) Bridge**: Interactive personalized UI for announcements. Uses FastAPI backend and Vanilla JS/CSS frontend with Glassmorphism aesthetics. **Cross-Layer Reactivity**: Actions performed in TMA (joining/leaving) automatically trigger an update of the physical Telegram message via the stored `chat_id`/`message_id` metadata. Includes mobile-native Haptic Feedback and fallback logic. [CC-5]
- [PL-5.1.21] **TMA Group Constraint Pattern**: Telegram strictly forbids `web_app` buttons in inline keyboards sent to group chats (raises `BUTTON_TYPE_INVALID`). **Resolution**: Group announcements use standard Telegram buttons (`✅ Иду` / `🚶 Не иду`) for quick interaction with localized alerts. The full **Mini App Dashboard** ("Личный кабинет") is centralized as a universal component in ALL main dashboards (User, Admin, Moderator) in Private Messages, serving as the primary hub for management and search.

### [PL-5.2] FSM Data Keys
All keys stored in FSM state across the application:
- [PL-5.2.1] `last_menu_id`: Tracks active inline keyboard message ID for cleanup.
- [PL-5.2.2] `edit_topic_id`, `edit_group_id`, `edit_user_id`: Stores specific ID context between FSM states during admin rename flows.
- [PL-5.2.3] `disambig_query`, `disambig_action`, `disambig_context`: Keys used for cross-handler user search disambiguation logic. `disambig_action` values: `"dir_add"` (grant direct access), `"mod_add"` (assign moderator), `"admin_role_target"` (role assignment flow).
- [PL-5.2.4] `disambig_role_id`: Referenced in disambiguation state cleanup but never set by any current handler — ghost key from an incomplete refactor. Safe to ignore; cleared on every disambiguation resolution.
- [PL-5.2.5] `moderator_direct_access_topic`: Set in `moderator.py` (`mod_add_user_list_` flow) to carry the target topic ID into the `waiting_for_direct_access_user` FSM state.
- [PL-5.2.6] `moderator_edit_topic_id`: Set in `moderator.py` (`mod_topic_rename_` flow) to carry the target topic ID into the `waiting_for_topic_name` FSM state.
- [PL-5.2.7] `moderator_add_target_topic`: Set in `moderator.py` (`mod_moderator_add_` flow) to carry the target topic ID into the `waiting_for_user_data` FSM state.
- [PL-5.2.8] `moderator_current_topic`: Set in `moderator.py` (`mod_topic_select_` flow) to track the currently selected topic in the moderator session.

### [PL-5.3] FSM Hygiene Rule
[PL-5.3.1] `state.clear()` is **forbidden** — it destroys all FSM data including `last_menu_id`, breaking the Sterile Interface. Always use `state.set_state(None)` to nullify state while preserving data.

### [PL-5.4] Close Menu Handler Behaviour
[PL-5.4.1] `handlers/common.py` (`F.data == "close_menu"`) calls `UIService.delete_msg(callback.message)` directly — it deletes the message the button is attached to. It also clears the tracking state: sets both `last_menu_id=None` and `last_menu_ids=[]` via `state.update_data` to ensure protocol synchronization [CC-3].

### [PL-5.5] Callback Resilience
[PL-5.5.1] `safe_callback()` decorator wraps all callback handlers. Suppresses `TelegramBadRequest` ("message is not modified") from rapid double-tapping.

### [PL-5.6] Unified Entry Point (Traffic Controller)
- [PL-5.6.1] **Unified /start**: The bot uses a single public entry point (`/start`). Separate commands like `/admin` and `/mod` are deprecated for general use and maintained only as hidden debug aliases.
- [PL-5.6.2] **Role-Based Routing**: When a user triggers `/start`, the system calls `UIService.get_landing_data`, which resolves the appropriate dashboard (Admin, Moderator, or User) based on the user's effective permissions.
- [PL-5.6.3] **Landing States**:
    - **Global Admin**: Redirects to `Admin Dashboard`.
    - **Moderator**: Redirects to `Moderator Dashboard` (topic selection).
    - **User**: Redirects to `User Main Menu`.
- [PL-5.6.4] **Navigation Parity**: The same landing logic is triggered when a user returns to the "Main Menu" via inline buttons (Callback `landing`).

---

## [PL-6] OPERATIONAL CONSTRAINTS FOR AI AGENTS
- [PL-6.1] **Facade Integrity**: Never import internal routing segments bypassing the Facade logic (Db or Keyboards). All calls must traverse the main `__init__.py` boundaries respectively.
- [PL-6.2] **Handlers Sterile Isolation**: Handlers (`handlers/*.py`) are strictly prohibited from importing `from database import db`. All data interaction must be mediated by the appropriate service layer.
- [PL-6.3] **FSM Maintenance**: Every handler that sends a new menu must immediately update `last_menu_ids` in FSM state with the sent message ID. Use `UIService.sterile_show` — it handles tracking automatically.
- [PL-6.4] **UIService.sterile_show as Single UI Gateway**: All menu transitions MUST use `UIService.sterile_show(state, event, text, reply_markup)`. Direct calls to `callback.message.edit_text(...)`, `message.answer(...)`, or `callback.message.edit_reply_markup(...)` from handlers are prohibited. **Prohibited Pattern**: Never "edit" a menu message into a status/log message (e.g., "Event Approved"). Use `delete_msg` to remove the interface and `NotificationService` to send a NEW message if feedback is required.
- [PL-6.5] **Unified Navigation Protocol**: All standard UI returns and transitions from handlers SHOULD use `UIService.generic_navigator` instead of direct `UIService.sterile_show` calls where possible, to centralize routing logic.
- [PL-6.6] **Handler State Signature Rule**: Every handler that calls `UIService.sterile_show`, `UIService.sterile_ask`, or any other `UIService` method requiring `state` MUST declare `state: FSMContext` in its signature. Omitting it causes a `NameError` at runtime.
- [PL-6.7] **ManagementService Mutation Protocol**: All entity mutations MUST traverse `ManagementService`. Handlers are prohibited from performing input validation (e.g., regex checks, string splitting) or direct `db.*` writes. The service is responsible for "sanitizing" intent and returning a user-facing result. **Exception**: Data retrieval for keyboard rendering (GET-only) remains direct via `database.db`. **Event Rule**: Every event creation (Standard or Quick) MUST automatically register the creator as a participant and a lead.
- [PL-6.8] **Search Delegation Rule**: Handlers must respect the `"SEARCH_REQUIRED"` signal from the management service. This ensures that complex search and disambiguation logic is shared rather than duplicated across admin and moderator flows.
- [PL-6.9] **Sterile UI Protocol Enforcement**: The system has moved away from direct Telegram API calls in handlers. Any new UI development must strictly follow the `UIService.sterile_show` gateway pattern.
- [PL-6.10] **Orphan Message Constraint**: Audit-notifications and other push-messages sent without FSM context MUST use `UIService.delete_msg(callback.message)` for finalization. Using `UIService.sterile_show` for orphan messages is an architectural violation as it risks leaving "zombie" buttons.
- [PL-6.11] **Sync Parity**: Administrative changes to topic names must be propagated both to the local DB (`db.update_topic_name`) and to the Telegram API (`bot.edit_forum_topic`).
- [PL-6.12] **IsGlobalAdmin Filter Pattern**: The `IsGlobalAdmin` custom filter applied at router level (`router.message.filter(IsGlobalAdmin())` + `router.callback_query.filter(IsGlobalAdmin())`) is the single authoritative access control for admin handlers. Do not add redundant inline `if user_id != ADMIN_ID: return` checks inside individual handlers.
- [PL-6.13] **noop Callback**: The `"noop"` callback data produced by `available_topics_kb()` has no registered handler. This is intentional.
- [PL-6.14] **Destructive Confirmation Protocol**: All destructive operations (e.g., `delete_group`, `delete_user`, `revoke_role`) MUST traverse a confirmation step via `UIService.get_confirmation_ui` and be executed through `ManagementService.execute_deletion` in `handlers/common.py`.
- [PL-6.15] **Roles Separation of Concerns**: The system uses a **Dashboard Pattern** for role information (FAQ and Global Lists in `common.py`) and a **Context Pattern** for role management (individual user actions in `admin.py`/`user_edit_kb`).
- [PL-6.16] **AdminStates Scope**: FSM states (`AdminStates`) are defined and used exclusively within `handlers/admin.py`. Never reference or set `AdminStates` from outside this file.
- [PL-6.17] **ModeratorStates Scope**: FSM states (`ModeratorStates`) are defined and used exclusively within `handlers/moderator.py`. Never reference or set `ModeratorStates` from outside this file.
- [PL-6.18] **Keyboard Data Access**: `keyboards/admin_kb.py`, `keyboards/moderator_kb.py`, and `keyboards/user_kb.py` are permitted to import from `database.db` directly for rendering live data. This is the only sanctioned exception to the Facade rule for the keyboard layer.
- [PL-6.19] **Virtual Superadmin Encapsulation**: The logic for granting the virtual `superadmin` role based on config `ADMIN_ID` resides safely inside `database/roles.py`'s `get_user_roles(user_id)`. UI handlers must not manipulate `ADMIN_ID` directly to append this role manually, since the DB response is pre-enriched.
- [PL-6.20] **Keyboard Import Order Criticality**: The import sequence in `keyboards/__init__.py` (`admin_kb` → `user_kb` → `moderator_kb`) is an architectural invariant. Modifying this order can lead to unpredictable runtime behavior due to wildcard exports shadowing identically named functions.
- [PL-6.21] **Search Deduplication Rule**: Search result fetching logic must use the `_fetch_search_results(s_type, query)` helper in `handlers/common.py`. Do not inline `if s_type == "user" / elif group / elif topic` branches in individual handlers.
- [PL-6.22] **No N+1 Queries in UI**: Any keyboard builder iterating over a list (users, groups, topics) MUST use batch-fetching methods from `database.db` (e.g., `get_topic_names_by_ids`) and set-based lookups. Direct DB calls inside loops are strictly prohibited to maintain performance. [PL-HI]
- [PL-6.23] **Verify Before Change (Rule 21)**: BEFORE making any code changes, it is mandatory to view the target file and all related signatures (methods, keyboards, DB tables). Writing calls without confirming their existence in the current code context is strictly prohibited.

---

## [PL-7] CRITICAL CONSTANTS

- [PL-7.1] **BOT_TOKEN** — `str`. Source: `.env` → `config.py` (`get_env_or_raise`). Raises `ValueError` on missing or empty value. Used in `loader.py` for `Bot` initialization.
- [PL-7.2] **ADMIN_ID** — `int`. Source: `.env` → `config.py` (cast via `int`). Used via `PermissionService.is_global_admin` to route handlers in the `IsGlobalAdmin` filter. Also enriched dynamically within `db.get_user_roles`.
- [PL-7.3] **GROUP_ID** — `int`. Source: `.env` → `config.py`. Used exclusively in `handlers/admin.py` and `handlers/moderator.py` as the `chat_id` argument for Telegram API calls. Expected to be a negative integer (Telegram supergroup convention). **Not used as a middleware guard condition.**
- [PL-7.4] **Topic ID `-1`** — Logical mapping for the "General" topic in a forum-enabled Telegram chat.
- [PL-7.5] **WEBAPP_HOST** — `str`. Web server binding address (default: `0.0.0.0`).
- [PL-7.6] **WEBAPP_PORT** — `int`. Web server port (default: `8000`).
- [PL-7.7] **WEBAPP_URL** — `str`. Public entry point for TMA. If empty, the system falls back to Callback-based UI. [CC-5]
- [PL-7.8] **WEBAPP_CORS_ORIGINS** — `list`. Allowed origins for WebApp requests.
- [PL-7.9] **LOG_MAX_BYTES / LOG_BACKUP_COUNT** — `int`. Rotation parameters for unified logging.

---

## [PL-8] TESTING INFRASTRUCTURE
[PL-8.1] Comprehensive automated testing suite using `pytest`. Tests are an integral part of the codebase.

### [PL-8.2] Configuration (`tests/conftest.py`)
- [PL-8.2.1] **Database Isolation**: `db_setup` redirects `connection.DB_PATH` to a temporary file in `tmp_path`. This ensures a clean schema for every test.
- [PL-8.2.2] **Mocked Bot**: `mock_bot` fixture provides an `AsyncMock(spec=Bot)`. Factories in `conftest.py` ensure `message.bot` and `callback.bot` point to this mock using `_bot` private attribute.
- [PL-8.2.3] **FSM Context**: `storage` and `create_context` fixtures allow full FSM state simulation.

### [PL-8.3] Journey Testing Standards
- [PL-8.3.1] **Total Shield Pattern**: High-level tests (`tests/test_journeys/`) must cover the complete lifecycle of an operation: User Input -> Service Mutation -> Notification Trigger -> FSM Transition.
- [PL-8.3.2] **Notification Assertions**: Every test involving a user feedback loop must assert `bot.send_message` calls with correct `chat_id` and text content (checking both `args` and `kwargs` for positional/keyword parity).
- [PL-8.3.3] **Permission Guard Testing**: Every journey test must include a "negative path" (unauthorized user attempt) to verify `PermissionService` integration in handlers.
- [PL-8.3.4] **Mocking Sterility**: `callback.answer` and `UIService.sterile_show` are mocked via `patch` in tests to prevent `aiogram` RuntimeError during unmounted execution.

### [PL-8.4] Test Categories
- [PL-8.4.1] **tests/test_database/**: Unit and integration tests for SQL operations. Focus: CRUD, cascading deletions, and access evaluation logic.
- [PL-8.4.2] **tests/test_services/**: Tests for domain services.
    - `test_ui_integrity.py` (Static and dynamic validation of keyboards, URLs and callbacks).
    - `test_ui_fuzzer.py` (Autonomous recursive interface exploration).
    - `test_google_sheets_service.py` (Mocked API validation).
    - `test_management_service.py` (Search-Or-Action protocol).
    - `test_permission_service.py` (Role resolution).
- [PL-8.4.3] **tests/test_handlers/**: Unit tests for handlers and middlewares. Focus: Routing, state transitions, and stealth moderation filters. Uses `__wrapped__` to bypass `sterile_command` redirects during logic verification.
- [PL-8.4.4] **tests/test_journeys/**: End-to-End flow tests for complex user journeys (e.g., Quick Announcements, Participation Audit). Focus: Cross-service orchestration and notification delivery.
    - `test_tma_integration.py` (Bot reaction to WebApp actions).
- [PL-8.4.5] **tests/test_web/**: Unit tests for Web Bridge authentication and API logic.
    - `test_auth.py` (HMAC security).

### [PL-8.5] Testing Rules
1. [PL-8.5.1] **Repository Standards**: The `tests/` directory is a permanent part of the repository.
2. [PL-8.5.2] **Ephemeral DB**: Always use the `db_setup` fixture. Writing to `bot.db` during testing is strictly prohibited.
3. [PL-8.5.3] **No Network**: All external API calls (Telegram) MUST be mocked via `mock_bot`.
4. [PL-8.5.4] **Router Detach**: When using global routers in integration tests, use `router._parent_router = None` before including them in a test-local `Dispatcher` to prevent `RuntimeError`.
5. [PL-8.5.5] **Pydantic Validation**: All mocked `Message` and `Update` objects must include valid data (e.g., `date=datetime.now()`) to pass Pydantic V2 validation used by aiogram 3.
6. [PL-8.5.6] **Aiogram Mocking Protocol**: 
    - Since aiogram 3 models are **frozen**, NEVER attempt to assign `callback.answer = AsyncMock()`. 
    - Use `with patch("aiogram.types.CallbackQuery.answer", new_callable=AsyncMock)` to intercept calls.
    - Ensure `bot` is attached via `._bot = mock_bot` to satisfy the internal `.bot` property of messages/callbacks.


