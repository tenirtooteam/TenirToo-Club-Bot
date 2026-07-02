# Contract: Governance Layer Interface

**Date**: 2026-07-02. Enforcement: `tests/test_governance.py`. Test names are binding.

## Consumer contract (any AI agent)

1. **Pre-read set** is exactly: `AGENTS.md` + `RULES.md` + `docs/knowledge/index.md` (≤30 KB total). Everything else is on-demand.
2. **Rule resolution**: any `R-<DOMAIN>-<n>` citation resolves inside `RULES.md`. Any legacy `PL-x.y`/`CP-x.y` citation resolves via `docs/knowledge/rule-map.md`.
3. **Tier semantics**: Tier A = agent judgment required, full text present. Tier B = CI enforces it; the agent treats the one-liner as awareness, the named mechanism as the gate.
4. **Tolerance**: unknown domains/fields must be tolerated (forward compatibility).

## Producer contract (docs-update skill and any doc-writing agent)

1. New behavioral rule → new `R-*` entry in `RULES.md` (next free number in its domain) + rule-map row if it supersedes a legacy anchor. Never into AGENTS.md, knowledge files, or redirects.
2. New descriptive content → owning `docs/knowledge/` concept file + index/log atomicity (feature-001 contract unchanged).
3. Process change (route, command, git) → `AGENTS.md` section text; if it contains an imperative, the imperative lives as `R-PROC-*` and the section cites it.
4. IDs are permanent: never renumber, never reuse; retired rules keep their row in rule-map with target `retired (see log)`.

## Enforcement mapping

| Contract clause | Test |
|---|---|
| Rule-ID uniqueness | `test_rule_ids_unique` |
| No rule text duplicated across governance files (≥20-word shingles) | `test_no_duplicate_rule_text` |
| Every frozen legacy anchor resolves | `test_rule_map_complete` |
| Every Tier-B pointer names an existing mechanism | `test_tier_b_enforcement_exists` |
| Shims contain no normative content | `test_shims_are_pure` |
| Spec-kit constitution has no template placeholders | `test_constitution_filled` |
| Bundle front matter / index / log invariants | feature-001 suite (adapted constants) |
