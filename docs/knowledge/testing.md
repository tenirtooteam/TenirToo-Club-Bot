---
type: testing
title: Testing Infrastructure — Configuration, Categories & Dev Sandbox
description: conftest.py fixtures, test-category directory map, and the Docker dev sandbox environment.
source_anchor: PL-8.1, PL-8.2, PL-8.4, PL-8.6
timestamp: 2026-07-02
tags: [testing, infrastructure, docker]
---

# Testing Infrastructure

> Moved from `PROJECT_LOGIC.md` [PL-8.1], [PL-8.2], [PL-8.4], [PL-8.6] during the governance
> consolidation (feature 002). Testing rules (fixture-only, no network, ID dynamism, etc.)
> live in [RULES.md](../../RULES.md) — see the `R-TEST-*` domain.

Comprehensive automated testing suite using `pytest`; tests are an integral part of the
codebase.

## Configuration (`tests/conftest.py`)

- **Database Isolation**: `db_setup` redirects `connection.DB_PATH` to a temporary file in
  `tmp_path`, ensuring a clean schema per test.
- **Mocked Bot**: `mock_bot` fixture provides an `AsyncMock(spec=Bot)`. Factories in
  `conftest.py` ensure `message.bot` and `callback.bot` point to this mock via the `_bot`
  private attribute.
- **FSM Context**: `storage` and `create_context` fixtures allow full FSM state simulation.

## Test Categories

- **`tests/test_database/`**: unit/integration tests for SQL operations — CRUD, cascading
  deletions, access evaluation logic.
- **`tests/test_services/`**: domain-service tests — `test_ui_integrity.py` (static/dynamic
  keyboard, URL, callback validation), `test_ui_fuzzer.py` (autonomous recursive interface
  exploration), `test_google_sheets_service.py` (mocked API validation),
  `test_management_service.py` (Search-Or-Action protocol), `test_permission_service.py`
  (role resolution).
- **`tests/test_handlers/`**: handler/middleware unit tests — routing, state transitions,
  stealth-moderation filters. Uses `__wrapped__` to bypass `sterile_command` redirects during
  logic verification.
- **`tests/test_journeys/`**: end-to-end flow tests for complex user journeys (Quick
  Announcements, Participation Audit) — cross-service orchestration and notification
  delivery. Includes `test_tma_integration.py` (bot reaction to WebApp actions).
- **`tests/test_web/`**: Web Bridge authentication/API tests, including `test_auth.py` (HMAC
  security).

## Dev Sandbox Environment (Docker)

A lightweight Docker sandbox is configured via `Dockerfile` and `docker-compose.yml` for
isolated dev-only executions. The sandbox installs dev dependencies
(`requirements-dev.txt`) and mounts the workspace, excluding the host Windows `.venv` and
database files to prevent locks. The production runtime does not use Docker and remains
dependency-clean.

## Subagent Configurations

See [subagents.md](subagents.md) for the full workspace subagent registry (proposal-auditor,
test-runner-and-debugger, cognitive-ux-auditor).
