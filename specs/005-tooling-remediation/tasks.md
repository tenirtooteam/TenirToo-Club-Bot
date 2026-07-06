# Tasks: AI Tooling Remediation (July 2026 Audit)

**Input**: Design documents from `/specs/005-tooling-remediation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: TDD is mandatory per constitution (R-PROC-3, Principle IV) — reproducing/regression
tests precede fixes wherever a testable behavior changes.

**Organization**: Tasks grouped by user story. US2 and US3 share one mechanism (plugin
registration, operator decision) — US2 builds the plugin infrastructure, US3 adds the agent
components on top of it; US3 therefore depends on US2 (documented deviation from full story
independence).

**Executor note**: Implementation runs on Opus/Sonnet. `/speckit-implement` MUST stop at every
HARD-STOP gate task and await Шэф's explicit approval (R-PROC-2). Rule IDs are cited per task
(R-CODE-7 — never copy rule text).

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Record pre-fix ground truth so every later comparison has a baseline.

- [x] T001 Record pre-fix reproduction per quickstart.md § 0: run `.\venv\Scripts\pytest -q` (expect ModuleNotFoundError), run `.\venv\Scripts\python -m pytest -q` and save full result counts as BASELINE into specs/005-tooling-remediation/walkthrough.md (create file, section "Baseline") (R-PROC-3)
- [x] T002 [P] Record pre-fix linter false positive: run `python local_scripts/prompt_linter.py --stage plan` over specs/001..004 dirs, append observed warnings to specs/005-tooling-remediation/walkthrough.md section "Baseline" (R-PROC-4)
- [x] T003 [P] Verify regression-guard tools green pre-change: `.\venv\Scripts\ruff check .` and `.\venv\Scripts\lint-imports`; note results in walkthrough.md "Baseline" (R-PROC-10)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The canonical test invocation (US1's fix) is foundational — the TDD sub-steps of
every later story depend on tests being runnable, and FR-008 makes the agent definition cite it.

**⚠️ CRITICAL**: No user story work begins until this phase is complete.

- [x] T004a Create tests/test_services/test_collection_smoke.py — subprocess run of `venv\Scripts\pytest --collect-only -q` asserting exit code 0 (imports project packages during collection); CONFIRM it FAILS before pytest.ini exists, will pass after (failing-reproducing test for the collection bug, R-PROC-3, Principle IV; R-TEST-3 — assert on subprocess args/returncode)
- [x] T004 Create pytest.ini at repo root with `[pytest]`, `pythonpath = .`, `testpaths = tests` per contracts/canonical-test-invocation.md (R-TEST-1)
- [x] T005 Verify fix: `.\venv\Scripts\pytest -q` collects and runs (T004a smoke test now GREEN); compare counts to BASELINE in walkthrough.md — must be identical (BASELINE + 1 smoke test); also re-run `.\venv\Scripts\python -m pytest -q` (no regression) (quickstart § 1)
- [x] T006 **HARD STOP**: Report progress to the user (Шэф) in Russian — summarize what was completed in this chunk and what comes next — and AWAIT EXPLICIT APPROVAL before proceeding to the next task. Do not continue on your own judgment. (R-PROC-2)

---

## Phase 3: User Story 1 — Canonical test invocation works everywhere (Priority: P1) 🎯 MVP

**Goal**: One documented invocation form, working and cited consistently across all living docs.

**Independent Test**: quickstart § 1 — canonical run green with BASELINE-equal counts; doc sweep
finds only the canonical form.

### Implementation for User Story 1

- [x] T007 [US1] Sweep living docs for test-invocation mentions: search `venv\Scripts\pytest`, `python -m pytest`, `pytest` across RULES.md, AGENTS.md, docs/knowledge/*.md, README.md, CHANGELOG.md (historical specs/001-004 exempt); list every hit and its required edit in walkthrough.md (FR-002)
- [x] T008 [US1] Apply the sweep edits: align docs/knowledge/subagents.md (test-runner instruction) and docs/knowledge/testing concept file on the canonical form `.\venv\Scripts\pytest` per contracts/canonical-test-invocation.md (FR-002, R-CODE-7)
- [x] T009 [US1] Regression gates: full `.\venv\Scripts\pytest -q` (incl. tests/test_governance.py, tests/test_knowledge_bundle.py — research.md R7), `ruff check .`, `lint-imports`; record in walkthrough.md (R-PROC-10)
- [x] T010 [US1] **HARD STOP**: Report progress to the user (Шэф) in Russian — summarize User Story 1 completion — and AWAIT EXPLICIT APPROVAL before starting User Story 2. (R-PROC-2)

**Checkpoint**: US1 fully functional — canonical invocation green, docs aligned.

---

## Phase 4: User Story 2 — Route B and Route C engines are invocable (Priority: P2)

**Goal**: tenirtoo-plugin registered as a proper Claude Code plugin; both engine skills
discoverable in a fresh session; single physical source (FR-006).

**Independent Test**: quickstart § 3 items 1 & 3; contracts/plugin-registration.md verification.

### Implementation for User Story 2

- [x] T011 [US2] Verify plugin/marketplace mechanics against the installed harness version (docs MCP / `claude plugin --help`) and record the exact settings-key shapes to use in walkthrough.md BEFORE editing any file (research.md R2 risk clause)
- [x] T012 [US2] Create .agents/plugins/tenirtoo-plugin/.claude-plugin/plugin.json (name tenirtoo-plugin, version 2.0.0, description) and delete legacy .agents/plugins/tenirtoo-plugin/plugin.json (contracts/plugin-registration.md)
- [x] T013 [US2] Create repo-root .claude-plugin/marketplace.json listing tenirtoo-plugin with relative source path per T011 findings (research.md R2)
- [x] T014 [US2] Wire .claude/settings.json: add extraKnownMarketplaces + enabledPlugins entries per T011 findings; preserve existing env/hooks keys untouched (FR-005)
- [x] T015 [US2] **HARD STOP**: Report progress to the user (Шэф) in Russian — registration chunk done, fresh-session verification comes next (requires Шэф to open a fresh session or approve the check method) — and AWAIT EXPLICIT APPROVAL. (R-PROC-2)
- [x] T016 [US2] Fresh-session verification: both skills appear exactly once and load canonical content (quickstart § 3 items 1 & 3, duplicate-name check per research.md R2); if discovery FAILS → report and request operator approval for the fallback clause of contracts/plugin-registration.md — do NOT apply fallback unilaterally (R-PROC-1)
- [x] T017 [US2] Update AGENTS.md § FILE REGISTRY row for the plugin (registration state) and docs/knowledge concept touching skills, per content-ownership rules (FR-013, R-CODE-7)

**Checkpoint**: Route B/C engines invocable; single source preserved.

- [x] T018 [US2] **HARD STOP**: Report progress to the user (Шэф) in Russian — summarize User Story 2 completion — and AWAIT EXPLICIT APPROVAL before starting User Story 3. (R-PROC-2)

---

## Phase 5: User Story 3 — Documented subagents are actually delegable (Priority: P2)

**Goal**: Three agent definitions inside the plugin, faithful to docs/knowledge/subagents.md,
delegable in a fresh session.

**Independent Test**: quickstart § 3 item 2; fidelity diff against subagents.md §§1-3.

**Depends on**: US2 (plugin infrastructure) — documented deviation.

### Implementation for User Story 3

- [x] T019 [P] [US3] Create .agents/plugins/tenirtoo-plugin/agents/proposal-auditor.md from docs/knowledge/subagents.md §1 (frontmatter name/description + system-prompt body; zero behavioral delta) (FR-007)
- [x] T020 [P] [US3] Create .agents/plugins/tenirtoo-plugin/agents/test-runner-and-debugger.md from §2 with the single permitted delta: canonical invocation `.\venv\Scripts\pytest` per contracts/canonical-test-invocation.md (FR-007, FR-008)
- [x] T021 [P] [US3] Create .agents/plugins/tenirtoo-plugin/agents/cognitive-ux-auditor.md from §3 (drives local_scripts/ux_cognitive_audit.py; zero behavioral delta) (FR-007)
- [x] T022 [US3] Add operational-mirror note to docs/knowledge/subagents.md (docs remain descriptive source; mirror location recorded) and re-run governance tests via `.\venv\Scripts\pytest -q` (FR-013, research.md R7)
- [x] T023 [US3] Fresh-session verification: three agent types offered; fidelity check definitions vs subagents.md §§1-3 (quickstart § 3 item 2)

**Checkpoint**: All five registered capabilities live (SC-003: 5/5).

- [x] T024 [US3] **HARD STOP**: Report progress to the user (Шэф) in Russian — summarize User Story 3 completion — and AWAIT EXPLICIT APPROVAL before starting User Story 4. (R-PROC-2)

---

## Phase 6: User Story 4 — Plan linter reports no false positives (Priority: P3)

**Goal**: Cyrillic check flags only genuine non-whitelisted Cyrillic tokens; regression-tested.

**Independent Test**: quickstart § 2 — new test module green; specs 001-005 lint with zero
Cyrillic warnings; seeded violation still flagged.

### Tests for User Story 4 (TDD — write first, MUST FAIL against unmodified linter)

- [x] T025 [US4] Create tests/test_services/test_prompt_linter.py covering: punctuation-only tokens `- -- —` (no warning), genuine Russian word (warning names it), whitelisted terms incl. `Теңир-Тоо` (no warning), mixed token `спек-kit` (warning); mock/parametrized assertions check args and kwargs where mocks used; run and CONFIRM the punctuation case FAILS pre-fix (R-PROC-3, R-TEST-3)

### Implementation for User Story 4

- [x] T026 [US4] Fix local_scripts/prompt_linter.py Cyrillic check per research.md R4: post-filter tokens to require ≥1 Cyrillic letter before whitelist comparison (FR-003)
- [x] T027 [US4] Verify: `.\venv\Scripts\pytest tests/test_services/test_prompt_linter.py -q` all green; lint specs/001..005 plan stage → zero Cyrillic warnings (SC-002); seeded-violation scratch check per quickstart § 2; record in walkthrough.md
- [x] T028 [US4] **HARD STOP**: Report progress to the user (Шэф) in Russian — summarize User Story 4 completion — and AWAIT EXPLICIT APPROVAL before starting User Story 5. (R-PROC-2)

**Checkpoint**: Lint gate trustworthy again.

---

## Phase 7: User Story 5 — Architecture SAST gate verified and honestly documented (Priority: P3)

**Goal**: Docker semgrep gate proven green; dev-deps installable on win32; skip behavior documented.

**Independent Test**: quickstart §§ 4-5.

### Implementation for User Story 5

- [x] T029 [US5] Inspect docker-compose.yml semgrep service: if `profiles: ["lint"]` is missing (research.md R5 note), add it so the documented command `docker-compose --profile lint run --rm semgrep` selects the service (R-PROC-11 is the contract)
- [x] T030 [US5] Run `docker-compose --profile lint run --rm semgrep` (Docker Desktop running); record pass/fail + findings count in walkthrough.md section "Semgrep gate" (FR-009, SC-004)
- [x] T031 [P] [US5] Edit requirements-dev.txt: `semgrep>=1.65.0; sys_platform != "win32"`; verify `.\venv\Scripts\pip install -r requirements-dev.txt --dry-run` succeeds on win32 (FR-010, quickstart § 4)
- [x] T032 [US5] Document in the docs/knowledge testing concept: Docker = canonical semgrep channel, host test_semgrep_lint.py skip on Windows is intended (FR-010, FR-013); re-run governance tests
- [x] T033 [US5] **HARD STOP**: Report progress to the user (Шэф) in Russian — summarize User Story 5 completion — and AWAIT EXPLICIT APPROVAL before starting User Story 6. (R-PROC-2)

**Checkpoint**: SAST gate verified, deps honest.

---

## Phase 8: User Story 6 — No dead references in agent-facing instructions (Priority: P4)

**Goal**: Zero references to artifacts the toolchain cannot produce.

**Independent Test**: quickstart § 6 sweep returns no hits in living docs.

### Implementation for User Story 6

- [x] T034 [US6] Remove the graphify-out/wiki/index.md bullet from CLAUDE.md (FR-011, research.md R6)
- [x] T035 [US6] Repo-wide sweep for non-producible artifact references in agent-facing files (CLAUDE.md, AGENTS.md, RULES.md, GEMINI.md, docs/knowledge/*.md; specs/001-004 exempt): quickstart § 6 pattern plus any other artifacts named but absent/non-producible; fix or report each hit (SC-005)

**Checkpoint**: Instruction files clean.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [x] T036 Scope guard: `git diff --stat main -- handlers services middlewares database keyboards web` → MUST be empty (FR-012, SC-006); record in walkthrough.md
- [x] T037 Full regression pass per quickstart § 8: `.\venv\Scripts\pytest -q` (expect 125 passed, 1 skipped = canonical 122 incl. T004a smoke + 3 linter regression cases merged into tests/test_prompt_linter.py), `ruff check .`, `lint-imports`; then `graphify update .` (AST-only refresh, R-PROC-12)
- [x] T038 **HARD STOP**: Report progress to the user (Шэф) in Russian — polish chunk done, final gates next — and AWAIT EXPLICIT APPROVAL. (R-PROC-2)
- [x] T039 Complete specs/005-tooling-remediation/walkthrough.md in Russian with sections "Changes made", "What was tested", "Validation results"; run `python local_scripts/prompt_linter.py --dir specs/005-tooling-remediation --stage report` → valid (R-PROC-4, R-PROC-8)
- [x] T040 Flag Route C follow-up: list registry/rule deltas for tenirtoo-docs-update (CMD-1..4) — CHANGELOG entry for feature 005, FILE REGISTRY row, any new R-* if the operator mandates one; do NOT perform git operations inside Route C (R-PROC-5)
- [x] T041 GW-1 local commit at milestone: `git status` → stage deletions → `git add .` → concise English commit message; NO push (R-PROC-5)
- [x] T042 Запуск линтера-чеклиста: run `python local_scripts/prompt_linter.py --dir specs/005-tooling-remediation --stage checklist` after all boxes above are checked → must pass (R-PROC-4)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** → **Foundational (Phase 2, = pytest fix)** → blocks everything.
- **US1 (Phase 3)**: depends on Phase 2 only.
- **US2 (Phase 4)**: depends on Phase 2; independent of US1 content but runs after (priority order).
- **US3 (Phase 5)**: depends on **US2** (plugin infra) and on Phase 2 (T020 cites the canonical form) — documented deviation from story independence.
- **US4 (Phase 6)**, **US5 (Phase 7)**, **US6 (Phase 8)**: depend on Phase 2 only; mutually independent.
- **Polish (Phase 9)**: depends on all stories.

### Parallel Opportunities

- T002 ∥ T003 (Setup).
- T019 ∥ T020 ∥ T021 (three agent files, different paths).
- T031 ∥ T030 (different surfaces) — but keep within-chunk ordering simple; sequential is acceptable.
- US4, US5, US6 could run in any order after Phase 2 if the operator re-prioritizes at a gate.

### Within Each Story

- TDD first where a testable behavior changes (T025 before T026) (R-PROC-3).
- Verification task closes every story before its HARD-STOP gate.

---

## Implementation Strategy

**MVP = Phase 1 + Phase 2 + US1**: with just the pytest fix and doc alignment, the core Route A
workflow (TDD sub-steps, test-runner instructions) is unbroken — deliverable value on its own.

**Incremental delivery**: each story closes with its own verification and a HARD-STOP report to
Шэф; any gate may pause or re-scope the remainder (e.g., skip US6 without affecting US1-US5).

**Model split**: these artifacts were planned on Fable; every task above is executed by
Opus/Sonnet under `/speckit-implement`, which MUST honor every HARD-STOP task literally.
