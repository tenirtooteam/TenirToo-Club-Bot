# Tasks: Two-Tier Documentation Architecture (Normative Core + OKF Reference Bundle) with Graphify Integration

**Input**: Design documents from `specs/001-okf-docs-graphify/` (plan.md, spec.md, research.md, data-model.md, contracts/okf-bundle-contract.md, quickstart.md)

**Executor**: Claude Opus via `speckit-implement`. All commands in PowerShell from repo root; python is `.\venv\Scripts\python.exe`, pytest is `.\venv\Scripts\pytest`. No `git push`.

**GEMINI.md chunking**: Phases 1–5 form Approval Chunk 1 (execution steps 1–4 of implementation_plan.md). STOP after Phase 5, report to the user (Шэф), await approval. Phases 6–7 form Approval Chunk 2 (steps 5–6).

**TDD gate**: T004–T005 (failing validation suite) MUST complete before any extraction task (T006+).

## Phase 1: Setup (baseline capture)

**Purpose**: Freeze the pre-migration ground truth that later tasks and tests compare against.

- [x] T001 Record baseline sizes of PROJECT_LOGIC.md and CONTEXT_PROMPT.md (`(Get-Item <file>).Length`) into specs/001-okf-docs-graphify/baseline.md (create file; note 89.8 KB combined baseline and 53.9 KB target from quickstart.md section 3)
- [x] T002 [P] Extract the complete pre-migration `[PL-x.y]` anchor inventory from PROJECT_LOGIC.md (regex `\[PL-\d+(\.\d+)*\]` over headings and list items) and append it to specs/001-okf-docs-graphify/baseline.md; also extract the imperative-statement inventory (lines containing MUST / prohibited / forbidden / never / strictly) for the SC-002 retention diff
- [x] T003 [P] Check PyYAML availability: `.\venv\Scripts\python.exe -c "import yaml; print(yaml.__version__)"`; record result in baseline.md (on failure the test module uses its regex fallback parser per research.md D6 — do NOT install new packages)

## Phase 2: Foundational (TDD validation suite — BLOCKS all user stories)

**Purpose**: The contract enforcement exists and fails before the bundle exists (CC-5, quickstart section 1).

- [x] T004 Write tests/test_knowledge_bundle.py implementing exactly the six contract tests from contracts/okf-bundle-contract.md: `test_frontmatter_required_fields`, `test_index_matches_files`, `test_pl_anchors_preserved` (uses the frozen anchor list from T002 embedded as a module constant), `test_core_bundle_references_resolve`, `test_cp_corruption_absent`, `test_log_exists_nonempty`; front matter parsed via PyYAML with regex fallback per T003 result; validation rules per data-model.md
- [x] T005 Run `.\venv\Scripts\pytest tests/test_knowledge_bundle.py -v` and confirm it FAILS with bundle-absent errors (except `test_cp_corruption_absent` which fails on the live corruption, and `test_pl_anchors_preserved` which passes pre-migration — record the exact red/green pattern in baseline.md)

**Checkpoint**: Suite exists and is red for the right reasons. No documentation has been touched yet.

## Phase 3: User Story 1 — Reference Content Extraction into OKF Bundle (P1) 🎯 MVP

**Goal**: `docs/knowledge/` bundle exists with extracted DDL and Module Registry; PROJECT_LOGIC.md is a thin core with surviving anchors.

**Independent Test**: `.\venv\Scripts\pytest tests/test_knowledge_bundle.py` — bundle-structure tests green; spot-resolve one stub end-to-end (quickstart manual checks).

- [x] T006 [US1] Create docs/knowledge/db-schema.md: move the full DDL body of section [PL-3.1] from PROJECT_LOGIC.md verbatim; add YAML front matter (`type: db-schema`, `title`, `description` one sentence, `source_anchor: PL-3.1`, `timestamp: 2026-07-02`) per data-model.md Concept File schema
- [x] T007 [US1] Create docs/knowledge/module-registry.md: move the registry table of section [PL-2.2] from PROJECT_LOGIC.md verbatim; front matter `type: module-registry`, `source_anchor: PL-2.2`, same field rules
- [x] T008 [US1] Replace the moved bodies in PROJECT_LOGIC.md with anchor stubs in the exact data-model.md format (heading with original `[PL-x.y]` + one-line summary + `> Moved to docs/knowledge/<file>.md — read on demand.`); verify every imperative statement inside [PL-3.2]–[PL-3.5] and all other sections remains untouched (per-statement criterion: PL-3.1 DDL is descriptive, PL-3.2 Access Control rules are imperative and STAY)
- [x] T009 [US1] Create docs/knowledge/index.md listing db-schema.md and module-registry.md (path + type + one-line description mirroring front matter) and docs/knowledge/log.md with initial extraction entries (`2026-07-02 — <file> — extracted from <anchor>`)
- [x] T010 [US1] Run `.\venv\Scripts\pytest tests/test_knowledge_bundle.py -v`: `test_frontmatter_required_fields`, `test_index_matches_files`, `test_pl_anchors_preserved`, `test_core_bundle_references_resolve`, `test_log_exists_nonempty` must be green (`test_cp_corruption_absent` still red — fixed in US2)

**Checkpoint**: Bundle is live and self-consistent; PROJECT_LOGIC.md is thin; US1 delivers standalone value.

## Phase 4: User Story 2 — Core Deduplication and Repair (P2)

**Goal**: CONTEXT_PROMPT.md is repaired, deduplicated, and compressed to one line per feature; displaced detail lands in the bundle.

**Independent Test**: `test_cp_corruption_absent` green; `Select-String -Path CONTEXT_PROMPT.md -Pattern 'refer to \*\*PROJ##'` returns nothing; visual check of CP-2 line lengths.

- [x] T011 [US2] Fix the corruption at the CP-2/CP-3 boundary in CONTEXT_PROMPT.md (line ~55): restore the closing pointer sentence ("For the complete module registry ... refer to PROJECT_LOGIC.md and docs/knowledge/index.md") and make `## [CP-3] CODING RULES AND CONSTRAINTS` a standalone heading
- [x] T012 [US2] Deduplicate rules: in CONTEXT_PROMPT.md replace the full restated rule text in [CP-3.6] with a one-line citation to [PL-4.5]/[PL-6.12] and in [CP-3.7] with a one-line citation to [PL-6.1]/[PL-6.2]/[PL-6.18], keeping in CP only what is unique to coding-response behavior; confirm the full text exists in PROJECT_LOGIC.md (authoritative home per contracts producer rule 4)
- [x] T013 [US2] Compress every multi-line CP-2 feature entry (CP-2.7, CP-2.17, CP-2.19, CP-2.22 through CP-2.28 and any other entry exceeding one line) to exactly one line each; move each displaced implementation detail into a new docs/knowledge/features/<slug>.md concept file (`type: feature-detail`, `source_anchor: CP-2.x`) — approx. 10–15 files
- [x] T014 [US2] Add index.md entries and log.md entries for every file created in T013 (atomicity per contracts producer rule 2)
- [x] T015 [US2] Run `.\venv\Scripts\pytest tests/test_knowledge_bundle.py -v` — ALL six tests green

**Checkpoint**: Both cores are thin and duplication-free; full contract suite passes.

## Phase 5: User Story 3 — Workflow and Tooling Synchronization (P2) — END OF APPROVAL CHUNK 1

**Goal**: The process files know about the two-tier structure; drift protection verified by mutation checks.

**Independent Test**: quickstart.md mutation checks (section "Mutation checks") each turn the suite red then green again; full pytest regression green.

- [x] T016 [US3] Update GEMINI.md: Route A pre-read becomes "PROJECT_LOGIC.md + CONTEXT_PROMPT.md + docs/knowledge/index.md"; add `docs/knowledge/` row to § FILE REGISTRY (Public, tracked); add Content Ownership rows (reference content → bundle concept files; one-line stubs allowed in cores); add onboarding note "if graphify-out/ exists, answer architecture questions via graphify queries first"
- [x] T017 [US3] Update .agents/plugins/tenirtoo-plugin/skills/docs-update/SKILL.md: CMD-1/CMD-2 route descriptive/reference updates into the owning bundle concept file with mandatory index.md sync and log.md append (producer contract from contracts/okf-bundle-contract.md); imperative rules still go to core files
- [x] T018 [P] [US3] Add `graphify-out/` to .gitignore
- [x] T019 [US3] Run full regression `.\venv\Scripts\pytest` — entire suite green; `git status tests/` shows only the new test_knowledge_bundle.py
- [x] T020 [US3] Execute the three mutation checks from quickstart.md (remove a `type:` line; remove an index entry; rename a stub anchor) — each must fail the suite with a message naming the offender; restore after each; record results in baseline.md

**Checkpoint / HARD STOP**: Report Chunk 1 results to the user (Шэф) in Russian and AWAIT APPROVAL before Phase 6 (GEMINI.md chunking rule).

## Phase 6: User Story 4 — Knowledge Graph over the Repository (P3)

**Goal**: graphify graph built over the migrated repository; onboarding points to it.

**Independent Test**: `Test-Path graphify-out/GRAPH_REPORT.md` is True; `git check-ignore graphify-out` passes; one architecture query answered from the graph.

- [x] T021 [US4] Invoke the user-level `graphify` skill over the repository root (`/graphify C:\TenirTooClub_Bot`); if the skill is unavailable in the execution environment, STOP this phase and report Story 4 as BLOCKED (spec edge case) — do not skip silently
- [x] T022 [US4] Verify graph artifacts: `Test-Path graphify-out/GRAPH_REPORT.md` → True; `git check-ignore graphify-out` → prints graphify-out (T018 prerequisite)
- [x] T023 [US4] Answer one architecture question via graphify query (e.g., "which modules depend on the database facade?") without opening source files; record the query and answer for walkthrough.md (SC-006)

## Phase 7: Polish & Finalization

**Purpose**: Success-criteria measurement, RNA artifact gates, changelog, commit.

- [x] T024 Measure pre-read size per quickstart.md section 3 (PROJECT_LOGIC.md + CONTEXT_PROMPT.md + docs/knowledge/index.md) — must be ≤ 53.9 KB (SC-001); compare imperative-statement inventory against T002 baseline — must be 100% retained (SC-002); record both in baseline.md
- [x] T025 Complete specs/001-okf-docs-graphify/task.md (mark all items done) and run `.\venv\Scripts\python.exe local_scripts/prompt_linter.py --dir specs/001-okf-docs-graphify --stage checklist` — "Checklist is valid."
- [x] T026 Write specs/001-okf-docs-graphify/walkthrough.md in Russian with required sections "Changes made", "What was tested", "Validation results" (include SC-001/SC-002 numbers, mutation check results, graphify query demo); run `.\venv\Scripts\python.exe local_scripts/prompt_linter.py --dir specs/001-okf-docs-graphify --stage report` — "Report is valid."
- [x] T027 Add CHANGELOG.md entry (Route C / CMD-4 style, English, one concise block for the two-tier docs migration + graphify integration); no other doc files touched in this task
- [x] T028 GW-1 local commit: `git status` → `git add .` → `git commit -m "docs: migrate to two-tier architecture (normative core + OKF reference bundle), add bundle validation suite and graphify integration"`; do NOT push

## Dependencies

- Phase 1 → Phase 2 → Phase 3 (strict: TDD gate T004–T005 before any extraction)
- Phase 3 (US1) → Phase 4 (US2): features/ files need the bundle skeleton (index.md, log.md) from T009
- Phase 4 → Phase 5 (US3): mutation checks (T020) need the full suite green (T015)
- Phase 5 → HARD STOP (user approval) → Phase 6 (US4) → Phase 7
- T018 [P] is independent within Phase 5; T002/T003 [P] independent within Phase 1

## Parallel Execution Examples

- Phase 1: T002 and T003 in parallel (different concerns, different outputs into one file — write sequentially or merge).
- Phase 3: T006 and T007 in parallel (different new files); T008 only after both.
- Phase 5: T018 in parallel with T016/T017.
- Phases 4 within: T013 file creations parallelizable per feature slug; T014 after all of T013.

## Implementation Strategy

MVP = Phase 1–3 (User Story 1): even if stopped there, the repository gains a validated bundle, a thin PROJECT_LOGIC.md, and drift protection. US2 completes the token-reduction goal; US3 locks the process; US4 is additive. Respect the HARD STOP after Phase 5 — Chunk 2 runs only on explicit user approval.
