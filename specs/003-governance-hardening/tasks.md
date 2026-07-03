# Tasks: Governance Hardening (Rule Retention Repair + Route/Spec-Kit Unification)

**Input**: Design documents from `specs/003-governance-hardening/` (plan.md, research.md D1–D7 — **D2 disposition table and D6 rule drafts are binding law**, contracts/hardening-contract.md, quickstart.md)

**Executor**: **Claude Sonnet end-to-end** via `speckit-implement`. PowerShell from repo root; pytest via `.\venv\Scripts\python.exe -m pytest`. No `git push`. Zero classification judgment: every disposition and rule text is pre-resolved in research.md.

**HARD STOP** after Phase 2 (end of Chunk A): report to the user (Шэф) in Russian, await approval before Chunk B.

**TDD gate**: T002–T003 (red retention test) before any F-fix (T004+); T008 (red linter v2 tests) before T009.

## Phase 1: Foundational — retention test red (Chunk A, F-group)

- [x] T001 Create tests/fixtures/imperative_dispositions.txt with EXACTLY the override rows from research.md D2 (verdicts `descriptive`: PL-1.2, PL-3.5.4, PL-4.7.1, CP-2.17, CP-3.42; verdict `retired`: CP-5.1) in the contract format `<anchor><TAB><verdict><TAB><justification>`; do NOT touch tests/fixtures/rules_inventory_baseline.txt (FR-004)
- [x] T002 Add `test_imperatives_map_to_rules` to tests/test_governance.py per contracts/hardening-contract.md: for each IMP-flagged anchor in the frozen inventory, resolve via docs/knowledge/rule-map.md → target must be an R-ID defined in RULES.md, OR the anchor must appear in the dispositions override file; include the map-hygiene sub-check (zero rows targeting `docs/knowledge/index.md`); keep ruff clean
- [x] T003 Run `.\venv\Scripts\python.exe -m pytest tests/test_governance.py -v` — new test MUST be RED, naming at minimum PL-4.1, CP-3.11, CP-3.28.2, CP-3.47 (plus the anchors whose map rows point at index.md); record the exact red list in specs/003-governance-hardening/baseline.md (create it)

## Phase 2: User Story 1 — restore rules & fix map (Chunk A, F-group) 🎯 — END OF CHUNK A

- [x] T004 [US1] Extract verbatim source texts: `git show 8280d6f^:CONTEXT_PROMPT.md` (sections CP-3.11, CP-3.28.2, CP-3.47) and `git show 8280d6f^:PROJECT_LOGIC.md` (PL-4.1); paste the four originals into baseline.md as the restore record
- [x] T005 [US1] Add to RULES.md exactly per research.md D6: `R-ARCH-9` (after R-ARCH-8), `R-UI-12` and `R-UI-13` (after R-UI-11), and append the incremental-updates sentence + `CP-3.28.2` Legacy anchor to `R-PROC-2`; entry schema identical to existing rules (Rule/Why/Legacy)
- [x] T006 [US1] Fix docs/knowledge/rule-map.md per the D2 table (24 rows) AND retarget every remaining `docs/knowledge/index.md` row (CP-6→R-PROC-8, CP-6.1→R-CODE-4, CP-6.2→R-PROC-6, residual PL sub-anchors → parent rule's R-ID per RULES.md Legacy fields); CP-5.1 → `retired (scope note obsolete — see log.md)`; append a log.md entry (bundle atomicity)
- [x] T007 [US1] Run `.\venv\Scripts\python.exe -m pytest tests/test_governance.py tests/test_knowledge_bundle.py -v` — ALL green; run mutation checks 1–2 from contracts (imperative anchor→bundle row; deleted override row) — each red-then-restored-green; record in baseline.md. **HARD STOP: report Chunk A to Шэф in Russian (restored rules, map-row count fixed, test state) and AWAIT APPROVAL**

## Phase 3: User Story 2 — linter v2 + constitution (Chunk B, К-group)

- [x] T008 [US2] Add red tests first: `test_plan_v2_speckit_file`, `test_plan_legacy_fallback`, `test_checklist_v2_tasks_file`, `test_checklist_legacy_fallback` to tests/test_prompt_linter.py + one v2 CLI case per stage to tests/test_journeys/test_prompt_linter_journey.py (fixtures per contracts § Linter v2); run — new cases RED, existing cases GREEN; record pattern in baseline.md
- [x] T009 [US2] Implement linter v2 in local_scripts/prompt_linter.py per research.md D4: plan stage prefers `plan.md` (H2s: Summary, Technical Context, Constitution Check, Project Structure), falls back to `implementation_plan.md` (legacy H2s); checklist stage prefers `tasks.md`, falls back to `task.md` (same checkbox rules; last-task phrase check unchanged); report stage untouched
- [x] T010 [US2] Run `.\venv\Scripts\python.exe -m pytest tests/test_prompt_linter.py tests/test_journeys/test_prompt_linter_journey.py -v` — all green; live checks: `--dir specs/002-governance-consolidation --stage plan` (legacy path valid) and `--dir specs/003-governance-hardening --stage plan` (v2 path valid)
- [x] T011 [US2] Update AGENTS.md per research.md D5: Route A text = spec-kit chain with linter gates per stage; § COMMAND REGISTRY += `speckit-specify/clarify/plan/tasks/implement/analyze` rows; `RNA-1` row → "legacy alias — RNA content lives in plan.md sections"; § RNA-BLUEPRINT retitled "§ PLAN CONTENT (RNA-Blueprint inside plan.md)" with the section mapping; Route B ordering note (PA-1 before specify, clarify after)
- [x] T012 [US2] Amend RULES.md R-PROC-2 and R-PROC-4 wording to name `plan.md`/`tasks.md` as canonical artifacts (legacy names accepted for historical features); one-line update in .agents/plugins/tenirtoo-plugin/skills/docs-update/SKILL.md validation section naming both linter target sets

## Phase 4: User Story 3 + Finalization (Chunk B)

- [x] T013 [US3] Add the mandatory HARD-STOP gate-task pattern to .specify/templates/tasks-template.md per research.md D5 (gate every 3–5 executable tasks; gate text: report to Шэф in Russian + await approval; executor MUST NOT proceed past an unchecked gate; cite R-PROC-2)
- [x] T014 Run full `.\venv\Scripts\python.exe -m pytest` — 0 failed; run mutation check 3 (drop Constitution Check H2 from a v2 plan fixture → plan stage fails → restore); run quickstart §4 manual greps — all pass; record in baseline.md
- [x] T015 Complete specs/003-governance-hardening/task.md and tasks.md checkboxes; run `--stage checklist` (validates tasks.md via v2) and write walkthrough.md in Russian (sections: Changes made / What was tested / Validation results; include restored-rule list and linter v2 summary); run `--stage report` — both "valid"
- [x] T016 CHANGELOG.md entry 1.4.0 (Added: retention test + gate template; Changed: rules restored, rule-map repaired, linter v2, Route A = spec-kit chain) + GW-1 local commit (no push)
- [x] T017 запуск линтера-чеклиста (run checklist-linter) — final `--stage checklist` confirmation after all boxes are marked

## Dependencies

Phase 1 → 2 → HARD STOP → 3 → 4 (strict). T002 before T004+; T008 before T009; T006 depends on T005 (R-IDs must exist before map rows point at them).

## Implementation Strategy

Chunk A alone already delivers the audit's F-group value (no lost rules, honest map, permanent CI guard). Chunk B removes the process duplication and makes approval gates mechanical. Every judgment call is pre-resolved in research.md D2/D6 — if the executor encounters a case not covered there, STOP and report instead of deciding.
