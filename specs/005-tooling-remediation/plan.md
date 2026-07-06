# Implementation Plan: AI Tooling Remediation (July 2026 Audit)

**Branch**: `005-tooling-remediation` | **Date**: 2026-07-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-tooling-remediation/spec.md`

## Summary

Restore the five broken/unverified capabilities of the AI process toolchain and remove one
dead reference, without touching bot production code (FR-012):

1. **P1 — Test invocation** (US1): `.\venv\Scripts\pytest` fails at collection
   (`ModuleNotFoundError: database`) because the project root is not on `sys.path` — there
   is no `pytest.ini` / `pyproject.toml` / root `conftest.py`. Fix: add `pytest.ini` with
   `pythonpath = .`, keep `python -m pytest` behavior identical, align all living docs on
   one canonical form.
2. **P2 — Plugin registration** (US2+US3, operator decision): restructure
   `.agents/plugins/tenirtoo-plugin` into a proper Claude Code plugin
   (`.claude-plugin/plugin.json`, `skills/`, `agents/`) registered through a local
   marketplace entry in `.claude/settings.json`. The plugin carries BOTH the two Route B/C
   engine skills AND the three subagent definitions generated from
   `docs/knowledge/subagents.md` — one mechanism closes US2 and US3.
3. **P3 — Linter false positive** (US4): `local_scripts/prompt_linter.py:61` matches
   punctuation-only tokens as "Cyrillic words" because `\-` sits inside the character
   class. Fix: post-filter tokens to require at least one Cyrillic letter; add regression
   tests (TDD: failing test first, R-PROC-3).
4. **P3 — Semgrep gate verification** (US5): run the canonical Docker channel
   (`docker-compose --profile lint run --rm semgrep`) once, record the result; add a
   platform marker to `requirements-dev.txt` (`semgrep>=1.65.0; sys_platform != "win32"`)
   and document the Windows host-skip as intended behavior.
5. **P4 — Dead wiki reference** (US6): remove the `graphify-out/wiki/index.md` line from
   `CLAUDE.md` (graphify CLI 0.8.49 has no wiki capability).

**Task RNA (logic, risks, edge cases)**: The plugin-registration mechanics are the only
genuinely risky element — settings keys (`extraKnownMarketplaces`, `enabledPlugins`) and
manifest layout must be verified against the installed harness at implementation time; a
verification HARD-STOP gate follows the registration chunk, with the documented fallback
(move skills to `.claude/skills/`, agents to `.claude/agents/`) requiring operator
approval before use. `pytest.ini` changes rootdir/collection behavior — the full suite
must be re-run and compared against the `python -m pytest` baseline. Duplicate-skill-name
collision (canonical + registered copy in one session) must be checked after registration.
Governance tests (`tests/test_governance.py`, `tests/test_knowledge_bundle.py`) may pin
doc contents — they are part of every verification step.

## Technical Context

**Language/Version**: Python 3.11 (venv mandatory, R-PROC-7); PowerShell 5.1 host; Git Bash available

**Primary Dependencies**: pytest 8.1.1, ruff 0.3.4, import-linter 2.1, semgrep (Docker image `returntocorp/semgrep`), Docker 29.5.3, Claude Code harness (plugin/skill/agent discovery), graphify CLI 0.8.49

**Storage**: N/A (filesystem config artifacts only)

**Testing**: pytest via the canonical invocation being fixed by this very feature; baseline `python -m pytest` (verified green: lint-gate subset `2 passed, 1 skipped`); new regression tests for `prompt_linter.py`

**Target Platform**: Windows 10 native dev machine (win32); Docker Desktop for the semgrep gate

**Project Type**: Tooling/process infrastructure (no bot runtime changes — FR-012)

**Performance Goals**: N/A (correctness-only feature)

**Constraints**: Single source of truth for skill content (FR-006); `docs/knowledge/subagents.md` stays descriptive source, plugin `agents/` files are its operational mirror; historical specs 001-004 are read-only; no `git push` (R-PROC-5); planning on Fable, implementation on Opus/Sonnet with HARD-STOP gates

**Scale/Scope**: ~14 files touched — 3 new config/test files, 1 modified script, plugin restructure (~7 files moved/created), 3-4 doc edits

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Rule | Applicability | Status |
|---|---|---|
| I. Layered Isolation (R-ARCH-1/2/4/8) | Not touched — no production imports change; import-linter re-run as regression guard | PASS |
| II. Sterile Interface (R-UI-1, R-FSM-1) | Not touched | PASS (N/A) |
| III. Service-Mediated Mutation (R-DATA-1/4) | Not touched | PASS (N/A) |
| IV. Test-First (R-PROC-3, R-TEST-1/3) | Linter bug gets a failing reproducing test BEFORE the fix; pytest.ini change validated against pre-recorded baseline; mock assertions check args and kwargs (R-TEST-3) where mocks are used | PASS |
| V. Single Source & Traceability (R-CODE-7) | Plugin move keeps one physical skill location; subagent docs remain descriptive source; plan cites rule IDs, never restates text | PASS |
| R-PROC-1 (align global options first) | Registration mechanism chosen by operator (full plugin registration) before this plan | PASS |
| R-PROC-2 (plan blueprint, incremental updates) | This plan carries the blueprint mapping; future corrections are incremental | PASS |
| R-PROC-4 (prompt-linter gates) | Linter runs after this plan (plan stage) and after tasks.md (checklist stage) | PASS |
| R-PROC-5 (no push without request) | Only local commits at milestones (GW-1) | PASS |
| R-PROC-10/11 (linter config parity, semgrep ruleset) | No new module/layer added; semgrep gate itself is verified by US5 | PASS |
| R-PROC-12 (graph-first) | `graphify update .` (AST-only) after implementation; no manual graph edits | PASS |

No violations — Complexity Tracking not required.

**Post-design re-check (after Phase 1)**: unchanged — design artifacts introduce no new
projects, layers, or rule violations. PASS.

## Project Structure

### Documentation (this feature)

```text
specs/005-tooling-remediation/
├── spec.md              # Feature specification (done)
├── plan.md              # This file
├── research.md          # Phase 0 — decisions on plugin mechanics, pytest config, regex fix, semgrep marker
├── data-model.md        # Phase 1 — config-artifact entities and relationships
├── quickstart.md        # Phase 1 — end-to-end validation guide
├── contracts/           # Phase 1 — plugin-manifest and canonical-invocation contracts
│   ├── plugin-registration.md
│   └── canonical-test-invocation.md
├── checklists/
│   └── requirements.md  # Spec quality checklist (done)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

Proposed changes (`[NEW]` / `[MODIFY]` / `[DELETE]` / `[MOVE]`):

```text
pytest.ini                                          [NEW]     pythonpath = ., testpaths = tests
local_scripts/prompt_linter.py                      [MODIFY]  Cyrillic check: require >=1 Cyrillic letter per token
tests/test_services/test_collection_smoke.py        [NEW]     subprocess pytest --collect-only smoke (failing-first for the collection bug, R-PROC-3)
tests/test_services/test_prompt_linter.py           [NEW]     regression tests for the linter (failing-first, R-PROC-3)
requirements-dev.txt                                [MODIFY]  semgrep pin gains `; sys_platform != "win32"` marker

.claude-plugin/marketplace.json                     [NEW]     local marketplace listing tenirtoo-plugin (exact layout per research.md)
.agents/plugins/tenirtoo-plugin/
├── .claude-plugin/plugin.json                      [NEW]     proper plugin manifest (name, version, description)
├── plugin.json                                     [DELETE]  superseded by .claude-plugin/plugin.json
├── skills/proposal-analysis/SKILL.md               [KEEP]    canonical content, unchanged location inside plugin
├── skills/docs-update/SKILL.md                     [KEEP]    canonical content, unchanged location inside plugin
└── agents/
    ├── proposal-auditor.md                         [NEW]     generated from docs/knowledge/subagents.md §1
    ├── test-runner-and-debugger.md                 [NEW]     generated from §2, prescribing the canonical invocation
    └── cognitive-ux-auditor.md                     [NEW]     generated from §3

.claude/settings.json                               [MODIFY]  extraKnownMarketplaces + enabledPlugins entries
CLAUDE.md                                           [MODIFY]  remove dead graphify-wiki line
docs/knowledge/subagents.md                         [MODIFY]  fix test invocation instruction; note operational mirror location
docs/knowledge/testing.md (or equivalent concept)   [MODIFY]  document canonical invocation + semgrep Windows-skip
```

**Structure Decision**: All changes live in tooling/config surfaces (`pytest.ini`,
`local_scripts/`, `tests/test_services/`, `.claude*/`, `.agents/`, docs). Directories
`handlers/`, `services/`, `middlewares/`, `database/`, `keyboards/`, `web/` are untouched
(FR-012, SC-006). The plugin remains physically at `.agents/plugins/tenirtoo-plugin/` —
registration makes the harness read it in place, preserving the single source of truth
(FR-006); no content is duplicated into `.claude/skills/`.

## Verification

- **Reproducing tests (R-PROC-3)**: `tests/test_services/test_prompt_linter.py` — the
  punctuation-only false-positive case MUST fail against the unmodified linter, then pass
  after the fix. The pytest-collection bug gets an automated failing-reproducing test
  (`tests/test_services/test_collection_smoke.py`, subprocess `pytest --collect-only`
  asserting exit 0) that fails before `pytest.ini` exists and passes after — honoring
  R-PROC-3 by the letter for a test-harness bootstrap bug.
- **End-to-end**: quickstart.md scenarios — canonical pytest run, fresh-session skill and
  agent discovery, linter re-run over specs 001-004 (zero warnings, SC-002), Docker
  semgrep gate pass (SC-004), artifact-reference sweep (SC-005), production-code diff
  check (SC-006).
- **Regression guards**: full `python -m pytest` suite, `ruff check .`, `lint-imports`,
  governance tests — all green at every HARD-STOP gate.

## Complexity Tracking

No constitution violations — table not required.
