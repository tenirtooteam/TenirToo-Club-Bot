# Baseline & Execution Log: 003-governance-hardening

## T001 — Dispositions fixture

Created `tests/fixtures/imperative_dispositions.txt` with 6 override rows (5 `descriptive`, 1 `retired`) exactly per research.md D2. `tests/fixtures/rules_inventory_baseline.txt` untouched (FR-004).

## T002–T003 — Retention test, red baseline (recorded)

Added `test_imperatives_map_to_rules` to `tests/test_governance.py` (+ `_rule_map_rows`/`_dispositions` helpers). Ran `.\venv\Scripts\python.exe -m pytest tests/test_governance.py::test_imperatives_map_to_rules -v` — **FAILED as expected**, naming exactly 18 anchors (the 24 D2 rows minus the 6 already-dispositioned in T001):

```
PL-2.4.1, PL-2.5.1, PL-4.1, PL-4.5.1, PL-4.6.2, PL-5.3.1,
CP-3.7, CP-3.11, CP-3.28.1, CP-3.28.2, CP-3.28.3, CP-3.28.5, CP-3.47,
CP-3.53.1, CP-3.53.2, CP-3.53.3, CP-3.60.1, CP-6.3
```

This confirms: (a) the map-hygiene mechanism works — every one of these targets a bundle file, not an R-ID; (b) the four genuinely lost rules (PL-4.1, CP-3.11, CP-3.28.2, CP-3.47) are present in this red list as required by quickstart.md §1; (c) the remaining 14 are map-repair-only (their content already exists in RULES.md, just mismapped). Full suite run at this point: 7 governance tests total, 1 new failure, rest green (confirms no regression from adding the test).

## T004 — Verbatim restore sources (from `git show 8280d6f^:...`)

**PL-4.1** (`PROJECT_LOGIC.md`):
> `[PL-4.1] Sequential 3-stage pipeline registered as \`outer_middleware\` on \`dp.message\` — order is fixed and must not be changed.`

**CP-3.11** (`CONTEXT_PROMPT.md`, item 10):
> `[CP-3.11] **STERILE UI ENFORCEMENT**: Every transition between independent FSM flows, disambiguation steps, or generation of new interactive elements MUST be preceded by \`await UIService.terminate_input(state, message)\`. Every FSM entry point (where text input is required) MUST use an isolated cancel keyboard (e.g., \`get_event_cancel_kb\`, \`get_admin_cancel_kb\`) to prevent bypasses via functional buttons. [PL-HI] For command-level handlers, use the \`@UIService.sterile_command\` decorator.`
> Rationale: The decorator centralizes redirect logic, PM error fallback, trigger cleanup, and `last_menu_id` tracking into a single declarative line. Bypassing the decorator and calling `sterile_redirect` manually is redundant and error-prone.

**CP-3.28.2** (`CONTEXT_PROMPT.md`, sub-item):
> `[CP-3.28.2] **Incremental Principle**: Do not rewrite the entire plan for every correction; update only the affected parts.`

**CP-3.47** (`CONTEXT_PROMPT.md`, item 47):
> `[CP-3.47] **ADMIN CREATION UX BRANCHING**: In workflows where an entity creation triggers an automatic audit notification (to admins), the creation handler MUST NOT immediately show the final entity card to the creator if they are an admin. Show a clean success message instead.`
> Rationale: Prevents UI clutter and notification fatigue for administrators who would otherwise receive both a state-update message and a new notification for the same action.

All four match research.md D6 verbatim — no interpretation needed for T005.

## T005 — Rules added to RULES.md

`R-ARCH-9` (after R-ARCH-8), `R-UI-12` and `R-UI-13` (after R-UI-11) added verbatim per research.md D6 draft text; `R-PROC-2` amended in place (Rule += incremental-updates sentence, Why extended, Legacy += CP-3.28.2). No renumbering, no ID reuse.

## T006 — Rule-map repair

Fixed 30 rows total: the 24 from research.md D2, plus 6 additional non-imperative anchors that were also falling back to `docs/knowledge/index.md` (PL-5.4.1→R-UI-6, PL-5.5.1→R-SEC-2, PL-6→R-ARCH-1, PL-6.13→descriptive, CP-6.1→R-CODE-4, CP-6.2→R-PROC-6) — verified each target's content actually covers the anchor's original text before mapping. **Zero rows now target `index.md`** (SC-002 met in full, not just for imperative anchors). Header counts updated: 295 anchors — 161 to R-IDs (was 138), 7 curated descriptive/retired, 127 to bundle files (was 157). Bundle atomicity: `docs/knowledge/log.md` entries appended for both the RULES.md additions and the rule-map repair.

## T007 — Suite green + mutation checks (Chunk A)

`pytest tests/test_governance.py tests/test_knowledge_bundle.py` → **12/12 passed**, including the new `test_imperatives_map_to_rules`.

Mutation checks:
1. Repoint `CP-3.11`'s rule-map row from `R-UI-12` back to a bundle file → **FAIL** (guard catches re-introduced loss) → restored → PASS.
2. Delete the `CP-5.1` disposition row → **FAIL**. Note: `CP-5.1` IS IMP-flagged in the frozen inventory (`This file governs code generation and bug-fixing only...`); it did not appear in the T003 red list only because its disposition was already created in T001, before the first red run — sequencing, not an error. Restored → PASS.

Both guards demonstrably fail-then-restore-green. Chunk A complete.

## T008 — Linter v2 tests, red baseline (Chunk B)

Added to `tests/test_prompt_linter.py`: `test_validate_plan_v2_structure_success`, `test_validate_plan_v2_structure_missing_sections`, `test_plan_v2_speckit_file`, `test_plan_legacy_fallback`, `test_plan_v2_wins_when_both_present`, `test_checklist_v2_tasks_file`, `test_checklist_legacy_fallback`, `test_checklist_v2_wins_when_both_present`, `test_find_plan_file_none_present` (9 new unit cases, 4 of them the contract-named ones). Added to `tests/test_journeys/test_prompt_linter_journey.py`: `test_journey_plan_v2_linter`, `test_journey_checklist_v2_linter` (2 new CLI cases).

Ran `pytest tests/test_prompt_linter.py tests/test_journeys/test_prompt_linter_journey.py -v` → **collection ERROR**: `ImportError: cannot import name 'find_plan_file' from 'local_scripts.prompt_linter'` — correct red-for-the-right-reason (v2 API does not exist yet). All 9 pre-existing unit tests and 3 pre-existing journey tests are unaffected by this collection error once T009 lands (verified next).

## T009 — Linter v2 implementation

Added `PLAN_LEGACY_REQUIRED_H2S`/`PLAN_V2_REQUIRED_H2S` constants, `find_plan_file(dir)`/`find_checklist_file(dir)` (prefer spec-kit file, fall back to legacy, `(None, None)` if neither exists), and gave `validate_plan` an optional `required_h2s` parameter defaulting to the legacy set (100% backward compatible signature — existing single-arg calls unchanged). `main()` now dispatches through the two finder functions instead of hardcoded filenames. `validate_checklist`/`validate_report` untouched (checklist structural rules are identical for `tasks.md`/`task.md`; report stage out of scope per contract).

## T010 — Suite green + live dual-path check

`pytest tests/test_prompt_linter.py tests/test_journeys/test_prompt_linter_journey.py -v` → **24/24 passed** (9 pre-existing + 9 new unit, 3 pre-existing + 2 new journey — zero regressions). Live CLI checks: `--dir specs/002-governance-consolidation --stage plan` → "Plan is valid." (legacy `implementation_plan.md` path); `--dir specs/003-governance-hardening --stage plan` → "Plan is valid." (v2 `plan.md` path, since this feature's `plan.md` already has the required v2 H2s). Both confirm FR-005/FR-006/SC-004.

## T011 — AGENTS.md canonization

Route A now names the spec-kit chain as the engine (`RNA-1` marked legacy alias); § COMMAND REGISTRY gained 6 `speckit-*` rows; § RNA-BLUEPRINT retitled § PLAN CONTENT with an explicit mapping from RNA-Blueprint sections to spec-kit artifact headings; Route B gained an ordering note (PA-1 before specify, clarify after a spec exists).

## T012 — R-PROC-2/R-PROC-4 + docs-update skill

`R-PROC-2`: rule text now names `plan.md` as canonical (`implementation_plan.md` accepted for historical features) and requires an explicit HARD-STOP gate task in `tasks.md`/`task.md` at chunk boundaries; Why extended. `R-PROC-4`: rule text now states which file each stage prefers/falls back to. `docs-update/SKILL.md` Validation section gained one sentence naming both linter target sets. Governance suite re-run: 7/7 green (no duplicate-text regression from the RULES.md prose changes).

## T013 — Tasks-template gate pattern

Added an "## Approval Gates (R-PROC-2 — MANDATORY)" section to `.specify/templates/tasks-template.md` defining the gate-task format and requiring `/speckit-tasks` to insert one at every chunk boundary. Inserted concrete `HARD STOP` sample tasks after Phase 2 (Foundational) and after each of the three sample user-story checkpoints, so the pattern is visible in the template output, not just described in prose.

## T014 — Full regression, mutation check 3, manual verification

- Full regression: **122 passed, 1 skipped, 0 failed** (up from 111 at end of Chunk A — +11 from the 9 new linter unit tests + 2 new journey tests).
- Mutation check 3: a v2 plan fixture missing the `## Constitution Check` H2 → plan stage **FAIL**; restored → PASS.
- Manual quickstart §4 checks: AGENTS.md names `speckit-implement`/`speckit-specify` (6 hits); tasks-template contains 5 `HARD STOP` occurrences and 6 `R-PROC-2` citations; RULES.md contains all three new rule IDs and the word "incremental" (2 hits: R-PROC-2 rule text + AGENTS.md § PLAN CONTENT cross-reference); rule-map.md has **0** remaining `index.md` fallback rows.

All SC-001..SC-006 targets met. Chunk B complete.
