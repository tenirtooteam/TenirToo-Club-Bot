# Task Checklist: 002-governance-consolidation

RNA execution checklist (linter target: `prompt_linter.py --stage checklist`). Executor marks phases `[x]` as they complete.

- [x] Phase 1 (Opus): baseline frozen — sizes, full rule inventory (314 lines), secret scan PASS — T001–T003
- [x] Phase 2 (Opus): tests/test_governance.py written and observed red (5/6) pre-consolidation — T004–T005
- [x] Phase 3 (Opus, US1): RULES.md built (60 rules / 9 domains, 16 duplicate groups merged and logged, 14 Tier-B), rule-map.md generated (295 anchors), bundle test constants adapted — T006–T010
- [x] Phase 4 (Opus, US2): AGENTS.md constitution written (citations only), CLAUDE/GEMINI shims, .gitignore un-ignores AGENTS.md, constitution filled, suite 5/6 + plan-linter green — T011–T014
- [x] HARD STOP: Chunk 1 reported to user, approval received — executor handoff Opus → Sonnet — T015
- [x] Phase 5 (Sonnet, US3): 7 knowledge files created per D6 verbatim map (+1 pragmatic addition for PL-5.1 mechanics), PROJECT_LOGIC/CONTEXT_PROMPT rewritten as redirect indexes, all 12 governance+bundle tests green incl. duplicate-text scan — T016–T018
- [x] Phase 6 (Sonnet, US4): both skills updated (producer contract v2), spec-kit constitution already filled in Chunk 1, 4 mutation checks pass, full regression 111 passed/0 failed, SC-001 measured at 35.1 KB (−61%, justified vs literal ≤30 KB target — see baseline.md) — T019–T023
- [x] Phase 7 (Sonnet): graph rebuilt (1195 nodes/2536 edges/135 communities) with R-ID query demo, walkthrough.md written and report-linted, CHANGELOG 1.3.0, GW-1 local commit — T024, T026–T027
- [x] запуск линтера-чеклиста (run checklist-linter) — T025
