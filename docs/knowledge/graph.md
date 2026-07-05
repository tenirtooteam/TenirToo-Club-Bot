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
| `graphify extract <path> --backend deepseek` | **Code + semantic** (docs/prose) via graphify's own headless API call | DeepSeek (see Model config) |
| `graphify hook install` / `hook status` | installs the git post-commit/post-checkout auto-rebuild | one-time |

After a semantic `extract`, run `graphify cluster-only <path> --backend deepseek` to regenerate
`GRAPH_REPORT.md` and name the communities.

## Model configuration

graphify runs its semantic LLM work **headlessly via the DeepSeek backend** — a direct API call
from graphify's own process, never the interactive session's budget. It needs `DEEPSEEK_API_KEY`
in the environment (kept in `.claude/settings.json` `env` block); graphify auto-selects the
backend from whichever API key is set. Query and `graphify update` (code-only, AST) need no LLM
at all. A full semantic pass over this repo costs ~$0.02 on DeepSeek.

**Backend note:** the `claude-cli` backend (`GRAPHIFY_CLAUDE_CLI_MODEL=haiku`) is also wired but
does NOT work from sandboxed agent shells (its `claude -p` subprocess reports `Not logged in`);
DeepSeek is the working default here. In a normal developer terminal claude-cli would also work.

## Two freshness channels

The graph rots silently if left alone, so R-PROC-12's "trust the graph before source" is
kept honest by two independent update paths:

1. **Code channel — automatic.** The git **post-commit hook** (`graphify hook install`)
   re-extracts changed `.py` files after every commit. No manual step; AST only.
2. **Docs / semantic channel — Route C.** After a documentation change, the
   `tenirtoo-docs-update` skill runs `graphify extract . --backend deepseek` (AST + semantic
   via graphify's own headless API call), because `graphify update` alone (code-only) does not
   re-read prose. This step performs **no git operation** — it only rewrites the git-ignored
   `graphify-out/`, so it is compatible with Route C's no-git rule.

If you have reason to believe both channels are stale (e.g. hook uninstalled and no recent
docs-update run), rebuild before trusting a structural answer.

## Fallback when the CLI is absent

If `graphify` is not installed or `graphify-out/graph.json` is missing, answer structural
questions by reading source directly and state the degradation explicitly in the response.
The graph is an accelerator, not a trust anchor — correctness always comes from source.
