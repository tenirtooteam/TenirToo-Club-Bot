---
type: graph-guide
title: Knowledge Graph — Usage & Freshness
description: How the graphify knowledge graph works, its query commands, and the two channels that keep it current.
timestamp: 2026-07-04
---

# Knowledge Graph (graphify)

The repository is indexed into a persistent knowledge graph under `graphify-out/`
(git-ignored, regenerable). It lets any assistant answer structural questions —
architecture, file relationships, call graphs, data flow — by traversing an extracted
map instead of re-reading source. The governed obligation to use it first lives in
[RULES.md](../../RULES.md) as **R-PROC-12**; this file is the descriptive how-to.

## Where it lives

- `graphify-out/graph.json` — the graph data (nodes + edges + communities).
- `graphify-out/GRAPH_REPORT.md` — human-readable audit (god nodes, communities, surprises).
- `graphify-out/.graphify_python` / `.graphify_root` — the interpreter and scan root recorded
  at build time. The tool runs from the **global** install (`graphifyy` on PATH), not the
  bot `venv` — it is an orchestration tool that operates on the repo, never imported by
  bot or test code.

## Query commands (read the graph — no rebuild)

| Command | Purpose |
|---|---|
| `graphify query "<question>"` | BFS traversal for a natural-language question — broad context. |
| `graphify query "<question>" --dfs` | Depth-first — trace one specific path. |
| `graphify path "A" "B"` | Shortest path between two named nodes. |
| `graphify explain "X"` | Plain-language explanation of a node and its neighbours. |

Answer only from what the traversal returns; quote a node's `src=…loc=…` when citing a fact.
If the CLI is missing, read source directly and say so — never pretend the graph answered.

## Rebuild commands (refresh the graph)

| Command | Layer refreshed | Cost |
|---|---|---|
| `graphify update <path>` | **Code only** (AST) — deterministic | free, no LLM |
| `graphify extract <path> --backend claude-cli` | **Code + semantic** (docs/prose) via graphify's own `claude -p` subprocess | Haiku (see Model config) |
| `graphify hook install` / `hook status` | installs the git post-commit/post-checkout auto-rebuild | one-time |

## Model configuration

graphify runs its LLM work **natively through the Claude Code CLI** (`claude-cli` backend) —
a separate `claude -p` subprocess, not the interactive session. The model for that subprocess
is pinned to **Haiku** via `GRAPHIFY_CLAUDE_CLI_MODEL=haiku` in `.claude/settings.json` (`env`
block); without it the claude-cli backend defaults to Opus (overkill for structured extraction).
Query/`update` need no model. Semantic rebuilds use `--backend claude-cli`, so the doc/prose
layer is re-extracted on Haiku without spending the main session's budget.

**Note on auth:** the `claude-cli` backend shells out to a standalone `claude -p` subprocess
and uses the developer's normal Claude Code login — in a regular terminal it just works.
A `Not logged in` error can appear only in sandboxed agent shells that proxy API access
(no credentials visible to subprocesses); in that case run the semantic extract from a
normal terminal instead. Query and `graphify update` (code-only) never need the LLM at all.

## Two freshness channels

The graph rots silently if left alone, so R-PROC-12's "trust the graph before source" is
kept honest by two independent update paths:

1. **Code channel — automatic.** The git **post-commit hook** (`graphify hook install`)
   re-extracts changed `.py` files after every commit. No manual step; AST only.
2. **Docs / semantic channel — Route C.** After a documentation change, the
   `tenirtoo-docs-update` skill runs `graphify extract . --backend claude-cli` (AST + semantic
   on Haiku, via graphify's own `claude -p` subprocess), because `graphify update` alone
   (code-only) does not re-read prose. This step performs **no git operation** — it only
   rewrites the git-ignored `graphify-out/`, so it is compatible with Route C's no-git rule.

If you have reason to believe both channels are stale (e.g. hook uninstalled and no recent
docs-update run), rebuild before trusting a structural answer.

## Fallback when the CLI is absent

If `graphify` is not installed or `graphify-out/graph.json` is missing, answer structural
questions by reading source directly and state the degradation explicitly in the response.
The graph is an accelerator, not a trust anchor — correctness always comes from source.
