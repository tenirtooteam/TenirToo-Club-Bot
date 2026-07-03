# Implementation Plan: Governance Hardening (Rule Retention Repair + Route/Spec-Kit Unification)

**Branch**: `003-governance-hardening` | **Date**: 2026-07-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-governance-hardening/spec.md`

## Summary

Close both audit groups of 2026-07-03. **F-group**: restore four rules lost/softened during the 002 consolidation (verbatim sources in git history), repair ~15 wrong rule-map rows, and add a deterministic content-level retention test so this failure class is caught by CI forever. **К-group**: canonize spec-kit as the Route A engine in `AGENTS.md`, upgrade `prompt_linter.py` to validate spec-kit artifacts directly (killing the plan/tasks duplication), and bake HARD-STOP approval gates into the tasks template so R-PROC-2 is enforced by mechanism, not memory. All classification judgment is pre-resolved in research.md's disposition table — the executor performs zero classification.

## Technical Context

**Language/Version**: Python 3.11 (linter + tests); markdown elsewhere

**Primary Dependencies**: pytest (existing); no new packages

**Storage**: Filesystem; git history as the verbatim source for restored rule texts (`git show 8280d6f^:CONTEXT_PROMPT.md`, `git show 8280d6f^:PROJECT_LOGIC.md`)

**Testing**: `.\venv\Scripts\python.exe -m pytest`; extended `tests/test_governance.py`; updated `tests/test_prompt_linter.py` + `tests/test_journeys/test_prompt_linter_journey.py`

**Target Platform**: Windows 10, PowerShell syntax

**Project Type**: Governance/tooling refactor (rules, map, linter, template, constitution)

**Performance Goals**: n/a

**Constraints**: Frozen fixture `rules_inventory_baseline.txt` immutable (FR-004); linter backward compatible with features 001/002 artifacts (FR-005/FR-006); `.claude/skills/speckit-*` not edited; no bot source changes; no `git push`; rule-ID permanence (new IDs only, no renumbering)

**Scale/Scope**: RULES.md +3 rules +1 amendment; rule-map ~15 row fixes + 1 retired row; 1 new test + 1 small fixture; linter v2 (2 stages × 2 paths) + its 2 test files; AGENTS.md 3 sections; 1 template; R-PROC-2/4 wording; CHANGELOG 1.4.0

**Executor**: **Claude Sonnet end-to-end**, two chunks with a HARD STOP between (Chunk A = F-group, Chunk B = К-group). Judgment eliminated by research.md D2 disposition table + verbatim git sources.

## Constitution Check

- [x] TDD-first: `test_imperatives_map_to_rules` + linter v2 test cases written and red before their fixes (R-PROC-3 pattern).
- [x] Chunked execution with HARD STOP + user approval between chunks (R-PROC-2).
- [x] Rule-ID permanence honored: R-UI-12, R-UI-13, R-ARCH-9 are new; R-PROC-2 amended in place (statement extended, ID kept).
- [x] Dual-format artifacts for THIS feature only (linter v2 lands mid-feature); prompt-linter gates run against `specs/003-governance-hardening`.

**Post-design re-check**: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/003-governance-hardening/
├── spec.md, plan.md, research.md (disposition table = executor's law), quickstart.md
├── contracts/hardening-contract.md
├── implementation_plan.md   # legacy linter target (this feature is dual-format)
├── task.md                  # legacy checklist target
├── tasks.md                 # executable tasks (becomes canonical after linter v2)
├── baseline.md              # execution log (created by executor)
└── checklists/requirements.md
```

### Source Code (repository root)

```text
RULES.md                                  # [MODIFY] +R-UI-12, +R-UI-13, +R-ARCH-9; amend R-PROC-2 (+incremental), R-PROC-4 (artifact names)
docs/knowledge/rule-map.md                # [MODIFY] ~15 rows per disposition table; CP-5.1 -> retired
docs/knowledge/log.md                     # [MODIFY] append entries (bundle atomicity)
tests/fixtures/imperative_dispositions.txt # [NEW] override file (descriptive/retired exceptions only)
tests/test_governance.py                  # [MODIFY] +test_imperatives_map_to_rules
local_scripts/prompt_linter.py            # [MODIFY] v2: plan.md/tasks.md preferred, legacy fallback
tests/test_prompt_linter.py               # [MODIFY] +v2 cases, keep legacy cases
tests/test_journeys/test_prompt_linter_journey.py  # [MODIFY] +v2 CLI cases
AGENTS.md                                 # [MODIFY] Route A = spec-kit chain; § COMMAND REGISTRY += speckit-*; RNA-1 = legacy alias; Route B ordering
.specify/templates/tasks-template.md      # [MODIFY] mandatory HARD-STOP gate-task pattern
.agents/plugins/tenirtoo-plugin/skills/docs-update/SKILL.md  # [MODIFY] validation command mentions both linter targets (one line)
CHANGELOG.md                              # [MODIFY] 1.4.0
```

**Structure Decision**: No new top-level files except the small dispositions fixture; everything else is in-place modification of the governance layer built in 001/002.

## Complexity Tracking

No violations — table not required.
