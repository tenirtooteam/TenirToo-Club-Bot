# Contracts: Linter v3 + R-PROC-12

## Contract 1 — `prompt_linter.py` (spec-kit-only)

**`find_plan_file(dir_path) -> (str | None, bool)`**
- Returns `(<dir>/plan.md, True)` if `plan.md` exists, else `(None, ...)`.
- MUST NOT return `implementation_plan.md`. `PLAN_LEGACY_REQUIRED_H2S` removed.
- Return-type note: legacy `is_v2` flag becomes vestigial (always True on hit); acceptable to keep the tuple shape for minimal test churn, or simplify to `str | None`. Implementation decides; tests assert behavior, not shape.

**`find_checklist_file(dir_path) -> (str | None, bool)`**
- Returns `(<dir>/tasks.md, True)` if `tasks.md` exists, else `(None, ...)`.
- MUST NOT return `task.md`.

**CLI behavior**
- `--stage plan` on a dir with only `implementation_plan.md` → prints `Error: no plan.md found in <dir>.`, exit 1.
- `--stage checklist` on a dir with only `task.md` → prints `Error: no tasks.md found in <dir>.`, exit 1.
- `--stage plan` on a valid `plan.md` (H2s: Summary, Technical Context, Constitution Check, Project Structure) → `Plan is valid.`, exit 0.
- `--stage checklist` on a `tasks.md` whose last task is the linter run and all boxes `[x]` → `Checklist is valid.`, exit 0.
- `--stage report` unchanged.

**Test contract** (`tests/test_prompt_linter.py`, `tests/test_journeys/test_prompt_linter_journey.py`)
- Legacy-fallback assertions replaced by legacy-rejection assertions (red-first, then green).
- v2 (plan.md/tasks.md) happy-path assertions retained.

## Contract 2 — `R-PROC-12 [A]` (RULES.md)

```
### R-PROC-12 [A] Graph-first for structural questions
**Rule**: When `graphify-out/` exists, architecture / relationship / data-flow / "what calls X" questions
MUST be answered via `graphify query "<question>"` (or `path`/`explain`) BEFORE reading source; source
reads are for verification and detail, not first-pass discovery. If the graphify CLI is unavailable, fall
back to source reads and STATE the degradation explicitly. Graph freshness is maintained on two channels:
code via the post-commit git hook (`graphify hook install`), docs/semantic via the docs-update skill
(`graphify --update`) — never trust the graph if you have reason to believe both channels are stale.
**Why**: The graph is the cheapest correct map of the codebase; querying first saves context and surfaces
cross-module connections source-diving misses. The explicit fallback prevents the rule from becoming a
hazard when the tool is absent.
**Legacy**: —
```

**Test contract**: `R-PROC-12` must satisfy whatever structural checks `tests/test_governance.py` applies to every rule (ID pattern, Why present, tier tag). No exact-text assertion exists for it (net-new).

## Contract 3 — Bundle atomicity for `docs/knowledge/graph.md`

A single edit MUST produce all three:
1. `docs/knowledge/graph.md` with YAML front matter (`type`, `title`, `description`, `timestamp: 2026-07-04`).
2. A new row in `docs/knowledge/index.md` concept-files table.
3. An appended `2026-07-04 — graph.md — <summary>` line in `docs/knowledge/log.md`.

Verified by `tests/test_knowledge_bundle.py` (front matter + index/log presence checks).
