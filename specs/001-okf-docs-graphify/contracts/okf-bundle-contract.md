# Contract: OKF Reference Bundle Interface

**Date**: 2026-07-02. This contract defines what AI agents (consumers) and the docs-update skill (producer) may rely on. `tests/test_knowledge_bundle.py` is the contract's enforcement.

## Consumer contract (any AI agent on a Route A task)

1. **Mandatory pre-read set** is exactly: `PROJECT_LOGIC.md`, `CONTEXT_PROMPT.md`, `docs/knowledge/index.md`. Nothing else in the bundle is pre-read.
2. **Lookup protocol**: To resolve reference data, the agent scans `index.md` descriptions, then opens only the matching concept file(s).
3. **Anchor resolution**: Any `PL-x.y` citation resolves inside `PROJECT_LOGIC.md` — either to full rule text or to a stub naming the bundle file. Agents MUST follow the stub rather than assume missing content.
4. **Tolerance**: Agents MUST tolerate unknown front-matter fields and unknown `type` values (forward compatibility, per OKF philosophy).

## Producer contract (docs-update skill, CMD-1 / CMD-2)

1. **Routing rule**: Imperative rules → core files. Descriptive reference content → the owning concept file. New reference topic → new concept file + index entry + log entry, in the same change.
2. **Atomicity**: A concept file change is complete only with its `index.md` description kept in sync (if changed) and a `log.md` entry appended.
3. **Front matter**: Producer MUST write all required fields (`type`, `title`, `description`, `timestamp`) and update `timestamp` on every content change.
4. **No duplication**: Content moved to the bundle MUST NOT be restated in core files beyond a one-line stub summary (Content Ownership rule extension).

## Enforcement mapping

| Contract clause | Enforced by |
|---|---|
| Front matter completeness | `test_frontmatter_required_fields` |
| Index ↔ files bidirectional consistency | `test_index_matches_files` |
| Anchor survival in core | `test_pl_anchors_preserved` |
| No dangling bundle paths from core | `test_core_bundle_references_resolve` |
| Corruption absence in CONTEXT_PROMPT.md | `test_cp_corruption_absent` |
| Bundle log non-empty | `test_log_exists_nonempty` |

Test names are binding for the implementer (spec SC-003 mutation checks reference them).
