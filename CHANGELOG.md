# Tenir-Too Club Bot Changelog

All notable changes to the Tenir-Too Club Bot project are documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.1.0] - 2026-06-18

### Added
- Domain data transfer objects (`EventDTO`, `AuditRequestDTO`) to enforce strict type contracts in database queries.
- Global dispatcher error handler (`handlers/errors.py`) to intercept, log, and report unhandled exceptions.
- Static AST-based import boundary validator (`tests/test_services/test_import_lint.py`) to prevent direct database imports in presentation layers.
- In-memory `UserSessionSimulator` test helper with automated UX assertions (markup balance, anti-spam, and navigation footers).
- E2E event creation journey TDD test verifying the entire interactive creation flow.

### Changed
- Refactored `database/events.py` and `database/audit.py` to return DTO instances instead of dict primitives (with backward-compatible dict interface).
- Eliminated direct `database.db` imports in handlers, delegating operations to `ManagementService` and `AnnouncementService`.
- Expanded autonomous UI fuzzer with unexpected command injection stress-tests during FSM states.

## [1.0.0] - 2026-06-18

### Changed
- **Prompt Architecture Restructuring**: Migrated static orchestrators and prompts to workspace-local plugin/skills architecture.
  - Relocated proposal audit prompt to `.agents/plugins/tenirtoo-plugin/skills/proposal-analysis/SKILL.md` as `tenirtoo-proposal-analysis`.
  - Relocated documentation maintenance prompt to `.agents/plugins/tenirtoo-plugin/skills/docs-update/SKILL.md` as `tenirtoo-docs-update` with command `CMD-4` support for `CHANGELOG.md`.
  - Created `AGENTS.md` specifying `proposal-auditor` and `test-runner-and-debugger` subagents.
  - Created `CLAUDE.md` to automate agent onboarding and rule references.
  - Updated `GEMINI.md` and `CONTEXT_PROMPT.md` to coordinate routes, commands, automated local commits, and TDD error-debugging.
