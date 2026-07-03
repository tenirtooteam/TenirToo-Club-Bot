# Goal Description: Governance Hardening - Rule Retention Repair (F-1..F-4) + Route/Spec-Kit Unification (K-1..K-3)

RNA view of [plan.md](plan.md) (this feature is dual-format: linter v2 lands mid-feature). Executor: Claude Sonnet end-to-end via `speckit-implement` over `tasks.md`.

## Base DNA

- Windows 10, PowerShell; pytest via `.\venv\Scripts\python.exe -m pytest`; no new packages; no `git push`; no bot source changes.

## Task RNA

- Logic: (F) restore four rules lost/softened in the 002 consolidation from verbatim git history, repair ~15 wrong rule-map rows, add a deterministic retention test (imperative anchor -> R-ID or curated disposition) so the loss class is CI-guarded forever; (K) register spec-kit as the canonical Route A engine in AGENTS.md, upgrade prompt_linter to validate spec-kit artifacts (plan.md/tasks.md) with legacy fallback, and bake HARD-STOP gate tasks into the tasks template so R-PROC-2 approval gates are mechanical.
- Risks: (1) executor judgment on anchor classification - eliminated: research.md D2 table pre-resolves all 24 cases, D6 pre-drafts all rule texts; uncovered case = STOP and report; (2) linter regression breaking historical features - mitigated by mandatory legacy fallback + pinned existing tests + live check against specs/002; (3) frozen fixture corruption - forbidden (FR-004), overrides live in a separate small file; (4) rule-ID churn - new IDs only (R-ARCH-9, R-UI-12, R-UI-13), R-PROC-2 amended in place.
- Edge cases: both plan.md and implementation_plan.md present (this very feature) - v2 prefers plan.md by contract; anchors mapping to R-IDs that do not exist - test fails by design; speckit skill files are upstream-generated and MUST NOT be edited (gates live in the local template).

## Contextual Constraints (CC)

- [CC-1] Zero rule loss, content-level guarantee [audit F-1/F-4; R-CODE-7 traceability].
- [CC-2] Rule-map honesty: no fallback junk targets [audit F-2].
- [CC-3] Single process, single artifact set; backward compatibility for 001/002 [K-1/K-2].
- [CC-4] Approval gates by mechanism [K-3; R-PROC-2].
- [CC-5] TDD-first for both the retention test and linter v2 [R-PROC-3 pattern].
- [CC-6] Frozen baseline immutable [FR-004].

## User Review Required

- Approval of this plan before execution.
- Executor confirmation: Sonnet end-to-end (judgment pre-resolved in research.md D2/D6).
- HARD STOP after Chunk A (F-group) - approval required before Chunk B (K-group).
- Awareness: from feature 004 onward only spec-kit artifacts (plan.md/tasks.md/walkthrough.md) are required; implementation_plan.md/task.md become historical.

## Open Questions

- None. All 24 disposition verdicts and all four rule texts are fixed in research.md; linter v2 contract is fully specified in contracts/hardening-contract.md.

## Proposed Changes

### F-group (Chunk A)
- [NEW] `tests/fixtures/imperative_dispositions.txt` - curated overrides (5 descriptive + 1 retired).
- [MODIFY] `tests/test_governance.py` - add `test_imperatives_map_to_rules` (+ map-hygiene sub-check).
- [MODIFY] `RULES.md` - add R-ARCH-9, R-UI-12, R-UI-13; amend R-PROC-2 (incremental principle, Legacy += CP-3.28.2).
- [MODIFY] `docs/knowledge/rule-map.md` - 24 D2 rows + all residual index.md rows retargeted; CP-5.1 retired.
- [MODIFY] `docs/knowledge/log.md` - atomicity entry.

### K-group (Chunk B)
- [MODIFY] `local_scripts/prompt_linter.py` - v2 per research D4 (plan.md/tasks.md preferred, legacy fallback, report stage unchanged).
- [MODIFY] `tests/test_prompt_linter.py`, `tests/test_journeys/test_prompt_linter_journey.py` - four new unit cases + v2 CLI cases; existing cases untouched.
- [MODIFY] `AGENTS.md` - Route A = spec-kit chain; command registry += speckit-*; RNA-1 legacy alias; § PLAN CONTENT retitle; Route B ordering.
- [MODIFY] `RULES.md` - R-PROC-2/R-PROC-4 artifact-name wording.
- [MODIFY] `.specify/templates/tasks-template.md` - mandatory HARD-STOP gate-task pattern citing R-PROC-2.
- [MODIFY] `.agents/plugins/tenirtoo-plugin/skills/docs-update/SKILL.md` - one-line validation-targets update.
- [MODIFY] `CHANGELOG.md` - 1.4.0.

## Execution Steps

1. **[TEST][CC-5][CC-6]** T001-T003: dispositions fixture; `test_imperatives_map_to_rules`; observe RED naming PL-4.1/CP-3.11/CP-3.28.2/CP-3.47 minimum; record in baseline.md.
2. **[CC-1]** T004-T005: extract verbatim texts from `git show 8280d6f^:...`; add the three rules + R-PROC-2 amendment exactly per research D6.
3. **[CC-2]** T006-T007: repair rule-map per D2 + retarget all index.md rows; suites green; mutation checks 1-2. **HARD STOP - report to Шэф, await approval.**
4. **[TEST][CC-3][CC-5]** T008-T010: linter v2 tests red; implement v2; tests green; live backward-compatibility check on specs/002 and v2 check on specs/003.
5. **[CC-3][CC-4]** T011-T013: AGENTS.md canonization; R-PROC-2/4 wording; docs-update skill line; tasks-template gate pattern.
6. **[CC-4]** T014-T017: full regression; mutation check 3; quickstart manual greps; checklist/report linter gates; CHANGELOG 1.4.0; GW-1 local commit.

Chunking: steps 1-3 = Chunk A, steps 4-6 = Chunk B, boundary = HARD STOP.

## Verification Plan

- **New/changed tests**: `test_imperatives_map_to_rules` (tests/test_governance.py); `test_plan_v2_speckit_file`, `test_plan_legacy_fallback`, `test_checklist_v2_tasks_file`, `test_checklist_legacy_fallback` (tests/test_prompt_linter.py) + v2 CLI journey cases. TDD reproducers: retention test RED on current tree (step 1); linter v2 cases RED before implementation (step 4) - both recorded in baseline.md.
- **Commands**: quickstart.md sections 1-6 (retention gate, linter suites + live dual-path checks, full regression, manual greps, mutation checks, this feature's own gates).
- **Manual checks**: read the four restored rule entries against the git-history originals; spot-resolve two repaired map rows end-to-end; read the gate pattern in tasks-template.
