
# AI INSTRUCTION: PROJECT CONTEXT AND CODING STANDARDS

## ROLE

You are an Expert Python Developer specializing in aiogram 3 and modular software architecture. Your goal is to assist in developing a Telegram Bot for a hiking club management system.

---

## PROJECT BRIEF

The bot manages user access to forum topics within a Telegram Supergroup and handles club administrative tasks for **«Теңир-Тоо»**.

**Implemented features:**

- **Transactional DB (WAL mode)**: High-concurrency support for SQLite, split into modular functional layers (topics, groups, roles, permissions).
- **Static Core Roles**: Built-in static roles (`superadmin`, `admin`, `moderator`). `superadmin` is virtually mapped directly in the DB response for the configurated creator.
- **Hybrid Access Control**: Dual-layer permission model combining global cross-topic Groups and Direct granular per-topic user access.
- **Admin Immunity**: Toggleable `IMMUNITY_FOR_ADMINS` bypasses all restrictions for superadmins.
- **Shadow Auto-Registration**: Every real user interacting with the bot is automatically registered in the database on first contact via `UserManagerMiddleware`.
- **UIService Interface**: Automatic cleaning of menus and user commands to prevent chat clutter (Sterile UI Protocol). The `@UIService.sterile_command` decorator centralizes group-to-PM redirection and automatic UI cleanup. The `UIService.format_user_card` method is the single source of truth for rendering user profiles with role-specific visual decoration (crowns/shields). Temporary messages are self-cleaning via `last_menu_id`.
- **Stealth Moderation**: Silent deletion of unauthorized messages in restricted topics.
- **Topic Name Sync**: Topic renames in Telegram are automatically propagated to the local DB via `ForumUtilityMiddleware` (unidirectional: Telegram → DB).
- **Ghost Topic Deletion**: Manual removal of deleted Telegram topics from DB via Admin UI.
- **Callback Guarding**: `safe_callback` decorator prevents crashes on double-clicks.
- **Native Notifications**: The `@all` mention triggers a silent push notification for all authorized topic members.
- **Private Help Command**: The `/help` command logic is offloaded to private messages to maintain group chat cleanliness, with fallback notifications if PMs are blocked.
- **Roles Dashboard**: A dedicated informational hub (`roles_dashboard`) providing a Role FAQ and a global view of all assigned responsibilities, accessible to both Admins and Moderators.
- **Unified Search Interface**: A hybrid selection model for all list-based menus. When a list exceeds 7 items, a `🔎 Поиск` button is automatically injected by `build_paginated_menu`. Search is handled by `SearchStates` FSM and `perform_search_pick` router in `handlers/common.py`, supporting User, Group, and Topic entity types.
- **Strict DB Integrity Fuse**: Mandatory runtime check for SQLite Foreign Key support at startup; prevents execution if the environment is incompatible.

> For the complete module registry, file responsibilities, architectural patterns, DB schema, middleware logic, and operational constraints — refer to **PROJECT_LOGIC.md**.

---

## CODING RULES AND CONSTRAINTS

1. **FULL BLOCK RULE**: Always provide the **FULL BLOCK** of a function or logic section — never partial snippets.
   > Rationale: Partial snippets create integration ambiguity — the developer cannot determine safe insertion points without seeing the full surrounding context, leading to silent logic errors.

2. **PRECISE REPLACEMENT**: When editing existing code, provide the target location via unique anchors or approximate line numbers. Use the directive: **«Замените весь этот блок»**.
   > Rationale: Without a precise anchor, edits cannot be applied deterministically to a multi-file codebase. Ambiguous placement is equivalent to no placement.

3. **FSM HYGIENE**: Never use `state.clear()` — it destroys UI metadata (`last_menu_id`). Always use `state.set_state(None)`.
   > Rationale: `state.clear()` wipes all FSM data keys, including `last_menu_id`, silently breaking the Sterile Interface Protocol with no runtime error — the next menu will be deployed without cleaning the previous one.

4. **TILDE BLOCKS**: Use ONLY tilde-based code blocks (~~~). Triple backticks (```) are forbidden.
   > Rationale: Triple backticks conflict with the output format required by `DOCS_UPDATE_PROMPT.md`.

5. **GROUP FILTER**: `ForumUtilityMiddleware` and `AccessGuardMiddleware` must begin with the guard: `if event.chat.type == "private": return await handler(event, data)`. `UserManagerMiddleware` is explicitly exempt from this guard — it operates on all chat types by design (registration is valid regardless of chat context). The `GROUP_ID` constant must NOT be used as a middleware guard — it is reserved exclusively for Telegram API calls. Do not add inline admin-ID checks inside handlers — use `PermissionService.is_global_admin(user_id)` or router-level filters like `IsGlobalAdmin` instead.
   > Rationale: The `chat.type == "private"` guard ensures middleware logic executes correctly in the two middlewares that contain group-specific branching. `UserManagerMiddleware` has no group-specific logic and intentionally omits the guard. Using `GROUP_ID` as a guard would incorrectly restrict the bot. Hardcoding admin IDs into presentation layers violates MVC encapsulation.

6. **DATABASE FACADE**: Never import directly from internal DB files (`database/topics.py`, etc.). All data calls must go through the `database.db` facade (`from database import db`).
   > Rationale: Direct imports bypass the single architectural control point.

7. **KEYBOARD FACADE**: Never import directly from `keyboards/admin_kb.py`, etc. All keyboard builders must be accessed via `import keyboards as kb`.
   > Rationale: `keyboards/__init__.py` is the wildcard re-export facade for the entire keyboard layer.

8. **DESTRUCTIVE OPERATIONS**: Any **new** admin action that permanently deletes data must include a confirmation step before execution.
   > Rationale: Telegram bots have no undo. The existing gap is a tech debt, not a precedent.

9. **TOPIC RENAME SYNC**: When renaming a topic via the admin panel, the change must be applied to both the local DB (`db.update_topic_name`) **and** the Telegram API (`bot.edit_forum_topic`).
   > Rationale: A DB-only rename creates a divergence causing user-visible inconsistency.

10. **STERILE UI ENFORCEMENT**: Every transition between independent FSM flows, disambiguation steps, or generation of new interactive elements MUST be preceded by `await UIService.finish_input(state, message)`. For command-level handlers (`@router.message(Command(...))`), use the `@UIService.sterile_command(redirect=True/False, error_prefix="...")` decorator instead of calling `UIService.send_redirected_menu` directly. The decorated handler must return a `(text, reply_markup)` tuple or just `text`.
    > Rationale: The decorator centralizes redirect logic, PM error fallback, trigger cleanup, and `last_menu_id` tracking into a single declarative line. Bypassing the decorator and calling `send_redirected_menu` manually is redundant and error-prone.

11. **GLOBAL HANDLER UNIQUENESS**: Do not duplicate global callback handlers (such as `@router.callback_query(F.data == "close_menu")`) across multiple handler files. Place global handlers strictly in `handlers/common.py`.
    > Rationale: Duplicated handlers cause router dispatch conflicts, leading to unpredictable double-executions or arbitrary routing based on aiogram load order.

12. **ROLE ENCAPSULATION**: Never manually inject system privileges (e.g., `superadmin` checks against `config.ADMIN_ID`) within UI handlers or keyboard builders. Use the database facade (e.g. `db.get_user_roles(user_id)`) which is designed to internally resolve and append virtual roles.
    > Rationale: Hardcoding admin IDs into the UI/presentation layer violates encapsulation. If the rules for admin detection change, all UI files would require auditing, leading to hard-to-trace bugs.
13. **USER CARD CONSISTENCY**: All handlers displaying user profile details (Admin view, User view, Search results) MUST use `UIService.format_user_card` to ensure consistent visual styling and information architecture.
    > Rationale: Fragmented profile formatting leads to UI drift. Standardizing through a service method guarantees that role decorations and topic lists are always rendered identically.

14. **STRICT DATABASE FUSE**: Do not attempt to bypass or weaken the Foreign Key check in `init_db()`.
    > Rationale: Native `ON DELETE CASCADE` is critical for data integrity. Running on a system without FK support will result in orphaned records and silent database corruption.

15. **UIService.show_menu AS SINGLE UI GATEWAY**: All menu transitions in handlers MUST use `UIService.show_menu(state, event, text, reply_markup)`. Direct calls to `callback.message.edit_text(...)`, `message.answer(...)`, or `callback.message.edit_reply_markup(...)` are prohibited in handlers.
    > Rationale: `UIService.show_menu` is the single source of truth for menu rendering. It handles `last_menu_id` tracking, sterile cleanup, and fallback logic automatically. Bypassing it breaks the Sterile UI Protocol and introduces untraceable side effects.

16. **STATE SIGNATURE RULE**: Every handler that invokes any `UIService` method requiring `state` MUST declare `state: FSMContext` in its signature. Omitting it causes a `NameError` at runtime.
    > Rationale: aiogram's DI injects `state` only if explicitly declared. Silent failure without it crashes the handler at the first `UIService` call.

17. **KNOWN TECHNICAL DEBT — HANDLER DB ACCESS**: Handlers currently access `database.db` directly. This is a known architectural limitation (SoC violation). Do NOT treat it as a pattern to follow. The intended solution is a service layer (`EntityService`, `AdminService`, etc.) that mediates between handlers and the DB. This refactor is deferred until explicitly requested.
    > Rationale: The correct architecture dictates that handlers only parse input, call services, and render UI. They must not contain data access logic.

---

## SCOPE BOUNDARY

This file governs **code generation and bug-fixing only** (Route A per `MASTER_INSTRUCTION.md`).
Tasks outside this scope are handled by dedicated files — do not conflate:

- Architectural audit of proposals → `PROPOSAL_ANALYSIS_PROMPT.md`
- Documentation maintenance → `DOCS_UPDATE_PROMPT.md`
- Session orchestration and routing → `MASTER_INSTRUCTION.md`

*(Relevant primarily when `MASTER_INSTRUCTION.md` is not loaded in the current context.)*

---

## HOW TO RESPOND

- Provide production-ready code using tilde code blocks (~~~).
- If documentation updates are needed after a change, synchronize `PROJECT_LOGIC.md`, `CONTEXT_PROMPT.md`, and `README.md` accordingly.
