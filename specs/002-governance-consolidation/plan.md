# Implementation Plan: Governance Consolidation (Single Constitution + Unified Rulebook + Knowledge Dissolution)

**Branch**: `002-governance-consolidation` | **Date**: 2026-07-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-governance-consolidation/spec.md`

## Summary

Replace the scattered three-file governance (GEMINI.md + PROJECT_LOGIC.md + CONTEXT_PROMPT.md) with the industry-standard layout: a tracked constitution at `AGENTS.md` (open agent-instructions standard), a single unified rulebook `RULES.md` (stable IDs, rationale, tier A/B, enforcement pointers, legacy-anchor mapping), and full dissolution of descriptive content into the existing `docs/knowledge/` OKF bundle. `CLAUDE.md`/`GEMINI.md` become shims; `PROJECT_LOGIC.md`/`CONTEXT_PROMPT.md` become thin redirect indexes; spec-kit constitution gets filled; skills and validation tests are synchronized; the knowledge graph is rebuilt. Bot source code untouched.

## Technical Context

**Language/Version**: Python 3.11 (validation suites only; deliverable is markdown restructuring)

**Primary Dependencies**: pytest (existing); regex front-matter parser from feature 001 (no PyYAML — confirmed absent)

**Storage**: Filesystem; git tracking changes: `AGENTS.md` + `RULES.md` newly tracked, shims stay ignored

**Testing**: `.\venv\Scripts\python.exe -m pytest` (invocation note from feature 001 baseline); new `tests/test_governance.py`; existing `tests/test_knowledge_bundle.py` adapted only in its base-file constants (documented)

**Target Platform**: Windows 10, PowerShell command syntax

**Project Type**: Documentation/governance refactor + test tooling

**Performance Goals**: Pre-read (`AGENTS.md` + `RULES.md` + `docs/knowledge/index.md`) ≤ 30 KB (SC-001)

**Constraints**: Zero rule loss (every rule text lands in RULES.md exactly once); all 250 `PL-x.y` + all `CP-x.y` anchors resolve via `docs/knowledge/rule-map.md`; no bot source changes; no `git push`; no secrets into tracked files (Phase 1 inventory includes a secret-scan of GEMINI/AGENTS content)

**Scale/Scope**: ~86+ rules consolidated (26 PL-6, ~60 CP-3, PL-2.3/2.4/2.5, PL-3.2, PL-5 protocol rules, PL-8.3/8.5, PL-2.2.50, GEMINI response/git/RNA rules); 2 new governance files; ~8 new knowledge files; 2 redirect rewrites; 3 shims; 2 skills updated; 1 constitution filled; 1 new test module

**Executor split (user-approved approach)**: **Opus** executes Chunk 1 (rule inventory, consolidation semantics, constitution drafting — judgment-heavy, loss-risk concentrated here). **Sonnet** executes Chunk 2 (verbatim dissolution moves per explicit map, shims, tooling sync, finalization — mechanical, fully specified by Chunk 1 outputs). Handoff artifact: completed `RULES.md` + `rule-map.md` + dissolution map validated green at the chunk boundary.

## Constitution Check

`.specify/memory/constitution.md` is an unfilled template (filling it is itself FR-010 of this feature). Governing constraints for this feature are the audit findings (F1–F7) and the process conventions retained from GEMINI.md (RNA chunking, prompt-linter gates, GW-1, TDD-first):

- [x] TDD-first: `tests/test_governance.py` written and red before any consolidation.
- [x] Chunked execution with HARD STOP between Chunk 1 (Opus) and Chunk 2 (Sonnet) — doubles as the executor handoff point.
- [x] Lossless consolidation: rule inventory frozen in Phase 1; retention diff enforced by test.
- [x] English artifacts; prompt-linter plan/checklist/report gates against `specs/002-governance-consolidation`.

**Post-design re-check**: PASS — no violations; no Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/002-governance-consolidation/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md
├── contracts/governance-contract.md
├── implementation_plan.md      # RNA/linter-compatible view
├── task.md                     # checklist-stage linter target
├── tasks.md                    # executable tasks with executor tags
├── baseline.md                 # Phase 1 outputs: rule inventory, sizes, secret scan
└── checklists/requirements.md
```

### Source Code (repository root)

```text
AGENTS.md                    # [REWRITE, TRACK] constitution (was: subagent registry, ignored)
RULES.md                     # [NEW, TRACK] unified rulebook
CLAUDE.md                    # [REWRITE] shim -> AGENTS.md (stays ignored)
GEMINI.md                    # [REWRITE] shim -> AGENTS.md (stays ignored)
PROJECT_LOGIC.md             # [REWRITE] thin tracked redirect index
CONTEXT_PROMPT.md            # [REWRITE] thin tracked redirect index
.gitignore                   # [MODIFY] un-ignore AGENTS.md
docs/knowledge/
├── rule-map.md              # [NEW] legacy anchor -> R-ID / bundle file
├── architecture.md          # [NEW] PL-2.1, PL-2.6 (+ layer descriptions)
├── middleware.md            # [NEW] PL-4 behavioral description
├── fsm-protocol.md          # [NEW] descriptive parts of PL-5 (FSM keys, landing, close-menu behavior)
├── db-patterns.md           # [NEW] PL-3.3–3.5 (+ PL-3.1.1 fact)
├── constants.md             # [NEW] PL-7
├── testing.md               # [NEW] descriptive parts of PL-8, subagent registry detail
├── features-overview.md     # [NEW] CP-2 one-line feature list
└── (index.md, log.md updated atomically)
.specify/memory/constitution.md                                   # [FILL]
.agents/plugins/tenirtoo-plugin/skills/docs-update/SKILL.md       # [MODIFY]
.agents/plugins/tenirtoo-plugin/skills/proposal-analysis/SKILL.md # [MODIFY] ground truth -> RULES.md
tests/test_governance.py     # [NEW]
tests/test_knowledge_bundle.py  # [ADAPT constants only — documented]
tests/fixtures/rules_inventory_baseline.txt  # [NEW] frozen rule inventory
```

**Structure Decision**: Constitution and rulebook at repo root (standard entry points, tracked); all reference in the existing bundle; anchors preserved via mapping table instead of stub headings (the dissolved files no longer carry per-section stubs — one redirect note + rule-map covers resolution).

## Complexity Tracking

No violations — table not required.
