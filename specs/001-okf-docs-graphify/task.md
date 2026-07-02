# Task Checklist: 001-okf-docs-graphify

RNA execution checklist (linter target: `prompt_linter.py --stage checklist`). Mirror of tasks.md phases; the executor marks items `[x]` as phases complete.

- [x] Phase 1: Baseline captured (sizes, PL-anchor inventory, imperative inventory, PyYAML check) — T001–T003
- [x] Phase 2: TDD validation suite tests/test_knowledge_bundle.py written and observed failing pre-migration — T004–T005
- [x] Phase 3 (US1): Bundle created (db-schema.md, module-registry.md, index.md, log.md), PROJECT_LOGIC.md stubs in place, bundle tests green — T006–T010
- [x] Phase 4 (US2): CONTEXT_PROMPT.md repaired, deduplicated, CP-2 compressed, design-system extracted, all six tests green — T011–T015
- [x] Phase 5 (US3): GEMINI.md + docs-update SKILL.md + .gitignore synced, full regression green, mutation checks pass — T016–T020
- [x] HARD STOP: Chunk 1 reported to user, approval received before Phase 6 (decision: keep −23%, rationales stay in core; proceed to graphify + finalize)
- [x] Phase 6 (US4): graphify graph built (1002 nodes / 2309 edges / 66 communities), artifacts verified & git-ignored, architecture query answered — T021–T023
- [x] Phase 7: SC-001 (−23%, justified partial) / SC-002 (all imperatives retained) measured, walkthrough.md written and linted (report stage), CHANGELOG.md updated, GW-1 local commit — T024, T026–T028
- [x] запуск линтера-чеклиста (run checklist-linter) — T025
