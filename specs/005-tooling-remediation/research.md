# Research: AI Tooling Remediation (Feature 005)

**Date**: 2026-07-05 | **Plan**: [plan.md](plan.md)

All decisions below resolve the unknowns flagged during planning. No NEEDS CLARIFICATION
markers remain.

## R1. pytest root-on-sys.path mechanism

- **Decision**: Add `pytest.ini` at the repository root:

  ```ini
  [pytest]
  pythonpath = .
  testpaths = tests
  ```

  Canonical invocation becomes `.\venv\Scripts\pytest` (bare form), which matches what
  the docs already prescribe — minimal doc churn.
- **Rationale**: `pythonpath` is a first-class pytest ini option since pytest 7.0
  (installed: 8.1.1); it prepends the root to `sys.path` during collection, which is
  exactly what `python -m pytest` did implicitly via `sys.path[0] = cwd`. `pytest.ini`
  also pins `rootdir` deterministically. `testpaths` keeps bare `pytest` from wandering
  into `venv/`, `scratch/`, `_nogit_*`.
- **Alternatives considered**:
  - Root `conftest.py` — works (pytest inserts the conftest's dir), but adds an empty
    magic file and does not pin rootdir/testpaths.
  - `pyproject.toml [tool.pytest.ini_options]` — equivalent, but the project has no
    pyproject.toml; introducing one just for pytest invites unrelated tool migration.
  - Documenting `python -m pytest` as canonical — leaves the docs' existing
    `.\venv\Scripts\pytest` form broken and requires more doc edits, not fewer.
- **Verification**: run full suite via both forms; result counts must be identical to the
  pre-change `python -m pytest` baseline.

## R2. Claude Code plugin registration mechanics (operator-chosen route)

- **Decision**: Register `tenirtoo-plugin` in place via a project-local marketplace:
  1. Plugin manifest at `.agents/plugins/tenirtoo-plugin/.claude-plugin/plugin.json`
     (`name`, `version`, `description`); delete the legacy flat `plugin.json`.
  2. Components inside the plugin root: existing `skills/proposal-analysis/`,
     `skills/docs-update/` (content untouched); new `agents/` directory with the three
     subagent definition files.
  3. Repo-root local marketplace: `.claude-plugin/marketplace.json` listing the plugin
     with a relative `source` path to `.agents/plugins/tenirtoo-plugin`.
  4. Wire into `.claude/settings.json`: `extraKnownMarketplaces` pointing at the repo
     root (local source) and `enabledPlugins` enabling `tenirtoo-plugin@<marketplace>`.
- **Rationale**: Operator explicitly chose full plugin registration. It keeps the single
  physical source (FR-006), preserves the plugin identity documented in AGENTS.md
  § FILE REGISTRY, and lets one mechanism deliver skills AND agents (US2+US3).
- **Risk & mitigation**: Exact settings-key shapes vary across harness versions. The
  implementing agent MUST verify the keys against the installed Claude Code version
  (`claude plugin --help` / official plugin docs via the docs MCP) before editing
  settings, then confirm discovery in a fresh session at the HARD-STOP gate. **Fallback
  (requires operator approval)**: move `skills/*` to `.claude/skills/` and `agents/*` to
  `.claude/agents/` — losing plugin identity but guaranteeing discovery via the paths
  already proven to work in this repo (speckit skills load from `.claude/skills/` today).
- **Alternatives considered**: symlinks into `.claude/skills/` (fragile on Windows,
  rejected by operator); plain move (rejected by operator in favor of plugin identity).
- **Duplicate-name check**: after registration, the available-skills list must contain
  exactly one `tenirtoo-proposal-analysis` and one `tenirtoo-docs-update`.

## R3. Subagent definition file format

- **Decision**: Standard Claude Code agent markdown files — YAML frontmatter
  (`name`, `description`, optional `tools` allowlist, optional `model`) + system prompt
  body — generated from `docs/knowledge/subagents.md` §§1-3 with zero behavioral deltas
  except one: `test-runner-and-debugger` prescribes the canonical invocation from R1
  (spec FR-008) instead of the previously broken form.
- **Rationale**: `docs/knowledge/subagents.md` already contains complete configs (roles,
  constraints, iteration limits, system prompts); the agent files are a mechanical
  operational mirror. Docs remain the descriptive source of truth; a pointer note in
  subagents.md records the mirror location to prevent silent divergence.
- **Constraint mapping**: `test-runner-and-debugger` — no edits to `tests/*.py` or
  configs, max 3 debug loops; `proposal-auditor` — Route B only, no code;
  `cognitive-ux-auditor` — drives `local_scripts/ux_cognitive_audit.py`.

## R4. prompt_linter Cyrillic false positive

- **Decision**: Keep the token-splitting regex, add a containment filter: a token is a
  violation only if `re.search(r"[а-яА-ЯёЁәӘіІңҢғҒүҮұҰқҚөӨһҺ]", token)` is truthy AND the
  lowercased token is not whitelisted. Equivalent minimal alternative (also acceptable at
  implementation time): drop `\-` from the class and match hyphenated words via an
  explicit group — but the filter is the smaller, more readable diff.
- **Rationale**: Root cause is `\-` inside the character class at
  `local_scripts/prompt_linter.py:61`, letting `-`, `--`, `---` match as "words". The
  filter fixes the class of bugs (any punctuation-only token) rather than one symptom.
- **Tests (failing-first, R-PROC-3)**: new `tests/test_services/test_prompt_linter.py`
  covering: bare hyphen / em-dash sequences (no warning), genuine Russian word (warning
  naming the word), whitelisted terms incl. `Теңир-Тоо` (no warning), mixed token
  `спек-kit` (warning), and the four historical plans 001-004 (zero warnings, SC-002).

## R5. semgrep on native Windows + Docker gate

- **Decision**: (a) Execute `docker-compose --profile lint run --rm semgrep` once during
  implementation; record pass/fail in the walkthrough/verification artifact. (b) Change
  the dev pin to `semgrep>=1.65.0; sys_platform != "win32"` (PEP 508 environment marker).
  (c) Document in the testing concept file: Docker is the canonical semgrep channel
  (R-PROC-11); the host-side `test_semgrep_lint.py` skip on Windows is intended behavior.
- **Rationale**: semgrep does not ship native Windows wheels — the unconditional pin
  makes `pip install -r requirements-dev.txt` fail on the supported dev platform. The
  Docker service already exists in `docker-compose.yml` and the host test already
  auto-skips; only verification and honest documentation are missing.
- **Alternatives considered**: removing the pin entirely (loses the Linux/WSL dev-install
  path); installing semgrep via WSL on this machine (out of scope per spec assumption).
- **Note**: `docker-compose.yml` currently has no `profiles:` key on the semgrep service;
  if `--profile lint` does not select it as R-PROC-11 describes, the implementer fixes
  the compose file to match the documented command (add `profiles: ["lint"]`) — the rule
  text is the contract.

## R6. Dead graphify-wiki reference

- **Decision**: Delete the `graphify-out/wiki/index.md` bullet from `CLAUDE.md`
  (project shim, local file). No replacement: `GRAPH_REPORT.md` + `query/path/explain`
  already cover navigation per R-PROC-12.
- **Rationale**: graphify CLI 0.8.49 exposes no wiki subcommand; the conditional never
  fires and misleads audits. Nothing blocks re-adding the line if graphify gains the
  capability (US6 acceptance 2).
- **Sweep**: implementation includes a repo-wide search for other references to
  non-producible artifacts in agent-facing instruction files (SC-005); known survivors in
  read-only specs 001-004 are exempt.

## R7. Governance-test interaction

- **Decision**: Treat `tests/test_governance.py` and `tests/test_knowledge_bundle.py` as
  hard regression gates at every chunk boundary; if a doc edit trips a pinned assertion,
  the fix updates the doc-edit (or, where the test itself encodes the stale instruction —
  e.g. the broken pytest form — the test is updated in the same TDD step with explicit
  note in the walkthrough).
- **Rationale**: These tests pin doc structure/content; feature 005 edits governed docs
  (subagents.md, testing concept, CLAUDE.md shim), so collisions are foreseeable and must
  be planned, not discovered.
