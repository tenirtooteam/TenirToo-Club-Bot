# PROJECT_LOGIC: Tenir-Too Access Control Bot

## 1. PROJECT IDENTITY & STACK
- **System Name**: Tenir-Too Access Control Bot.
- **Python Version**: 3.11 (Required for optimal stability and dependency compatibility).
- **Virtual Environment**: Mandatory `venv` isolation to prevent dependency conflicts and ensure consistent environment across development and production.
- **Framework**: aiogram 3.4.1 (Asynchronous Python framework).
- **Testing Suite**: pytest 8.1.1 with pytest-asyncio, pytest-mock and pytest-cov.
- **Database Engine**: SQLite 3 with Write-Ahead Logging (WAL).
- **Core Purpose**: Granular access control and stealth moderation for Telegram Forum Topics within a Supergroup.

---

## 2. ARCHITECTURAL OVERVIEW

### 2.1. Layered Architecture
Decoupled concerns across five layers:
- **Handlers** — UI and command routing.
- **Middlewares** — Logic interception pipeline.
- **Services** — Business logic.
- **Keyboards** — Inline keyboard builders. Import from `database.db` directly to render data-driven menus. Exposed via wildcard re-export facade (`keyboards/__init__.py`).
- **Database** — Persistence via Facade pattern.
- **Tests** — Automated test suite using in-memory database and mocks.

### 2.2. Module Registry
Complete file list with individual responsibilities and full function inventory:

- **main.py** — Entry point: `setup_logging` (RotatingFileHandler, 5MB limit, 5 backup files, dual console+file output to `logs/bot.log`), DB initialization via `db.init_db()`, router registration (common → user → admin → moderator), outer middleware chaining (UserManager → ForumUtility → AccessGuard), bot polling with `drop_pending_updates=True`.
- **loader.py** — Initializes `Bot` and `Dispatcher` with `MemoryStorage`.
- **config.py** — Helper `get_env_or_raise(key)`: reads env var, raises `ValueError` on missing/empty value. Exposes constants: `BOT_TOKEN` (str), `ADMIN_ID` (int), `GROUP_ID` (int), `IMMUNITY_FOR_ADMINS` (bool, default False). Raises on missing values at import time.
- **database/__init__.py** — Package initializer: `from . import db`. Enables the `from database import db` import pattern used across the codebase. No logic of its own.
- **database/connection.py** — SQLite connection context manager `get_conn`: opens connection with `check_same_thread=False`, activates WAL on every connection, activates native Foreign Key enforcement (`PRAGMA foreign_keys = ON;`) on every connection, guarantees closure in `finally`. `DB_PATH` is resolved relative to `connection.py`'s own file location (`os.path.dirname(__file__)`), placing `bot.db` inside the `database/` directory. `init_db()`: creates all tables with `ON DELETE CASCADE` constraints and indexes in a single transaction; performs a **Runtime Check** at startup — if Foreign Keys are not supported by the environment, raises `RuntimeError` and terminates bot execution immediately to prevent data corruption. **Remediation Fix**: Table `group_topics` now correctly references `topic_names(topic_id)` with `ON DELETE CASCADE`. New indices: `idx_group_members_user_id` and `idx_direct_topic_access_user_id` for optimized template/access lookups.
- **database/members.py** — Transactional CRUD for users: `add_user`, `delete_user`, `update_user_name`, `get_user_name`, `get_all_users`, `user_exists`, `find_users_by_query` (case-insensitive exact-match search on `first_name`/`last_name` fields; filtering is performed in Python rather than SQL because SQLite's `LOWER()` does not handle Cyrillic characters correctly; accepts a 1- or 2-word query string; returns a list of `(user_id, first_name, last_name)` tuples). Note: `delete_user` issues a single `DELETE FROM users` — cascade to `user_roles`, `group_members`, and `direct_topic_access` is handled at the DB level via `ON DELETE CASCADE`.
- **database/topics.py** — Transactional CRUD for topics (registration, renaming, deletion): `get_all_unique_topics`, `update_topic_name`, `get_topic_name`, `delete_topic`, `register_topic_if_not_exists`.
- **database/groups.py** — Transactional CRUD for global groups and group-topic/template linkages: `create_group`, `get_all_groups`, `delete_group`, `get_topics_of_group`, `add_topic_to_group`, `remove_topic_from_group`, `get_groups_by_topic`, `get_group_name`, `add_to_group_template`, `remove_from_group_template`, `get_group_template_members`, `find_groups_by_query`.
- **database/roles.py** — Roles definitions, issuance to users, and role scoping: `get_role_id`, `grant_role` (includes existence check to prevent duplicates), `revoke_role`, `get_user_roles` (dynamically resolves virtual `superadmin` role for `config.ADMIN_ID`), `get_moderators_of_topic`, `is_global_admin`, `is_moderator_of_topic`, `get_all_roles`, `get_role_name_by_id`.
- **database/permissions.py** — Direct access management and unified access evaluation: `can_write`, `is_topic_restricted`, `get_topic_authorized_users`, `grant_direct_access`, `revoke_direct_access`, `has_direct_access`, `get_direct_access_users`.
- **database/db.py** — Single facade re-exporting functions from `members.py`, `topics.py`, `groups.py`, `roles.py`, `permissions.py`, and `init_db`/`get_conn` from `connection.py` as a unified module. **The only permitted import point for data operations.**
- **services/ui_service.py** — Centralized UI lifecycle via `UIService` class (all methods `@staticmethod`): `clear_last_menu` (Multi-Message Stack cleanup via `last_menu_ids`), `delete_msg`, `finish_input`, `send_redirected_menu`, `show_menu`, `generic_navigator` (central UI router using `PAGINATED_CMDS` constant for explicit call signatures), `show_admin_dashboard`, `show_moderator_dashboard`, `ask_input`, `show_temp_message` (adds message to cleanup stack), `show_user_detail`, `show_group_detail`, `show_topic_detail`, `show_moderator_groups`, `show_moderator_moderators`, `sterile_command`, `get_confirmation_ui`, `format_user_card`.
- **services/management_service.py** — Centralized Domain Service for entity management. **Contract**: All methods MUST return a `(bool, str)` tuple. **Search-Or-Action Protocol**: Methods like `assign_moderator_role` and `grant_direct_access` return `False, "SEARCH_REQUIRED"` if an unambiguous ID is not found, signaling the handler to trigger search disambiguation. **Functions**: `ensure_user_registered` (shadow auto-reg), `add_user` (flexible space-aware parsing for multi-word names), `create_group`, `assign_moderator_role`, `grant_direct_access`, `toggle_user_group_template` (manages non-runtime membership/template), `apply_group_to_topic` (bulk copy from template to direct access), `sync_group_to_topic` (full sync: wipe topic direct access + copy from template), `copy_topic_to_topic` (access transfer), `grant_role`, `execute_deletion`.
- **services/permission_service.py** — Unified Authorization Service. **Functions**: `is_superadmin`, `is_global_admin`, `is_moderator_of_topic`, `can_manage_topic`, `can_manage_user_roles`, `get_manageable_topics`, `can_user_write_in_topic` (low-level access check).
- **services/notification_service.py** — Feature extension via `NotificationService` class (methods `@staticmethod`): `send_native_all(bot, chat_id, topic_id, sender_name, text)` (sends a single message containing invisible mentions up to 50 authorized users via `db.get_topic_authorized_users`).
- **services/callback_guard.py** — `safe_callback()` decorator factory (no parameters): suppresses `TelegramBadRequest` with "message is not modified" (calls `callback.answer()` silently), catches all other `TelegramBadRequest` and unknown exceptions with user-facing `show_alert=True` error message.
- **handlers/common.py** — Unfiltered router (no role filter). Private helper `_fetch_search_results(s_type, query)` — single centralized point for dispatching search queries across user/group/topic entity types, eliminating triple duplication. Global `close_menu` callback handler. Global role-aware `/help` command. Global user disambiguation pagination (`usr_pg_`) and pick (`usr_pick_`) handlers. **Roles Dashboard** handlers: `roles_dashboard_menu` (informational center for admins and moderators), `roles_faq_view` (role description guide), `list_users_with_roles` (overview of all active assignments). **Unified Search** handlers: `search_start_handler` (initiates type-aware search prompt), `search_query_handler` (processes input, delegates to `_fetch_search_results`, auto-selects single results), `search_results_pagination` (paginates search results), `search_pick_handler` (delegates to `perform_search_pick`), `perform_search_pick` (universal post-selection router).
- **handlers/admin.py** — Admin flows protected by `IsGlobalAdmin`. FSM states: `waiting_for_group_name`, `waiting_for_topic_name`, `waiting_for_user_data`, `waiting_for_new_name`. Handles **Template Management** (User Templates) and bulk access application. Functions: `admin_dashboard`, `back_to_main`, `show_groups` (Templates list), `role_assign_choose_topic`, `group_detail`, `add_group_init`, `process_group_add`, `delete_group_init`, `group_template_action_choose_topic` (Apply/Sync start), `group_template_action_execute`, `show_all_topics`, `topic_detail`, `show_group_topics`, `remove_topic_from_group_init`, `add_topic_to_group_init`, `confirm_add_topic`, `topic_rename_init`, `process_topic_name_save`, `global_topic_delete_init`, `show_users`, `add_user_init`, `process_user_add`, `user_detail`, `user_rename_init`, `process_user_rename`, `user_groups_ui` (Template toggling), `toggle_group`, `user_delete_init`, `role_assign_choose_user`, `user_roles_manage_handler`, `role_pick_handler`, `role_assign_topic_confirm`, `role_revoke_init`. Delegated UI transitions to `UIService.generic_navigator`.
- **handlers/moderator.py** — Moderator flows protected by `IsTopicManager`. FSM states: `waiting_for_topic_name`, `waiting_for_user_data`, `waiting_for_direct_access_user`. Functions: `moderator_dashboard`, `moderator_topic_select`, `moderator_back_to_topic`, `moderator_rename_topic_init`, `moderator_rename_topic_finish`, `moderator_show_groups`, `moderator_link_group_list`, `moderator_link_group`, `moderator_unlink_group_init`, `moderator_unlink_group_confirm`, `moderator_show_users`, `moderator_add_user_list`, `moderator_toggle_direct_access`, `process_direct_access_user_search`, `moderator_remove_direct_access_init`, `moderator_show_moderators`, `moderator_add_moderator_start`, `moderator_add_moderator_finish`, `moderator_remove_moderator_init`. Delegated UI transitions to `UIService.generic_navigator`.
- **handlers/user.py** — User-facing flows: `/start`, `back_to_user_main`, `user_profile_callback`, `show_user_topics`, `user_topic_detail`, `handle_all_mention`. All handlers declare `state: FSMContext` in signature where UIService.show_menu is called.
- **middlewares/access_check.py** — Three-middleware sequential chain: `UserManagerMiddleware` → `ForumUtilityMiddleware` → `AccessGuardMiddleware`. All three are registered as `outer_middleware` on `dp.message`.
- **keyboards/__init__.py** — Keyboard layer facade with wildcard re-exports in fixed order: `from .admin_kb import *`, `from .user_kb import *`, `from .moderator_kb import *`. The import order is architecturally critical for correct operation and conflict resolution. Exposes `build_paginated_menu` from `pagination_util` as a direct named export. Enables the `import keyboards as kb` pattern.
- **keyboards/admin_kb.py** — Inline keyboard builders for all admin menus. Functions: `main_admin_kb`, `all_topics_kb`, `topic_edit_kb`, `group_topics_list_kb`, `available_topics_kb`, `groups_list_kb` (Templates list), `group_edit_kb`, `template_action_topic_select_kb` (Topic picker for mass template operations), `users_list_kb`, `user_edit_kb` (takes `is_superadmin`), `user_groups_edit_kb`, `roles_dashboard_kb`, `role_selection_kb`, `user_roles_manage_kb`, `topic_selection_for_role_kb`, `back_to_roles_dashboard_kb`, `user_disambiguation_kb`.
- **keyboards/moderator_kb.py** — Inline keyboard builders for topic moderators. Functions: `moderator_topics_list_kb(topics, page)`, `moderator_topic_menu_kb(topic_id)`, `moderator_group_list_kb(topic_id, page)`, `moderator_available_groups_kb(topic_id, page)`, `moderator_users_list_kb(topic_id, page)`, `moderator_users_to_add_kb(topic_id, page)`, `moderator_topic_moderators_kb(topic_id, page)` (paginated list of topic moderators with add/remove controls).
- **keyboards/pagination_util.py** — Helper logic for pagination: `build_paginated_menu(item_buttons, static_buttons, page, limit, callback_prefix, adjust_items)` — universally standardizes pagination navigation interface.
- **keyboards/user_kb.py** — Inline keyboard builders for user menus. Imports from `database.db`. Functions: `user_main_kb()`, `user_topics_list_kb(user_id)`, `user_profile_kb` (dedicated back-to-menu navigation), `user_topic_detail_kb`.
- **local_scripts/dev_run.py** — Developer-only hot-reload runner.
- **local_scripts/Gemini_maker.py** — Developer-only AI context packager. Regenerates `local_scripts/full_project_code.txt`.

### 2.3. Import Dependency Graph
Permitted import direction — top consumers to bottom providers. Any arrow reversal is an architectural violation.

~~~
handlers/*              →  services/*                    →  database/db.py  →  database/(members|topics|groups|roles|permissions).py
keyboards/__init__.py   →  keyboards/*_kb.py             →  database/db.py  →  database/(members|topics|groups|roles|permissions).py
middlewares/*           →  services/access_service.py    →  database/db.py
main.py                 →  handlers/*, middlewares/*, database/db.py (init_db only)
database/__init__.py    →  database/db.py
database/db.py          →  database/connection.py (init_db, get_conn re-export)
                        →  database/(members|topics|groups|roles|permissions).py
~~~

### 2.4. Database Facade
`database/db.py` is the exclusive interface for all data operations. Direct imports from files like `database/topics.py` or `database/members.py` are a critical architectural violation.

### 2.5. Keyboard Facade
`keyboards/__init__.py` is the exclusive import point for all keyboard builders. Handlers must use `import keyboards as kb` and access all functions via `kb.*`. This mirrors the Database Facade pattern at the keyboard layer. The strict top-down wildcard import order within `__init__.py` determines conflict resolution.

### 2.6. Context Manager Connectivity
`database/connection.py` uses a custom `@contextmanager` (`get_conn`) for deterministic connection handling and guaranteed closure on both success and exception. WAL mode is activated on every individual connection open, not globally at startup. `DB_PATH` is resolved relative to `connection.py`'s own location, always placing `bot.db` inside the `database/` directory regardless of the working directory at launch.

---

## 3. DATABASE SCHEMATICS & INTEGRITY

### 3.1. Entity Relationship Model — DDL

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
~~~

- **Transactional Integrity**: Native `ON DELETE CASCADE` is enforced at the database level via `PRAGMA foreign_keys = ON;` executed on every connection open. **Strict Enforcement**: `init_db()` performs a runtime check at startup; if `PRAGMA foreign_keys` returns `0`, the bot throws a `RuntimeError` and terminates immediately to prevent data corruption.

### 3.2. Access Control Logic (Template Model)
- **Default State**: A topic is "Public" if absent from the `direct_topic_access` registry — all users may write.
- **Restricted State**: A topic becomes "Private" once it appears in `direct_topic_access`.
- **Groups as Templates**: The `groups` table (with `group_members` and `group_topics`) no longer provides runtime access. Instead, it serves as a **template toolset**. Admins use templates to bulk-copy users into a topic's `direct_topic_access`.
- **Authorization**: Access is evaluated ONLY against `direct_topic_access` and user roles (Admin/Moderator).

### 3.3. Upsert Pattern
`update_topic_name(topic_id, name)` uses `INSERT OR REPLACE INTO topic_names` — an upsert pattern. This means the function both inserts new topic name records and updates existing ones atomically. This is the only function in the codebase that uses this pattern; all other mutations use standard `INSERT` or `UPDATE`.

### 3.4. Indexes
- `idx_group_members_user_id ON group_members(user_id)` — hot path for template member lookups.
- `idx_group_topics_topic_id ON group_topics(topic_id)` — hot path for topic template lookups.

---

## 4. MIDDLEWARE EXECUTION LOGIC
Sequential 3-stage pipeline registered as `outer_middleware` on `dp.message` — order is fixed and must not be changed.

### Stage 1 — UserManagerMiddleware
Operates on all chat types (no private-chat guard — intentional, registration is useful from any chat context). Guard: skips processing if `event.from_user` is absent or is a bot (`event.from_user.is_bot`). For all real users: calls `AccessService.ensure_user_registered(event.from_user)` — auto-registers the user in `users` table if not present. Naming fallback hierarchy: (1) if no name at all → `Пользователь_{user_id}`; (2) if only `last_name` present → promoted to `first_name`. Always passes to the next handler regardless of registration outcome.

### Stage 2 — ForumUtilityMiddleware
Guard: if `event.chat.type == "private"` → passes. Branching logic for groups:
1. `forum_topic_edited` event → sync new name to DB + delete service message → **early return**.
2. `forum_topic_created` event → delete service message → **early return**.
3. Normal message → auto-register topic → pass to next handler.

### Stage 3 — AccessGuardMiddleware
Guard: if `event.chat.type == "private"` or `event.from_user.id == event.bot.id` → passes. If user is global admin and `config.IMMUNITY_FOR_ADMINS` is True, passes. For all other messages: resolves `topic_id`, calls `PermissionService.can_user_write_in_topic`. If access denied → silently deletes message and returns. All decisions logged: denied messages at `INFO` (❌), permitted messages at `INFO` (✅).

### Private Chat Guard Pattern
`ForumUtilityMiddleware` and `AccessGuardMiddleware` use `event.chat.type == "private"` as an early pass-through guard. `UserManagerMiddleware` is exempt from this guard — it operates on all chat types by design. The `GROUP_ID` constant is used only in `handlers/admin.py` and `handlers/moderator.py` for API calls (`bot.edit_forum_topic`), never as a middleware guard condition.

### Error Handling
All three stages follow a **fail-open** strategy: non-critical exceptions are caught, logged, and the pipeline continues.
- **Critical exception** (fail-closed): `init_db()` in `connection.py` re-raises any exception after logging — a DB initialization failure must halt the bot immediately.

---

## 5. UI/UX & STATE MANAGEMENT (FSM)

### 5.1. The "Sterile Interface" Protocol
- **last_menu_id**: FSM key tracking the message ID of the currently active inline keyboard or system message. Set via `state.update_data(last_menu_id=sent_message.message_id)` immediately after every menu deployment.
- **UIService.clear_last_menu**: Reads `last_menu_id` from FSM state, deletes the tracked message, nullifies FSM data in a `finally` block (guaranteed even if deletion fails).
- **UIService.finish_input**: Atomic sequence: (1) `clear_last_menu`, (2) `delete_msg` (user's trigger message), (3) `state.set_state(None)`.
- **UIService.ask_input**: Clears previous menu, deletes trigger message if in group, sends prompt, tracks it as `last_menu_id`, sets FSM state. Used for all FSM text-input initiation flows.
- **UIService.show_temp_message**: Clears previous menu, deletes trigger, sends self-cleaning status or error message tracked as `last_menu_id`. Used for all transient error/status notifications.
- **UIService.generic_navigator**: Unified entry point for all UI transitions. Maps callback data strings to specific `UIService` show methods or keyboard builders. Uses the `PAGINATED_CMDS` class constant to explicitly determine if a keyboard requires the `page` argument, eliminating unsafe `try/except` signature guessing. Includes fallback logging for unknown commands.
- **UIService.show_admin_dashboard / show_moderator_dashboard**: Wrappers for main panels that support optional custom feedback text while maintaining layout integrity and superadmin visibility.
- **UIService.sterile_command**: Decorator factory applied to `@router.message(Command(...))` handlers. Decorated handler returns `(text, reply_markup)` tuple. Decorator intercepts and delegates to `send_redirected_menu`, handling group-to-PM redirect, error fallback, cleanup, and `last_menu_id` tracking automatically.

### 5.2. FSM Data Keys
All keys stored in FSM state across the application:
- `last_menu_id`: Tracks active inline keyboard message ID for cleanup.
- `edit_topic_id`, `edit_group_id`, `edit_user_id`: Stores specific ID context between FSM states during admin rename flows.
- `disambig_query`, `disambig_action`, `disambig_context`: Keys used for cross-handler user search disambiguation logic. `disambig_action` values: `"dir_add"` (grant direct access), `"mod_add"` (assign moderator), `"admin_role_target"` (role assignment flow).
- `disambig_role_id`: Referenced in disambiguation state cleanup but never set by any current handler — ghost key from an incomplete refactor. Safe to ignore; cleared on every disambiguation resolution.
- `moderator_direct_access_topic`: Set in `moderator.py` (`mod_add_user_list_` flow) to carry the target topic ID into the `waiting_for_direct_access_user` FSM state.
- `moderator_edit_topic_id`: Set in `moderator.py` (`mod_topic_rename_` flow) to carry the target topic ID into the `waiting_for_topic_name` FSM state.
- `moderator_add_target_topic`: Set in `moderator.py` (`mod_moderator_add_` flow) to carry the target topic ID into the `waiting_for_user_data` FSM state.
- `moderator_current_topic`: Set in `moderator.py` (`mod_topic_select_` flow) to track the currently selected topic in the moderator session.

### 5.3. FSM Hygiene Rule
`state.clear()` is **forbidden** — it destroys all FSM data including `last_menu_id`, breaking the Sterile Interface. Always use `state.set_state(None)` to nullify state while preserving data.

### 5.4. Close Menu Handler Behaviour
`handlers/common.py` (`F.data == "close_menu"`) calls `UIService.delete_msg(callback.message)` directly — it deletes the message the button is attached to. It does **not** call `UIService.clear_last_menu`. After deletion, it sets `last_menu_id=None` via `state.update_data`.

### 5.5. Callback Resilience
`safe_callback()` decorator wraps all callback handlers. Suppresses `TelegramBadRequest` ("message is not modified") from rapid double-tapping.

---

## 6. OPERATIONAL CONSTRAINTS FOR AI AGENTS
- **Facade Integrity**: Never import internal routing segments bypassing the Facade logic (Db or Keyboards). All calls must traverse the main `__init__.py` boundaries respectively.
- **FSM Maintenance**: Every handler that sends a new menu must immediately update `last_menu_id` in FSM state with the sent message ID. Use `UIService.show_menu` — it handles `last_menu_id` tracking automatically. Manual `state.update_data(last_menu_id=...)` is only required in edge cases not covered by `UIService`.
- **UIService.show_menu as Single UI Gateway**: All menu transitions MUST use `UIService.show_menu(state, event, text, reply_markup)`. Direct calls to `callback.message.edit_text(...)`, `message.answer(...)`, or `callback.message.edit_reply_markup(...)` from handlers are prohibited.
- **Unified Navigation Protocol**: All standard UI returns and transitions from handlers SHOULD use `UIService.generic_navigator` instead of direct `UIService.show_menu` calls where possible, to centralize routing logic.
- **Handler State Signature Rule**: Every handler that calls `UIService.show_menu`, `UIService.ask_input`, or any other `UIService` method requiring `state` MUST declare `state: FSMContext` in its signature. Omitting it causes a `NameError` at runtime.
- **ManagementService Mutation Protocol**: All entity mutations MUST traverse `ManagementService`. Handlers are prohibited from performing input validation (e.g., regex checks, string splitting) or direct `db.*` writes. The service is responsible for "sanitizing" intent and returning a user-facing result. **Exception**: Data retrieval for keyboard rendering (GET-only) remains direct via `database.db`.
- **Search Delegation Rule**: Handlers must respect the `"SEARCH_REQUIRED"` signal from the management service. This ensures that complex search and disambiguation logic is shared rather than duplicated across admin and moderator flows.
- **Sterile UI Protocol Enforcement**: The system has moved away from direct Telegram API calls in handlers. Any new UI development must strictly follow the `UIService.show_menu` gateway pattern.
- **Sync Parity**: Administrative changes to topic names must be propagated both to the local DB (`db.update_topic_name`) and to the Telegram API (`bot.edit_forum_topic`).
- **IsGlobalAdmin Filter Pattern**: The `IsGlobalAdmin` custom filter applied at router level (`router.message.filter(IsGlobalAdmin())` + `router.callback_query.filter(IsGlobalAdmin())`) is the single authoritative access control for admin handlers. Do not add redundant inline `if user_id != ADMIN_ID: return` checks inside individual handlers.
- **noop Callback**: The `"noop"` callback data produced by `available_topics_kb()` has no registered handler. This is intentional.
- **Destructive Confirmation Protocol**: All destructive operations (e.g., `delete_group`, `delete_user`, `revoke_role`) MUST traverse a confirmation step via `UIService.get_confirmation_ui` and be executed through `ManagementService.execute_deletion` in `handlers/common.py`.
- **Roles Separation of Concerns**: The system uses a **Dashboard Pattern** for role information (FAQ and Global Lists in `common.py`) and a **Context Pattern** for role management (individual user actions in `admin.py`/`user_edit_kb`).
- **AdminStates Scope**: FSM states (`AdminStates`) are defined and used exclusively within `handlers/admin.py`. Never reference or set `AdminStates` from outside this file.
- **ModeratorStates Scope**: FSM states (`ModeratorStates`) are defined and used exclusively within `handlers/moderator.py`. Never reference or set `ModeratorStates` from outside this file.
- **Keyboard Data Access**: `keyboards/admin_kb.py`, `keyboards/moderator_kb.py`, and `keyboards/user_kb.py` are permitted to import from `database.db` directly for rendering live data. This is the only sanctioned exception to the Facade rule for the keyboard layer.
- **Virtual Superadmin Encapsulation**: The logic for granting the virtual `superadmin` role based on config `ADMIN_ID` resides safely inside `database/roles.py`'s `get_user_roles(user_id)`. UI handlers must not manipulate `ADMIN_ID` directly to append this role manually, since the DB response is pre-enriched.
- **Keyboard Import Order Criticality**: The import sequence in `keyboards/__init__.py` (`admin_kb` → `user_kb` → `moderator_kb`) is an architectural invariant. Modifying this order can lead to unpredictable runtime behavior due to wildcard exports shadowing identically named functions.
- **Search Deduplication Rule**: Search result fetching logic must use the `_fetch_search_results(s_type, query)` helper in `handlers/common.py`. Do not inline `if s_type == "user" / elif group / elif topic` branches in individual handlers.
- **Verify Before Change (Rule 21)**: BEFORE making any code changes, it is mandatory to view the target file and all related signatures (methods, keyboards, DB tables). Writing calls without confirming their existence in the current code context is strictly prohibited.

---

## 7. CRITICAL CONSTANTS

- **BOT_TOKEN** — `str`. Source: `.env` → `config.py` (`get_env_or_raise`). Raises `ValueError` on missing or empty value. Used in `loader.py` for `Bot` initialization.
- **ADMIN_ID** — `int`. Source: `.env` → `config.py` (cast via `int`). Used via `PermissionService.is_global_admin` to route handlers in the `IsGlobalAdmin` filter. Also enriched dynamically within `db.get_user_roles`.
- **GROUP_ID** — `int`. Source: `.env` → `config.py`. Used exclusively in `handlers/admin.py` and `handlers/moderator.py` as the `chat_id` argument for Telegram API calls. Expected to be a negative integer (Telegram supergroup convention). **Not used as a middleware guard condition.**
- **Topic ID `-1`** — Logical mapping for the "General" topic in a forum-enabled Telegram chat.

---

## 8. TESTING INFRASTRUCTURE
Comprehensive automated testing suite using `pytest`. Tests are an integral part of the codebase.

### 8.1. Configuration (`tests/conftest.py`)
- **Database Isolation**: `mock_db_path` (autouse) redirects `connection.DB_PATH` to a temporary file in `tmp_path` and runs `init_db()`. This ensures a clean schema and WAL support for every test.
- **Mocked Bot**: `mock_bot` fixture provides an `AsyncMock(spec=Bot)`. Crucially, `bot.return_value` is mocked to support the `bot(method)` call pattern in aiogram 3.
- **Mocks**: `mock_dispatcher`, `mock_state` (FSMContext) available for handler/middleware testing.

### 8.2. Test Categories
- **tests/test_database/**: Unit and integration tests for SQL operations. Focus: CRUD, cascading deletions, and access evaluation logic.
- **tests/test_services/**: Tests for `ManagementService` and `PermissionService`. Focus: Validation logic, Search-Or-Action protocol, and role resolution.
- **tests/test_handlers/**: Unit tests for handlers and middlewares. Focus: Routing, state transitions, and stealth moderation filters. Uses `__wrapped__` to bypass `sterile_command` redirects during logic verification.
- **tests/test_integration/**: End-to-End flow tests using a real `Dispatcher` but mocked `Bot`. Focus: Full update processing chain from middleware to final handler response.

### 8.3. Testing Rules
1. **Repository Standards**: The `tests/` directory is a permanent part of the repository.
2. **Ephemeral DB**: Always use the `mock_db_path` fixture. Writing to `bot.db` during testing is strictly prohibited.
3. **No Network**: All external API calls (Telegram) MUST be mocked via `mock_bot`.
4. **Router Detach**: When using global routers in integration tests, use `router._parent_router = None` before including them in a test-local `Dispatcher` to prevent `RuntimeError`.
5. **Pydantic Validation**: All mocked `Message` and `Update` objects must include valid data (e.g., `date=datetime.now()`) to pass Pydantic V2 validation used by aiogram 3.


