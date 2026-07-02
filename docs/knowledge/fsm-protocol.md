---
type: fsm-protocol
title: FSM Data Keys, Sterile Interface Mechanics, Callback Resilience & Traffic Controller
description: UIService method mechanics, full inventory of FSM state keys, and descriptive behavior of the callback-resilience decorator and the unified /start entry point.
source_anchor: PL-5.1, PL-5.2, PL-5.5, PL-5.6
timestamp: 2026-07-02
tags: [fsm, ui, routing]
---

# FSM Data Keys, Sterile Interface Mechanics, Callback Resilience & Traffic Controller

> Moved from `PROJECT_LOGIC.md` [PL-5.1], [PL-5.2], [PL-5.5], [PL-5.6] during the governance
> consolidation (feature 002). The FSM hygiene rule (never `state.clear()`) and the sterile
> UI protocol gateway are rules — see `R-FSM-1`, `R-UI-*` in [RULES.md](../../RULES.md). This
> file holds the implementation mechanics of the `UIService` methods those rules reference.

## Sterile Interface Protocol — UIService Mechanics

- **`last_menu_id`**: FSM key tracking the message ID of the currently active inline keyboard
  or system message. Set via `state.update_data(last_menu_id=sent_message.message_id)`
  immediately after every menu deployment.
- **`last_menu_ids`**: FSM key holding a list (stack) of message IDs for transient alerts,
  error messages, or multi-step menus requiring bulk deletion.
- **`UIService.delete_tracked_ui`**: reads `last_menu_id` and `last_menu_ids` from FSM state,
  deletes all tracked messages, nullifies FSM data in a `finally` block (guaranteed even if
  deletion fails). The single point of physical interface destruction.
- **`UIService.terminate_input`**: atomic sequence — (1) `delete_tracked_ui`, (2) `delete_msg`
  (the user's trigger message), (3) `state.set_state(None)` if `reset_state=True`. Full cleanup
  of input traces; the reset is optional to support FSM chains (`R-FSM-2`).
- **`UIService.sterile_ask`**: the primary terminator, used before requesting text input.
  Clears the previous menu (`delete_tracked_ui`), deletes the trigger message if in a group,
  sends the prompt (e.g. "Введите название"), tracks it as `last_menu_id`, and sets FSM state.
- **`UIService.sterile_show`**: the main UI-transition gateway (`R-UI-1`). If invoked from a
  callback — edits the current message (swap). If invoked from a message handler (after user
  input) — calls `terminate_input(reset_state=False)`, removing the prompt and the user's
  message, then sends a fresh menu. Hardening: catches `BUTTON_TYPE_INVALID` and falls back to
  `answer` (a new message) if editing is impossible.
- **`UIService.generic_navigator`**: unified entry point for UI transitions (`R-UI-3`). Maps
  callback-data strings to specific show methods or keyboard builders. Supports global panels
  (Admin, Moderator, User), profile views, topic details, and Help Infrastructure (prefix
  `help:`, `help:{key}:{back_data}` format via `HelpService`). Uses the `PAGINATED_CMDS` class
  constant to determine whether a keyboard requires the `page` argument; logs unknown commands.
- **`UIService.show_admin_dashboard` / `show_moderator_dashboard`**: wrappers for main panels
  supporting optional custom feedback text while preserving layout integrity and superadmin
  visibility.
- **`UIService.sterile_command`**: decorator factory for `@router.message(Command(...))`
  handlers. The decorated handler returns `(text, reply_markup)`; the decorator delegates to
  `sterile_redirect`, handling group-to-PM redirect, error fallback, cleanup, and
  `last_menu_id` tracking automatically.
- **Quick Announcement Protocol**: `/an` in forum topics creates a "Rapid Event" (date set to
  'Оперативно') and posts a rich announcement. Shortened layout hides the date line for Rapid
  events; uses "📍 Топик" terminology. Any join/leave interaction triggers a real-time text
  update with the current participant list; the original command message is deleted.
- **TMA Bridge**: interactive personalized UI for announcements — FastAPI backend, Vanilla
  JS/CSS frontend, Glassmorphism aesthetics. Cross-layer reactivity: TMA actions trigger an
  update of the physical Telegram message via stored `chat_id`/`message_id` metadata. Includes
  mobile-native Haptic Feedback and fallback logic.
- **TMA Group Constraint**: Telegram forbids `web_app` buttons in group inline keyboards
  (raises `BUTTON_TYPE_INVALID`). Resolution: group announcements use standard buttons
  (`✅ Иду` / `🚶 Не иду`); the full Mini App Dashboard ("Личный кабинет") is centralized in
  all main dashboards (User/Admin/Moderator) in Private Messages.
- **Topic Lifecycle Synchronization**: `ForumUtilityMiddleware` intercepts
  `forum_topic_deleted` service messages and triggers
  `ManagementService.handle_external_topic_deletion`, instantly removing hand-deleted topics
  from the database and purging associated announcements to prevent `BAD_REQUEST` errors.
- **`UIService.clear_fsm_data_safely`**: clears user-defined FSM context variables while
  preserving the sterile-UI tracking keys (`last_menu_ids`, `last_menu_id`,
  `admin_onboarded`). Applied automatically in navigation routing and cancel/back flows.

## FSM Data Keys

All keys stored in FSM state across the application:

- `last_menu_id`: tracks the active inline keyboard message ID for cleanup.
- `edit_topic_id`, `edit_group_id`, `edit_user_id`: specific ID context between FSM states
  during admin rename flows.
- `disambig_query`, `disambig_action`, `disambig_context`: cross-handler user-search
  disambiguation keys. `disambig_action` values: `"dir_add"` (grant direct access), `"mod_add"`
  (assign moderator), `"admin_role_target"` (role assignment flow).
- `moderator_direct_access_topic`: set in `moderator.py` (`mod_add_user_list_` flow) to carry
  the target topic ID into the `waiting_for_direct_access_user` FSM state.
- `moderator_edit_topic_id`: set in `moderator.py` (`mod_topic_rename_` flow) to carry the
  target topic ID into the `waiting_for_topic_name` FSM state.
- `moderator_add_target_topic`: set in `moderator.py` (`mod_moderator_add_` flow) to carry the
  target topic ID into the `waiting_for_user_data` FSM state.
- `moderator_current_topic`: set in `moderator.py` (`mod_topic_select_` flow) to track the
  currently selected topic in the moderator session.
- `search_type`, `search_action`, `search_context`, `search_query`: used in
  `handlers/common.py` during global text search.

## Callback Resilience

The `safe_callback()` decorator wraps callback handlers and suppresses
`TelegramBadRequest` ("message is not modified") errors caused by rapid double-tapping.

## Unified Entry Point (Traffic Controller)

- **Unified `/start`**: the bot uses a single public entry point. Separate commands like
  `/admin` and `/mod` are deprecated for general use and kept only as hidden debug aliases.
- **Role-Based Routing**: on `/start`, the system calls `UIService.get_landing_data`, which
  resolves the appropriate dashboard (Admin, Moderator, or User) based on effective
  permissions.
- **Landing States**: Global Admin → Admin Dashboard; Moderator → Moderator Dashboard (topic
  selection); User → User Main Menu.
- **Navigation Parity**: the same landing logic fires when a user returns to the Main Menu via
  the `landing` inline callback.
