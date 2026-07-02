# Data Model: Governance Consolidation

**Date**: 2026-07-02. Entities are markdown documents and machine-checkable structures.

## Entity: Rule Entry (in `RULES.md`)

```text
### R-<DOMAIN>-<n> [A|B] <Short Title>
**Rule**: <imperative statement — the single authoritative text>
**Why**: <one-line rationale>
**Enforced by**: <mechanism>            # Tier B only; omitted for Tier A
**Legacy**: PL-x.y, CP-x.y[, GEMINI §…] # every anchor this entry absorbs
```

Tier B compact form (one line): `- R-<DOMAIN>-<n> [B] <statement> — enforced by <mechanism> (Legacy: …)`

**Domains**: ARCH, DB, UI, FSM, CODE, TEST, PROC, SEC.

**Validation**: IDs unique (`test_rule_ids_unique`); every Tier-B `Enforced by` target exists (`test_tier_b_enforcement_exists`); every legacy anchor listed exactly once across all entries (feeds rule-map generation).

## Entity: Rule Map (`docs/knowledge/rule-map.md`)

Table: `| Legacy anchor | New home |` where New home is an `R-<DOMAIN>-<n>` ID or a `docs/knowledge/<file>.md` path. Generated from Rule Entry `Legacy:` fields plus the D6 dissolution map for descriptive anchors.

**Validation**: every anchor from `tests/fixtures/rules_inventory_baseline.txt` (250 PL + all CP + GEMINI section names) has a row; every row's target exists (`test_rule_map_complete`).

## Entity: Constitution (`AGENTS.md`, tracked)

Sections: Identity & Brief; Onboarding (pre-read set, progressive disclosure, graphify); Routes A–D; Command Registry; RNA-Blueprint format; Git Protocol; Response Protocol; Subagents; File Registry; Content Ownership. May cite `R-*` IDs; MUST NOT contain full rule texts (that would re-create F1).

**Validation**: `test_no_duplicate_rule_text` shingle scan covers it.

## Entity: Shim (`CLAUDE.md`, `GEMINI.md`)

≤3 lines, pointer/import only (e.g. `@AGENTS.md` / "All project governance lives in AGENTS.md"). **Validation**: `test_shims_are_pure` (no MUST/prohibited/forbidden/never/strictly content lines).

## Entity: Redirect Index (post-dissolution `PROJECT_LOGIC.md`, `CONTEXT_PROMPT.md`)

≤15 lines: purpose note ("dissolved 2026-07-02"), pointer to `RULES.md`, `docs/knowledge/index.md`, and `docs/knowledge/rule-map.md` for legacy anchors. Stays tracked (public contract, git history preserves old content).

## Entity: Frozen Rule Inventory (`tests/fixtures/rules_inventory_baseline.txt`)

One line per pre-consolidation normative statement: `<anchor> | <first 80 chars of statement>` — captured in Phase 1 from GEMINI.md, PROJECT_LOGIC.md, CONTEXT_PROMPT.md before any edit. Feeds the retention diff (zero-loss check) and the rule map completeness test.

## Relationships & State

```text
Frozen Inventory ──(retention diff)──▶ RULES.md entries (every statement absorbed exactly once)
RULES.md Legacy fields ──(generates)──▶ rule-map.md ◀──(resolves)── historical citations
AGENTS.md ──(cites)──▶ R-IDs        Shims ──(point to)──▶ AGENTS.md
Redirect indexes ──(point to)──▶ RULES.md + bundle + rule-map
Knowledge graph ──(rebuilt from)──▶ all of the above
```

Rule lifecycle: `absorbed` (Chunk 1, logged in baseline.md) → `active` → future changes via docs-update skill (new rules get next free ID; never reuse retired IDs; map rows never deleted).
