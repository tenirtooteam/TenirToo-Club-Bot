# Feature Specification: Governance Hardening (Rule Retention Repair + Route/Spec-Kit Unification)

**Feature Branch**: `003-governance-hardening`

**Created**: 2026-07-03

**Status**: Draft

**Input**: Two Fable audits of 2026-07-03: (a) readiness audit findings F-1 (three rules lost during the 002 consolidation), F-2 (~15 wrong rule-map rows from generator fallbacks), F-3 (stale feature.json), F-4 (retention checking was anchor-level, not content-level); (b) routes/spec-kit compatibility analysis findings К-1 (spec-kit is the de-facto Route A engine but unregistered in the constitution), К-2 (artifact duplication: plan.md↔implementation_plan.md, tasks.md↔task.md, caused by prompt_linter's hardcoded filenames), К-3 (speckit-implement has no built-in user-approval gate; R-PROC-2 chunk gates exist only if hand-written into tasks.md).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - No Imperative Left Behind (Priority: P1)

An AI agent consulting `RULES.md` finds every behavioral rule that existed before the consolidation — including the three that were silently dropped — and an automated test permanently guarantees that every imperative-flagged legacy anchor resolves to a real rule ID (or an explicitly justified `retired`/`descriptive` disposition), never to a descriptive bundle file.

**Why this priority**: Rule loss is the exact failure the whole governance effort exists to prevent (audit F-1/F-4).

**Independent Test**: New test `test_imperatives_map_to_rules` is red on the current tree (catches CP-3.11, CP-3.47, CP-3.28.2 et al.), green after the restore + map fixes; mutation check (point one imperative anchor at a bundle file) turns it red again.

**Acceptance Scenarios**:

1. **Given** the frozen imperative inventory (116 lines), **When** the new test runs, **Then** every imperative anchor's rule-map target is an existing `R-<DOMAIN>-<n>`, or the anchor is listed in the curated dispositions file as `descriptive` or `retired`.
2. **Given** the restored rules, **When** `RULES.md` is searched, **Then** R-UI-12 (isolated cancel keyboards / terminate_input before independent transitions), R-UI-13 (admin-creation UX branching), R-ARCH-9 (middleware pipeline order invariant) exist, and R-PROC-2 contains the incremental-plan-update principle.
3. **Given** `docs/knowledge/rule-map.md`, **When** scanned, **Then** zero rows point to `docs/knowledge/index.md`, and no imperative anchor points to `features-overview.md`.

---

### User Story 2 - One Process, One Set of Artifacts (Priority: P1)

An AI agent running Route A follows a single canonical flow — the spec-kit chain, registered in `AGENTS.md` — and produces exactly one plan (`plan.md`) and one checklist (`tasks.md`), both validated by the prompt linter directly; the duplicate RNA artifacts (`implementation_plan.md`, `task.md`) are no longer required for new features.

**Why this priority**: К-1/К-2 — double bookkeeping costs every future feature and risks drift; the constitution currently describes a process nobody runs.

**Independent Test**: Linter v2 unit/journey tests: plan stage passes on a spec-kit `plan.md` (and still passes on legacy `implementation_plan.md`); checklist stage passes on a completed `tasks.md` whose last task is the linter run (and still on legacy `task.md`).

**Acceptance Scenarios**:

1. **Given** `AGENTS.md`, **When** Route A and § COMMAND REGISTRY are read, **Then** the spec-kit chain (`/speckit-specify → plan → tasks → implement`) is the named Route A engine, `speckit-*` commands are registered, and `RNA-1` is marked as the legacy alias whose required sections now live inside spec-kit `plan.md`.
2. **Given** a feature directory containing `plan.md` but no `implementation_plan.md`, **When** `prompt_linter.py --stage plan` runs, **Then** it validates `plan.md` (required H2s: Summary, Technical Context, Constitution Check, Project Structure; English) and reports valid.
3. **Given** a feature directory containing only legacy artifacts (features 001/002), **When** any linter stage runs, **Then** behavior is unchanged (backward compatible — historical features still lint).
4. **Given** the linter's own test suites (`tests/test_prompt_linter.py`, `tests/test_journeys/test_prompt_linter_journey.py`), **When** the suite runs, **Then** both v2 and legacy paths are covered and green.

---

### User Story 3 - Approval Gates by Mechanism, Not Memory (Priority: P2)

A tasks author using `/speckit-tasks` gets a template that already contains mandatory HARD-STOP gate tasks at chunk boundaries, so `speckit-implement` cannot legally run past a user-approval point even if the plan author forgets to add one.

**Why this priority**: К-3 — the R-PROC-2 gate currently exists only as hand-written text; today's without-confirmation incident is this exact failure class.

**Independent Test**: `.specify/templates/tasks-template.md` contains the gate-task pattern and an executor instruction that HARD-STOP tasks terminate the run; grep-level check plus manual read.

**Acceptance Scenarios**:

1. **Given** the tasks template, **When** read, **Then** it defines a mandatory `HARD STOP` task type (report to Шэф in Russian, await approval, do not proceed) required at every chunk boundary of 3–5 steps, citing `R-PROC-2`.
2. **Given** `RULES.md` R-PROC-2 and R-PROC-4, **When** read, **Then** they name the spec-kit artifacts (`plan.md`, `tasks.md`) as the canonical targets, with legacy names noted as accepted-for-history.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Restore the lost rules verbatim-based from git history (`git show 8280d6f^:CONTEXT_PROMPT.md`, `git show 8280d6f^:PROJECT_LOGIC.md`): new `R-UI-12` (from CP-3.11), new `R-UI-13` (from CP-3.47), new `R-ARCH-9` (from PL-4.1), amend `R-PROC-2` (add CP-3.28.2 incremental principle). Each with Why, tier A, and Legacy anchors.
- **FR-002**: Fix `docs/knowledge/rule-map.md` per the disposition table in research.md: zero `index.md` targets remain; every imperative anchor targets an R-ID or is dispositioned; `CP-5.1` row becomes `retired (scope note obsolete — file split; see log)`.
- **FR-003**: Add `tests/fixtures/imperative_dispositions.txt` (small override file: only `descriptive`/`retired` exceptions) and `test_imperatives_map_to_rules` in `tests/test_governance.py` per the contract; TDD: test written and red before FR-001/FR-002 fixes.
- **FR-004**: The frozen inventory fixture `rules_inventory_baseline.txt` is NOT modified (it is a historical baseline); all corrections live in the dispositions override file and rule-map.
- **FR-005**: Upgrade `local_scripts/prompt_linter.py` to v2: plan stage prefers `plan.md` (H2s: Summary, Technical Context, Constitution Check, Project Structure; Cyrillic warning logic unchanged), falls back to `implementation_plan.md` (legacy H2s); checklist stage prefers `tasks.md` (all checkboxes `[x]`; last checkbox task contains "запуск линтера-чеклиста" or "run checklist-linter"), falls back to `task.md`; report stage unchanged (`walkthrough.md`, Russian).
- **FR-006**: Update the linter's unit and journey tests to cover both v2-preferred and legacy-fallback paths for plan and checklist stages; all existing test cases remain green (backward compatibility is a hard requirement).
- **FR-007**: Rewrite `AGENTS.md` Route A as the spec-kit chain (optional PA-1 for architectural features → specify → plan → tasks → implement), register `speckit-specify/plan/tasks/implement/clarify/analyze` in § COMMAND REGISTRY, mark `RNA-1` as legacy alias, and state that RNA-Blueprint's required content (Base DNA / Task RNA / CC / steps with rule-ID tags) lives inside spec-kit `plan.md` sections; define Route B ordering (PA-1 audits the idea BEFORE specify; `/speckit-clarify` refines requirements AFTER a spec exists).
- **FR-008**: Add the mandatory HARD-STOP gate-task pattern to `.specify/templates/tasks-template.md` (chunk boundary every 3–5 executable steps; gate task = report in Russian + await approval; executor may not proceed past an unchecked gate), citing R-PROC-2.
- **FR-009**: Amend `R-PROC-2` and `R-PROC-4` wording in `RULES.md` to name `plan.md`/`tasks.md` as canonical (legacy names accepted for historical features); update the docs-update skill's validation command list if it names linter targets.
- **FR-010**: `.specify/feature.json` points at this feature during work (fixes F-3 as a side effect); no bot source changes; full regression green; CHANGELOG 1.4.0 entry; GW-1 local commit at the end (no push).

### Key Entities

- **Disposition**: curated verdict for an imperative legacy anchor — `R-<DOMAIN>-<n>` (via rule-map), `descriptive` (heuristic over-capture), or `retired` (function died by design). Overrides file holds only non-R-ID cases.
- **Linter v2 contract**: stage → (preferred file, required structure) with legacy fallback.
- **Gate task**: a tasks.md checklist item that halts `speckit-implement` until Шэф approves.

## Success Criteria *(mandatory)*

- **SC-001**: `test_imperatives_map_to_rules` green; red on current tree first (TDD proof recorded); mutation check red-then-green.
- **SC-002**: Zero rule-map rows target `index.md`; zero imperative anchors target bundle files without a disposition.
- **SC-003**: All four rule restorations present in `RULES.md` with Legacy anchors; rule-map rows updated accordingly.
- **SC-004**: Linter v2 validates spec-kit artifacts AND legacy artifacts; its full test suite green; features 001/002 directories still pass their historical stages.
- **SC-005**: `AGENTS.md` registers the spec-kit commands and names it the Route A engine; tasks template contains the gate pattern.
- **SC-006**: Full regression green (expected ~112+ passed, 0 failed); no edits to unrelated tests.

## Assumptions

- Executor: **Claude Sonnet** end-to-end — research.md's disposition table and verbatim git-history sources remove all classification judgment (research D7-002 precedent).
- Two approval chunks: Chunk A = F-group (Phases 1–2), HARD STOP, Chunk B = К-group (Phases 3–4). This feature's own artifacts are dual-format (legacy `implementation_plan.md`/`task.md` present) because linter v2 lands mid-feature; from feature 004 on, only spec-kit artifacts are required.
- `.claude/skills/speckit-*` files are NOT edited (upstream-generated); gate enforcement lives in the local template + RULES, which speckit-implement consumes via tasks.md.
