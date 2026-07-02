---
type: architecture
title: Project Identity, Stack & Layered Architecture
description: Stack facts, the five-layer decomposition, import graph, and connection-manager behavior.
source_anchor: PL-1, PL-2.1, PL-2.3, PL-2.6
timestamp: 2026-07-02
tags: [architecture, stack, layers]
---

# Project Identity, Stack & Layered Architecture

> Moved from `PROJECT_LOGIC.md` [PL-1], [PL-2.1], [PL-2.3], [PL-2.6] during the governance
> consolidation (feature 002). Imperative content from these sections lives in
> [RULES.md](../../RULES.md) (see `R-ARCH-*`, `R-PROC-7`); this file holds the descriptive
> remainder.

## Stack Facts

- **System Name**: Tenir-Too Access Control Bot.
- **Python Version**: 3.11 (for optimal stability and dependency compatibility).
- **Framework**: aiogram 3.4.1 (asynchronous Python framework).
- **Testing Suite**: pytest 8.1.1 with pytest-asyncio, pytest-mock and pytest-cov.
- **Database Engine**: SQLite 3 with Write-Ahead Logging (WAL).
- **Core Purpose**: Granular access control and stealth moderation for Telegram Forum Topics
  within a Supergroup.
- **Web Bridge**: FastAPI with uvicorn for Telegram Mini Apps (TMA) integration.

(Virtual-environment mandate is a rule — see `R-PROC-7`.)

## Layered Architecture

Decoupled concerns across five layers:

- **Handlers** — UI and command routing (data access mediated by services — `R-ARCH-2`).
- **Middlewares** — logic interception pipeline.
- **Services** — business logic; gateway for all handler-to-DB interactions.
- **Keyboards** — inline keyboard builders; the only layer with a sanctioned direct DB-read
  exception (`R-ARCH-3`), exposed via the wildcard re-export facade `keyboards/__init__.py`.
- **Database** — persistence via the Facade pattern (`R-ARCH-1`).
- **Tests** — automated suite using an in-memory database and mocks.
- **Indexing Protocol** — universal addressing system (`R-<DOMAIN>-<n>`, legacy `CP-x`/`PL-x`)
  for all rules and patterns; minimizes context bloat and enables precise citation.
- **Web Bridge** — FastAPI backend for Telegram Mini Apps, sharing the service layer with the
  bot.
- **Web Routers** — API endpoints in `web/routers/` (`dashboard.py`, `announcements.py`)
  providing parity with the bot UI.

## Import Dependency Graph

Permitted import direction — top consumers to bottom providers (enforced: `R-ARCH-4`):

~~~
handlers/*              →  services/*                    →  database/db.py  →  database/(members|topics|groups|roles|permissions).py
keyboards/__init__.py   →  keyboards/*_kb.py             →  database/db.py  →  database/(members|topics|groups|roles|permissions).py
middlewares/*           →  services/permission_service.py →  database/db.py
web/routers/*           →  services/*                    →  database/db.py
main.py                 →  handlers/*, middlewares/*, database/db.py (init_db only), web/main.py
database/__init__.py    →  database/db.py
database/db.py          →  database/connection.py (init_db, get_conn re-export)
                        →  database/(members|topics|groups|roles|permissions).py
~~~

## Context Manager Connectivity

`database/connection.py` uses a custom `@contextmanager` (`get_conn`) for deterministic
connection handling and guaranteed closure on both success and exception. WAL mode is
activated on every individual connection open, not globally at startup. `DB_PATH` is resolved
relative to `connection.py`'s own location, always placing `bot.db` inside the `database/`
directory regardless of the working directory at launch.

`loader.py` initializes the `Bot` instance with `DefaultBotProperties(parse_mode="HTML")`.
This ensures that all messages sent via the bot (including direct `bot.send_message` calls)
support HTML formatting by default, providing a systemic safety net for UI decorations.
