# AI INSTRUCTION: PROJECT CONTEXT AND CODING STANDARDS

## ROLE
You are an Expert Python Developer specializing in aiogram 3 and modular software architecture. Your goal is to assist in developing a Telegram Bot for a hiking club management system.

---

## PROJECT BRIEF
The bot manages user access to forum topics within a Telegram Supergroup and handles club administrative tasks for **«Теңир-Тоо»**.

**Implemented features:**
- **Transactional DB (WAL mode)**: High-concurrency support for SQLite, split into modular functional layers (topics, groups, roles, permissions).
- **Hybrid Access Control**: Dual-layer permission model combining global cross-topic Groups and Direct granular per-topic user access.
- **Admin Immunity**: Toggleable `IMMUNITY_FOR_ADMINS` bypasses all restrictions for superadmins.
- **Shadow Auto-Registration**: Every real user interacting with the bot is automatically registered in the database on first contact via `UserManagerMiddleware`, with a naming fallback if no Telegram name is available.
- **UIService Interface**: Automatic cleaning of menus and user commands to prevent chat clutter.
- **Stealth Moderation**: Silent deletion of unauthorized messages in restricted topics.
- **Topic Name Sync**: Topic renames in Telegram are automatically propagated to the local DB via `ForumUtilityMiddleware` (unidirectional: Telegram → DB).
- **Ghost Topic Deletion**: Manual removal of deleted Telegram topics from DB via Admin UI.
- **Callback Guarding**: `safe_callback` decorator prevents crashes on double-clicks.
- **Native Notifications**: The `@all` mention triggers a silent push notification for all authorized topic members (or all users if public) via zero-width character HTML mentions, limited to 50 users per message.

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
   > Rationale: Triple backticks conflict with the output format required by `DOCS_UPDATE_PROMPT.md`, which requires raw Markdown output without fence wrappers. A single codebase-wide convention eliminates ambiguity.

5. **GROUP FILTER**: Every middleware operating on group messages must begin with the guard: `if event.chat.type == "private": return await handler(event, data)`. The `GROUP_ID` constant must NOT be used as a middleware guard — it is reserved exclusively for Telegram API calls (e.g., `bot.edit_forum_topic`). Do not add inline admin-ID checks inside handlers — use the `IsAdmin` router-level filter instead.
   > Rationale: The `chat.type == "private"` guard ensures middleware logic executes only in group contexts across all groups. Using `GROUP_ID` as a guard would incorrectly restrict the bot to a single hardcoded group ID and contradicts the documented pattern in `PROJECT_LOGIC.md § 4`.

6. **DATABASE FACADE**: Never import directly from internal DB files (`database/topics.py`, `database/groups.py`, `database/roles.py`, `database/permissions.py`, `database/members.py`). All data calls must go through the `database.db` facade (`from database import db`).
   > Rationale: Direct imports bypass the single architectural control point, making refactors and audits unreliable. A violation here is undetectable at runtime — it only breaks when the facade interface changes.

7. **KEYBOARD FACADE**: Never import directly from `keyboards/admin_kb.py`, `keyboards/moderator_kb.py` or `keyboards/user_kb.py`. All keyboard builders must be accessed via `import keyboards as kb`.
   > Rationale: `keyboards/__init__.py` is the wildcard re-export facade for the entire keyboard layer, mirroring the role of `database/db.py`. Bypassing it breaks the established two-facade architecture and makes keyboard refactors unreliable.

8. **DESTRUCTIVE OPERATIONS**: Any **new** admin action that permanently deletes data (group, user, topic) must include a confirmation step before execution. Note: the existing `delete_group` and `delete_user` handlers are a known exception — they execute immediately without confirmation (Destructive Confirmation Gap, documented in `PROJECT_LOGIC.md § 6`). Do not replicate this pattern.
   > Rationale: Telegram bots have no undo. Without a confirmation step, a misclick produces an irrecoverable data loss. The existing gap is a tech debt, not a precedent.

9. **TOPIC RENAME SYNC**: When renaming a topic via the admin panel, the change must be applied to both the local DB (`db.update_topic_name`) **and** the Telegram API (`bot.edit_forum_topic`). DB-only updates are incomplete. API failures are non-fatal — log as warning and report status to the admin.
   > Rationale: The local DB and Telegram's topic metadata are two independent stores. A DB-only rename creates a divergence: the bot's internal name changes, but Telegram still shows the old name, causing user-visible inconsistency.

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