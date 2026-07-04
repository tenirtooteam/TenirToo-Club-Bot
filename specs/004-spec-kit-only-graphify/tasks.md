---
description: "Task list for 004-spec-kit-only-graphify"
---

# Tasks: Spec-Kit-Only Route A + Full Graphify Integration

**Input**: Design documents from `specs/004-spec-kit-only-graphify/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/linter-and-rules.md, quickstart.md

**Tests**: TDD test tasks are included for the linter change (required by spec FR-003 / constitution principle IV).

**Organization**: Grouped by user story. Chunk A = US1 (spec-kit-only). Chunk B = US2 + US3 (graphify). Each chunk boundary ends in a mandatory HARD-STOP gate (R-PROC-2).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable (different files, no incomplete-task dependency)
- **[Story]**: US1 / US2 / US3

---

## Phase 1: Setup (Preflight)

**Purpose**: Establish a clean baseline before any change.

- [x] T001 Preflight in repo root: run `graphify --version` (expect 0.8.49) and `.\venv\Scripts\python.exe -m pytest -q` (record baseline green count); note in a scratch line that `CLAUDE.md` currently contains the `@AGENTS.md` shim (needed to verify FR-006 later).

---

## Phase 2: Foundational

**Purpose**: None. The governance/linter/graphify edits are mutually independent and need no shared blocking infrastructure. Proceed directly to User Story 1.

---

## Phase 3: User Story 1 — Spec-Kit Is the Only Route A (Priority: P1) 🎯 MVP · Chunk A

**Goal**: Remove the legacy RNA-1 path so the spec-kit chain is the sole Route A (registry, rules, linter), keeping specs 001–003 as read-only records.

**Independent Test**: `prompt_linter.py --stage plan` on a dir with only `implementation_plan.md` errors; `AGENTS.md`/`RULES.md` carry no `RNA-1` command entry; linter + governance suites green.

### Tests for User Story 1 (TDD — write first, ensure they FAIL) ⚠️

- [x] T002 [P] [US1] In `tests/test_prompt_linter.py`: replace the two legacy-fallback unit tests (`find_plan_file falls back to implementation_plan.md`, `find_checklist_file falls back to task.md`) with legacy-rejection assertions — `find_plan_file` returns `(None, ...)` when only `implementation_plan.md` exists; `find_checklist_file` returns `(None, ...)` when only `task.md` exists. Retain the `plan.md`/`tasks.md` happy-path tests. Run to confirm RED against current source.
- [x] T003 [P] [US1] In `tests/test_journeys/test_prompt_linter_journey.py`: remove the legacy-fallback journeys (lines ~17, ~107 fixtures) and add a CLI journey asserting `--stage plan` on a dir with only `implementation_plan.md` exits 1 with `no plan.md`; same for `task.md`/`--stage checklist`. Keep the v2 (`plan.md`/`tasks.md`) journeys. Run to confirm RED.

### Implementation for User Story 1

- [x] T004 [US1] In `local_scripts/prompt_linter.py`: delete `PLAN_LEGACY_REQUIRED_H2S`; simplify `find_plan_file` to return `(<dir>/plan.md, True)` or `(None, True)` (drop `implementation_plan.md` branch); simplify `find_checklist_file` to `tasks.md` only (drop `task.md` branch); update the two `main()` error strings to `no plan.md found` / `no tasks.md found`; remove the `required_h2s is None → legacy` default in `validate_plan` (always use `PLAN_V2_REQUIRED_H2S`). Re-run T002/T003 → GREEN.
- [x] T005 [US1] In `AGENTS.md`: remove the `RNA-1` row from § COMMAND REGISTRY; remove "RNA-1 is a legacy alias" from § EXECUTION WORKFLOW Route A; remove `implementation_plan.md` acceptance from § PLAN CONTENT; in § INDEXING add `RNA-1 → retired (superseded by /speckit-plan)`.
- [x] T006 [US1] In `RULES.md`: amend R-PROC-1 (planning starts via `/speckit-plan` after an approved audit — drop "explicit RNA-1"); amend R-PROC-2 (`plan.md`/`tasks.md` sole canonical artifacts; specs 001–003 = read-only records; drop "implementation_plan.md accepted for historical features"); amend R-PROC-4 (drop the `implementation_plan.md`/`task.md` legacy-fallback clause). No ID renumbering.
- [x] T007 [P] [US1] In `docs/knowledge/rule-map.md`: add row `RNA-1 → retired (superseded by /speckit-plan, 2026-07-04)`.
- [x] T008 [P] [US1] In `.agents/plugins/tenirtoo-plugin/skills/docs-update/SKILL.md`: in the Producer Contract v2 Validation paragraph, drop the legacy-artifact naming (`implementation_plan.md`/`task.md`) so only `plan.md`/`tasks.md` are named as linter targets.

**Checkpoint**: Legacy Route A removed; linter spec-kit-only; governance prose consistent.

- [x] T009 [US1] Run `.\venv\Scripts\python.exe -m pytest tests/test_prompt_linter.py tests/test_journeys/test_prompt_linter_journey.py tests/test_governance.py tests/test_knowledge_bundle.py -q` — all green. Then quickstart Chunk A steps 3–4 (no `PLAN_LEGACY`/`implementation_plan` symbols; AGENTS/RULES clean).
- [x] T010 [US1] **HARD STOP**: Report Chunk A completion to Шэф in Russian — summarize the legacy-removal edits and suite result — and AWAIT EXPLICIT APPROVAL before starting User Story 2. Do not continue on your own judgment. (R-PROC-2)

---

## Phase 4: User Story 2 — Graphify Fully Operational and Governed (Priority: P1) · Chunk B (part 1)

**Goal**: Working, always-on, governed graph: verified CLI, native Claude Code integration, a governed `R-PROC-12` rule, and an in-repo `graph.md` for future sessions.

**Independent Test**: `graphify query` answers from the graph; `R-PROC-12` in RULES.md; `docs/knowledge/graph.md` exists and is registered in index/log.

### Implementation for User Story 2

- [x] T011 [US2] Verify CLI: run `graphify query "which modules depend on the database facade?"` and confirm it answers from `graphify-out/graph.json` without opening source (quickstart step 6). No install into venv (research D1).
- [x] T012 [US2] Run `graphify claude install`; then read `CLAUDE.md` and confirm the `@AGENTS.md` shim is still present AND a `## graphify` section was appended. If the shim was removed, restore the `@AGENTS.md` line in the same task. Confirm the PreToolUse hook landed in `.claude/settings*.json` (research D3).
- [x] T013 [US2] In `RULES.md`: add `R-PROC-12 [A] Graph-first for structural questions` per contracts/linter-and-rules.md Contract 2 (Rule / Why / Legacy: —), placed in the PROC domain after R-PROC-11.
- [x] T014 [P] [US2] Create `docs/knowledge/graph.md` with YAML front matter (`type: graph-guide`, `title`, `description`, `timestamp: 2026-07-04`) describing: what the graph is, `query`/`path`/`explain`/`update` CLI commands, the two freshness channels (post-commit hook = code; docs-update = docs/semantic), and the CLI-absent fallback. (Bundle atomicity — see T015.)
- [x] T015 [US2] Bundle atomicity for graph.md: add a row to the concept-files table in `docs/knowledge/index.md` and append `2026-07-04 — graph.md — graph guide + commands + freshness channels` to `docs/knowledge/log.md`.
- [x] T016 [US2] In `AGENTS.md` § ONBOARDING item 5: replace the soft "answer via graphify queries" hint with a citation of `R-PROC-12` (pointer to graph.md).
- [x] T017 [US2] Run `.\venv\Scripts\python.exe -m pytest tests/test_governance.py tests/test_knowledge_bundle.py -q` — confirm R-PROC-12 satisfies rule-format checks and graph.md passes bundle checks.
- [x] T018 [US2] **HARD STOP**: Report US2 completion to Шэф in Russian — graph queryable, claude-install done (shim intact), R-PROC-12 + graph.md added — and AWAIT EXPLICIT APPROVAL before starting User Story 3. (R-PROC-2)

---

## Phase 5: User Story 3 — The Graph Stays Fresh Automatically (Priority: P2) · Chunk B (part 2)

**Goal**: Close the two update channels — git post-commit hook for code, docs-update skill step for docs/semantic — so R-PROC-12 never points at a stale graph.

**Independent Test**: `graphify hook status` reports installed; docs-update `SKILL.md` contains a `graphify --update` step and a "graph refreshed" validation item.

### Implementation for User Story 3

- [x] T019 [US3] Run `graphify hook install`; then `graphify hook status` to confirm the post-commit/post-checkout git hooks are installed (quickstart step 8).
- [x] T020 [US3] In `.agents/plugins/tenirtoo-plugin/skills/docs-update/SKILL.md`: add a final step to the CMD-1 and CMD-2 procedures — "After the documentation edit, run the semantic-aware graph refresh: `/graphify <repo-root> --update` (skill flow, AST + semantic — NOT the code-only `graphify update` CLI). This performs no git operation (Route C stays git-free)." Add a "[ ] Knowledge graph refreshed (`/graphify --update`)" item to the Output Validation checklist.
- [x] T021 [US3] Rebuild the graph now to reflect the Chunk A + US2 governance edits: run `graphify update .` for the code layer (per research D4, the semantic/doc layer is refreshed via the `/graphify --update` skill flow — invoke it if doc-node freshness is needed for the smoke query).
- [x] T022 [US3] Re-run the smoke query `graphify query "how is Route A structured?"` and confirm the refreshed graph reflects spec-kit-only (no RNA-1 as an active route).
- [x] T023 [US3] **HARD STOP**: Report US3 completion to Шэф in Russian — hooks installed, docs-update wired, graph rebuilt — and AWAIT EXPLICIT APPROVAL before Polish (CHANGELOG + commit). (R-PROC-2) — approved (Шэф: «закончить с этим переходом»); Haiku model pinned via `GRAPHIFY_CLAUDE_CLI_MODEL` per follow-up instruction.
- [x] T024 Run the full regression `.\venv\Scripts\python.exe -m pytest -q` — expect all green, 0 failed; compare against the T001 baseline count. Result: 122 passed, 1 skipped — matches baseline.
- [x] T025 Update `CHANGELOG.md` via CMD-4: new version block `## [1.5.0] - 2026-07-04` with `### Added` (R-PROC-12; graph.md; graphify claude+hook integration on Haiku; docs-update graph-refresh step) and `### Changed` (spec-kit sole Route A; RNA-1 retired; linter v3 spec-kit-only).
- [x] T026 **GW-1**: local commit — `git add .` + concise English commit message; NO push (R-PROC-5). Authorized by Шэф.
- [x] T027 [US1][US2][US3] Run the checklist linter gate `.\venv\Scripts\python.exe local_scripts/prompt_linter.py --dir specs/004-spec-kit-only-graphify --stage checklist` — запуск линтера-чеклиста.

---

## Dependencies & Execution Order

- **Phase 1 (Setup)** → no deps.
- **Phase 3 (US1)** → after Setup. Chunk A. TDD: T002/T003 (RED) before T004 (GREEN). T005–T008 are doc edits (T007, T008 [P] — different files). T009 verifies; T010 gates.
- **Phase 4 (US2)** → after T010 approval. T014/[P] independent of T013; T015 depends on T014; T017 after T013–T016; T018 gates.
- **Phase 5 (US3)** → after T018 approval. T020 depends on nothing but the skill file (shared with T008 — sequential, not [P]); T021 after governance edits so the rebuild reflects them; T023 gates.
- **Phase 6 (Polish)** → after T023 approval. the checklist-linter run (T027) is the final checklist item per the linter contract; GW-1 commit (T026) precedes it.

### Within-story parallel opportunities

- US1: T002 ∥ T003 (different test files); T007 ∥ T008 (rule-map vs skill file). T004 must follow T002/T003; T005/T006 touch AGENTS/RULES sequentially with T007.
- US2: T014 ∥ T013 (graph.md vs RULES.md). T012, T011 are CLI actions (sequential, side effects).

---

## Implementation Strategy

- **MVP = US1 (Chunk A)**: spec-kit-only Route A is independently valuable and shippable alone.
- **Chunk B = US2 + US3**: graphify made operational, governed, and self-refreshing. US2 is usable without US3 (graph works and is governed; US3 only automates freshness).
- Commit once at the end (T026), after all approvals — matches the plan's single GW-1 milestone.

## Notes

- No bot source (`handlers/`/`services/`/`database/`) is touched — governance/tooling only.
- `.claude/skills/speckit-*` and `tests/fixtures/rules_inventory_baseline.txt` are NOT edited.
- graphify runs from the global install; `graphify-out/` is git-ignored.
- Every HARD-STOP (T010, T018, T023) halts `/speckit-implement` until Шэф approves.
