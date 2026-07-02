# Research: Governance Consolidation

**Date**: 2026-07-02. Decisions consolidated from the frame-free governance audit (APA-1, industry-standard reference). No open NEEDS CLARIFICATION items.

## D1. Constitution lives at AGENTS.md (open standard), tracked in Git

- **Decision**: `AGENTS.md` becomes the single tracked constitution. Current subagent-registry content becomes a section inside it (detail can overflow to `docs/knowledge/testing.md`). `CLAUDE.md` → shim (`@AGENTS.md`); `GEMINI.md` → shim pointer (kept for Gemini-CLI compatibility). Shims stay git-ignored; `AGENTS.md` is un-ignored.
- **Rationale**: AGENTS.md is the cross-vendor agent-instructions standard (adopted across OpenAI/Google/Cursor/Zed toolchains); governance must be versioned (audit F2). The current layout inverts the standard: the real constitution (GEMINI.md) is ignored and vendor-misnamed while the standard filename holds a registry.
- **Alternatives considered**: (a) Keep GEMINI.md as constitution but track it — fixes versioning, keeps wrong entry point and vendor naming; rejected. (b) CLAUDE.md as constitution — vendor-locks the entry point; rejected.

## D2. Single rulebook RULES.md with domain-prefixed stable IDs

- **Decision**: All behavioral rules consolidate into `RULES.md`. ID scheme `R-<DOMAIN>-<n>` with domains: `ARCH` (facades, imports, layers), `DB`, `UI` (sterile protocol), `FSM`, `CODE` (coding/response mechanics), `TEST`, `PROC` (routes, RNA, git, audit protocol), `SEC`. Each entry: ID, statement, one-line rationale, tier, enforcement (Tier B), legacy anchors.
- **Rationale**: Single source of truth (audit F1). Domain prefixes make citations self-describing; legacy anchors inside entries make the mapping table generatable and testable.
- **Alternatives considered**: rules/ directory with one file per domain — better diff locality but 8 more pre-read file reads and index overhead at this scale (~86 rules fits one file comfortably); rejected for now, revisit if RULES.md exceeds ~25 KB.

## D3. Tier taxonomy and enforcement map

- **Decision**: Tier A = judgment rules, full text. Tier B = machine-enforced rules, exactly one line: `R-x-n [B] <short statement> — enforced by <mechanism>`. Known Tier-B candidates: semgrep's five rules, import-linter contracts, AST import test, ruff, prompt-linter gates, bundle/governance pytest suites, FK-fuse runtime check. Target ≥15 demotions (SC-004).
- **Rationale**: Enforcement over instruction — context is spent only where the machine cannot check (audit F4).
- **Alternatives considered**: Removing Tier-B rules from RULES.md entirely — rejected: the rulebook must stay the complete registry; one-liners cost ~40 tokens each.

## D4. Duplicate-merge policy

- **Decision**: For each duplicate group (11 groups named in spec US1/AS2), merge into one entry. Conflict resolution: most restrictive variant wins; if variants differ materially, the newer/validated-by-tests text wins; every merge decision logged in `baseline.md`. Process-rule duplicates (CP-3.28/3.29/3.30/3.35 vs GEMINI sections) resolve into `R-PROC-*` with the GEMINI text as base (it is the operational original).
- **Rationale**: Deterministic, auditable merging prevents silent semantic drift — the highest-risk step of the whole feature.
- **Alternatives considered**: Keeping "coding-view" and "process-view" variants of the same rule — rejected: that is exactly the current disease.

## D5. Anchor preservation via mapping table, not stubs

- **Decision**: `docs/knowledge/rule-map.md` maps every legacy `PL-x.y`/`CP-x.y` to its new home (R-ID or bundle file). The redirect indexes (`PROJECT_LOGIC.md`, `CONTEXT_PROMPT.md`) carry one pointer to the map instead of per-section stub headings. Feature-001's `test_pl_anchors_preserved` base set changes from "core+bundle files" to "core+bundle+rule-map" (constant-level adaptation, documented per FR-011).
- **Rationale**: 250+ stub headings would defeat the size goal; a single generated table preserves resolution and is testable both directions.
- **Alternatives considered**: Keeping stubs (feature-001 style) — right for a partial extraction, wrong for full dissolution; rejected.

## D6. Dissolution map (locked; per-statement criterion still applies)

| Source | Destination |
|---|---|
| PL-1 identity/stack | `AGENTS.md` brief (1 short paragraph) + rest to `docs/knowledge/architecture.md` |
| PL-2.1, PL-2.6 | `docs/knowledge/architecture.md` |
| PL-2.3 import graph, PL-2.4, PL-2.5, PL-2.2.50 | `RULES.md` (R-ARCH / R-TEST) |
| PL-3.2 | `RULES.md` (R-DB) |
| PL-3.1.1, PL-3.3–3.5 | `docs/knowledge/db-patterns.md` (3.1.1 fact; imperative sentences inside → RULES) |
| PL-4 | `docs/knowledge/middleware.md` (PL-4.5 pattern statement → R-ARCH) |
| PL-5.1 protocol imperatives, PL-5.3, PL-5.4 rule parts | `RULES.md` (R-UI / R-FSM) |
| PL-5.2 FSM keys, PL-5.5, PL-5.6 descriptions | `docs/knowledge/fsm-protocol.md` |
| PL-6 (all 26) | `RULES.md` (6.24–6.26 → Tier B) |
| PL-7 | `docs/knowledge/constants.md` |
| PL-8 descriptive | `docs/knowledge/testing.md`; PL-8.3/8.5 imperatives → R-TEST |
| CP-1, CP-5, CP-6 | `AGENTS.md` (response protocol cites R-CODE IDs) |
| CP-2 feature list | `docs/knowledge/features-overview.md` |
| CP-3 (~60) | `RULES.md` (dedup per D4) |
| GEMINI routes/commands/git/RNA/registry/ownership | `AGENTS.md` (process text) + `R-PROC-*` for imperatives |
| AGENTS.md subagent registry | `AGENTS.md` § Subagents (summary) + `docs/knowledge/testing.md` (detail) |

- **Rationale**: Every source section has exactly one named destination before execution starts — Sonnet's Chunk 2 requires zero classification judgment.

## D7. Executor split

- **Decision**: Chunk 1 (inventory, TDD suite, RULES.md consolidation, AGENTS.md drafting) — **Opus**. Chunk 2 (verbatim dissolution per D6 map, shims, redirects, constitution fill, skills sync, graph rebuild, finalization) — **Sonnet**. Handoff gate: governance suite green on Chunk 1 outputs + user approval at HARD STOP.
- **Rationale**: Semantic merging of ~86 rules is where silent loss happens — highest-capability model there. Chunk 2 is fully specified moves and syncs — Sonnet-safe, cheaper, faster. The chunk boundary already exists as a process HARD STOP, so the split adds no coordination cost.
- **Alternatives considered**: Opus end-to-end — safe but wasteful on mechanical moves; Sonnet end-to-end — unacceptable loss risk in D4 merges.

## D8. Validation

- **Decision**: New `tests/test_governance.py`: `test_rule_ids_unique`, `test_no_duplicate_rule_text` (≥20-word shingle scan across AGENTS/RULES/redirects), `test_rule_map_complete` (every frozen legacy anchor resolves), `test_tier_b_enforcement_exists` (pointer targets exist on disk/config), `test_shims_are_pure` (no imperative content in CLAUDE/GEMINI shims), `test_constitution_filled` (no template placeholders). Frozen inputs: `tests/fixtures/rules_inventory_baseline.txt` (Phase 1). Feature-001 suite adapted in constants only.
- **Rationale**: Same TDD/mutation pattern that proved itself in feature 001, extended to governance invariants (SC-006).
