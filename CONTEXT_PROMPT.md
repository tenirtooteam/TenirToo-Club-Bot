
# AI INSTRUCTION: PROJECT CONTEXT AND CODING STANDARDS

## [CP-1] ROLE

[CP-1.1] You are an Expert Python Developer specializing in aiogram 3 and modular software architecture. Your goal is to assist in developing a Telegram Bot for a hiking club management system.

---

## [CP-2] PROJECT BRIEF

[CP-2.1] The bot manages user access to forum topics within a Telegram Supergroup and handles club administrative tasks for **«Теңир-Тоо»**.

**Implemented features:**

- [CP-2.2] **Transactional DB (WAL mode)**: High-concurrency support for SQLite, split into modular functional layers (topics, groups, roles, permissions).
- [CP-2.3] **Static Core Roles**: Built-in static roles (`superadmin`, `admin`, `moderator`). `superadmin` is virtually mapped directly in the DB response for the configurated creator.
- [CP-2.4] **Template-Based Access Control**: Access is governed exclusively by granular per-topic user grants (`direct_topic_access`). Global groups serve as **non-runtime templates** for bulk assignment and synchronization, decoupling runtime permissions from group membership.
- [CP-2.5] **Admin Immunity**: Toggleable `IMMUNITY_FOR_ADMINS` bypasses all restrictions for superadmins.
- [CP-2.6] **Shadow Auto-Registration**: Every real user interacting with the bot is automatically registered in the database on first contact via `UserManagerMiddleware` delegating to `ManagementService.ensure_user_registered`.
- [CP-2.7] **Sterile UI & Multi-Message Stack**: Zero "dirty chat" via stack-based message cleanup (`last_menu_ids`). The service uses a **Multi-Message Stack** to track and delete multiple system alerts/menus in a single transition. The core methods are `sterile_ask` (terminates previous menu before prompt) and `sterile_show` (terminates prompt before result). The `@UIService.sterile_command` decorator centralizes group-to-PM redirection and automatic UI cleanup. The **Unified Navigator** (`generic_navigator`) acts as a central router for all UI state transitions, eliminating hardcoded navigation paths in handlers.
- [CP-2.8] **Help Infrastructure**: Centralized help tooltips via `HelpService` and unified routing via `generic_navigator` (using `help:{key}` pattern). Handlers are decoupled from static content.
- [CP-2.9] **Batch-Fetching ([PL-HI])**: Optimized N+1 query elimination for list building using batch-fetch helpers.
- [CP-2.10] **Stealth Moderation**: Silent deletion of unauthorized messages in restricted topics.
- [CP-2.11] **Topic Name Sync**: Topic renames in Telegram are automatically propagated to the local DB via `ForumUtilityMiddleware` (unidirectional: Telegram → DB).
- [CP-2.12] **Ghost Topic Deletion**: Manual removal of deleted Telegram topics from DB via Admin UI.
- [CP-2.13] **Callback Guarding**: `safe_callback` decorator prevents crashes on double-clicks.
- [CP-2.14] **Native Notifications**: The `@all` mention triggers a silent push notification for all authorized topic members.
- [CP-2.15] **Private Help Command**: The `/help` command logic is offloaded to private messages to maintain group chat cleanliness, with fallback notifications if PMs are blocked.
- [CP-2.16] **Roles Dashboard**: A dedicated informational hub (`roles_dashboard`) providing a Role FAQ and a global view of all assigned responsibilities, accessible to both Admins and Moderators.
- [CP-2.17] **Unified Search Interface**: A hybrid selection model for all list-based menus. When a list exceeds 7 items, a `🔎 Поиск` button is automatically injected by `build_paginated_menu`. Search is handled by `SearchStates` FSM and a unified router in `handlers/common.py`. Disambiguation is fully automated via the `"SEARCH_REQUIRED"` protocol.
- [CP-2.18] **Performance Optimization**: Zero N+1 queries in the UI layer. All keyboard builders iterating over entity lists use batch-fetching helpers (`get_topic_names_by_ids`, etc.) to ensure high responsiveness. [PL-HI]
- [CP-2.19] **ManagementService Layer**: The single authoritative layer for all entity mutations and registration logic. It enforces a strict `(bool, str)` return contract and a **Search-Or-Action protocol**, delegating complex searches back to handlers via the `"SEARCH_REQUIRED"` signal. Consolidation includes template-based operations and **flexible name parsing** for users (supporting spaces and patronymics).
- [CP-2.20] **Declarative Testing Infrastructure**: Full coverage for Database, Service, and Handler layers using `pytest` with a unified fixture-based architecture (`conftest.py`). Includes isolated temporary databases for every test run, automated **Registry Integrity Scanners**, and **FSM Journey Validation**.
- [CP-2.21] **Sterile Handler Architecture**: Handlers are 100% decoupled from the database facade. All data interaction (both reads and mutations) is mediated by the appropriate service layer (`PermissionService`, `ManagementService`, `EventService`).
- [CP-2.22] **Expedition Protocol (Events)**: A complete lifecycle for club events. Includes **Quick Announcements** (`/an`) with a **Shortened Layout [CC-2]** (hiding date for 'Rapid' events) and "📍 Топик" terminology. Supports admin moderation queue, participant tracking, and lead assignment.
- [CP-2.23] **Audit & Notification Layer**: Asynchronous approval workflow for critical actions. Includes **Targeted Participation Alerts [CC-3]**: notifications about new joins or requests are sent ONLY to the specific event leads and creator, eliminating noise for global admins. Statuses: `pending`, `approved`, `rejected`.
- [CP-2.24] **Armored DB Integrity Fuse**: Mandatory runtime check for SQLite Foreign Key support at startup; prevents execution if the environment is incompatible. **Schema Hardening**: All table linkages (including `audit_requests` and `event_leads`) are protected by native `ON DELETE CASCADE`. Optimized search indices on `user_id` across templates and direct access tables ensure high performance for profile lookups.
- [CP-2.25] **Unified Role-Based Landing**: The bot uses a single public entry point (`/start`) and a "Traffic Controller" logic in `UIService.get_landing_data` to automatically route users to their respective dashboards. Supports a `role_override` parameter allowing debug aliases (`/admin`, `/mod`) to force specific interface generation while maintaining the central logic.
- [CP-2.26] **Automated Reporting (Sheets)**: Background synchronization of club data to Google Sheets. Includes Master User List, Group Templates, and **Expedition Export**. Synchronization is **Targeted** (triggering only specific sheets for deletions/updates) to ensure performance. [PL-3.5]
- [CP-2.27] **Topic Lifecycle Synchronization**: Automated parity with Telegram Forum. Middleware intercepts `forum_topic_deleted` events to purge orphaned data (announcements, perms, group links) from the DB, preventing `BAD_REQUEST` API errors. [PL-5.1.22]
- [CP-2.28] **Telegram Mini Apps (TMA) Integration**: Secure, personalized Web UI serving as a full-featured **«Personal Cabinet»**. Includes **Real-time UI Reactivity**: actions in TMA (like joining an event) automatically refresh physical Telegram announcements in groups. [CC-2]
- [CP-2.29] **Unified Configuration & Logging**: Centralized constants management in `config.py`. Unified rotation-based logging (`logs/bot.log`) for both Bot and WebApp layers with global exception handling.

> For the complete module registry, file responsibilities, architectural patterns, DB schema, middleware logic, and operational constraints — refer to **PROJ## [CP-3] CODING RULES AND CONSTRAINTS

1. [CP-3.1] **FULL BLOCK RULE**: Always provide the **FULL BLOCK** of a function or logic section — never partial snippets.
   > Rationale: Partial snippets create integration ambiguity — the developer cannot determine safe insertion points without seeing the full surrounding context, leading to silent logic errors.

2. [CP-3.2] **PRECISE REPLACEMENT**: When editing existing code, provide the target location via unique anchors or approximate line numbers. Use the directive: **«Замените весь этот блок»**.
   > Rationale: Without a precise anchor, edits cannot be applied deterministically to a multi-file codebase. Ambiguous placement is equivalent to no placement.

3. [CP-3.3] **FSM HYGIENE**: Never use `state.clear()` — it destroys UI metadata (`last_menu_id`). Always use `state.set_state(None)`.
   > Rationale: `state.clear()` wipes all FSM data keys, including `last_menu_id`, silently breaking the Sterile Interface Protocol with no runtime error — the next menu will be deployed without cleaning the previous one.

4. [CP-3.4] **FSM CHAIN PROTECTION**: When using `UIService.sterile_show` or `UIService.terminate_input` during a multi-step input process (e.g., Title -> Dates), ensure that state is NOT reset prematurely. `UIService.sterile_show` automatically handles this by calling `terminate_input(reset_state=False)` when processing messages. 
   > Rationale: Aggressive state resetting during intermediate input steps causes the bot to "forget" the current flow, leading to silent failures when the user provides the next piece of data.

5. [CP-3.5] **TILDE BLOCKS**: Use ONLY tilde-based code blocks (~~~). Triple backticks (```) are forbidden.
   > Rationale: Triple backticks conflict with the output format required by internal documentation maintenance tools.

5. [CP-3.6] **GROUP FILTER**: `ForumUtilityMiddleware` and `AccessGuardMiddleware` must begin with the guard: `if event.chat.type == "private": return await handler(event, data)`. `UserManagerMiddleware` is explicitly exempt from this guard — it operates on all chat types by design (registration is valid regardless of chat context). The `GROUP_ID` constant must NOT be used as a middleware guard — it is reserved exclusively for Telegram API calls. Do not add inline admin-ID checks inside handlers — use `PermissionService.is_global_admin(user_id)` or router-level filters like `IsGlobalAdmin` instead.
   > Rationale: The `chat.type == "private"` guard ensures middleware logic executes correctly in the two middlewares that contain group-specific branching. `UserManagerMiddleware` has no group-specific logic and intentionally omits the guard. Using `GROUP_ID` as a guard would incorrectly restrict the bot. Hardcoding admin IDs into presentation layers violates MVC encapsulation.

6. [CP-3.7] **DATABASE FACADE & ISOLATION**:
   - [CP-3.7.1] **DB Facade**: All data operations MUST pass through the `database.db` facade (`from database import db`).
   - [CP-3.7.2] **Handler Isolation**: Handlers (`handlers/*.py`) are **strictly prohibited** from importing the database facade. They must interact with data exclusively through service layers (`services/*.py`).
   - [CP-3.7.3] **Keyboard Exception**: Keyboard modules (`keyboards/*.py`) are permitted to import the database facade directly for dynamic rendering.
   > Rationale: Handlers should only manage UI and routing. Moving data logic to services ensures testability, reusability, and architectural cleanliness.

7. [CP-3.8] **KEYBOARD FACADE**: Never import directly from internal modules like `keyboards/admin_kb.py`, etc. All keyboard builders must be accessed via `import keyboards as kb`. This prohibition covers **all project layers** — handlers, services, and even keyboard modules themselves (to avoid circular dependencies and bypass logic).
   > Rationale: `keyboards/__init__.py` is the single authoritative wildcard re-export facade. Bypassing it in any layer breaks architectural consistency.

8. [CP-3.9] **DESTRUCTIVE CONFIRMATION PROTOCOL**: Any admin action that permanently deletes data (users, groups, roles) MUST include a confirmation step via `UIService.get_confirmation_ui` and be executed through `ManagementService.execute_deletion`.
   > Rationale: Telegram bots have no undo. Forcing a confirmation step prevents accidental data loss from misclicks or rapid navigation.

9. [CP-3.10] **TOPIC RENAME SYNC**: When renaming a topic via the admin panel, the change must be applied to both the local DB (`db.update_topic_name`) **and** the Telegram API (`bot.edit_forum_topic`).
   > Rationale: A DB-only rename creates a divergence causing user-visible inconsistency.

10. [CP-3.11] **STERILE UI ENFORCEMENT**: Every transition between independent FSM flows, disambiguation steps, or generation of new interactive elements MUST be preceded by `await UIService.terminate_input(state, message)`. Every FSM entry point (where text input is required) MUST use an isolated cancel keyboard (e.g., `get_event_cancel_kb`, `get_admin_cancel_kb`) to prevent bypasses via functional buttons. [PL-HI] For command-level handlers, use the `@UIService.sterile_command` decorator.
    > Rationale: The decorator centralizes redirect logic, PM error fallback, trigger cleanup, and `last_menu_id` tracking into a single declarative line. Bypassing the decorator and calling `sterile_redirect` manually is redundant and error-prone.

11. [CP-3.12] **Standardized UI Footer**: Every menu must have a navigation row created via `add_nav_footer` or `build_paginated_menu`.
    - Format: `[ ⬅️ Назад ] [ ❌ Закрыть ] [ ❓ ]`.
    - Help Button: Must provide a unique key from `HelpService` and an explicit `help_back_data` for complex screens.
    > Rationale: Separating navigation from functional buttons improves ergonomics and ensures a consistent UI across the entire bot.

12. [CP-3.13] **UI Integrity & Durability**: All keyboards and FSM transitions are verified by `test_ui_integrity.py` (Registry sync), `test_permission_scenarios.py` (Access isolation), and the **Deep-UI Fuzzer** (`test_ui_fuzzer.py`), which uses global Bot-method interception to detect all interactive elements. All tests MUST follow the **Declarative Testing Standard [PL-HI]** using shared fixtures from `conftest.py`.

13. [CP-3.14] **Heartfelt UI**: User-facing text must be community-oriented. Avoid technical jargon like "management system", "entities", "permissions" in the interface. Use "Assistant", "Gid", "Rights".

15. [CP-3.15] **GLOBAL HANDLER UNIQUENESS**: Do not duplicate global callback handlers (such as `@router.callback_query(F.data == "close_menu")`) across multiple handler files. Place global handlers strictly in `handlers/common.py`.
    > Rationale: Duplicated handlers cause router dispatch conflicts, leading to unpredictable double-executions or arbitrary routing based on aiogram load order.

16. [CP-3.16] **ROLE ENCAPSULATION**: Never manually inject system privileges (e.g., `superadmin` checks against `config.ADMIN_ID`) within UI handlers or keyboard builders. Use the database facade (e.g. `db.get_user_roles(user_id)`) which is designed to internally resolve and append virtual roles.
    > Rationale: Hardcoding admin IDs into the UI/presentation layer violates encapsulation. If the rules for admin detection change, all UI files would require auditing, leading to hard-to-trace bugs.

17. [CP-3.17] **USER CARD CONSISTENCY**: All handlers displaying user profile details (Admin view, User view, Search results) MUST use `UIService.format_user_card` to ensure consistent visual styling and information architecture.
    > Rationale: Fragmented profile formatting leads to UI drift. Standardizing through a service method guarantees that role decorations and topic lists are always rendered identically.

18. [CP-3.18] **STRICT DATABASE FUSE**: Do not attempt to bypass or weaken the Foreign Key check in `init_db()`.
    > Rationale: Native `ON DELETE CASCADE` is critical for data integrity. Running on a system without FK support will result in orphaned records and silent database corruption.

19. [CP-3.19] **UIService.sterile_show AS SINGLE UI GATEWAY**: All menu transitions in handlers MUST use `UIService.sterile_show(state, event, text, reply_markup)`. Direct calls to `callback.message.edit_text(...)`, `message.answer(...)`, or `bot.edit_message_reply_markup(...)` are prohibited in handlers. **Dynamic Announcements**: For announcement interactions, use `edit_text` with `AnnouncementService.format_announcement_text` to refresh the participant list in real-time. **Safety Net**: The bot is initialized in `loader.py` with global `parse_mode="HTML"`, but `UIService` remains the authoritative gateway for state management.
    > Rationale: `UIService` methods are the single source of truth for UI lifecycle management. They handle `last_menu_id` tracking, cleanup, and state protection automatically. Manual Bot API calls bypass this infrastructure, leading to "dirty chat" and UI inconsistency.

20. [CP-3.20] **STATE SIGNATURE RULE**: Every handler that invokes any `UIService` method requiring `state` MUST declare `state: FSMContext` in its signature. Omitting it causes a `NameError` at runtime.
    > Rationale: aiogram's DI injects `state` only if explicitly declared. Silent failure without it crashes the handler at the first `UIService` call.

21. [CP-3.21] **MANAGEMENT SERVICE MUTATION & QUERY PROTOCOL**: All entity mutations and data queries in handlers MUST traverse a service layer. Handlers are strictly prohibited from performing input validation (e.g., regex checks, string splitting) or direct `db.*` calls of any kind.
    > Rationale: The service layer (ManagementService, PermissionService, EventService) sanitizes intent and provides proxy methods for reads. Centralizing this logic prevents code duplication and ensures that business rules are applied consistently across all UI flows.

22. [CP-3.22] **SEARCH DELEGATION RULE**: Handlers must respect the `"SEARCH_REQUIRED"` signal from `ManagementService`. When received, the handler should trigger the shared search/disambiguation logic from `handlers/common.py`.
    > Rationale: This ensures that complex search logic is shared rather than duplicated across multiple management flows.

23. [CP-3.23] **UNIFIED NAVIGATION RULE**: All standard UI returns, menu transitions, and dashboard entries SHOULD use `UIService.generic_navigator(state, event, callback_data)`. The navigator MUST implement a **Defensive Routing** protocol: before calling any keyboard builder or transition, it must verify the route exists and is valid (e.g., via callable checks or explicit key matching).
    > Rationale: Centralizing routing logic prevents "UI logic leak". Defensive checks prevent `TypeError` or `NoneType` crashes in the router if a route mapping is incomplete or misconfigured.

24. [CP-3.24] **VERIFY BEFORE AND AFTER CHANGE**: BEFORE making any code changes, view the target file and signatures. AFTER any modification to a strategic file (`.md`, `db.py`, `UIService`), it is mandatory to `view_file` the entire modified section to ensure no structural truncation or logic drift occurred.
    > Rationale: Relying on memory leads to bugs. Post-edit verification is the only way to catch "greedy match" errors that silently delete surrounding structural logic.

25. [CP-3.25] **AUTOMATED TESTING**: All modifications to core logic (Database, Services, Handlers) MUST be verified against the existing test suite using `pytest`. New features or critical bug fixes MUST include corresponding tests in the `tests/` directory.
    > Rationale: The test suite is the single source of functional truth and the only way to prevent regressions in a complex, multi-layered bot architecture.

26. [CP-3.26] **VENV ISOLATION**: All development, testing, and execution MUST occur within a virtual environment (`venv`). Commands provided to the user must assume an active environment or include activation steps.
    > Rationale: Global package installations lead to version conflicts and unpredictable behavior. Mandatory `venv` ensures environment parity between development and production.

27. [CP-3.27] **NON-BLOCKING I/O RULE**: All network operations (e.g., Google Sheets API, external webhooks) MUST be executed asynchronously and SHOULD use background tasks (`asyncio.create_task`) if they are triggered by user actions but don't require immediate UI feedback. Use **Targeted Sync** (modes like `"users"`, `"groups"`, `"events"`) to avoid unnecessary overhead. [PL-3.5]
    > Rationale: Blocking the main event loop during network latency causes the bot to "freeze" for all users. Background execution ensures a fluid user experience.

28. [CP-3.28] **STRATEGIC PLANNING (RNA-BLUEPRINT)**: For any non-trivial logical change (features, refactoring, audit), an implementation plan using the **RNA-Blueprint** format must be established.
    - [CP-3.28.1] **Header Logic**: The header must include **Base DNA** (standards), **Task RNA** (logic, risks), and **Contextual Constraints (CC)**. CC are critical principles and nuances extracted from `PROJECT_LOGIC.md` and `CONTEXT_PROMPT.md` specifically for the current task, indexed (e.g., `[CC-1]`). It must explicitly state that execution is limited to 3-5 steps, after which a status report and user approval are mandatory.
    - [CP-3.28.2] **Incremental Principle**: Do not rewrite the entire plan for every correction; update only the affected parts.
    - [CP-3.28.3] **Constraint Mapping**: Every step in the plan must be tagged with short codes (e.g., `[G-DNA]`, `[CC-x]`) referring to the header logic. Every task must be verified against the CC list for compliance.
    - [CP-3.28.4] **Native Process**: Plan updates are handled natively in chat without requiring a separate plan for the update itself.
    - [CP-3.28.5] **Execution & Reporting**: Plan execution is strictly limited to 3-5 steps per iteration. After each chunk, a status report and user approval are mandatory to proceed.
    > Rationale: Externalizing strategic reasoning before action prevents instruction drift and ensures total architectural alignment.

29. [CP-3.29] **GIT WORKFLOW [GW-1]**: All repository updates must follow the mandatory sequence: OS validation, `git status`, `git add .` (unless selective staging is explicitly requested), concise English commit message, and `git push`. **Execution occurs ONLY upon explicit user request.**
     > Rationale: Standardizing the synchronization process prevents accidental data loss, ensures clear history, and maintains environment parity across distributed workspaces.

30. [CP-3.30] **ANALYSIS & IMPROVEMENT [AI-1]**: Proactive system auditing using the Proposal Analysis engine to identify technical debt and philosophy violations. RNA plans are generated only for significant improvements.
     > Rationale: Prevents architectural decay and ensures the codebase remains lean and aligned with project-specific constraints without introducing unnecessary churn.

31. [CP-3.31] **BATCH-FETCH RULE**: Keyboard builders iterating over entity lists (users, topics, groups) MUST use batch-fetching helpers (e.g., `db.get_topic_names_by_ids`) to avoid N+1 database queries. direct `db.*` calls inside loops are strictly prohibited. [PL-HI]
    > Rationale: Minimizes I/O overhead and database lock contention, ensuring the UI remains responsive even as the number of entities grows.

32. [CP-3.32] **STRATEGIC ANCHORING**: When modifying strategic files (`🔒 Private` or `🌐 Public` prompts and technical docs), `TargetContent` MUST include the section header and at least 2 lines of surrounding context. Simplification of match targets that sacrifices structural anchors is strictly prohibited.
     > Rationale: High-fidelity anchoring prevents accidental deletion of "structural" bullet points or constraints that reside near the modification area.

33. [CP-3.33] **BY-ID PREFERENCE**: When an entity ID (user_id, topic_id, group_id) is already known as an integer, handlers MUST use `*_by_id` service methods (e.g., `ManagementService.assign_moderator_role_by_id`) instead of string-parsing equivalents.
     > Rationale: Eliminates redundant type conversions and string validation logic, reducing CPU cycles and improving code readability in high-frequency routing paths.
34. [CP-3.34] **JOURNEY TESTING ENFORCEMENT**: New features affecting cross-service logic or user-admin feedback loops (notifications) MUST be covered by journey tests in `tests/test_journeys/`. These tests must assert successful data mutation, notification delivery (checking bot call args/kwargs), and state transitions.
    > Rationale: Unit tests often miss integration bugs (e.g., incorrect argument order in a service call triggered by a handler). Journey tests verify the "thread" of logic that connects different system layers.

35. [CP-3.35] **ZERO CREATIVITY**: Architectural or logic proposals regarding bot functionality MUST NEVER be answered conversationally. They MUST trigger Route B (**PA-1** / **APA-1**). Any technical advice outside verified patterns must be flagged as "Speculative" and require an explicit audit. Implementation planning (RNA-Blueprint) MUST start only after an explicit **RNA-1** command following an approved audit.
     > Rationale: Prevents protocol drift and ensures all changes are vetted against the Optimality Standard and project constraints before a single line of plan or code is written.

36. [CP-3.36] **CONTENT ISOLATION**: All user-facing documentation, help tooltips, and long static messages MUST reside in `services/help_service.py`. Handlers MUST NOT contain hardcoded help strings. [CC-2]
    > Rationale: Ensures a clean separation of concerns, simplifies localization, and prevents code bloat in UI handlers.

37. [CP-3.37] **delete_msg AS ORPHAN TERMINATOR**: Notifications and push-messages sent via direct `bot.send_message` (outside FSM tracking) MUST be finalized using `UIService.delete_msg(callback.message)`. Using `UIService.sterile_show` for these "orphan" messages is an architectural violation.
    > Rationale: Orphan messages have no FSM `last_menu_id` entry. `sterile_show` attempts to track state, which fails for orphan messages, potentially leaving active buttons in the chat history. `delete_msg` ensures the UI is cleaned and the callback is answered without state side-effects.

38. [CP-3.38] **UI TRACE ENFORCEMENT**: When analyzing or proposing changes to UI transitions, the AI MUST perform a step-by-step trace of `last_menu_ids` state. It must explicitly identify which method (e.g., `sterile_ask`, `terminate_input`, or `sterile_show`) is responsible for deleting specific message IDs at each stage of the interaction.
    > Rationale: Prevents shallow trace errors where the AI assumes cleanup happens by "magic", which leads to logic regressions and double-deletion attempts.

39. [CP-3.39] **STRICT ID HARDENING**: All user IDs retrieved from DB or config MUST be explicitly cast to `int` before being used in `set()` operations or collection-based logic.
    > Rationale: Prevents duplication of notifications and logic bypasses caused by Python's type-sensitivity when handling potential mixed string/int data from SQLite.

40. [CP-3.40] **UNIVERSAL INDEXING PROTOCOL**: Every logic block, rule, and pattern in strategic files MUST be assigned a unique Index ID (`CP-x` for context, `PL-x` for logic). These IDs MUST be used in `implementation_plan.md` [CP-3.25] and as in-code markers to ensure 100% traceability.
    > Rationale: Indexing eliminates the need to copy full rule text into plans, saving context window while maintaining strict architectural alignment and facilitating rapid lookups.

41. [CP-3.41] **UNIVERSAL DISPATCHING**: All interactive buttons posted in broadcast messages (Announcements) MUST use the `announcements` database registry as a dispatcher. Do not link buttons directly to entity IDs (e.g. `event_join:42`). Use `ann_join:{announcement_id}` to ensure context-aware permission checks.
    > Rationale: Dispatching abstracts the interaction from the entity, allowing unified handling and strict adherence to the "Only topic members" engagement rule.

42. [CP-3.42] **QUICK ANNOUNCEMENT FORMAT**: The `/an` command MUST support the format `Title\nDescription`. The handler is responsible for creating a "Rapid Event" and cleaning up the trigger message to maintain thread sterility.
    > Rationale: Standardization of command input ensures data integrity while maintaining the "Quick" nature of operational announcements.

43. [CP-3.43] **CASCADE COMPLIANCE**: When implementing deletion of any entity (User, Topic, Event), the developer MUST verify both native DB cascades (FK) and polymorphic cleanups (e.g. removing entries from `announcements`). Failure to clean up dispatcher-based links is an architectural violation.
    > Rationale: Polymorphic links bypass native FK protection. Explicit cleanup is the only way to prevent data rot and orphaned interaction buttons in the chat history.

44. [CP-3.44] **FSM JOURNEY VALIDATION**: For any multi-step FSM scenario (Editing, Creation), the developer MUST provide or update an asynchronous journey test (e.g. `test_event_fsm.py`) to verify that the state machine doesn't hang and clears properly.
    > Rationale: FSM is the most fragile part of the UI; automated journey tests prevent "frozen" interfaces for end-users.

45. [CP-3.45] **SMART DATE PROTOCOL**: All date-related inputs MUST be processed via `DateService.parse_smart_date`. Never implement ad-hoc regex or string splitting for dates in handlers.
    > Rationale: Centralizing date parsing ensures that natural language support ("Завтра", "Сб") and normalization to ISO-8601 remain consistent across the system.

46. [CP-3.46] **PRESENTATION/DATA SEPARATION**: Strings stored in the database (e.g., `start_date`, `end_date`) MUST remain in their raw human-entered format without UI decorations like weekday suffixes (e.g., "(Пн)"). All decorations MUST be applied at the presentation layer (e.g., `EventService.format_event_card`).
    > Rationale: Prevents "data pollution" and cumulative duplication of UI elements when records are edited or displayed multiple times.

47. [CP-3.47] **ADMIN CREATION UX BRANCHING**: In workflows where an entity creation triggers an automatic audit notification (to admins), the creation handler MUST NOT immediately show the final entity card to the creator if they are an admin. Show a clean success message instead.
    > Rationale: Prevents UI clutter and notification fatigue for administrators who would otherwise receive both a state-update message and a new notification for the same action.

48. [CP-3.48] **CREATOR AUTO-JOIN**: All event creation logic (ManagementService) MUST automatically add the creator as a participant and a lead to ensure data consistency and expected user behavior. [PL-6.7]

49. [CP-3.49] **PARTICIPATION NOTIFICATIONS**: Every new participation request (Audit) or direct join (Quick Announcements) MUST trigger a notification to all global admins and the event organizer via `EventService` to ensure operational visibility. [PL-5.1.13]

50. [CP-3.50] **MOCK ASSERTION PARITY**: When asserting mock calls (e.g. `bot.send_message`), ALWAYS check both positional `args` and `kwargs`. Positional parameters in code (e.g. `send_message(chat_id, text)`) will NOT be found in `kwargs`.
    > Rationale: Prevents false-negative test failures where the call happened but the test looked in the wrong dictionary.

51. [CP-3.51] **TEST ID DYNAMISM**: Strictly PROHIBITED to use hardcoded IDs (e.g. `event_id=10`) in tests using `db_setup`. Always use the ID returned by the creation method.
    > Rationale: In isolated DBs, IDs are non-deterministic or start from 1, leading to Foreign Key violations if hardcoded.

52. [CP-3.52] **DEFAULT DENY ENFORCEMENT**: All topics MUST be closed to non-admin users by default unless explicitly configured in `direct_topic_access`. Any UI display of topic status MUST clearly state when a topic is in "Default Deny" mode. [PL-3.2.1]

53. [CP-3.53] **UI ROBUSTNESS & WEBAPP HARDENING**: 
    - [CP-3.53.1] **WebApp URL Check**: All `web_app` buttons MUST be wrapped in a conditional check for `config.WEBAPP_URL`. Do not render the button if the URL is empty or invalid. 
    - [CP-3.53.2] **Callback Parsing**: Help handlers and other colon-separated callback parsers MUST implement robust splitting to handle legacy button formats and prevent `IndexError`.
    - [CP-3.53.3] **Error Recovery**: `UIService.sterile_show` MUST catch `BUTTON_TYPE_INVALID` and fall back to sending a new message to prevent the interface from "hanging" or crashing.
    > Rationale: Prevents system-wide crashes caused by configuration errors or the presence of legacy messages in user chat history. Ensures a resilient user experience across all interaction types.

---

---

## [CP-4] DESIGN SYSTEM (Premium Minimalist)

[CP-4.1] **Core Palette**:
- **Background**: `#050505` (Deep Black).
- **Cards/Containers**: `rgba(20, 20, 20, 0.7)` (Glass Dark).
- **Borders**: `rgba(255, 255, 255, 0.08)` (Subtle White).
- **Accents**: Pure White (`#ffffff`) for primary, Dim White (`rgba(255, 255, 255, 0.6)`) for secondary.

[CP-4.2] **Typography**:
- **Font Family**: `Outfit` (Google Fonts).
- **Headings**: Bold, tight tracking (`letter-spacing: -1px`), line-height 1.1.

[CP-4.3] **Glassmorphism & Interactivity**:
- **Blur Effect**: `backdrop-filter: blur(20px)`.
- **Corner Radii**: Standard `20px` or `24px`.
- **Micro-Animations**: Scale down on active state (`0.96`), slight opacity transitions.

[CP-4.4] **Iconography & Layout**:
- **System Emojis**: 🏔 (Expedition), 📍 (Topic), 👤 (Profile), 🛡️ (Admin), 🔎 (Search).
- **Grid Layout**: Use 2-column grids for menus to maximize screen efficiency on mobile.

---

## [CP-5] SCOPE BOUNDARY

[CP-5.1] This file governs **code generation and bug-fixing only**. Tasks outside this scope (such as architectural audits, documentation maintenance, or high-level session orchestration) are handled by dedicated internal instructions — do not conflate.

---

## [CP-6] HOW TO RESPOND

- [CP-6.1] Provide production-ready code using tilde code blocks (~~~).
- [CP-6.2] If documentation updates are needed after a change, synchronize `PROJECT_LOGIC.md`, `CONTEXT_PROMPT.md`, and `README.md` accordingly.
