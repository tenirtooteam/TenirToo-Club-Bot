# PROJECT_LOGIC: Tenir-Too Access Control Bot

## 1. PROJECT IDENTITY & STACK
- **System Name**: Tenir-Too Access Control Bot.
- **Framework**: aiogram 3.4.1 (Asynchronous Python framework).
- **Database Engine**: SQLite 3 with Write-Ahead Logging (WAL), `PRAGMA journal_mode=WAL` for concurrent access.
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

### 2.2. Module Registry
Complete file list with individual responsibilities and full function inventory:

- **main.py** — Entry point: `setup_logging` (RotatingFileHandler, 5MB limit, 5 backup files, dual console+file output to `logs/bot.log`), DB initialization via `db.init_db()`, router registration (common → user → admin), outer middleware chaining (UserManager → ForumUtility → AccessGuard), bot polling with `drop_pending_updates=True`.
- **loader.py** — Initializes `Bot` and `Dispatcher` with `MemoryStorage`.
- **config.py** — Helper `get_env_or_raise(key)`: reads env var, raises `ValueError` on missing/empty value. Exposes constants: `BOT_TOKEN` (str), `ADMIN_ID` (int), `GROUP_ID` (int), `IMMUNITY_FOR_ADMINS` (bool, default False). Raises on missing values at import time.
- **database/__init__.py** — Package initializer: `from . import db`. Enables the `from database import db` import pattern used across the codebase. No logic of its own.
- **database/connection.py** — SQLite connection context manager `get_conn`: opens connection with `check_same_thread=False`, activates WAL on every connection, guarantees closure in `finally`. `DB_PATH` is resolved relative to `connection.py`'s own file location (`os.path.dirname(__file__)`), placing `bot.db` inside the `database/` directory. `init_db()`: creates all tables and indexes in a single transaction; re-raises any exception after logging (fail-closed).
- **database/members.py** — Transactional CRUD for users: `add_user`, `delete_user`, `update_user_name`, `get_user_name`, `get_all_users`, `user_exists`.
- **database/topics.py** — Transactional CRUD for topics (registration, renaming, deletion): `get_all_unique_topics`, `update_topic_name`, `get_topic_name`, `delete_topic`, `register_topic_if_not_exists`.
- **database/groups.py** — Transactional CRUD for global groups and group-topic/user-group linkages: `create_group`, `get_all_groups`, `delete_group`, `get_topics_of_group`, `add_topic_to_group`, `remove_topic_from_group`, `get_groups_by_topic`, `get_user_groups`, `grant_group`, `revoke_group`, `get_group_name`, `get_user_available_topics`.
- **database/roles.py** — Roles definitions, issuance to users, and role scoping: `add_role`, `get_role_id`, `grant_role`, `revoke_role`, `get_user_roles`, `get_moderators_of_topic`, `is_global_admin`, `is_moderator_of_topic`, `get_all_roles`.
- **database/permissions.py** — Direct access management and unified access evaluation: `can_write`, `is_topic_restricted`, `get_topic_authorized_users`, `grant_direct_access`, `revoke_direct_access`, `has_direct_access`, `get_direct_access_users`.
- **database/db.py** — Single facade re-exporting all functions from `members.py`, `topics.py`, `groups.py`, `roles.py`, `permissions.py`, and `init_db` + `get_conn` from `connection.py`, as a unified `db` module. **The only permitted import point for all data operations.**
- **services/ui_service.py** — Centralized UI lifecycle via `UIService` class (all methods `@staticmethod`): `clear_last_menu(state, bot, chat_id)` (delete tracked menu via `bot.delete_message`, nullify `last_menu_id` in FSM state in `finally` block), `delete_msg(message)` (safe single-message delete, exceptions silently swallowed), `finish_input(state, message)` (atomic sequence: `clear_last_menu` → `delete_msg` → `state.set_state(None)`).
- **services/access_service.py** — Business logic via `AccessService` class (all methods `@staticmethod`): `ensure_user_registered(user)` (auto-registration on first contact; naming fallback: `Пользователь_{user_id}` if no name available; if only `last_name` present — promoted to `first_name`), `can_user_write_in_topic(user_id, topic_id)` (write-permission check: unrestricted topics return `True` immediately, restricted topics delegate to `db.can_write`).
- **services/permission_service.py** — Higher level business abstraction for roles. Fetches user's manageable topics (`get_manageable_topics`), or checks admin override.
- **services/notification_service.py** — Feature extension via `NotificationService` class (methods `@staticmethod`): `send_native_all(bot, chat_id, topic_id, sender_name, text)` (sends a single message containing invisible mentions up to 50 authorized users via `db.get_topic_authorized_users`).
- **services/callback_guard.py** — `safe_callback()` decorator factory (no parameters): suppresses `TelegramBadRequest` with "message is not modified" (calls `callback.answer()` silently), catches all other `TelegramBadRequest` and unknown exceptions with user-facing `show_alert=True` error message.
- **handlers/common.py** — Global `close_menu` callback handler (`F.data == "close_menu"`) and global role-aware `/help` command: deletes the menu message via `UIService.delete_msg(callback.message)`, nullifies `last_menu_id` in FSM state via `state.update_data(last_menu_id=None)`, answers callback with «Закрыто». Note: uses `delete_msg` directly on `callback.message`, not `clear_last_menu`.
- **handlers/admin.py** — All admin flows protected at router level by `IsAdmin` filter (custom `aiogram.filters.Filter`; checks `event.from_user.id == ADMIN_ID`; applied to both `router.message` and `router.callback_query`). FSM states defined in `AdminStates(StatesGroup)`: `waiting_for_group_name`, `waiting_for_topic_name`, `waiting_for_user_data`, `waiting_for_new_name`. Flows: admin dashboard (`/admin`), group management (list, detail, create, delete), topic management (global list, per-group list, unified detail view via `topic_detail` handler — handles both `topic_global_view_*` and `topic_in_group_*` callbacks, rename with Telegram API sync, add to group, remove from group, global DB delete), user management (list, detail, add manually, rename, delete, group access toggle).
- **handlers/moderator.py** — Moderator flows protected by `IsTopicManager` filter. Commands: `/mod`. Allows moderators to toggle direct access (`direct_topic_access`) for users in their assigned topic, view attached groups, and switch between user management modes (view existing access vs `➕ Выдать доступ`).
- **handlers/user.py** — User-facing flows: `/start` (clears old menu, deletes command message, sends main menu, tracks `last_menu_id`), `back_to_user_main` (`F.data == "user_main"`), `user_profile_callback` (`F.data == "user_profile_view"`: shows name from DB, user ID, active groups), `show_user_topics` (`F.data == "user_topics"`: shows all topics with ✅/❌ access status), `user_topic_detail` (`F.data.startswith("u_topic_info_")`: shows topic name, ID, which groups have access, user's own access status), `handle_all_mention` (handles `@all` prefix in non-private chats, triggers `NotificationService.send_native_all` and deletes trigger message).
- **middlewares/access_check.py** — Three-middleware sequential chain: `UserManagerMiddleware` → `ForumUtilityMiddleware` → `AccessGuardMiddleware`. All three are registered as `outer_middleware` on `dp.message`.
- **keyboards/__init__.py** — Keyboard layer facade: `from .admin_kb import *`, `from .moderator_kb import *`, `from .user_kb import *`. Wildcard re-export enables the `import keyboards as kb` pattern used in all handlers. Structurally equivalent to `database/db.py` for the keyboard layer. All keyboard builder functions are accessed through this single import point.
- **keyboards/admin_kb.py** — Inline keyboard builders for all admin menus. Imports from `database.db` to render live data. Functions: `main_admin_kb()`, `all_topics_kb()`, `topic_edit_kb(topic_id, group_id=0)`, `group_topics_list_kb(group_id)`, `available_topics_kb(group_id)` (filters out already-assigned topics; renders `"noop"` callback button when no topics are available — intentional silent no-op, no handler registered), `groups_list_kb()`, `group_edit_kb(group_id)`, `users_list_kb()`, `user_edit_kb(user_id)`, `user_groups_edit_kb(user_id)` (renders ✅/❌ per group with toggle action).
- **keyboards/moderator_kb.py** — Inline keyboard builders for topic moderators. Includes user management split (existing access vs '➕ Выдать доступ').
- **keyboards/user_kb.py** — Inline keyboard builders for user menus. Imports from `database.db`. Functions: `user_main_kb()`, `user_topics_list_kb(user_id)` (renders all topics with ✅/❌ access status for user), `user_topic_detail_kb()`.
- **local_scripts/dev_run.py** — Developer-only hot-reload runner (not part of bot runtime). Uses `watchfiles.run_process` to monitor project root and restart `main.py` via subprocess on any `.py` file change. Ignores `logs/`, `database/`, `local_scripts/` directories to prevent restart loops on DB writes and log rotation.
- **local_scripts/Gemini_maker.py** — Developer-only AI context packager (not part of bot runtime). Traverses the project, collects all `.py` files and `requirements.txt`, concatenates them into `local_scripts/full_project_code.txt` for uploading to AI assistants as a single-file context snapshot. Excludes `venv`, `.git`, `__pycache__`, `logs`, `local_scripts` directories and all `.db` files.
- **local_scripts/full_project_code.txt** — Auto-generated output of `Gemini_maker.py`. Not committed, regenerated on demand.

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

Direct imports from internal DB files (`database/*.py`) in any layer above `database/db.py` are a critical violation of the Facade pattern. Direct imports from individual keyboard files (`admin_kb`, `user_kb`, `moderator_kb`) bypassing `keyboards/__init__.py` break the keyboard layer contract.

### 2.4. Database Facade
`database/db.py` is the exclusive interface for all data operations. Direct imports from files like `database/topics.py` or `database/members.py` are a critical architectural violation.

### 2.5. Keyboard Facade
`keyboards/__init__.py` is the exclusive import point for all keyboard builders. Handlers must use `import keyboards as kb` and access all functions via `kb.*`. This mirrors the Database Facade pattern at the keyboard layer.

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
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

CREATE TABLE IF NOT EXISTS direct_topic_access (
    user_id  INTEGER,
    topic_id INTEGER,
    PRIMARY KEY (user_id, topic_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS groups (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS group_topics (
    group_id INTEGER,
    topic_id INTEGER,
    PRIMARY KEY (group_id, topic_id),
    FOREIGN KEY (group_id) REFERENCES groups(id)
);

CREATE TABLE IF NOT EXISTS users (
    user_id    INTEGER PRIMARY KEY,
    first_name TEXT,
    last_name  TEXT
);

CREATE TABLE IF NOT EXISTS user_groups (
    user_id  INTEGER,
    group_id INTEGER,
    PRIMARY KEY (user_id, group_id),
    FOREIGN KEY (user_id)  REFERENCES users(user_id),
    FOREIGN KEY (group_id) REFERENCES groups(id)
);

CREATE TABLE IF NOT EXISTS topic_names (
    topic_id INTEGER PRIMARY KEY,
    name     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_user_groups_user_id   ON user_groups(user_id);
CREATE INDEX IF NOT EXISTS idx_group_topics_topic_id ON group_topics(topic_id);
~~~

> Note: SQLite FK enforcement is disabled by default. Cascading deletes are implemented manually within transactions in `access.py`. Do not rely on `ON DELETE CASCADE`.

### 3.2. Access Control Logic
- **Default State**: A topic is "Public" if absent from the `group_topics` registry — all users may write.
- **Restricted State**: A topic becomes "Private" once associated with any group. Write access is granted only if the user shares a common group linkage with the topic.
- **Transactional Integrity**: Manual cascading deletion — removing a Group or Topic explicitly purges all orphan records in `user_groups` and `group_topics` within the same transaction. SQLite FK cascades are not relied upon (disabled by default in SQLite).

### 3.3. Upsert Pattern
`update_topic_name(topic_id, name)` uses `INSERT OR REPLACE INTO topic_names` — an upsert pattern. This means the function both inserts new topic name records and updates existing ones atomically. This is the only function in the codebase that uses this pattern; all other mutations use standard `INSERT` or `UPDATE`.

### 3.4. Indexes
- `idx_user_groups_user_id ON user_groups(user_id)` — hot path for access checks.
- `idx_group_topics_topic_id ON group_topics(topic_id)` — hot path for topic restriction lookups.

---

## 4. MIDDLEWARE EXECUTION LOGIC
Sequential 3-stage pipeline registered as `outer_middleware` on `dp.message` — order is fixed and must not be changed.

### Stage 1 — UserManagerMiddleware
Operates on all chat types. Guard: skips processing if `event.from_user` is absent or is a bot (`event.from_user.is_bot`). For all real users: calls `AccessService.ensure_user_registered(event.from_user)` — auto-registers the user in `users` table if not present. Naming fallback hierarchy: (1) if no name at all → `Пользователь_{user_id}`; (2) if only `last_name` present → promoted to `first_name`. Always passes to the next handler regardless of registration outcome.

### Stage 2 — ForumUtilityMiddleware
Guard: if `event.chat.type == "private"` → passes through immediately without processing. For group messages, branching logic (mutually exclusive, evaluated in order):
1. `forum_topic_edited` event → sync new name to DB via `db.update_topic_name` + delete service message → **early return** (does not call next handler).
2. `forum_topic_created` event → delete service message → **early return** (does not call next handler).
3. Normal message → auto-register topic via `db.register_topic_if_not_exists` (maps `message_thread_id` or `-1` for General) → pass to next handler.

### Stage 3 — AccessGuardMiddleware
Guard: if `event.chat.type == "private"` or `event.from_user.id == event.bot.id` → passes through immediately. If user is global admin and `config.IMMUNITY_FOR_ADMINS` is True, passes through. For all other messages: resolves `topic_id` (`message_thread_id` or `-1`), calls `AccessService.can_user_write_in_topic`. If access denied → silently deletes message and returns (no next handler call). All decisions logged: denied messages at `INFO` (❌), permitted messages at `INFO` (✅).

### Private Chat Guard Pattern
None of the three middlewares use `GROUP_ID` as a guard condition. The real guard pattern across all three stages is `event.chat.type == "private"` for early pass-through, applied independently per middleware. This means the bot will process group messages in **any** group it is present in — not exclusively `GROUP_ID`. The `GROUP_ID` constant is used only in `handlers/admin.py` for Telegram API calls (`bot.edit_forum_topic`).

### Error Handling
All three stages follow a **fail-open** strategy: non-critical exceptions are caught, logged, and the pipeline continues.

- **`ForumUtilityMiddleware`**: `event.delete()` calls are wrapped in `try/except Exception: pass` — failure to delete a service message is non-fatal and silently ignored.
- **`AccessGuardMiddleware`**: deletion failure on moderation is caught and logged at `ERROR` level; the handler returns without re-raising, preventing cascade failure.
- **`UserManagerMiddleware`**: delegates exception handling to `AccessService.ensure_user_registered`, which wraps DB calls via the facade. SQLite errors in `add_user` are logged at `ERROR` level without raising.
- **Critical exception** (fail-closed): `init_db()` in `connection.py` re-raises any exception after logging — a DB initialization failure must halt the bot immediately.

---

## 5. UI/UX & STATE MANAGEMENT (FSM)

### 5.1. The "Sterile Interface" Protocol
- **last_menu_id**: FSM key tracking the message ID of the currently active inline keyboard. Set via `state.update_data(last_menu_id=sent_message.message_id)` immediately after every menu deployment.
- **UIService.clear_last_menu**: Reads `last_menu_id` from FSM state, deletes the tracked message via `bot.delete_message`, nullifies `last_menu_id` in FSM data in a `finally` block (guaranteed even if deletion fails).
- **UIService.finish_input**: Atomic sequence: (1) `clear_last_menu`, (2) `delete_msg` (user's trigger message), (3) `state.set_state(None)`.

### 5.2. FSM Data Keys
All keys stored in FSM state across the application:

| Key | Set by | Used by | Purpose |
|---|---|---|---|
| `last_menu_id` | All handlers that send a menu | `UIService.clear_last_menu`, `handlers/common.py` | Tracks active inline keyboard message ID for cleanup |
| `edit_topic_id` | `topic_rename_init` | `process_topic_name_save` | Stores topic ID between FSM states during rename flow |
| `edit_group_id` | `topic_rename_init` | `process_topic_name_save` | Stores group context during topic rename flow |
| `edit_user_id` | `user_rename_init` | `process_user_rename` | Stores user ID between FSM states during rename flow |

### 5.3. FSM Hygiene Rule
`state.clear()` is **forbidden** — it destroys all FSM data including `last_menu_id`, breaking the Sterile Interface. Always use `state.set_state(None)` to nullify state while preserving data.

### 5.4. Close Menu Handler Behaviour
`handlers/common.py` (`F.data == "close_menu"`) calls `UIService.delete_msg(callback.message)` directly — it deletes the message the button is attached to. It does **not** call `UIService.clear_last_menu`. After deletion, it sets `last_menu_id=None` via `state.update_data`. This is intentional: the message is already physically in scope via `callback.message`, so no FSM key lookup is needed.

### 5.5. Callback Resilience
`safe_callback()` decorator wraps all callback handlers. Suppresses `TelegramBadRequest` ("message is not modified") from rapid double-tapping. Catches unknown exceptions and shows a user-facing error alert via `show_alert=True` without crashing.

---

## 6. OPERATIONAL CONSTRAINTS FOR AI AGENTS
- **Facade Integrity (Database)**: Never import from `database/topics.py` or `database/members.py` directly. All data calls must traverse `database.db`.
- **Facade Integrity (Keyboards)**: Never import directly from `keyboards/admin_kb.py` or `keyboards/user_kb.py`. All keyboard access must go through `import keyboards as kb`.
- **FSM Maintenance**: Every handler that sends a new menu must immediately update `last_menu_id` in FSM state with the sent message ID.
- **Sync Parity**: Administrative changes to topic names must be propagated both to the local DB (`db.update_topic_name`) and to the Telegram API (`bot.edit_forum_topic`). DB-only updates are incomplete. API call failures are non-fatal and logged as warnings with a status note returned to the admin.
- **Group Type Guard**: Middleware group-message logic must guard with `if event.chat.type == "private": return await handler(event, data)` — not with a `GROUP_ID` equality check. The `GROUP_ID` constant is reserved for Telegram API calls only (e.g., `bot.edit_forum_topic`).
- **IsAdmin Filter Pattern**: The `IsAdmin` custom filter applied at router level (`router.message.filter(IsAdmin())` + `router.callback_query.filter(IsAdmin())`) is the single authoritative access control for admin handlers. Do not add redundant inline `if user_id != ADMIN_ID: return` checks inside individual handlers — this pattern has been removed from the codebase.
- **noop Callback**: The `"noop"` callback data produced by `available_topics_kb()` has no registered handler. This is intentional — the button is purely informational ("all topics already in group"). Do not add a `noop` handler. Do not rename this callback data.
- **Destructive Confirmation Gap**: The current implementation does NOT include confirmation steps before `delete_group` and `delete_user` operations in the admin handler — these execute immediately on callback. This is a known deviation from the desired safety standard. Any new destructive operation added to the codebase MUST include a confirmation step to prevent scope creep of this gap.
- **AdminStates Scope**: FSM states (`AdminStates`) are defined and used exclusively within `handlers/admin.py`. Never reference or set `AdminStates` from outside this file.
- **Keyboard Data Access**: `keyboards/admin_kb.py` and `keyboards/user_kb.py` are permitted to import from `database.db` directly for rendering live data. This is the only sanctioned exception to the "handlers → services → db" flow and is architecturally intentional.
- **local_scripts/ Exclusion**: Files in `local_scripts/` are developer tooling only. They must not be imported by any bot module and must not be modified as part of feature development.

---

## 7. CRITICAL CONSTANTS

- **BOT_TOKEN** — `str`. Source: `.env` → `config.py` (`get_env_or_raise`). Raises `ValueError` on missing or empty value. Used in `loader.py` for `Bot` initialization.
- **ADMIN_ID** — `int`. Source: `.env` → `config.py` (cast via `int(get_env_or_raise(...))`). Raises `ValueError` on missing or non-integer value. Applied as `IsAdmin` filter at router level in `handlers/admin.py` (both `router.message.filter` and `router.callback_query.filter`).
- **GROUP_ID** — `int`. Source: `.env` → `config.py` (cast via `int(get_env_or_raise(...))`). Raises `ValueError` on missing or non-integer value. Used exclusively in `handlers/admin.py` as the `chat_id` argument for `bot.edit_forum_topic` API calls. Expected to be a negative integer (Telegram supergroup convention). **Not used as a middleware guard condition.**
- **Topic ID `-1`** — Logical mapping for the "General" topic in a forum-enabled Telegram chat (messages outside any explicit topic thread). Assigned by `ForumUtilityMiddleware` when `event.message_thread_id` is `None`. Registered with name `"General"` by `register_topic_if_not_exists`.
- **DB_PATH** — Not an env variable. Hardcoded in `database/connection.py` via `os.path.join(os.path.dirname(__file__), "bot.db")`. Always resolves to `database/bot.db` relative to the source file, independent of the working directory at launch.

