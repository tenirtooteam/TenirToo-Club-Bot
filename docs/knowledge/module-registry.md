---
type: module-registry
title: Module Registry — File Responsibilities & Function Inventory
description: Complete file list with individual responsibilities and full function inventory.
source_anchor: PL-2.2
timestamp: 2026-07-02
tags: [architecture, modules, inventory]
---

# Module Registry

> Moved from `PROJECT_LOGIC.md` [PL-2.2] during the two-tier documentation migration.
> The imperative testing rule [PL-2.2.50] (Declarative Testing Standard) stays in
> `PROJECT_LOGIC.md` because it is a normative rule, not descriptive reference data.

Complete file list with individual responsibilities and full function inventory:

- [PL-2.2.1] **main.py** — Entry point: `setup_logging`, DB initialization, router registration, outer middleware chaining, and concurrent execution of WebApp (uvicorn) and Bot polling via `asyncio.gather`. [CC-3]

- [PL-2.2.2] **loader.py** — Initializes `Bot` and `Dispatcher` with `MemoryStorage`.
- [PL-2.2.3] **config.py** — Environment variable loader and global constants definition. Centralizes all magic numbers, logging parameters, and WebApp configurations.
- [PL-2.2.4] **database/__init__.py** — Package initializer for DB facade pattern.
- [PL-2.2.5] **database/connection.py** — Connection context manager, WAL activation, and Foreign Key enforcement.
- [PL-2.2.6] **database/audit.py** — Audit requests management: `create_audit_request`, `get_audit_request`, `resolve_audit_request`, `get_pending_requests_by_type`, `get_user_pending_request`, `delete_audit_request`.
- [PL-2.2.7] **database/members.py** — User entity management: `add_user`, `user_exists`, `get_all_users`, `get_user_name`, `get_user_names_by_ids` (Batch-Fetch, N+1 fix), `update_user_name`, `delete_user`, `find_users_by_query`.
- [PL-2.2.8] **database/topics.py** — Forum topic management: `add_topic`, `rename_topic`, `get_topic_name`, `get_all_unique_topics`, `get_topic_names_by_ids` (Batch-Fetch), `delete_topic`.
- [PL-2.2.9] **database/groups.py** — Global templates management: `create_group`, `delete_group`, `get_all_groups`, `get_group_name`, `add_topic_to_group`, `remove_topic_from_group`, `get_topics_of_group`, `get_group_ids_by_topic`, `get_group_template_members`, `add_to_group_template`, `remove_from_group_template`.
- [PL-2.2.10] **database/roles.py** — Roles definitions and scoping: `get_role_id`, `grant_role`, `revoke_role`, `get_user_roles`, `get_roles_for_users` (batched, N+1-free), `get_moderators_of_topic`, `is_global_admin`, `is_moderator_of_topic`, `get_all_roles`, `get_role_name_by_id`, `get_global_admin_ids`.
- [PL-2.2.11] **database/permissions.py** — Direct access management: `grant_direct_access`, `grant_direct_access_bulk`, `revoke_direct_access`, `revoke_all_direct_access`, `get_direct_access_users`, `can_write`, `get_topic_authorized_users`, `get_user_available_topics`, `get_direct_access_user_ids`, `get_topic_authorized_user_ids`.
- [PL-2.2.12] **database/events.py** — Expedition management: `create_event`, `update_event_details`, `approve_event`, `set_event_sheet_url`, `delete_event`, `add_event_lead`, `add_event_participant`, `remove_event_participant`, `is_event_participant`, `get_event_details`, `get_active_events`, `get_pending_events`. (Supports ISO-8601 storage with contract validation).
- [PL-2.2.13] **database/announcements.py** — Announcement dispatcher management: `create_announcement`, `get_announcement`, `get_announcements_by_target`, `update_announcement_metadata`, `delete_announcements_by_target`, `delete_announcements_by_topic`.
- [PL-2.2.14] **database/db.py** — Single facade re-exporting all database functions (including announcements.py). **The only permitted import point for data operations.**
- [PL-2.2.14.1] **database/dtos.py** — Domain data containers (EventDTO, AuditRequestDTO) with dict-like compatibility interface.
- [PL-2.2.15] **services/ui_service.py** — Централизованный UI lifecycle via `UIService`: `delete_tracked_ui`, `delete_msg`, `terminate_input`, `clear_fsm_data_safely`, `sterile_redirect`, `sterile_show`, `generic_navigator`, `get_landing_data(user_id, role_override)` (Traffic Controller), `show_admin_dashboard`, `show_moderator_dashboard`, `sterile_ask`, `show_temp_message`, `show_user_detail`, `show_group_detail`, `show_topic_detail`, `show_moderator_groups`, `show_moderator_moderators`, `sterile_command`, `get_confirmation_ui`, `format_user_card`.
- [PL-2.2.16] **services/event_service.py** — Expedition business logic: `format_event_card`, `notify_admins_for_approval`, `can_edit_event`, `get_active_events`, `get_pending_events`, `get_event_details`, `is_event_participant`.
- [PL-2.2.17] **services/google_sheets_service.py** — Asynchronous Google Sheets API integration via `GoogleSheetsService`. Methods: `export_users`, `export_groups`, `export_events`, `export_event_participants`, `import_users`, `import_groups`.
- [PL-2.2.18] **services/help_service.py** — Centralized help content registry and tooltip logic via `HelpService`. Methods: `get_help`.
- [PL-2.2.19] **services/management_service.py** — Domain Service for entity management. All methods return `(bool, str)`. Functions: `ensure_user_registered`, `add_user`, `create_group`, `assign_moderator_role`, `grant_direct_access`, `toggle_user_group_template`, `apply_group_to_topic`, `sync_group_to_topic`, `copy_topic_to_topic`, `grant_role`, `execute_deletion`, `update_user_name`, `update_topic_name`, `register_topic_if_not_exists`, `create_event_action` (Internal Sanitization [PL-6.7]), `toggle_event_participation`, `leave_event_action` (remove-only, no audit bypass), `add_event_participation_action`, `remove_event_participation_action`, `approve_event_action`, `submit_request`, `resolve_request` (Atomic Audit, idempotent CAS gate), `get_pending_request_id`, `get_user_pending_request_id`, `cancel_participation_request_action`, `get_entity_name`, `search_entities`, `_trigger_sheets_sync`.
- [PL-2.2.20] **services/permission_service.py** — Unified Authorization Service: `is_superadmin`, `is_global_admin`, `is_moderator_of_topic`, `can_manage_topic`, `can_manage_user_roles`, `get_manageable_topics`, `can_user_write_in_topic`, `get_user_display_name`, `get_role_name`, `get_role_id`, `get_access_sets`.
- [PL-2.2.21] **services/notification_service.py** — Notification logic: `send_native_all`, `send_to_users` (Targeted Broadcast).
- [PL-2.2.22] **services/announcement_service.py** — Announcement lifecycle logic: `format_announcement_text`, `create_quick_event`, `broadcast_event_announcement`, `refresh_announcements` (Real-time TMA sync).
- [PL-2.2.23] **services/callback_guard.py** — `safe_callback()` decorator factory.
- [PL-2.2.24] **handlers/common.py** — Shared logic & search. Functions: `cmd_help`, `close_menu_handler`, `roles_dashboard_menu`, `roles_faq_view`, `list_users_with_roles`, `search_start_handler`, `search_query_handler`, `search_results_pagination`, `search_pick_handler`, `perform_search_pick`, `confirm_execution`, `universal_help_handler` (Robust Parsing [G-DNA]), `show_help_view`. **Decoupled**: Uses `ManagementService.search_entities`.
- [PL-2.2.25] **handlers/admin.py** — Superadmin flows. FSM: `waiting_for_group_name`, `waiting_for_topic_name`, `waiting_for_user_data`, `waiting_for_new_name`.
- [PL-2.2.26] **handlers/moderator.py** — Moderator flows. FSM: `waiting_for_topic_name`, `waiting_for_user_data`, `waiting_for_direct_access_user`.
- [PL-2.2.27] **handlers/events.py** — Expedition flows (Events). FSM: `waiting_for_title`, `waiting_for_dates`, `confirm_date`, `waiting_for_end_date`. Functions: `show_events_list`, `show_pending_events`, `start_event_creation`, `process_event_title`, `process_event_dates`, `process_date_preset`, `process_date_retry`, `process_date_confirm`, `process_date_add_end_start`, `process_event_end_date`, `view_event`, `join_event`, `cancel_join_handler`, `leave_event`, `delete_event_init`, `approve_event_handler`, `reject_event_handler`, `show_event_card`.
- [PL-2.2.28] **handlers/user.py** — User flows: Unified `/start` (Traffic Controller), profile, topics.
- [PL-2.2.28.1] **handlers/errors.py** — Global dispatcher exception handler catching and logging all unexpected errors.
- [PL-2.2.27] **middlewares/access_check.py** — Sequential chain: `UserManagerMiddleware` → `ForumUtilityMiddleware` → `AccessGuardMiddleware`.
- [PL-2.2.27.1] **middlewares/fsm_button_guard.py** — Callback query protection middleware checking message ID consistency during active FSM states.
- [PL-2.2.28] **keyboards/admin_kb.py** — Admin keyboards: `main_admin_kb`, `get_admin_cancel_kb`, `all_topics_kb`, `group_topics_list_kb`, `available_topics_kb`, `groups_list_kb`, `group_edit_kb`, `template_action_topic_select_kb`, `users_list_kb`, `user_edit_kb`, `user_groups_edit_kb`, `roles_dashboard_kb`, `role_selection_kb`, `user_roles_manage_kb`, `topic_selection_for_role_kb`, `back_to_roles_dashboard_kb`, `search_results_kb`, `confirmation_kb`, `simple_back_kb`.
- [PL-2.2.29] **keyboards/moderator_kb.py** — Moderator keyboards: `get_mod_cancel_kb`, `moderator_topics_list_kb`, `moderator_topic_menu_kb`, `topic_moderators_kb`, `moderator_search_kb`, `moderator_topic_groups_kb`, `moderator_unattached_groups_kb`.
- [PL-2.2.30] **keyboards/announcements_kb.py** — Announcement interaction buttons: `get_announcement_kb`.
- [PL-2.2.31] **keyboards/event_kb.py** — Expedition keyboards: `get_events_list_kb`, `get_event_card_kb`, `get_event_moderation_kb`, `get_event_cancel_kb`, `get_date_picker_kb`, `get_date_confirm_kb`, `get_audit_log_kb`.
- [PL-2.2.32] **keyboards/user_kb.py** — User keyboards: `user_main_kb`, `user_topics_list_kb`, `user_profile_kb`, `user_topic_detail_kb`.
- [PL-2.2.33] **keyboards/pagination_util.py** — Universal keyboard utilities: `build_paginated_menu`, `add_nav_footer`.
- [PL-2.2.34] **handlers/announcements.py** — Announcement flows: `cmd_quick_announcement`, `announcement_join_handler`, `event_announce_init_handler`.
- [PL-2.2.35] **local_scripts/dev_run.py** — Developer-only hot-reload runner.
- [PL-2.2.36] **local_scripts/Gemini_maker.py** — Developer-only AI context packager.
- [PL-2.2.36.1] **local_scripts/prompt_linter.py** — Developer-only artifact quality control linter (plan, checklist, report).
- [PL-2.2.37] **tests/conftest.py** — Global test infrastructure: isolated DB (`db_setup`), mock bot, and context factories (`create_context`, `create_callback`). [PL-HI]
- [PL-2.2.38] **tests/test_database/test_event_contracts.py** — Contract tests ensuring DB-to-Dict mapping consistency.
- [PL-2.2.40] **tests/test_database/test_integrity_suite.py** — Integrity tests for DB relations (FK Cascade and manual cleanup).
- [PL-2.2.41] **tests/test_handlers/test_event_edit_collision.py** — Regression suite for FSM bypass and collision prevention.
- [PL-2.2.42] **tests/test_handlers/test_permission_scenarios.py** — Declarative security boundary tests (Admin/Moderator).
- [PL-2.2.43] **tests/test_handlers/test_admin_flow.py** — Integration tests for Admin CRUD operations (Groups/Topics).
- [PL-2.2.44] **tests/test_handlers/test_announcement_logic.py** — Logic tests for quick announcements and dispatching.
- [PL-2.2.44.1] **tests/test_handlers/test_ux_audited_flows.py** — UX audit verification tests: pending event access control, cancel join request.
- [PL-2.2.45] **tests/test_journeys/test_default_deny_journey.py** — Verification of "Closed by Default" logic, including admin immunity bypass.
- [PL-2.2.46] **tests/test_services/test_date_logic.py** — Deep unit tests for DateService parsing edge cases.
- [PL-2.2.46] **tests/test_services/test_sheets_sync.py** — Resilience tests for Google Sheets API error handling.
- [PL-2.2.47] **tests/test_services/test_ui_fuzzer.py** — Autonomous Deep-UI Fuzzer for recursive menu exploration.
- [PL-2.2.48] **tests/test_services/test_ui_integrity.py** — UI Integrity and Hardening tests: callback length, WebApp URL safety, HelpService coverage.
- [PL-2.2.48.1] **tests/test_services/test_import_lint.py** — Dev-only integration test executing `import-linter` as a subprocess to enforce layer boundaries (skips gracefully if not installed in production).
- [PL-2.2.48.2] **tests/test_prompt_linter.py** — Unit tests for the developer prompt linter.
- [PL-2.2.48.3] **tests/test_journeys/test_prompt_linter_journey.py** — Journey/integration tests verifying CLI execution of the prompt linter.
- [PL-2.2.49] **obsolete_tests/** — Directory containing legacy and broken tests moved for reference during the 'Total Shield' transition.
- [PL-2.2.51] **web/auth.py** — Security layer: `validate_webapp_init_data` (HMAC-SHA256 validation), `get_current_user_id` (FastAPI dependency for user auth). [CC-3]
- [PL-2.2.52] **web/main.py** — FastAPI application: Unified logging, router inclusion (`announcements`, `dashboard`).
- [PL-2.2.53] **web/routers/announcements.py** — Web API for announcements: `get_announcement_details`, `toggle_participation`. [CC-1]
- [PL-2.2.54] **web/routers/dashboard.py** — Web API for personal cabinet: `get_dashboard_init`, `get_user_topics`, `get_user_profile`, `get_all_events`, `get_event_view`, `toggle_event_participation_direct`, `get_all_topics_admin`, `get_all_groups_admin`, `get_roles_faq`.
- [PL-2.2.55] **web/frontend/** — Static assets for Mini App: `index.html` (Multi-view Dashboard), `style.css` (Premium Grid/Glassmorphism), `app.js` (Navigation, API Bridge, Admin Views).
- [PL-2.2.56] **tests/test_web/test_auth.py** — Unit tests for Web Bridge authentication (HMAC-SHA256).
- [PL-2.2.57] **tests/test_journeys/test_tma_integration.py** — Journey test for WebApp-to-Bot reactivity.
- [PL-2.2.57.1] **tests/test_journeys/test_event_creation_tdd.py** — E2E event creation journey test validating UI lifecycle via simulator.
- [PL-2.2.57.2] **tests/test_journeys/test_ux_journeys.py** — TDD journey tests validating onboarding FAQ, PM deny alerts, soft close stubs, and FSM button guards.
- [PL-2.2.57.3] **tests/test_journeys/test_start_routing_journey.py** — Journey tests for /start Traffic Controller role-based landing and overrides.
- [PL-2.2.57.4] **tests/test_journeys/test_event_lifecycle_journey.py** — Journey tests for event rejection, deletion, leave, and participant audit resolution.
- [PL-2.2.57.5] **tests/test_journeys/test_admin_crud_journey.py** — Journey tests for admin user management (CRUD) and templates sync.
- [PL-2.2.57.6] **tests/test_journeys/test_moderator_flows_journey.py** — Journey tests for moderator scoped topic management, templates linking, and access toggles.
- [PL-2.2.57.7] **tests/test_journeys/test_middleware_pipeline_journey.py** — Journey tests for UserManager, ForumUtility, AccessGuard, and FsmButtonGuard middlewares.
- [PL-2.2.57.8] **tests/test_journeys/test_tma_bridge_journey.py** — Journey tests for TMA dashboard init and toggle reactivity with Telegram.
- [PL-2.2.57.9] **tests/test_journeys/test_ux_fallback_journey.py** — Journey tests for FSM creation Escape Hatch, fallback callback handlers, and safe_callback.
- [PL-2.2.57.10] **tests/test_journeys/test_ux_refinement_journey.py** — Journey tests for onboarding loop prevention, escape hatches, search back navigation, moderator redirects, and terminology alignment.
- [PL-2.2.58] **tests/test_web/** — Directory for Web Bridge layer tests.
