# Tasks: Governance Consolidation (Constitution + Rulebook + Dissolution)

**Input**: Design documents from `specs/002-governance-consolidation/` (plan.md, research.md D1–D8, data-model.md, contracts/governance-contract.md, quickstart.md)

**Executors**: **Chunk 1 (Phases 1–4) = Claude Opus**; **Chunk 2 (Phases 5–7) = Claude Sonnet** — both via `speckit-implement`. PowerShell from repo root; python `.\venv\Scripts\python.exe`; pytest via `python -m pytest`. No `git push`.

**HARD STOP** after Phase 4: report to the user (Шэф), await approval; approval = executor handoff Opus → Sonnet.

**TDD gate**: T004–T005 MUST complete before any governance file is created/edited (T006+).

## Phase 1: Setup — frozen baseline (Opus)

- [x] T001 Record baseline sizes (PROJECT_LOGIC.md, CONTEXT_PROMPT.md, GEMINI.md, AGENTS.md, docs/knowledge/index.md; current pre-read total 69.5 KB; SC-001 target ≤30 KB) into specs/002-governance-consolidation/baseline.md (create file)
- [x] T002 Extract EVERY normative statement (imperative sentences: MUST/prohibited/forbidden/never/strictly/Do not + rule-shaped entries) with its anchor from GEMINI.md, PROJECT_LOGIC.md, CONTEXT_PROMPT.md, AGENTS.md into tests/fixtures/rules_inventory_baseline.txt (format per data-model.md Frozen Rule Inventory); record count in baseline.md — this is the zero-loss reference (SC-002/SC-003)
- [x] T003 [P] Secret scan: verify GEMINI.md and AGENTS.md content contains no tokens/credentials/IDs unsafe for public tracking; record verdict in baseline.md (spec Assumption 1). If anything sensitive is found — STOP and report before any tracking change

## Phase 2: Foundational — TDD governance suite (Opus)

- [x] T004 Write tests/test_governance.py implementing exactly the six tests from contracts/governance-contract.md (`test_rule_ids_unique`, `test_no_duplicate_rule_text` with ≥20-word shingle scan over AGENTS.md/RULES.md/PROJECT_LOGIC.md/CONTEXT_PROMPT.md, `test_rule_map_complete` against the frozen inventory, `test_tier_b_enforcement_exists`, `test_shims_are_pure`, `test_constitution_filled`); reuse the regex front-matter parser pattern from tests/test_knowledge_bundle.py; keep ruff clean
- [x] T005 Run `.\venv\Scripts\python.exe -m pytest tests/test_governance.py -v` — MUST fail (RULES.md and rule-map.md absent); record the exact red pattern in baseline.md

**Checkpoint**: suite red for the right reasons; nothing edited yet.

## Phase 3: User Story 1 — Unified Rulebook (P1, Opus) 🎯 core risk

- [x] T006 [US1] Build RULES.md: absorb every statement from tests/fixtures/rules_inventory_baseline.txt into `R-<DOMAIN>-<n>` entries (schema per data-model.md; domains ARCH/DB/UI/FSM/CODE/TEST/PROC/SEC); merge the 11 duplicate groups from spec US1-AS2 per research D4 (most restrictive wins); append every merge decision to baseline.md
- [x] T007 [US1] Assign tiers: mark Tier B (one-liner + `Enforced by`) for every rule covered by semgrep-rules.yaml (5), .importlinter, tests/test_services/test_import_lint.py, AST/ruff gates, prompt_linter stages, tests/test_knowledge_bundle.py, FK runtime fuse — target ≥15 demotions (SC-004); leave judgment rules Tier A with full text + Why
- [x] T008 [US1] Generate docs/knowledge/rule-map.md from RULES.md `Legacy:` fields + research D6 descriptive destinations (every PL-x.y/CP-x.y/GEMINI-section anchor gets a row); add index.md + log.md entries for rule-map.md
- [x] T009 [US1] Adapt tests/test_knowledge_bundle.py constants ONLY (anchor-resolution base now includes docs/knowledge/rule-map.md; document the diff in baseline.md per FR-011)
- [x] T010 [US1] Run `.\venv\Scripts\python.exe -m pytest tests/test_governance.py tests/test_knowledge_bundle.py -v` — `test_rule_ids_unique`, `test_rule_map_complete`, `test_tier_b_enforcement_exists` and the bundle suite green (`test_no_duplicate_rule_text` may still be red until Phase 4/5 removes source duplicates — record state)

## Phase 4: User Story 2 — Versioned Constitution (P1, Opus) — END OF CHUNK 1

- [x] T011 [US2] Rewrite AGENTS.md as the constitution (sections per data-model.md: Identity & Brief [from PL-1/CP-1], Onboarding & pre-read set, Routes A–D, Command Registry, RNA-Blueprint, Git Protocol GW-1, Response Protocol [from CP-6/GEMINI § RESPONSE RULES], Subagents [old AGENTS.md content, summarized], File Registry, Content Ownership) — citing R-IDs, zero full rule texts
- [x] T012 [US2] Write shims: CLAUDE.md → `@AGENTS.md`; GEMINI.md → 2-line pointer to AGENTS.md (kept for Gemini-CLI); both stay git-ignored
- [x] T013 [US2] Update .gitignore: remove `AGENTS.md` from the ignore list (RULES.md is not ignored by any pattern — verify); `git ls-files` / `git check-ignore` checks from quickstart section 4
- [x] T014 [US2] Run full `.\venv\Scripts\python.exe -m pytest` + `local_scripts/prompt_linter.py --dir specs/002-governance-consolidation --stage plan`; update task.md phase marks
- [x] T015 **HARD STOP**: report Chunk 1 to the user in Russian (rule count, merges, tier split, sizes so far) and AWAIT APPROVAL — handoff to Sonnet

## Phase 5: User Story 3 — Knowledge Dissolution (P2, Sonnet)

- [x] T016 [US3] Create docs/knowledge/architecture.md, middleware.md, fsm-protocol.md, db-patterns.md, constants.md, testing.md, features-overview.md — verbatim moves per research D6 map, front matter per feature-001 schema, index.md + log.md atomicity (contract producer rule 2)
- [x] T017 [US3] Rewrite PROJECT_LOGIC.md and CONTEXT_PROMPT.md as ≤15-line redirect indexes (data-model.md Redirect Index schema); they remain tracked
- [x] T018 [US3] Run `.\venv\Scripts\python.exe -m pytest tests/test_governance.py tests/test_knowledge_bundle.py -v` — ALL green including `test_no_duplicate_rule_text` (sources of duplication are gone)

## Phase 6: User Story 4 — Tooling Sync (P2, Sonnet)

- [x] T019 [US4] Update .agents/plugins/tenirtoo-plugin/skills/docs-update/SKILL.md: producer contract v2 (rules → RULES.md, description → bundle, process → AGENTS.md; CMD targets updated; ID permanence rule)
- [x] T020 [P] [US4] Update .agents/plugins/tenirtoo-plugin/skills/proposal-analysis/SKILL.md: Project Mode ground truth = RULES.md + docs/knowledge/ (replaces PROJECT_LOGIC.md references)
- [x] T021 [P] [US4] Fill .specify/memory/constitution.md from RULES.md top principles (cite R-IDs; no placeholders — `test_constitution_filled` green)
- [x] T022 [US4] Execute the four mutation checks from quickstart.md (duplicate text / ID collision / deleted map row / imperative in shim) — each must fail the suite, restore, suite green; record in baseline.md
- [x] T023 [US4] Full regression `.\venv\Scripts\python.exe -m pytest` green; measure SC-001 pre-read (quickstart section 3, ≤30 KB) and zero-loss retention spot-checks (section 5); record in baseline.md

## Phase 7: Finalization (Sonnet)

- [x] T024 Rebuild knowledge graph: `/graphify C:\TenirTooClub_Bot --update`; verify GRAPH_REPORT.md regenerated; demo query resolving an R-ID (record in walkthrough)
- [x] T025 Complete specs/002-governance-consolidation/task.md and run `--stage checklist` linter — "Checklist is valid."
- [x] T026 Write walkthrough.md in Russian (sections: Changes made / What was tested / Validation results; include rule counts, merge log summary, SC table) and run `--stage report` linter — "Report is valid."
- [x] T027 CHANGELOG.md entry (CMD-4 style, version 1.3.0) + GW-1 local commit (no push)

## Dependencies

Phase 1 → 2 → 3 → 4 → HARD STOP → 5 → 6 → 7 (strict). Within phases: T003 [P]; T020/T021 [P] after T019 starts. T009 depends on T008; T013 after T011/T012.

## Implementation Strategy

MVP = Phases 1–4 (Chunk 1): even stopping there yields the tracked rulebook + constitution + map with tests — the audit's two critical findings (F1, F2) resolved. Chunk 2 completes F3/F5/F6 and the size goal. Executor handoff is safe because Chunk 2 contains zero classification judgment: every move's destination is named in research D6 and validated by the already-green governance suite.
