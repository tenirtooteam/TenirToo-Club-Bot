# Feature Specification: Governance Consolidation (Single Constitution + Unified Rulebook + Knowledge Dissolution)

**Feature Branch**: `002-governance-consolidation`

**Created**: 2026-07-02

**Status**: Draft

**Input**: Full governance audit (2026-07-02) findings F1–F7: rules scattered across three files with duplication; the de-facto constitution (GEMINI.md) unversioned and vendor-misnamed; PROJECT_LOGIC charter self-contradictory; no rule taxonomy or enforcement map; mixed concerns per file; empty spec-kit constitution; triple feature-list maintenance.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Unified Rulebook (Priority: P1)

An AI agent starting any task loads exactly one rulebook (`RULES.md`) where every behavioral rule of the project lives once, with a stable ID, its rationale, a tier (judgment vs CI-enforced), and an enforcement pointer. No rule exists in two homes; historical `PL-x.y`/`CP-x.y` citations still resolve through a mapping table.

**Why this priority**: This is audit finding F1 (critical) — the root of the "rules chaos". Every other story depends on rules having a single home.

**Independent Test**: A validation suite proves: unique rule IDs, zero duplicated rule text across governance files, every pre-consolidation anchor resolves via the mapping, every Tier-B rule's enforcement pointer names an existing linter/test.

**Acceptance Scenarios**:

1. **Given** `RULES.md`, **When** any rule ID is searched across `AGENTS.md`, `PROJECT_LOGIC.md`, `CONTEXT_PROMPT.md`, **Then** the full rule text exists only in `RULES.md`; other files may cite the ID.
2. **Given** the known duplicate groups (CP-3.28↔RNA-Blueprint, CP-3.29↔GW-1, CP-3.35↔Route B, CP-6↔Response Rules, PL-6.4↔CP-3.19, PL-6.6↔CP-3.20, PL-6.7↔CP-3.21, PL-6.22↔CP-3.31, PL-6.14↔CP-3.9, PL-6.11↔CP-3.10, PL-6.8↔CP-3.22), **When** consolidation completes, **Then** each group maps to exactly one rule entry with both legacy anchors in its mapping row.
3. **Given** a rule enforced by CI (semgrep/import-linter/AST/ruff/pytest gates), **When** it appears in `RULES.md`, **Then** it is a one-line Tier-B entry naming its enforcement mechanism.
4. **Given** any legacy citation `PL-x.y` or `CP-x.y` from a historical plan, **When** looked up in the mapping table, **Then** it resolves to a rule ID or a knowledge-bundle file.

---

### User Story 2 - Versioned Constitution at the Standard Entry Point (Priority: P1)

An AI agent (any vendor) entering the repository finds the project constitution at `AGENTS.md` (the open agent-instructions standard), tracked in Git: identity, project brief, routes, commands, git protocol, response protocol, subagent registry, and pointers to `RULES.md` and the knowledge bundle. `CLAUDE.md` and `GEMINI.md` are one-line compatibility shims.

**Why this priority**: Audit F2 (critical) — governance must be versioned and discoverable at the standard location; ties with US1 as the two pillars.

**Independent Test**: `git ls-files` shows `AGENTS.md` and `RULES.md` tracked; shims contain only imports/pointers; the constitution contains no full rule texts (only citations).

**Acceptance Scenarios**:

1. **Given** the migrated repo, **When** `git ls-files AGENTS.md RULES.md` runs, **Then** both are tracked (removed from `.gitignore`).
2. **Given** `CLAUDE.md` and `GEMINI.md`, **When** read, **Then** each is a shim importing/pointing to `AGENTS.md` with no independent normative content.
3. **Given** the old `AGENTS.md` subagent registry, **When** migration completes, **Then** its content lives as a section (or knowledge file) referenced by the constitution — no information lost.

---

### User Story 3 - Description-Only Knowledge Layer (Priority: P2)

A maintainer reading `PROJECT_LOGIC.md` or `CONTEXT_PROMPT.md` finds thin, tracked redirect indexes; all descriptive content (architecture layers, middleware behavior, FSM data keys, DB patterns, constants, testing infrastructure, feature overview) lives in `docs/knowledge/` concept files; all rules live in `RULES.md`. "PROJECT_LOGIC = description only" finally matches its charter.

**Why this priority**: Audit F3/F5 — depends on US1 (rules must have a destination before leaving PL/CP).

**Independent Test**: Scanning the two legacy core files finds no imperative rule text and no multi-paragraph descriptive bodies — only index/redirect stubs; the bundle suite stays green.

**Acceptance Scenarios**:

1. **Given** migrated `PROJECT_LOGIC.md`, **When** scanned per statement, **Then** it contains only: title, purpose note, anchor-mapping pointers, and redirects into `docs/knowledge/` and `RULES.md`.
2. **Given** the dissolution map (per-section destinations defined in plan), **When** each section moves, **Then** content transfers verbatim (lossless) and the bundle index/log are updated atomically.
3. **Given** the pre-read set (`AGENTS.md` + `RULES.md` + `docs/knowledge/index.md`), **When** measured, **Then** total ≤ 30 KB.

---

### User Story 4 - Process & Tooling Synchronization (Priority: P2)

The spec-kit constitution is filled and mirrors the rulebook's top principles; the workspace skills (`docs-update`, `proposal-analysis`) reference `RULES.md`/`AGENTS.md`/bundle instead of the dissolved monoliths; validation tests guard the new structure; the knowledge graph is rebuilt.

**Why this priority**: Without tooling sync the new structure drifts immediately (same condition as feature 001's US3).

**Independent Test**: Grep of skills and `.specify/memory/constitution.md` shows no stale references to dissolved content; governance test suite green; mutation checks red-then-green.

**Acceptance Scenarios**:

1. **Given** `.specify/memory/constitution.md`, **When** read, **Then** it is filled (no template placeholders) and cites rule IDs rather than restating them.
2. **Given** the skills' SKILL.md files, **When** they name ground-truth documents, **Then** they name `RULES.md` (rules), `docs/knowledge/` (reference), `AGENTS.md` (process).
3. **Given** the governance validation suite, **When** a rule is duplicated, an ID collides, a mapping row is deleted, or a shim gains normative text, **Then** the suite fails naming the offender.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A single tracked `RULES.md` MUST hold every behavioral rule with: stable ID (`R-<DOMAIN>-<n>`), statement, rationale, tier (`A` judgment / `B` CI-enforced), enforcement pointer (Tier B), and legacy anchors.
- **FR-002**: A mapping table (`docs/knowledge/rule-map.md`) MUST resolve every pre-consolidation `PL-x.y` and `CP-x.y` anchor to a rule ID or a bundle file; zero dangling legacy citations.
- **FR-003**: Duplicate rule groups identified by the audit MUST merge into single entries; conflicts between variants MUST be resolved in favor of the most restrictive/most recently validated text, with the decision logged.
- **FR-004**: Tier-B entries MUST be one-liners naming their enforcement (semgrep rule id, import-linter contract, test file, ruff); an enforcement map MUST verify each pointer exists.
- **FR-005**: `AGENTS.md` MUST become the tracked constitution (identity, brief, routes A–D, command registry, git protocol GW-1, response protocol, subagent registry, file registry, ownership rules) citing rule IDs, never restating rule text.
- **FR-006**: `CLAUDE.md` and `GEMINI.md` MUST become compatibility shims; `.gitignore` MUST stop ignoring `AGENTS.md` (and track `RULES.md`); no secrets may enter tracked files.
- **FR-007**: All descriptive content of `PROJECT_LOGIC.md`/`CONTEXT_PROMPT.md` MUST move verbatim into `docs/knowledge/` concept files per an explicit per-section dissolution map; the two files become thin tracked redirect indexes.
- **FR-008**: The bundle contract (front matter, index/log atomicity) from feature 001 MUST apply to all new concept files; existing bundle tests MUST stay green (adapted where the anchor-survival base now includes `rule-map.md`).
- **FR-009**: A new governance validation suite (pytest) MUST verify: rule-ID uniqueness, no duplicated rule text across governance files, mapping completeness (all legacy anchors), enforcement-pointer existence, shim purity, constitution filled.
- **FR-010**: `.specify/memory/constitution.md` MUST be filled from the rulebook's top principles; workspace skills MUST be updated to the new ground-truth documents.
- **FR-011**: No bot source code changes; the pre-existing test suite MUST remain green with zero edits to existing test files (the feature-001 bundle test may be adapted only where its base-file assumptions changed — documented).
- **FR-012**: The knowledge graph MUST be rebuilt (`graphify --update` or full) after migration.
- **FR-013**: Route A pre-read set becomes `AGENTS.md` + `RULES.md` + `docs/knowledge/index.md`, total ≤ 30 KB.

### Key Entities

- **Rule entry**: one rule in `RULES.md` — ID, statement, rationale, tier, enforcement, legacy anchors.
- **Rule map**: table resolving legacy `PL-x.y`/`CP-x.y` → rule ID or bundle file.
- **Constitution**: `AGENTS.md` — process and identity, citations only.
- **Shim**: `CLAUDE.md`/`GEMINI.md` — pointer-only compatibility files.
- **Redirect index**: post-dissolution `PROJECT_LOGIC.md`/`CONTEXT_PROMPT.md`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Pre-read set (`AGENTS.md` + `RULES.md` + bundle index) ≤ 30 KB (vs 69.5 KB current, 89.8 KB original — ≥66% total reduction).
- **SC-002**: 100% of rules exist in exactly one home; duplicate-text scan across governance files returns zero hits ≥20 words.
- **SC-003**: 100% of legacy anchors (250 `PL-x.y` + all `CP-x.y`) resolve via rule map or bundle (test-enforced).
- **SC-004**: Every Tier-B enforcement pointer names an existing mechanism (test-enforced); ≥15 rules demoted from prose to Tier-B one-liners.
- **SC-005**: Existing test suite green; zero edits to pre-existing test files (feature-001 suite adaptation documented if needed).
- **SC-006**: Governance mutation checks (ID collision, duplicated rule text, deleted mapping row, normative text in shim) each fail the suite.

## Assumptions

- Nothing in GEMINI.md/AGENTS.md content is secret; making the constitution public is safe (verified during Phase 1 inventory; anything sensitive stays in `_nogit_*`).
- GEMINI.md shim is kept (git-ignored) for Gemini-CLI compatibility; CLAUDE.md shim for Claude Code.
- Legacy anchors are preserved via mapping, not via keeping stub headings in the dissolved files (redirect index points to `rule-map.md`).
- Execution is split between Claude Opus (judgment-heavy consolidation) and Claude Sonnet (mechanical dissolution/sync) per the plan's executor tags.
- Git: local commits per GW-1 at chunk boundaries; no push.
