---
type: architecture
title: Project Identity, Stack & Layered Architecture
description: Stack facts, the five-layer decomposition, import graph, and connection-manager behavior.
source_anchor: PL-1, PL-2.1, PL-2.3, PL-2.6
timestamp: 2026-07-17
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
loader.py               →  database/db.py (SQLiteStorage class only — feature 012 / №16)
database/__init__.py    →  database/db.py
database/db.py          →  database/connection.py (init_db, get_conn re-export)
                        →  database/fsm_storage.py (SQLiteStorage re-export)
                        →  database/(members|topics|groups|roles|permissions).py
~~~

The `loader.py → database/db.py` arrow (added in feature 012) reaches the facade for the
`SQLiteStorage` FSM backend only; it mirrors the existing `main.py → database/db.py (init_db
only)` edge and flows consumer-to-provider like every other arrow. Note this edge is **not**
covered by import-linter, whose `root_packages` are `handlers`/`middlewares`/`services`/
`database` — root-level modules such as `loader.py` sit outside its contract, so this graph is
the authoritative record for it.

## Context Manager Connectivity

`database/connection.py` exposes a custom `@contextmanager` (`get_conn`) as the single
connection provider for the facade. Since feature 008 it yields **one process-wide reusable
connection** (`_shared_conn`, lazily created) instead of opening and closing a fresh
connection per call: WAL mode and `PRAGMA foreign_keys=ON` are applied **once** at connection
creation, not on every operation. `get_conn` deliberately does **not** close the connection on
exit; write transactions still commit/roll back through the caller's nested `with conn:`
block, and `get_conn` rolls back any dangling transaction if the body raises, keeping the
shared connection clean. This is safe because all `db.*` operations are synchronous with no
`await` inside a transaction — under the single-threaded asyncio loop two operations never
interleave mid-statement, so no pool or lock is needed. The change cut connection churn from
~6 `connect`+PRAGMA cycles per incoming message to ≤1.

`init_db()` calls `close_shared_conn()` first, so re-initialisation (notably a `DB_PATH`
switch in tests) rebinds the shared connection to the current database; `close_shared_conn()`
is also the shutdown hook. `DB_PATH` is resolved relative to `connection.py`'s own location,
always placing `bot.db` inside the `database/` directory regardless of the working directory
at launch.

Out of scope for feature 008 (gated behind profiling): migrating to an async driver
(`aiosqlite`) or offloading DB work to a thread pool — either would break the
single-loop-thread invariant above and require a real connection pool.

## Registration Caching (Service Layer)

`ManagementService` keeps a short-TTL in-memory memo (`REGISTRATION_TTL_SECONDS = 300`) for
user and topic registration facts (feature 008). `ensure_user_registered` and
`register_topic_if_not_exists` skip the DB when a fresh memo entry exists, eliminating the two
redundant registration lookups every incoming message otherwise incurs. Staleness is bounded
by the TTL: name changes and external deletions are re-applied within the window rather than
via per-mutation cache-busting. `reset_registration_cache()` clears both memos (used by the
`db_setup` test fixture for isolation). The cache is advisory — a cold cache reproduces the
exact prior behavior.

`loader.py` initializes the `Bot` instance with `DefaultBotProperties(parse_mode="HTML")`.
This ensures that all messages sent via the bot (including direct `bot.send_message` calls)
support HTML formatting by default, providing a systemic safety net for UI decorations.
