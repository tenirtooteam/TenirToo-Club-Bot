# Tenir-Too Club Bot Changelog

All notable changes to the Tenir-Too Club Bot project are documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] - 2026-06-18

### Changed
- **Prompt Architecture Restructuring**: Migrated static orchestrators and prompts to workspace-local plugin/skills architecture.
  - Relocated proposal audit prompt to `.agents/plugins/tenirtoo-plugin/skills/proposal-analysis/SKILL.md` as `tenirtoo-proposal-analysis`.
  - Relocated documentation maintenance prompt to `.agents/plugins/tenirtoo-plugin/skills/docs-update/SKILL.md` as `tenirtoo-docs-update` with command `CMD-4` support for `CHANGELOG.md`.
  - Created `AGENTS.md` specifying `proposal-auditor` and `test-runner-and-debugger` subagents.
  - Created `CLAUDE.md` to automate agent onboarding and rule references.
  - Updated `GEMINI.md` and `CONTEXT_PROMPT.md` to coordinate routes, commands, automated local commits, and TDD error-debugging.
