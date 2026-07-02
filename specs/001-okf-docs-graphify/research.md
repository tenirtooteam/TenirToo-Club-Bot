# Research: Two-Tier Documentation Architecture

**Date**: 2026-07-02. All unknowns were resolved during the pre-plan architectural audit (PA-1/APA-1 sessions); no open NEEDS CLARIFICATION items remain. This file consolidates the decisions.

## D1. Adopt OKF as a structural pattern, not a conformance target

- **Decision**: Borrow the OKF v0.1 structure (concept files with YAML front matter, `index.md`, `log.md`) without claiming spec conformance or tracking spec evolution.
- **Rationale**: OKF v0.1 was published 2026-06-12 and has no external adoption yet; the underlying LLM-wiki / progressive-disclosure pattern, however, is industry-established. Borrowing structure captures the benefit with zero coupling to an unstable spec.
- **Alternatives considered**: (a) Full OKF conformance — rejected: no consumer exists, spec is 3 weeks old. (b) Ad-hoc fragmentation without front matter — rejected: front matter is nearly free and makes files machine-checkable and graph-friendly.

## D2. Two-tier split with a per-statement classification criterion

- **Decision**: Imperative statements (MUST / prohibited / forbidden / never / strictly) remain in the always-preread core files. Descriptive/reference content (DDL, registries, feature implementation details) moves to the bundle. The criterion applies per statement, not per section; ambiguous cases stay in core.
- **Rationale**: Rules must be guaranteed present in context at violation time — an agent cannot know in advance which rule it is about to break, so rules cannot be behind progressive disclosure. Reference data is looked up deliberately, so on-demand reading is safe. This was the decisive argument of the audit (full migration scored 2/6; this hybrid scored 5/6).
- **Alternatives considered**: (a) Full migration of everything including rules — rejected: removes rules from guaranteed context, likely worsening rule adherence. (b) No migration, only deduplication — rejected: does not fix graph granularity and leaves ~180 lines of pure reference data in every pre-read.

## D3. Extraction scope for phase one

- **Decision**: Extract exactly: `[PL-3.1]` DDL schema (~100 lines), `[PL-2.2]` Module Registry (~84 lines), and the implementation details embedded in multi-line `CP-2` feature entries. Everything else stays.
- **Rationale**: These are the three largest purely descriptive blocks; together they account for the bulk of the reference volume. A minimal, verifiable first cut satisfies the audit's "migrate in phases" condition.
- **Alternatives considered**: Also extracting `[PL-2.3]` import graph, `[PL-7]` constants, `[PL-8]` testing infrastructure — deferred: `[PL-7]`/`[PL-8]` mix imperative rules with description; splitting them per-statement is follow-up work after the pattern proves itself.

## D4. Anchor stub format for extracted sections

- **Decision**: Each extracted section keeps its heading and `PL-x.y` anchor in `PROJECT_LOGIC.md`, followed by a one-line summary and an explicit pointer: `> Moved to docs/knowledge/<file>.md — read on demand.`
- **Rationale**: The `PL-x.y` indexing system is load-bearing (cited by plans, tests, skills); dangling indices would break the RNA citation protocol. Stubs preserve resolution at near-zero token cost.
- **Alternatives considered**: Renumbering or dropping moved anchors — rejected: silently invalidates historical plans and cross-references.

## D5. Bundle location and git visibility

- **Decision**: `docs/knowledge/`, tracked in git.
- **Rationale**: The bundle is public technical truth (same class as `PROJECT_LOGIC.md` in the GEMINI.md File Registry). A `docs/` root keeps repository top level clean.
- **Alternatives considered**: `_nogit_knowledge/` (local-only) — rejected: reference truth must travel with the repository; `.agents/` — rejected: that tree is git-ignored workspace tooling.

## D6. Validation approach

- **Decision**: New pytest module `tests/test_knowledge_bundle.py` validating: parseable front matter with non-empty `type` in every concept file; bidirectional index↔file consistency; survival of all pre-migration `PL-x.y` anchors in `PROJECT_LOGIC.md`; absence of the `refer to **PROJ##` corruption fragment; no dangling `docs/knowledge/` references from core files. Front matter parsed with PyYAML if present in venv, otherwise a small `re`-based parser inside the test module.
- **Rationale**: The audit's acceptance condition — drift protection must ship in the same change. Pytest is the project's existing gate; the suite runs in CI-equivalent local flow with the rest of the tests.
- **Alternatives considered**: Extending `local_scripts/prompt_linter.py` — rejected for phase one: the linter validates per-feature agent artifacts (plan/checklist/report stages), not repository state; mixing concerns would change its CLI contract.

## D7. Graphify integration mode

- **Decision**: Build the graph over the repository root with the user-level `graphify` skill after the fragmentation lands; output `graphify-out/` added to `.gitignore`; `GEMINI.md` onboarding gains a pointer that architecture questions should be answered via graphify queries first when `graphify-out/` exists.
- **Rationale**: Post-fragmentation build maximizes node granularity and per-file semantic caching. Graph artifacts are derived data — regenerable, hence local-only.
- **Alternatives considered**: Graphing only `docs/knowledge/` — rejected: cross-linking code entities with doc concepts is the main query value. Committing `graphify-out/` — rejected: derived artifacts churn the history.

## D8. Executor and process fit

- **Decision**: Execution by Claude Opus through `speckit-implement` over `tasks.md`; RNA artifacts (`implementation_plan.md`, `task.md`, `walkthrough.md`) live in the same feature directory so all three `prompt_linter.py` stages run against one `--dir`.
- **Rationale**: Satisfies both process contracts (spec-kit and GEMINI.md RNA) without duplicating content: `tasks.md` is the executable checklist, `implementation_plan.md` is the linter-shaped RNA view of this plan.
- **Alternatives considered**: RNA-only flow without spec-kit — viable, but the user explicitly requested spec-kit tooling for the Opus handoff.
