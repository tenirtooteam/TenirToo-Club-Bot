# Research: Spec-Kit-Only Route A + Full Graphify Integration

Phase 0 findings. All NEEDS CLARIFICATION resolved against the actual repository state and the installed graphify CLI (v0.8.49), not against documentation assumptions.

## D1. graphify install location — global, not the bot venv

- **Decision**: Use the existing **global** graphify install (`graphifyy` 0.8.49, `C:\Users\user\AppData\Local\Programs\Python\Python311`, `graphify` on PATH). Do **NOT** `pip install` graphify into the project `venv`.
- **Rationale**: graphify is an AI-assistant orchestration tool that operates *on* the repository (like git/ripgrep), never imported by bot or test code. The graph was already built with the global Python311 (recorded in `graphify-out/.graphify_python`). `R-PROC-7` (venv isolation) governs bot dev/test/execution — graphify is none of those. Adding it to the runtime venv would pull heavy transitive deps (networkx, etc.) into a clean bot environment for zero runtime benefit.
- **Impact on spec**: FR-005 changes from "install into venv" to "verify the global install is functional; smoke-test `graphify query`". No venv mutation.
- **Alternatives rejected**: venv install (pollutes runtime deps); pinning a second copy (drift between two installs).

## D2. Actual graphify CLI surface (v0.8.49) — verified command forms

Verified via `graphify --help`. The `/graphify` *skill* slash-syntax differs from the *CLI* subcommand syntax; the plan/tasks MUST use the CLI form:

| Need | Correct CLI form | Notes |
|---|---|---|
| Query the graph | `graphify query "<question>"` | BFS traversal of `graph.json` |
| Shortest path | `graphify path "A" "B"` | |
| Explain a node | `graphify explain "X"` | |
| Rebuild after code change | `graphify update <path>` | **code-only (AST, no LLM)**; NOT `graphify --update` |
| Git auto-rebuild hooks | `graphify hook install` / `hook status` / `hook uninstall` | post-commit + post-checkout |
| Claude Code integration | `graphify claude install` | writes `## graphify` section to CLAUDE.md **and** a PreToolUse hook to `.claude/settings.json` |

- **Correction**: The spec's `graphify --update` references are the skill slash-form; the CLI subcommand is `graphify update .`. Tasks use `graphify update .` for code and the `/graphify … --update` skill flow for semantic/doc refresh (see D4).

## D3. `graphify claude install` side effects — CLAUDE.md + settings.json

- **Decision**: Run `graphify claude install`. Before/after, verify: (a) `CLAUDE.md` retains its `@AGENTS.md` shim (the command appends a `## graphify` section, does not replace); (b) the added PreToolUse hook in `.claude/settings.json` (or `settings.local.json`) is acceptable — it makes the graph-check automatic before tool use, which is exactly the R-PROC-12 intent.
- **Rationale**: This is the "install everything for full graph operation" requirement — it wires graphify into every future Claude Code session natively, beyond the in-repo `R-PROC-12` rule (which also serves non-Claude agents).
- **Risk**: If `claude install` overwrites rather than appends, the `@AGENTS.md` shim could be lost. Mitigation: read `CLAUDE.md` before and after; if the shim is gone, restore it in the same task. TDD-style verification captured in quickstart.

## D4. Two update channels — code (hook/CLI) vs docs+semantic (skill/LLM)

- **Decision**: Split graph freshness into two governed channels:
  - **Code channel (automatic)**: `graphify hook install` → post-commit re-extracts changed `.py` files (AST). Covers every code commit with no manual step.
  - **Docs/semantic channel (Route C)**: The `tenirtoo-docs-update` skill, after a CMD-1/CMD-2 documentation edit, runs the semantic-aware update. Because doc/semantic extraction needs the LLM subagent flow, the docs-update step invokes the `/graphify <root> --update` **skill** path (AST + semantic), not the code-only `graphify update` CLI.
- **Rationale**: `graphify update` CLI is explicitly "no LLM needed" (code only). Documentation changes alter the semantic layer, which only the skill's subagent/Gemini flow re-extracts. Pointing docs-update at the code-only CLI would leave doc changes unreflected — defeating the user's "документация, ЛЛМ" requirement.
- **Constraint**: Route C performs **no git operations** (`R-PROC-5`/Route C rule). Running `graphify update` does not commit — it only rewrites `graphify-out/` (git-ignored). So the step is compatible with the Route C no-git constraint. The post-commit *hook* is a git-layer mechanism installed once (FR-007), separate from Route C execution.
- **Alternatives rejected**: code-only CLI in docs-update (misses semantic layer); requiring a full manual rebuild every docs change (expensive, discourages compliance).

## D5. Linter legacy removal — test coupling is contained

- **Decision**: Remove `PLAN_LEGACY_REQUIRED_H2S`, the `implementation_plan.md` fallback in `find_plan_file`, and the `task.md` fallback in `find_checklist_file`. Both resolvers return only `plan.md`/`tasks.md` or `(None, None)`.
- **Coupling found**:
  - `tests/test_prompt_linter.py` — unit tests explicitly assert the legacy fallbacks (`find_plan_file falls back to implementation_plan.md`, `find_checklist_file falls back to task.md`). These MUST be rewritten to assert legacy names are now rejected (return `(None, None)` / linter errors). TDD: rewrite tests red-first.
  - `tests/test_journeys/test_prompt_linter_journey.py` — journey tests for v2-preferred-over-legacy end-to-end. The "legacy fallback" journeys are removed; the "v2 only" journeys stay.
  - `tests/test_governance.py` — **no** references to `RNA-1`, R-PROC wording, `implementation_plan.md`, or graphify (grep-verified). Editing AGENTS.md/RULES.md prose will not break exact-text assertions there.
  - `tests/fixtures/rules_inventory_baseline.txt` — a **frozen** baseline; line 307 references `implementation_plan.md` as a historical GEMINI.md section anchor. It is NOT modified (feature-003 froze it); the linter change does not touch it.
- **Rationale**: The linter runs only during an active Route A feature. Completed features 001–003 are never re-linted, so dropping legacy support cannot retroactively break them.

## D6. Rule additions/edits — format and ID permanence

- **Decision**: Add `R-PROC-12 [A]` (new ID, never reuse). Amend prose of `R-PROC-1`, `R-PROC-2`, `R-PROC-4` in place without renumbering. Add an `RNA-1 → retired` disposition row to `docs/knowledge/rule-map.md`.
- **Rationale**: `R-CODE-7` / constitution principle V — IDs are permanent; retired rules are marked, not deleted. `test_imperatives_map_to_rules` (from feature 003) tolerates a `retired` disposition, so the RNA-1 retirement row is compatible.
- **Format**: `R-PROC-12` follows the Tier-A shape (Rule / Why / Legacy). No legacy anchor (net-new rule) → omit or mark `Legacy: —`.

## D7. Executor model

- **Decision**: **Claude Opus** end-to-end (current session model is already `claude-opus-4-8`).
- **Rationale**: Cross-file governance coupling (RULES prose ↔ linter code ↔ linter tests ↔ governance tests), ID-permanence discipline, and the CLAUDE.md/settings.json side-effect verification are judgment-heavy. The graphify chunk alone would suit Sonnet, but a single-feature model split costs more in handoff than it saves.
- **Fallback**: If budget-constrained — Opus for Chunk A (governance/linter), Sonnet for Chunk B (graphify tooling).
