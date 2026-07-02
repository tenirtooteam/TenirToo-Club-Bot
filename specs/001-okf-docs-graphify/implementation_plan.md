# Goal Description: Two-Tier Documentation Architecture (Normative Core + OKF Reference Bundle) + Graphify Integration

RNA-Blueprint view of [plan.md](plan.md) for the GEMINI.md Route A process. Executor: Claude Opus via `speckit-implement` over `tasks.md`.

## Base DNA

- OS: Windows 10 Pro, PowerShell syntax only; venv python at `.\venv\Scripts\python.exe`; pytest at `.\venv\Scripts\pytest`.
- Stack: Python 3.11 (validation tests only); primary deliverable is markdown restructuring.
- Runtime constraints: no `git push`; local commits per GW-1 at milestones; no edits to existing test files or bot source code.

## Task RNA

- Logic: Extract descriptive reference content (DDL [PL-3.1], Module Registry [PL-2.2], multi-line CP-2 feature details) from the two monolithic core files into an OKF-style bundle `docs/knowledge/` (concept files with YAML front matter + `index.md` + `log.md`). Core files keep all imperative rules and anchor stubs. Repair CONTEXT_PROMPT.md corruption and CP-PL duplication. Sync `GEMINI.md` and the docs-update skill. Guard with a new pytest suite. Build graphify graph last.
- Risks: (1) A normative rule accidentally classified as reference and moved out of guaranteed context — mitigated by per-statement criterion (ambiguous stays in core) and rule-inventory diff; (2) index/bundle drift after future updates — mitigated by `tests/test_knowledge_bundle.py` and producer contract in the docs-update skill; (3) broken `PL-x.y` citations in historical artifacts — mitigated by anchor stubs and `test_pl_anchors_preserved`.
- Edge cases: mixed sections (imperative + descriptive) split per statement; graphify skill unavailable in executor environment (report blocked, do not skip silently); PyYAML absent from venv (fallback regex front-matter parser inside the test module).

## Contextual Constraints (CC)

- [CC-1] File Registry and Content Ownership [GEMINI.md § FILE REGISTRY]: bundle gains a registry row and an ownership home; no duplication between core and bundle.
- [CC-2] One line per feature in CONTEXT_PROMPT [CP-2.2 rule, GEMINI.md]: enforced during CP-2 compression.
- [CC-3] Indexing System [GEMINI.md § INDEXING SYSTEM]: `PL-x.y` anchors must keep resolving; stubs preserve them.
- [CC-4] Prompt Linter gates [GEMINI.md Route A]: plan/checklist/report stages run against `specs/001-okf-docs-graphify`.
- [CC-5] TDD-first [GEMINI.md § RNA-BLUEPRINT]: the validation suite is written and observed failing before the bundle exists.
- [CC-6] No bot source changes [spec FR-011]: `handlers/`, `services/`, `database/`, `keyboards/`, `middlewares/`, `webapp/` untouched.

## User Review Required

- Approval of this plan before any file changes (GEMINI.md Route A chunking rule: 3-5 steps, report, await approval).
- Confirmation that `docs/knowledge/` (tracked, public) is the accepted bundle location (spec FR-013, research D5).
- Note: `.specify/memory/constitution.md` is an unfilled template; GEMINI.md conventions act as the governing constraints for this feature.

## Open Questions

- None blocking. PyYAML availability in venv is checked at execution time (fallback parser specified in research D6). Graphify availability is checked at Step 5 (blocked-report path specified).

## Proposed Changes

### Documentation bundle (new)
- [NEW] `docs/knowledge/index.md` - progressive-disclosure index (added to Route A pre-read set).
- [NEW] `docs/knowledge/log.md` - append-only bundle change log.
- [NEW] `docs/knowledge/db-schema.md` - full DDL moved from [PL-3.1].
- [NEW] `docs/knowledge/module-registry.md` - registry table moved from [PL-2.2].
- [NEW] `docs/knowledge/features/<slug>.md` - detail files for each multi-line CP-2 entry (approx. 10-15 files).

### Core files
- [MODIFY] `PROJECT_LOGIC.md` - replace extracted sections with anchor stubs (format per data-model.md); all imperative rules stay verbatim.
- [MODIFY] `CONTEXT_PROMPT.md` - fix `refer to **PROJ##` corruption; restore `## [CP-3]` heading; compress CP-2 to one line per feature; replace duplicated rule text in CP-3.6/CP-3.7 with index citations to PL-4.5/PL-6.2/PL-6.18.

### Workflow and tooling
- [MODIFY] `GEMINI.md` - Route A pre-read set (thin cores + bundle index), File Registry row, Content Ownership rows, onboarding pointer to graphify queries.
- [MODIFY] `.agents/plugins/tenirtoo-plugin/skills/docs-update/SKILL.md` - CMD-1/CMD-2 route reference-type updates into bundle files with index/log maintenance (producer contract).
- [MODIFY] `.gitignore` - add `graphify-out/`.
- [NEW] `tests/test_knowledge_bundle.py` - validation suite (test names bound by contracts/okf-bundle-contract.md).

## Execution Steps

1. **[TEST][CC-5]** Write `tests/test_knowledge_bundle.py` (frozen pre-migration `PL-x.y` anchor list captured from current `PROJECT_LOGIC.md`; all six contract tests). Run `.\venv\Scripts\pytest tests/test_knowledge_bundle.py` - MUST fail (bundle absent). Record the failure output.
2. **[CC-3][CC-1]** Create bundle skeleton and extract `PROJECT_LOGIC.md` content: `db-schema.md` ([PL-3.1]), `module-registry.md` ([PL-2.2]) with front matter; insert anchor stubs; create `index.md` and `log.md`. TDD sub-check: contract tests for these files flip to green; anchor test green.
3. **[CC-2]** Repair `CONTEXT_PROMPT.md`: fix corruption, dedupe CP-3.6/CP-3.7 via index citations, compress CP-2 entries to one line each, moving displaced details into `docs/knowledge/features/*.md` (with index/log entries). TDD sub-check: `test_cp_corruption_absent` and index tests green.
4. **[CC-1][CC-4]** Sync workflow: update `GEMINI.md` (pre-read, registry, ownership, graphify onboarding note), docs-update `SKILL.md` (producer contract), `.gitignore`. Run full `.\venv\Scripts\pytest` - green; run mutation checks from quickstart.md.
5. **[TEST]** Build knowledge graph: invoke `graphify` skill over repo root; verify `graphify-out/GRAPH_REPORT.md` exists and `git check-ignore graphify-out` passes; answer one architecture question via graph query (SC-006). If the skill is unavailable - report blocked per Task RNA edge case.
6. **[CC-4]** Finalize: measure pre-read size (SC-001, target <= 53.9 KB); complete `task.md`; run linter checklist stage; write `walkthrough.md` (Russian) and run linter report stage; CMD-4 changelog entry; GW-1 local commit.

Chunking per GEMINI.md: execute steps 1-4, report, await approval, then steps 5-6.

## Verification Plan

- **Reproducing/new test file**: `tests/test_knowledge_bundle.py`; test cases: `test_frontmatter_required_fields`, `test_index_matches_files`, `test_pl_anchors_preserved`, `test_core_bundle_references_resolve`, `test_cp_corruption_absent`, `test_log_exists_nonempty`. TDD reproducer: the suite fails on the pre-migration tree (bundle absent) - this failure is observed and recorded in Step 1 before any extraction.
- **Commands**: see [quickstart.md](quickstart.md) sections 1-6 (suite, full regression, size measurement, corruption scan, linter gates, graph checks, mutation checks).
- **Manual checks**: spot-read migrated `PROJECT_LOGIC.md` [PL-6] rules for verbatim retention; follow two random `index.md` entries to their concept files; resolve one stubbed anchor end-to-end.
