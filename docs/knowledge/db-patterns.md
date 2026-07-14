---
type: db-patterns
title: Database Integrity Fact, Upsert Pattern, Indexes & Background Sync
description: Transactional integrity mechanism, the one upsert exception, hot-path indexes, and the background Google Sheets sync pattern.
source_anchor: PL-3.1.1, PL-3.3, PL-3.4, PL-3.5
timestamp: 2026-07-02
tags: [database, patterns, sync]
---

# Database Integrity Fact, Upsert Pattern, Indexes & Background Sync

> Moved from `PROJECT_LOGIC.md` [PL-3.1.1], [PL-3.3], [PL-3.4], [PL-3.5] during the governance
> consolidation (feature 002). The FK-integrity rule and the non-blocking-I/O rule live in
> [RULES.md](../../RULES.md) (`R-DB-5`, `R-DATA-7`); this file holds the mechanism detail.

## Transactional Integrity (fact)

Native `ON DELETE CASCADE` is enforced at the database level via
`PRAGMA foreign_keys = ON;` executed on every connection open. `init_db()` performs a runtime
check at startup; if `PRAGMA foreign_keys` returns `0`, the bot throws a `RuntimeError` and
terminates immediately to prevent data corruption.

## Upsert Pattern

`update_topic_name(topic_id, name)` uses `INSERT OR REPLACE INTO topic_names` — an upsert
pattern that both inserts new topic-name records and updates existing ones atomically. This is
the only function in the codebase using this pattern; all other mutations use standard
`INSERT` or `UPDATE`.

## Indexes

- `idx_group_members_user_id ON group_members(user_id)` — hot path for template member
  lookups.
- `idx_group_topics_topic_id ON group_topics(topic_id)` — hot path for topic template lookups.

## Background Sync Pattern

To keep the bot responsive during Google Sheets network I/O, synchronization runs in owned
background tasks. **Trigger**: any data mutation in `ManagementService` — user/topic name
updates, deletions, template mutations, participation changes. **Mechanism**:
`_trigger_sheets_sync(mode, entity_id)` (signature unchanged across ~77 call-sites) computes a
per-type sync key (`mode`, or `event_participants:{entity_id}`) and schedules an owned
`asyncio.Task` held in the module-level `_pending_syncs` registry — never a bare
fire-and-forget `create_task`. **Debounce/coalescing**: each task waits
`SHEETS_SYNC_DEBOUNCE_SECONDS` before exporting; a new trigger for the same key cancels the
prior pending task, so a burst of edits collapses into a single export reading fresh DB state
at export time. **Ownership**: the task reference is retained for the whole lifecycle and
removed via `add_done_callback` (no GC race, no lost errors — resolves the historical
"Task was destroyed" warnings). **Roles fetch**: user export uses the batched
`db.get_roles_for_users(user_ids)` (one query) instead of an N+1 per-user loop. **Shutdown**:
`ManagementService.flush_pending_syncs()` is registered as a `dp.shutdown` hook and runs all
pending exports immediately so the last coalesced change is not lost on stop. **Error
Handling**: failures inside the task are logged and never interrupt the main flow. Making the
in-task `db.*` calls non-blocking (`to_thread`) is intentionally out of scope, gated behind
profiling like the feature-008 DB work.
