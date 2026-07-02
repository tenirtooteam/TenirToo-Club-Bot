---
type: constants
title: Critical Constants
description: Environment-sourced constants — types, sources, and usage.
source_anchor: PL-7
timestamp: 2026-07-02
tags: [constants, config]
---

# Critical Constants

> Moved from `PROJECT_LOGIC.md` [PL-7] during the governance consolidation (feature 002).

- **BOT_TOKEN** — `str`. Source: `.env` → `config.py` (`get_env_or_raise`). Raises
  `ValueError` on missing or empty value. Used in `loader.py` for `Bot` initialization.
- **ADMIN_ID** — `int`. Source: `.env` → `config.py` (cast via `int`). Used via
  `PermissionService.is_global_admin` to route handlers in the `IsGlobalAdmin` filter. Also
  enriched dynamically within `db.get_user_roles`.
- **GROUP_ID** — `int`. Source: `.env` → `config.py`. Used exclusively in `handlers/admin.py`
  and `handlers/moderator.py` as the `chat_id` argument for Telegram API calls. Expected to be
  a negative integer (Telegram supergroup convention). Not used as a middleware guard
  condition (`R-ARCH-6`).
- **Topic ID `-1`** — logical mapping for the "General" topic in a forum-enabled Telegram
  chat.
- **WEBAPP_HOST** — `str`. Web server binding address (default: `0.0.0.0`).
- **WEBAPP_PORT** — `int`. Web server port (default: `8000`).
- **WEBAPP_URL** — `str`. Public entry point for TMA. If empty, the system falls back to
  Callback-based UI.
- **WEBAPP_CORS_ORIGINS** — `list`. Allowed origins for WebApp requests.
- **LOG_MAX_BYTES / LOG_BACKUP_COUNT** — `int`. Rotation parameters for unified logging.
