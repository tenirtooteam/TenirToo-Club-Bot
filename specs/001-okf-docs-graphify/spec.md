# Feature Specification: Two-Tier Documentation Architecture (Normative Core + OKF Reference Bundle) with Graphify Integration

**Feature Branch**: `001-okf-docs-graphify`

**Created**: 2026-07-02

**Status**: Draft

**Input**: User description: "Migrate project documentation to a two-tier context architecture (normative core + OKF-style reference bundle) and integrate graphify knowledge graph. Approved by architectural audit (5/6, conditionally accepted)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reference Content Extraction into OKF Bundle (Priority: P1)

An AI agent starting a Route A task loads the core documentation files and, instead of ~90KB of mixed content, receives a compact normative core plus a bundle index. When the task requires reference data (database schema, module registry, feature implementation details), the agent opens only the specific concept file listed in the bundle index.

**Why this priority**: This is the root fix for both reported pains: normative rules stop being diluted by reference bulk, and the knowledge corpus becomes granular. All other stories build on the bundle existing.

**Independent Test**: Can be fully tested by measuring the size of the mandatory pre-read set before/after, verifying every extracted concept file is reachable from the bundle index, and confirming no normative rule left the core.

**Acceptance Scenarios**:

1. **Given** the bundle exists at `docs/knowledge/`, **When** an agent reads `docs/knowledge/index.md`, **Then** every concept file in the bundle is listed with a one-line description and no listed file is missing.
2. **Given** a concept file in the bundle, **When** its header is parsed, **Then** it contains machine-readable metadata with a non-empty content type, title, description, and timestamp.
3. **Given** the migrated `PROJECT_LOGIC.md`, **When** an agent looks up an extracted section by its `PL-x.y` index, **Then** the core file contains a stub with the same anchor pointing to the exact bundle file.
4. **Given** the full rule inventory of the pre-migration core files, **When** migration completes, **Then** every imperative statement (MUST / prohibited / forbidden / never) is still present verbatim in the core files.

---

### User Story 2 - Core Deduplication and Repair (Priority: P2)

A maintainer reading the core files sees each rule stated exactly once in its authoritative home: coding constraints reference architectural rules by index instead of restating them, the feature list holds one line per feature, and the text corruption in the context file is repaired.

**Why this priority**: Duplication between the two core files is the measured cause of signal dilution; removing it shrinks the pre-read further and eliminates contradictory drift. Depends on User Story 1 only for the destination of moved detail.

**Independent Test**: Can be tested by scanning the core files for the known duplicated rule pairs and for the corrupted text fragment, and by checking the feature list line lengths.

**Acceptance Scenarios**:

1. **Given** the migrated `CONTEXT_PROMPT.md`, **When** searching for the corrupted fragment `refer to **PROJ##`, **Then** it is absent and the `[CP-3]` header renders as a proper standalone heading.
2. **Given** the migrated `CONTEXT_PROMPT.md`, **When** comparing `CP-3.6`/`CP-3.7` against `PL-4.5`/`PL-6.2`/`PL-6.18`, **Then** the rule text exists in full in exactly one file and the other file cites it by index.
3. **Given** the migrated `CP-2` feature list, **When** any feature entry is inspected, **Then** it occupies one line and its implementation details live in the bundle or `PROJECT_LOGIC.md`, not in the list entry.

---

### User Story 3 - Workflow and Tooling Synchronization (Priority: P2)

An AI agent following the orchestrator workflow finds updated instructions: the Route A pre-read names the thin core files plus the bundle index, content ownership rules cover the bundle, the documentation-update skill knows how to write into the bundle, and an automated validation suite fails the build if the bundle degrades (broken index, missing metadata, broken cross-references).

**Why this priority**: Without synchronized workflow docs and automated validation, the two-tier structure drifts apart within a few update cycles — this was an explicit condition of the architectural audit's acceptance.

**Independent Test**: Can be tested by running the new validation suite against the bundle (green on the migrated state, red on a deliberately broken fixture) and by inspecting the workflow files for updated pre-read and ownership sections.

**Acceptance Scenarios**:

1. **Given** the validation suite, **When** it runs against the migrated repository, **Then** it passes; **When** a concept file's metadata is removed or an index entry is deleted, **Then** it fails with a message naming the offending file.
2. **Given** the updated orchestrator file, **When** an agent reads the Route A pre-read instruction, **Then** it lists the core files and the bundle index, and the content ownership table assigns bundle content an authoritative home.
3. **Given** the updated documentation-update skill, **When** a module registry or schema change is documented, **Then** the skill's instructions direct the write into the corresponding bundle concept file.

---

### User Story 4 - Knowledge Graph over the Repository (Priority: P3)

A maintainer or AI agent asks an architecture question ("what depends on the database facade?", "which flows touch event moderation?") and gets an answer from a pre-built knowledge graph over the code and the fragmented documentation, instead of re-reading files.

**Why this priority**: Valuable but non-blocking; it consumes the granularity created by Stories 1–2 and can be rebuilt at any time.

**Independent Test**: Can be tested by building the graph and issuing a query that returns nodes referencing both code entities and bundle concept files.

**Acceptance Scenarios**:

1. **Given** the migrated documentation, **When** the knowledge graph build runs over the repository, **Then** a local graph output directory is produced and is excluded from version control.
2. **Given** the built graph, **When** the onboarding instructions are read, **Then** they direct agents to answer architecture questions via graph queries first.

---

### Edge Cases

- What happens when a normative rule and reference detail are interleaved in one section (e.g., PL-3.2 access logic inside the schema chapter)? → The classification criterion applies per statement, not per section: imperative sentences stay in core, descriptive tables/DDL move; the core stub must summarize what moved.
- How does the system handle a `PL-x.y` index cited by an existing implementation plan or test after its content moves to the bundle? → The anchor must survive in the core as a stub line pointing to the bundle file; validation fails on any dangling `PL-x.y` reference.
- What happens when the bundle index and the bundle contents diverge (file added without index entry, or entry without file)? → Validation suite fails in both directions.
- What happens if the graph build tooling is unavailable in the execution environment? → Stories 1–3 must complete independently; Story 4 is reported as blocked, not silently skipped.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a reference bundle directory (`docs/knowledge/`) containing one concept file per extracted topic, an `index.md` listing every concept file with a one-line description, and a `log.md` recording bundle changes chronologically.
- **FR-002**: Every concept file MUST carry machine-readable front matter with at minimum a non-empty `type`, plus `title`, `description`, and `timestamp` fields.
- **FR-003**: The migration MUST move the database DDL schema [PL-3.1], the Module Registry [PL-2.2], and per-feature implementation details currently embedded in `CP-2` entries into bundle concept files, and MUST NOT move any imperative statement out of the core files.
- **FR-004**: For every extracted section, `PROJECT_LOGIC.md` MUST retain the original `PL-x.y` anchor as a stub line that names the bundle file holding the content.
- **FR-005**: The migration MUST remove rule-text duplication between `CONTEXT_PROMPT.md` and `PROJECT_LOGIC.md` for the known pairs (`CP-3.6`↔`PL-4.5`, `CP-3.7`↔`PL-6.2`/`PL-6.18`), leaving full text in one authoritative file and an index citation in the other.
- **FR-006**: The migration MUST repair the corrupted text at the `CP-2`/`CP-3` boundary in `CONTEXT_PROMPT.md` (fragment `refer to **PROJ## [CP-3]`).
- **FR-007**: The migration MUST compress each `CP-2` feature entry to a single line, relocating displaced detail per the classification criterion.
- **FR-008**: `GEMINI.md` MUST be updated so the Route A pre-read set is the thin core files plus `docs/knowledge/index.md`, the File Registry and Content Ownership tables cover the bundle, and onboarding directs architecture questions to the knowledge graph when present.
- **FR-009**: The `tenirtoo-docs-update` skill MUST be updated so its commands write reference-type changes into bundle concept files (including index and log maintenance) instead of the monolith sections.
- **FR-010**: An automated validation suite (pytest) MUST verify: parseable front matter with non-empty `type` in every concept file, bidirectional index-to-file consistency, presence of all pre-migration `PL-x.y` anchors in `PROJECT_LOGIC.md`, absence of the corrupted fragment, and absence of dangling bundle references from core files.
- **FR-011**: The existing test suite MUST remain green; the migration MUST NOT modify bot source code (`handlers/`, `services/`, `database/`, `keyboards/`, `middlewares/`, `webapp/`).
- **FR-012**: A knowledge graph MUST be built over the repository into a local output directory excluded from version control, and the onboarding documentation MUST reference it as the first stop for architecture questions.
- **FR-013**: All bundle files MUST be tracked in version control (the bundle is public documentation, same visibility class as `PROJECT_LOGIC.md`).

### Key Entities

- **Core file**: An always-preread documentation file (`PROJECT_LOGIC.md`, `CONTEXT_PROMPT.md`) holding only normative rules, index anchors, and stubs after migration.
- **Concept file**: A bundle markdown file holding one reference topic (schema, registry, feature detail) with machine-readable front matter.
- **Bundle index**: `docs/knowledge/index.md`; the progressive-disclosure entry point enumerating all concept files.
- **Anchor stub**: A line in a core file preserving a `PL-x.y` index whose body moved to the bundle, naming the destination file.
- **Knowledge graph output**: Locally generated, git-ignored graph artifacts (`graphify-out/`) built from code and bundle files.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The mandatory Route A pre-read volume (core files + bundle index) is reduced by at least 40% relative to the current 90KB baseline.
- **SC-002**: 100% of imperative statements present in the pre-migration core files remain in the post-migration core files (verified by rule inventory diff).
- **SC-003**: The bundle validation suite passes on the migrated repository and detects each seeded defect class (missing metadata, index divergence, dangling anchor) in mutation checks.
- **SC-004**: The pre-existing test suite passes with zero modifications to its files.
- **SC-005**: Every pre-migration `PL-x.y` index resolves — either to full content or to a stub naming a bundle file — with zero dangling references.
- **SC-006**: An architecture question about module relationships can be answered from the knowledge graph without opening source files.

## Assumptions

- The executing agent (Opus via `speckit-implement`) has access to the workspace-local skills (`tenirtoo-docs-update`) and the user-level `graphify` skill; if `graphify` is unavailable, Story 4 is reported as blocked rather than skipped silently.
- OKF is adopted as a structural pattern (front matter + index + log), not as a conformance target; no external OKF consumer exists yet, so spec version drift (v0.1) carries no risk.
- The classification criterion ("imperative statements stay in core; descriptive content moves to bundle") is applied per statement, with ambiguous cases defaulting to core (safer: rule stays in guaranteed context).
- `CHANGELOG.md`, `README.md`, and `_nogit_*` files are out of scope except for a `CHANGELOG.md` entry on completion (CMD-4 route).
- Git operations follow the project's GW-1 protocol: local commits allowed at milestones, no push.
