# Data Model: AI Tooling Remediation (Feature 005)

No database entities are involved (tooling/config feature). The "data model" is the set
of configuration artifacts and their relationships.

## Entities

### CanonicalTestInvocation
- **Form**: `.\venv\Scripts\pytest` (bare), backed by `pytest.ini`
- **Fields**: `pythonpath = .`, `testpaths = tests`
- **Invariants**: collection succeeds from a clean shell at repo root; result counts
  identical to `python -m pytest` baseline
- **Referenced by**: docs/knowledge (testing concept, subagents.md), plugin agent
  `test-runner-and-debugger.md`, quickstart scenarios

### PluginManifest
- **Location**: `.agents/plugins/tenirtoo-plugin/.claude-plugin/plugin.json`
- **Fields**: `name` (tenirtoo-plugin), `version` (2.0.0 — restructure), `description`
- **Replaces**: legacy flat `plugin.json` (deleted)

### MarketplaceEntry
- **Location**: `.claude-plugin/marketplace.json` (repo root)
- **Fields**: marketplace `name`, plugins list → relative `source` path to the plugin
- **Consumed by**: `.claude/settings.json` (`extraKnownMarketplaces`, `enabledPlugins`)

### SkillRegistration (x2)
- `tenirtoo-proposal-analysis`, `tenirtoo-docs-update`
- **Canonical content**: `skills/<dir>/SKILL.md` inside the plugin — single physical copy
  (FR-006)
- **Invariant**: exactly one skill of each name discoverable per session (no duplicate
  collision)

### AgentDefinition (x3)
- `proposal-auditor.md`, `test-runner-and-debugger.md`, `cognitive-ux-auditor.md` under
  the plugin's `agents/`
- **Source**: mechanical mirror of `docs/knowledge/subagents.md` §§1-3
- **Permitted delta**: exactly one — canonical test invocation (FR-008)
- **Invariant**: docs stay descriptive source; mirror location noted in subagents.md

### LintGateFix
- **Target**: `local_scripts/prompt_linter.py` Cyrillic check
- **Invariant**: token flagged ⇔ contains ≥1 Cyrillic letter AND not whitelisted
- **Guarded by**: `tests/test_services/test_prompt_linter.py` (failing-first)

### DevDependencyPin
- **Target**: `requirements-dev.txt` semgrep line
- **New value**: `semgrep>=1.65.0; sys_platform != "win32"`
- **Invariant**: `pip install -r requirements-dev.txt` succeeds on win32

## Relationships

```text
pytest.ini ──enables──> CanonicalTestInvocation ──cited by──> docs + AgentDefinition(test-runner)
PluginManifest ──listed in──> MarketplaceEntry ──wired via──> .claude/settings.json
PluginManifest ──contains──> SkillRegistration(x2) + AgentDefinition(x3)
docs/knowledge/subagents.md ──descriptive source of──> AgentDefinition(x3)
LintGateFix ──guarded by──> test_prompt_linter.py
```
