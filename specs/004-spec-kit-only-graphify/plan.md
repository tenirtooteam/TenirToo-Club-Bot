# Implementation Plan: Spec-Kit-Only Route A + Full Graphify Integration

**Branch**: `004-spec-kit-only-graphify` | **Date**: 2026-07-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-spec-kit-only-graphify/spec.md`

## Summary

Two governance/tooling threads, no bot runtime change. **Thread 1** finishes what feature 003 started: make the spec-kit chain the *only* Route A by removing the legacy RNA-1 path — strip `RNA-1` and `implementation_plan.md`/`task.md` from the command registry, the R-PROC rules, and the prompt linter (deleting `PLAN_LEGACY_REQUIRED_H2S` and both filename fallbacks), keeping historical specs 001–003 as read-only records. **Thread 2** makes graphify a first-class, always-fresh, governed capability: verify the global CLI, wire native Claude Code integration (`graphify claude install`) and git auto-rebuild hooks (`graphify hook install`), rebuild the graph, add a governed rule `R-PROC-12` (graph-first with explicit CLI-absent fallback) plus an in-repo `docs/knowledge/graph.md` for future sessions, and integrate a semantic-aware `graphify --update` step into the docs-update skill. Technical approach and exact CLI forms are pinned in [research.md](research.md); artifact contracts in [contracts/linter-and-rules.md](contracts/linter-and-rules.md).

## Technical Context

**Language/Version**: Python 3.11 (linter, tests); Markdown (governance docs).

**Primary Dependencies**: `local_scripts/prompt_linter.py` (stdlib only); pytest; global `graphify` CLI (`graphifyy` 0.8.49, on PATH, NOT in venv — see research D1).

**Storage**: N/A (no DB change). Graph artifacts in git-ignored `graphify-out/`.

**Testing**: pytest — `tests/test_prompt_linter.py`, `tests/test_journeys/test_prompt_linter_journey.py`, `tests/test_governance.py`, `tests/test_knowledge_bundle.py`, plus full regression.

**Target Platform**: Windows 10 dev workstation; Git Bash for git hooks.

**Project Type**: Governance/tooling change to an existing single-project Telegram bot repo.

**Performance Goals**: N/A.

**Constraints**: No bot source (`handlers/`, `services/`, `database/`) edits. `R-PROC-7` (venv for bot dev/test). Route C = no git ops. ID permanence (`R-CODE-7`). Bundle atomicity for any `docs/knowledge/` file.

**Scale/Scope**: ~1 script, ~2 test files, 3 governance docs (AGENTS/RULES/rule-map), 1 new knowledge file, 1 skill file, 1 CHANGELOG entry; graphify CLI invocations (no code).

## Constitution Check

*GATE: passes. This feature edits governance itself; principle citations below.*

- **I. Layered Isolation** — untouched (no bot source change).
- **II. Sterile Interface** — untouched.
- **III. Service-Mediated Mutation** — untouched.
- **IV. Test-First (NON-NEGOTIABLE)** — HONORED: linter changes are TDD (rewrite `test_prompt_linter.py`/journey legacy cases red-first, then remove legacy code). `R-PROC-3` applies to the linter behavior change.
- **V. Single Source of Truth & Traceability** — HONORED: new `R-PROC-12` gets a unique permanent ID; amended rules keep their IDs; `RNA-1` marked retired in rule-map, not deleted (`R-CODE-7`, constitution §Governance).
- **Development Workflow** — this plan is the spec-kit `plan.md` (canonical, `R-PROC-2`); execution is chunked with HARD-STOP gates and user approval between chunks (`R-PROC-1`). CHANGELOG via CMD-4 (`R-PROC-6`); GW-1 local commit only, no push (`R-PROC-5`).

No violations → Complexity Tracking omitted.

## Project Structure

### Documentation (this feature)

```text
specs/004-spec-kit-only-graphify/
├── plan.md              # This file
├── spec.md              # Feature spec
├── research.md          # Phase 0 — CLI verification + design decisions
├── data-model.md        # Governance artifacts + freshness state machine
├── quickstart.md        # Chunked validation guide
├── contracts/
│   └── linter-and-rules.md   # Linter v3 + R-PROC-12 + bundle contracts
├── checklists/
│   └── requirements.md  # Spec quality checklist (passed)
└── tasks.md             # Phase 2 — /speckit-tasks output (with HARD-STOP gates)
```

### Source Code (repository root)

```text
local_scripts/
└── prompt_linter.py          # [MODIFY] remove PLAN_LEGACY_REQUIRED_H2S + both fallbacks

tests/
├── test_prompt_linter.py     # [MODIFY] legacy-reject assertions (TDD red-first)
└── test_journeys/
    └── test_prompt_linter_journey.py   # [MODIFY] drop legacy-fallback journeys

AGENTS.md                     # [MODIFY] remove RNA-1 from registry/Route A/PLAN CONTENT; INDEXING retired note; onboarding item 5 → cite R-PROC-12
RULES.md                      # [MODIFY] amend R-PROC-1/2/4; [NEW] R-PROC-12
docs/knowledge/rule-map.md    # [MODIFY] add RNA-1 → retired row
docs/knowledge/graph.md       # [NEW] graph concept file
docs/knowledge/index.md       # [MODIFY] add graph.md row (bundle atomicity)
docs/knowledge/log.md         # [MODIFY] append graph.md entry (bundle atomicity)
.agents/plugins/tenirtoo-plugin/skills/docs-update/SKILL.md   # [MODIFY] graphify --update step + validation item; drop legacy naming
CHANGELOG.md                  # [MODIFY] new version entry (CMD-4)

# graphify-managed (via CLI, not hand-edited):
CLAUDE.md                     # graphify claude install appends ## graphify (verify @AGENTS.md shim intact)
.claude/settings*.json        # graphify claude install adds PreToolUse hook
.git/hooks/post-commit        # graphify hook install
graphify-out/                 # graphify update . (git-ignored)
```

**Structure Decision**: Single-project repo; changes are confined to the linter, its tests, governance docs, and the docs-update skill. graphify wiring is done through its own CLI (verified in research D2/D3), not by hand-editing generated files.

## Execution Chunks (→ /speckit-tasks materializes these with gates)

**Chunk A — Spec-kit-only Route A** (FR-001–004, 013)
1. [TDD] Rewrite legacy-fallback tests in `test_prompt_linter.py` + journey → legacy-rejection (red).
2. Remove `PLAN_LEGACY_REQUIRED_H2S` + both fallbacks from `prompt_linter.py`; simplify resolvers (green).
3. Edit `AGENTS.md` (registry/Route A/PLAN CONTENT/INDEXING) + `RULES.md` R-PROC-1/2/4 + `rule-map.md` RNA-1 retired row.
4. Update docs-update `SKILL.md` validation list (drop legacy naming).
5. Run linter + governance + bundle suites. **HARD STOP → approval.**

**Chunk B — Graphify integration** (FR-005–012, 014)
6. Verify global CLI (`--version`, smoke `query`); `graphify claude install` (verify `@AGENTS.md` shim); `graphify hook install` + `hook status`.
7. Add `R-PROC-12` to `RULES.md`; add `docs/knowledge/graph.md` + index row + log entry (bundle atomicity); `AGENTS.md` onboarding item 5 → cite R-PROC-12.
8. Add `graphify --update` step + "graph refreshed" item to docs-update `SKILL.md`.
9. `graphify update .` (rebuild); full regression `pytest -q`.
10. CHANGELOG (CMD-4). **HARD STOP → approval → GW-1 local commit (no push).**

Verification per chunk is in [quickstart.md](quickstart.md); each maps to SC-001…SC-007.
