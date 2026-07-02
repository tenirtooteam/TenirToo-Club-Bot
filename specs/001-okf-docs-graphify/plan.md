# Implementation Plan: Two-Tier Documentation Architecture (Normative Core + OKF Reference Bundle) with Graphify Integration

**Branch**: `001-okf-docs-graphify` | **Date**: 2026-07-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-okf-docs-graphify/spec.md`

## Summary

Split the two monolithic pre-read files (`PROJECT_LOGIC.md` 51KB, `CONTEXT_PROMPT.md` 38.6KB) into a thin normative core (imperative rules only, always pre-read) and an OKF-style reference bundle at `docs/knowledge/` (concept files with YAML front matter + `index.md` + `log.md`, read on demand). Repair known core defects (CP-2/CP-3 corruption, CP↔PL rule duplication), synchronize the orchestrator workflow (`GEMINI.md`) and the `tenirtoo-docs-update` skill, guard the new structure with a pytest validation suite, then build a graphify knowledge graph over the repository. Documentation-only change: bot source code is untouched.

## Technical Context

**Language/Version**: Python 3.11 (validation suite only; primary deliverable is markdown)

**Primary Dependencies**: pytest (existing), PyYAML for front-matter parsing (verify presence in venv; if absent, parse front matter with `re` — no new dependency without user approval)

**Storage**: Filesystem — markdown files tracked in git; `graphify-out/` local and git-ignored

**Testing**: pytest via `.\venv\Scripts\pytest`; new suite `tests/test_knowledge_bundle.py`; artifact gates via `.\venv\Scripts\python.exe local_scripts/prompt_linter.py`

**Target Platform**: Windows 10, PowerShell syntax for all commands

**Project Type**: Documentation architecture refactor + test tooling inside an existing Telegram-bot repository

**Performance Goals**: Route A mandatory pre-read volume (thin cores + bundle index) reduced ≥40% vs 90KB baseline

**Constraints**: Every imperative statement stays in core files verbatim; every pre-migration `PL-x.y` anchor survives (full text or stub); existing pytest suite stays green with zero edits to existing test files; no changes under `handlers/`, `services/`, `database/`, `keyboards/`, `middlewares/`, `webapp/`; no `git push`

**Scale/Scope**: 2 core files rewritten, ~15–20 new bundle files, 1 new test module, 2 workflow files updated (`GEMINI.md`, docs-update `SKILL.md`), 1 graph build

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is an unfilled template — no formal constitution gates. The governing constraints are `GEMINI.md` (RNA-Blueprint conventions, prompt-linter gates, GW-1 git protocol, PowerShell-only, venv python) and the audited design conditions:

- [x] Classification criterion fixed: imperative statements stay in core; descriptive content moves to bundle; ambiguous → core. (Audit condition 1)
- [x] Skill + linter + workflow docs updated in the same change as the extraction. (Audit condition 2)
- [x] TDD-first: bundle validation suite written and failing before the bundle exists.
- [x] English-only artifacts; plan passes `prompt_linter.py --stage plan` via RNA-compatible `implementation_plan.md`.

**Post-design re-check (after Phase 1)**: PASS — no violations introduced; no Complexity Tracking entries needed.

## Project Structure

### Documentation (this feature)

```text
specs/001-okf-docs-graphify/
├── plan.md                  # This file
├── spec.md                  # Feature specification
├── research.md              # Phase 0: consolidated decisions
├── data-model.md            # Phase 1: bundle entity schemas
├── quickstart.md            # Phase 1: validation guide
├── contracts/
│   └── okf-bundle-contract.md   # Bundle format contract consumed by agents & tests
├── implementation_plan.md   # RNA-compatible plan (prompt_linter --stage plan target)
├── task.md                  # Execution checklist (prompt_linter --stage checklist target)
└── tasks.md                 # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
docs/
└── knowledge/               # [NEW] OKF-style reference bundle (tracked in git)
    ├── index.md             # [NEW] progressive-disclosure entry point
    ├── log.md               # [NEW] chronological bundle change log
    ├── db-schema.md         # [NEW] extracted from PROJECT_LOGIC.md [PL-3.1]
    ├── module-registry.md   # [NEW] extracted from PROJECT_LOGIC.md [PL-2.2]
    └── features/            # [NEW] per-feature detail files extracted from CP-2 entries
        └── <slug>.md        # one file per feature whose CP-2 entry exceeded one line

PROJECT_LOGIC.md             # [MODIFY] thin core: rules + anchor stubs for extracted sections
CONTEXT_PROMPT.md            # [MODIFY] repair corruption, dedupe CP-3.6/3.7, compress CP-2
GEMINI.md                    # [MODIFY] Route A pre-read, File Registry, Content Ownership
.agents/plugins/tenirtoo-plugin/skills/docs-update/SKILL.md   # [MODIFY] CMD-1/CMD-2 bundle targets
.gitignore                   # [MODIFY] add graphify-out/
tests/test_knowledge_bundle.py   # [NEW] bundle validation suite
graphify-out/                # [NEW, git-ignored] knowledge graph artifacts
```

**Structure Decision**: Single-repository documentation refactor. The bundle lives under `docs/knowledge/` (tracked, public — same visibility class as `PROJECT_LOGIC.md` per spec FR-013). Graph artifacts are local-only.

## Complexity Tracking

No constitution violations — table not required.
