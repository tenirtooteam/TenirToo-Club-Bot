---
type: feature-detail
title: Implemented Features — Full Overview
description: Full descriptive list of shipped bot features; CONTEXT_PROMPT.md keeps only the one-line index.
source_anchor: CP-2
timestamp: 2026-07-02
tags: [features, overview]
---

# Implemented Features — Full Overview

> Descriptive companion to the one-line feature index that now lives in the redirect index
> (formerly `CONTEXT_PROMPT.md` § CP-2). Moved during the governance consolidation
> (feature 002). Bot brief: the bot manages user access to forum topics within a Telegram
> Supergroup and handles club administrative tasks for «Теңир-Тоо».

- **Transactional DB (WAL mode)**: high-concurrency support for SQLite, split into modular
  functional layers (topics, groups, roles, permissions).
- **Static Core Roles**: built-in static roles (`superadmin`, `admin`, `moderator`);
  `superadmin` is virtually mapped directly in the DB response for the configured creator.
- **Template-Based Access Control**: access governed exclusively by granular per-topic user
  grants (`direct_topic_access`); global groups serve as non-runtime templates for bulk
  assignment and synchronization.
- **Admin Immunity**: toggleable `IMMUNITY_FOR_ADMINS` bypasses all restrictions for
  superadmins.
- **Shadow Auto-Registration**: every real user is automatically registered on first contact
  via `UserManagerMiddleware` delegating to `ManagementService.ensure_user_registered`.
- **Sterile UI & Multi-Message Stack**: zero "dirty chat" via stack-based message cleanup
  (`last_menu_ids`); tracks and deletes multiple system alerts/menus in a single transition.
- **Help Infrastructure**: centralized help tooltips via `HelpService` and unified routing via
  `generic_navigator` (`help:{key}` pattern); handlers are decoupled from static content.
- **Batch-Fetching**: optimized N+1 query elimination for list building using batch-fetch
  helpers.
- **Stealth Moderation**: silent deletion of unauthorized messages in restricted topics.
- **Topic Name Sync**: Telegram topic renames automatically propagate to the local DB via
  `ForumUtilityMiddleware` (unidirectional: Telegram → DB).
- **Ghost Topic Deletion**: manual removal of deleted Telegram topics from DB via Admin UI.
- **Callback Guarding**: `safe_callback` decorator prevents crashes on double-clicks.
- **Native Notifications**: the `@all` mention triggers a silent push notification for all
  authorized topic members.
- **Private Help Command**: `/help` logic is offloaded to private messages to keep group chats
  clean, with fallback notifications if PMs are blocked.
- **Roles Dashboard**: a dedicated informational hub (`roles_dashboard`) providing a Role FAQ
  and a global view of all assigned responsibilities.
- **Unified Search Interface**: a hybrid selection model for list-based menus; a
  `🔎 Поиск` button auto-injects for lists over 7 items via `build_paginated_menu`. Search is
  handled by `SearchStates` FSM and a unified router in `handlers/common.py`; disambiguation
  is fully automated via the `"SEARCH_REQUIRED"` protocol.
- **Performance Optimization**: zero N+1 queries in the UI layer via batch-fetching helpers.
- **ManagementService Layer**: single authoritative layer for entity mutations and
  registration logic, enforcing a strict `(bool, str)` contract and a Search-Or-Action
  protocol; supports template-based operations and flexible name parsing (spaces,
  patronymics).
- **Declarative Testing Infrastructure**: full coverage for Database, Service, and Handler
  layers using `pytest` with a unified fixture-based architecture; isolated temporary
  databases per run, Registry Integrity Scanners, and FSM Journey Validation.
- **Sterile Handler Architecture**: handlers 100% decoupled from the database facade; all data
  interaction mediated by the appropriate service layer.
- **Expedition Protocol (Events)**: complete lifecycle for club events — Quick Announcements
  (`/an`) with a shortened layout (hiding date for Rapid events) and "📍 Топик" terminology;
  admin moderation queue, participant tracking, lead assignment.
- **Audit & Notification Layer**: asynchronous approval workflow for critical actions;
  targeted participation alerts sent only to event leads and creator, eliminating noise for
  global admins. Statuses: `pending`, `approved`, `rejected`. Resolution is an atomic
  compare-and-swap (`resolve_audit_request` flips `pending` only), so concurrent admin
  approvals are idempotent — exactly one side effect and one notification.
- **Armored DB Integrity Fuse**: mandatory runtime SQLite Foreign Key check at startup;
  schema hardening via native `ON DELETE CASCADE` on all table linkages including
  `audit_requests` and `event_leads`; optimized search indices on `user_id`.
- **Unified Role-Based Landing**: single public entry point (`/start`) with "Traffic
  Controller" logic in `UIService.get_landing_data`; supports a `role_override` parameter for
  debug aliases (`/admin`, `/mod`).
- **Automated Reporting (Sheets)**: background synchronization of club data to Google Sheets —
  Master User List, Group Templates, Expedition Export; targeted sync triggers only the
  specific sheets needed for deletions/updates.
- **Topic Lifecycle Synchronization**: automated parity with the Telegram Forum; middleware
  intercepts `forum_topic_deleted` events to purge orphaned data (announcements, perms, group
  links), preventing `BAD_REQUEST` API errors.
- **Telegram Mini Apps (TMA) Integration**: secure, personalized Web UI as a full-featured
  «Personal Cabinet»; real-time UI reactivity refreshes physical Telegram announcements when
  actions occur in the TMA (e.g. joining an event).
- **Unified Configuration & Logging**: centralized constants in `config.py`; unified
  rotation-based logging (`logs/bot.log`) for both Bot and WebApp layers with global exception
  handling.
- **Error Interceptor Layer**: global dispatcher exception router logging errors and
  notifying users without thread blocking.
- **AST Import Linter**: static code validation enforcing architectural boundaries,
  prohibiting DB imports in handlers.
- **UserSessionSimulator**: declarative zero-token in-memory UI simulator for E2E journey
  testing with automatic markup, anti-spam, and footer assertions.
- **Type Hardening (DTOs)**: Event and Audit entities strictly typed using dataclass DTO
  containers (`EventDTO`, `AuditRequestDTO`) with a fallback dict interface.
- **Security Fallback Handler**: a global fallback handler catches unhandled callback queries
  and displays a warning alert, preventing infinite button loading for unauthorized users.
- **FSM Data Hygiene & Resets**: strict FSM data sanitization via
  `UIService.clear_fsm_data_safely`, executed during all main navigation transitions to purge
  user-defined context keys.
- **Artifact Prompt Linter**: CLI validator ensuring structure and language standards for
  implementation plans (English), task checklists (completion status), and walkthrough
  reports (Russian).
