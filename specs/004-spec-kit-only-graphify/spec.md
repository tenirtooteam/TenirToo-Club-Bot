# Feature Specification: Spec-Kit-Only Route A + Full Graphify Integration

**Feature Branch**: `004-spec-kit-only-graphify`

**Created**: 2026-07-04

**Status**: Draft

**Input**: Fable readiness audit of 2026-07-04. Three defects: (1) Route A is dual-process — the spec-kit chain and the legacy RNA-1/`implementation_plan.md`/`task.md` path coexist; feature 003 only *deprecated* RNA-1 and made the linter backward-compatible, leaving double bookkeeping and an ambiguous canonical artifact for new features. (2) Graphify integration is best-effort and undocumented — onboarding says "answer architecture questions via graphify first" but the CLI is not guaranteed installed, no post-commit auto-rebuild hook exists, no in-repo doc explains the graph to future sessions, the "use the graph" instruction is a SHOULD in onboarding rather than a governed rule, and the graph silently goes stale (no freshness enforcement, no docs-update step). (3) The implementation executor (Sonnet vs Opus) is not designated for this change.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Spec-Kit Is the Only Route A (Priority: P1)

An AI agent starting a Route A task finds exactly one canonical process: the spec-kit chain. `RNA-1`, `implementation_plan.md`, and `task.md` are gone from the normative surface (registry, rules, linter). Historical feature directories (001–003) keep their legacy artifacts as read-only records, but no new feature may produce or lint them.

**Why this priority**: Dual-process is the primary friction the whole governance effort exists to remove; an agent must never have to decide "which artifact is canonical" by cross-reading three documents.

**Independent Test**: `prompt_linter.py --stage plan` on a directory containing only `implementation_plan.md` (no `plan.md`) now errors "no plan.md found"; the same for `task.md` at the checklist stage. A governance test asserts `AGENTS.md`/`RULES.md` contain no `RNA-1` command entry and no legacy-fallback wording.

**Acceptance Scenarios**:

1. **Given** `AGENTS.md` § COMMAND REGISTRY, **When** read, **Then** there is no `RNA-1` row and no "legacy alias" language; Route A names only the spec-kit chain; § INDEXING records `RNA-1` as retired (superseded by `/speckit-plan`).
2. **Given** `RULES.md` R-PROC-1, R-PROC-2, R-PROC-4, **When** read, **Then** none references `implementation_plan.md` or `task.md` as an accepted artifact; R-PROC-2 names `plan.md` as the sole canonical plan and `tasks.md` as the sole canonical checklist; historical artifacts are called out only as read-only records.
3. **Given** `local_scripts/prompt_linter.py`, **When** its legacy code paths are searched, **Then** `PLAN_LEGACY_REQUIRED_H2S` and the `implementation_plan.md`/`task.md` fallbacks are removed, and the linter's own tests are red-before / green-after for the "legacy file rejected" case.
4. **Given** `docs/knowledge/rule-map.md`, **When** scanned, **Then** an `RNA-1 → retired` disposition row exists.

---

### User Story 2 - Graphify Fully Operational and Governed (Priority: P1)

An AI agent (any session, any assistant) can rely on a working, always-on knowledge graph: the CLI is installed, the graph is freshly built over the repository, a governed rule (not a soft onboarding hint) mandates querying it first for architecture/relationship questions, and an in-repo knowledge file explains the graph and its commands so future sessions need nothing beyond the repository.

**Why this priority**: The graph is only valuable if it is present, current, and its use is mechanical rather than optional; today all three are uncertain.

**Independent Test**: `graphify query "which modules depend on the database facade?"` returns the facade node from the existing graph without opening source. `docs/knowledge/graph.md` exists and is listed in `index.md`/`log.md`. A new rule `R-PROC-12` exists in `RULES.md`.

**Acceptance Scenarios**:

1. **Given** the developer environment, **When** graphify install steps run, **Then** the `graphify` CLI is importable/executable and `graphify query "<question>"` answers from `graphify-out/graph.json`.
2. **Given** `RULES.md`, **When** read, **Then** `R-PROC-12` mandates: when `graphify-out/` exists, architecture/relationship/data-flow questions MUST be answered via `graphify query` first; source reads are for verification and detail; if the CLI is absent, the agent falls back to source reads and states the degradation explicitly.
3. **Given** `docs/knowledge/graph.md`, **When** read, **Then** it describes what the graph is, the `query`/`path`/`explain`/`--update` commands, the auto-rebuild hook and its limitation (code only, not docs), the fallback when the CLI is unavailable, and it is referenced from `AGENTS.md` onboarding via the R-PROC-12 citation. `index.md` gains a row and `log.md` an entry (bundle atomicity).
4. **Given** `AGENTS.md` § ONBOARDING item 5, **When** read, **Then** the soft "answer via graphify queries" hint is replaced by a citation of `R-PROC-12`.

---

### User Story 3 - The Graph Stays Fresh Automatically (Priority: P2)

The graph does not silently rot. Code changes trigger an automatic rebuild of the graph's structural layer on commit; documentation and semantic changes are refreshed by the docs-update skill as part of Route C, so the "trust the graph before source" mandate is never pointed at a stale graph.

**Why this priority**: Without freshness enforcement, R-PROC-12 becomes a hazard — it directs agents to a possibly-outdated map. Auto-rebuild + a docs-update step close the two update channels (code, docs/LLM).

**Independent Test**: `graphify hook status` reports the post-commit hook installed; after a code commit, `graphify-out/graph.json` mtime advances. The docs-update `SKILL.md` contains a graphify-refresh step in its CMD-1/CMD-2 flow and Output Validation checklist.

**Acceptance Scenarios**:

1. **Given** the repository, **When** `graphify hook install` has run, **Then** `.git/hooks/post-commit` invokes a graphify rebuild of changed code files, and `graphify hook status` confirms it.
2. **Given** a commit that changes a `.py` source file, **When** the commit completes, **Then** the graph's structural layer is rebuilt for the changed files (no manual step).
3. **Given** the `tenirtoo-docs-update` skill, **When** CMD-1 or CMD-2 completes a documentation change, **Then** its procedure includes running `graphify --update` (covering doc/semantic changes the commit hook does not) and its Output Validation checklist includes a "graph refreshed" item — without introducing any git operation into Route C.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Remove `RNA-1` from `AGENTS.md` § COMMAND REGISTRY and every "legacy alias" reference in § EXECUTION WORKFLOW Route A and § PLAN CONTENT; add an `RNA-1 → retired` note to § INDEXING pointing to `/speckit-plan` as the successor.
- **FR-002**: Amend `RULES.md` R-PROC-1 (remove "starts only after an explicit RNA-1"; planning starts via `/speckit-plan` after an approved audit), R-PROC-2 (remove "`implementation_plan.md` is accepted for historical features"; `plan.md`/`tasks.md` are the sole canonical artifacts; historical specs 001–003 remain read-only records), and R-PROC-4 (remove the `implementation_plan.md`/`task.md` legacy-fallback clause). No rule ID is renumbered or reused (ID permanence).
- **FR-003**: Remove the legacy code paths from `local_scripts/prompt_linter.py`: delete `PLAN_LEGACY_REQUIRED_H2S`, the `implementation_plan.md` fallback in the plan-file resolver, and the `task.md` fallback in the tasks-file resolver; both stages accept only `plan.md`/`tasks.md`. TDD: update the linter tests to assert legacy filenames are rejected (red first), then make the change (green).
- **FR-004**: Add an `RNA-1 → retired (superseded by /speckit-plan, 2026-07-04)` disposition row to `docs/knowledge/rule-map.md`.
- **FR-005**: Install the graphify CLI (`pip install graphifyy` per the upstream package name) into the project `venv`; verify `graphify --version` and a smoke `graphify query` against the existing graph.
- **FR-006**: Run `graphify claude install` (native CLAUDE.md integration) so future Claude Code sessions check/rebuild the graph automatically; the write MUST preserve the existing `@AGENTS.md` shim in `CLAUDE.md` (append a `## graphify` section, not replace the file).
- **FR-007**: Run `graphify hook install` to add the post-commit auto-rebuild hook; verify `graphify hook status`. The hook rebuilds only the structural (code) layer — this limitation MUST be documented (FR-010).
- **FR-008**: Rebuild the current graph with `graphify --update` (incremental, including semantic/doc extraction) so the committed governance changes are reflected before the graph is declared authoritative.
- **FR-009**: Add rule `R-PROC-12 [A]` to `RULES.md`: when `graphify-out/` exists, architecture/relationship/data-flow questions MUST be answered via `graphify query` before source reads; source reads verify and add detail; if the CLI is unavailable, fall back to source reads and state the degradation explicitly. Include the freshness contract (hook covers code; docs via Route C).
- **FR-010**: Add `docs/knowledge/graph.md` concept file (front matter with `type`/`title`/`description`/`timestamp`) describing the graph, the `query`/`path`/`explain`/`--update` commands, the commit-hook auto-rebuild and its code-only limitation, and the CLI-absent fallback. Satisfy bundle atomicity: add the file, a row in `index.md`, and an entry in `log.md`.
- **FR-011**: Replace `AGENTS.md` § ONBOARDING item 5's soft graphify hint with a citation of `R-PROC-12`.
- **FR-012**: Add a graphify-refresh step to the `tenirtoo-docs-update` skill: after CMD-1/CMD-2 documentation edits, run `graphify --update`; add a "graph refreshed" item to its Output Validation checklist. No git operation is introduced into Route C.
- **FR-013**: Update the docs-update skill's Validation command list to drop any legacy-artifact naming (consistency with FR-003).
- **FR-014**: `.specify/feature.json` points at this feature during work; CHANGELOG entry (next version) via CMD-4; GW-1 local commit at the end (no push). No bot source (handlers/services/database) changes; full regression suite green.

### Key Entities

- **Canonical Route A artifact**: `plan.md` (plan) and `tasks.md` (checklist) — the only artifacts the linter and rules recognize for new features.
- **Retired command**: `RNA-1` — recorded as retired in § INDEXING and rule-map, never invoked for new features.
- **Graph freshness contract**: two update channels — code (post-commit hook, automatic) and docs/semantic (`graphify --update` via Route C).
- **R-PROC-12**: the governed mandate to query the graph first, with an explicit CLI-absent degradation path.

## Success Criteria *(mandatory)*

- **SC-001**: `prompt_linter.py` rejects `implementation_plan.md`/`task.md` (legacy names) at plan/checklist stages; its test suite is green with the "legacy rejected" cases added; no `PLAN_LEGACY_REQUIRED_H2S` symbol remains in the source.
- **SC-002**: `AGENTS.md` and `RULES.md` contain zero `RNA-1` command entries and zero `implementation_plan.md`/`task.md` acceptance wording; `RNA-1 → retired` appears in § INDEXING and rule-map.
- **SC-003**: `graphify query "<architecture question>"` answers from the graph without opening source; `graphify --version` succeeds inside the venv.
- **SC-004**: `graphify hook status` confirms the post-commit hook; `graphify claude install` added a `## graphify` section to `CLAUDE.md` with the `@AGENTS.md` shim intact.
- **SC-005**: `R-PROC-12` exists in `RULES.md`; `docs/knowledge/graph.md` exists and is listed in `index.md` and `log.md`; `AGENTS.md` onboarding cites `R-PROC-12`.
- **SC-006**: The docs-update skill contains a `graphify --update` step and a "graph refreshed" Output Validation item; no git operation added to Route C.
- **SC-007**: Full regression green (governance + knowledge-bundle + linter suites); no edits to unrelated bot tests.

## Assumptions

- **Executor: Claude Opus** end-to-end. Rationale: the change edits governance invariants with cross-file coupling (R-PROC-1/2/4 wording must stay in sync with the linter code and the governance/knowledge-bundle tests; ID permanence; integrity guards). The graphify chunk alone would suit Sonnet, but splitting one feature across two models costs more in context handoff than it saves; if budget is a hard constraint, an acceptable fallback is Opus for the governance/linter chunk and Sonnet for the graphify-tooling chunk.
- Two approval chunks, each ending in a HARD-STOP gate task in `tasks.md`: Chunk A = spec-kit-only removal (FR-001–004, 013), Chunk B = graphify integration (FR-005–012, 014).
- This feature's own artifacts are spec-kit only (`plan.md`/`tasks.md`) — no legacy artifacts are produced, validating the removal in FR-003.
- Historical feature directories 001–003 are not modified; their legacy artifacts remain as completed records and are never re-linted.
- `graphify` package name is `graphifyy` on PyPI (per the graphify skill); the CLI entry point is `graphify`. The upstream reference is https://github.com/safishamsi/graphify.
- `.claude/skills/speckit-*` files are upstream-generated and NOT edited; the HARD-STOP gate mechanism already lands in `.specify/templates/tasks-template.md` from feature 003.
