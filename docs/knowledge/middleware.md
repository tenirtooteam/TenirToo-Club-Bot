---
type: middleware
title: Middleware Execution Pipeline
description: The four-stage middleware pipeline behavior — registration, guards, and per-stage logic.
source_anchor: PL-4
timestamp: 2026-07-02
tags: [middleware, pipeline, fsm]
---

# Middleware Execution Logic

> Moved from `PROJECT_LOGIC.md` [PL-4] during the governance consolidation (feature 002).
> The private-chat guard pattern is a rule — see `R-ARCH-6` in [RULES.md](../../RULES.md).

Sequential 3-stage pipeline registered as `outer_middleware` on `dp.message` — the order is
fixed by design (message pipeline) plus a 4th stage on the callback pipeline.

## Stage 1 — UserManagerMiddleware

Operates on all chat types (no private-chat guard — intentional, registration is useful from
any chat context). Guard: skips processing if `event.from_user` is absent or is a bot
(`event.from_user.is_bot`). For all real users: calls
`AccessService.ensure_user_registered(event.from_user)` — auto-registers the user in the
`users` table if not present. Naming fallback hierarchy: (1) if no name at all →
`Пользователь_{user_id}`; (2) if only `last_name` present → promoted to `first_name`. Always
passes to the next handler regardless of registration outcome.

## Stage 2 — ForumUtilityMiddleware

Guard: if `event.chat.type == "private"` → passes. Branching logic for groups:
- `forum_topic_edited` event → sync new name to DB + delete service message → early return.
- `forum_topic_created` event → delete service message → early return.
- Normal message → auto-register topic → pass to next handler.

## Stage 3 — AccessGuardMiddleware

Guard: if `event.chat.type == "private"` or `event.from_user.id == event.bot.id` → passes. If
the user is a global admin and `config.IMMUNITY_FOR_ADMINS` is True, passes. For all other
messages: resolves `topic_id`, calls `PermissionService.can_user_write_in_topic`. If access is
denied → silently deletes the message and returns. All decisions are logged: denied messages
at `INFO` (❌), permitted messages at `INFO` (✅).

## Error Handling

All three message-pipeline stages follow a fail-open strategy: non-critical exceptions are
caught, logged, and the pipeline continues. The one fail-closed exception is DB initialization:
`init_db()` in `connection.py` re-raises after logging — a DB init failure halts the bot.

## Stage 4 — FsmButtonGuardMiddleware (Callback Pipeline)

Registered as outer middleware on `dp.callback_query`. Inspects callback query updates in
private chats: if an FSM state is active, checks whether the message ID matches the active
`last_menu_id`. If they do not match, it deletes the obsolete message and terminates
dispatcher propagation to protect the FSM chain from stale buttons. Whitelisted callbacks
(e.g. `landing`, `close_menu`) bypass this check.
