# Data Model: Spec-Kit-Only Route A + Full Graphify Integration

No database or runtime entities change. The "entities" here are governance/tooling artifacts and their invariants.

## Governance artifacts

| Entity | Location | Invariant after this feature |
|---|---|---|
| Canonical plan artifact | `specs/<feature>/plan.md` | The only plan the linter accepts (`plan` stage). Legacy `implementation_plan.md` rejected for new features. |
| Canonical checklist artifact | `specs/<feature>/tasks.md` | The only checklist the linter accepts (`checklist` stage). Legacy `task.md` rejected. |
| Retired command | `RNA-1` | Recorded as retired in `AGENTS.md` § INDEXING and `rule-map.md`; never invoked for new features. |
| New rule | `R-PROC-12` | Tier-A rule mandating graph-first querying with an explicit CLI-absent fallback. Unique ID, never reused. |
| Amended rules | `R-PROC-1`, `R-PROC-2`, `R-PROC-4` | Prose updated to name `plan.md`/`tasks.md` as sole canonical artifacts; no ID renumbering. |
| Knowledge concept file | `docs/knowledge/graph.md` | Describes the graph, CLI commands, freshness channels, fallback. Registered in `index.md` + `log.md` (bundle atomicity). |

## Graph freshness state machine

```text
                    ┌─────────────── code commit ──────────────┐
                    │  (git post-commit hook, automatic, AST)   │
                    ▼                                           │
   [graph.json] ──── stale on code change ──▶ [rebuilt: code layer] ──┘

                    ┌──────── docs/rules change (Route C) ──────┐
                    │  (docs-update skill → /graphify --update, │
                    │   AST + semantic/LLM)                     │
                    ▼                                           │
   [graph.json] ─── stale on doc change ──▶ [rebuilt: code+semantic] ─┘
```

- **Code channel**: triggered by every commit touching `.py`; owner = git hook (installed once, FR-007).
- **Docs/semantic channel**: triggered by CMD-1/CMD-2 doc edits; owner = `tenirtoo-docs-update` skill (FR-012); no git op.
- **Invariant**: `R-PROC-12`'s "trust the graph before source" is only sound while at least one channel keeps `graph.json` current; both channels together cover code and docs.

## Linter contract transition

| Stage | Before (feature 003) | After (this feature) |
|---|---|---|
| plan | `plan.md` preferred, `implementation_plan.md` fallback | `plan.md` only |
| checklist | `tasks.md` preferred, `task.md` fallback | `tasks.md` only |
| report | `walkthrough.md` | `walkthrough.md` (unchanged) |
