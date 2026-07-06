# Contract: Plugin Registration (tenirtoo-plugin)

**Consumers**: Claude Code harness (fresh session discovery); AGENTS.md § FILE REGISTRY /
§ SUBAGENTS; Route B and Route C workflows.

## Provided interface

After implementation, a fresh session in this project MUST expose:

| Capability | Name | Kind |
|---|---|---|
| Route B audit engine | `tenirtoo-proposal-analysis` | Skill (invocable) |
| Route C docs-sync engine | `tenirtoo-docs-update` | Skill (invocable) |
| Dialectic auditor | `proposal-auditor` | Agent type (delegable) |
| Test runner/debugger | `test-runner-and-debugger` | Agent type (delegable) |
| UX walkthrough auditor | `cognitive-ux-auditor` | Agent type (delegable) |

## Structural contract

```text
.agents/plugins/tenirtoo-plugin/
├── .claude-plugin/plugin.json        # {name, version, description}
├── skills/
│   ├── proposal-analysis/SKILL.md    # frontmatter name: tenirtoo-proposal-analysis (unchanged)
│   └── docs-update/SKILL.md          # frontmatter name: tenirtoo-docs-update (unchanged)
└── agents/
    ├── proposal-auditor.md           # frontmatter: name, description; body = system prompt
    ├── test-runner-and-debugger.md
    └── cognitive-ux-auditor.md

.claude-plugin/marketplace.json       # repo-root local marketplace listing the plugin
.claude/settings.json                 # extraKnownMarketplaces + enabledPlugins
```

## Guarantees

1. **Single source**: skill/agent content exists in exactly one physical location (the
   plugin). No copy in `.claude/skills/` or `.claude/agents/`.
2. **No duplicate names**: the session skill list contains each skill name exactly once.
3. **Behavioral fidelity**: agent definitions match `docs/knowledge/subagents.md` §§1-3;
   the sole permitted delta is the canonical test invocation in
   `test-runner-and-debugger` (FR-008).
4. **Fallback (gated)**: if the installed harness does not honor the marketplace wiring,
   the fallback (relocate to `.claude/skills/` + `.claude/agents/`) may be applied ONLY
   after operator approval at the corresponding HARD-STOP gate; guarantee 1 then applies
   to the new location and AGENTS.md § FILE REGISTRY is updated in the same change.

## Verification

Fresh-session check: list available skills and agent types; invoke each skill once
(content loads, matches canonical SKILL.md); confirm the three agent types are offered.
