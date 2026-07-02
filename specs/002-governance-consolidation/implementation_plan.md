# Goal Description: Governance Consolidation - Single Constitution (AGENTS.md) + Unified Rulebook (RULES.md) + Full Knowledge Dissolution

RNA-Blueprint view of [plan.md](plan.md). Executors: Claude Opus (Chunk 1), Claude Sonnet (Chunk 2), both via `speckit-implement` over `tasks.md`.

## Base DNA

- OS: Windows 10, PowerShell syntax; python `.\venv\Scripts\python.exe`; pytest via `python -m pytest` (feature-001 baseline note).
- Deliverable: markdown governance restructuring + pytest validation; no bot source changes; no `git push`.

## Task RNA

- Logic: consolidate ~86+ scattered rules (PL-6, CP-3, PL-2.3/2.4/2.5, PL-3.2, PL-5/PL-8 imperatives, GEMINI process rules) into `RULES.md` with stable `R-<DOMAIN>-<n>` IDs, tier A/B taxonomy and enforcement pointers; promote `AGENTS.md` to a tracked constitution (open agent-instructions standard); dissolve all descriptive content of PROJECT_LOGIC/CONTEXT_PROMPT into `docs/knowledge/` per the locked D6 map; preserve every legacy anchor via `docs/knowledge/rule-map.md`; sync skills and spec-kit constitution; rebuild the knowledge graph.
- Risks: (1) silent rule loss/drift during merging - mitigated by frozen inventory + retention diff test + Opus on Chunk 1; (2) duplicate-merge picking the weaker variant - mitigated by D4 policy (most restrictive wins, decisions logged); (3) broken legacy citations - mitigated by rule-map completeness test over the frozen anchor set; (4) secrets entering tracked files - mitigated by Phase 1 secret scan of GEMINI/AGENTS content; (5) feature-001 suite breakage - mitigated by constants-only adaptation, documented.
- Edge cases: mixed sections split per statement (imperative to RULES, description to bundle); rules cited by semgrep/importlinter configs keep wording compatibility; GEMINI kept as shim for Gemini-CLI; retired/duplicate anchors map to a single R-ID (many-to-one allowed, dangling forbidden).

## Contextual Constraints (CC)

- [CC-1] Single source of truth per rule [audit F1; spec FR-001..FR-004].
- [CC-2] Versioned constitution at standard entry point [audit F2; FR-005/FR-006].
- [CC-3] Description-only knowledge layer; per-statement criterion [audit F3/F5; FR-007].
- [CC-4] Enforcement over instruction: Tier-B one-liners with existing mechanisms [audit F4; FR-004].
- [CC-5] TDD-first: governance suite red before consolidation [research D8].
- [CC-6] Chunked execution with HARD STOP = executor handoff Opus -> Sonnet [research D7].
- [CC-7] Prompt-linter gates plan/checklist/report against this feature directory.

## User Review Required

- Approval of this plan before execution (Route A chunking rule).
- Confirmation of executor split: Opus for Chunk 1 (consolidation semantics), Sonnet for Chunk 2 (mechanical dissolution/sync) - research D7.
- Awareness: `AGENTS.md` and `RULES.md` become public tracked files; Phase 1 includes a secret scan before anything is staged.
- Awareness: `PROJECT_LOGIC.md`/`CONTEXT_PROMPT.md` become thin redirect indexes (old content remains in git history; anchors resolve via rule-map).

## Open Questions

- None blocking. All destinations locked in research D6; duplicate groups enumerated in spec US1; conflict policy fixed in D4.

## Proposed Changes

### Governance core
- [NEW] `RULES.md` - unified rulebook (tracked).
- [REWRITE] `AGENTS.md` - constitution (tracked; old subagent registry absorbed).
- [REWRITE] `CLAUDE.md`, `GEMINI.md` - pointer shims (ignored).
- [MODIFY] `.gitignore` - un-ignore `AGENTS.md`.

### Knowledge dissolution
- [NEW] `docs/knowledge/rule-map.md`, `architecture.md`, `middleware.md`, `fsm-protocol.md`, `db-patterns.md`, `constants.md`, `testing.md`, `features-overview.md` (+ index/log updates).
- [REWRITE] `PROJECT_LOGIC.md`, `CONTEXT_PROMPT.md` - thin redirect indexes.

### Tooling & validation
- [NEW] `tests/test_governance.py` (six contract tests per contracts/governance-contract.md) + `tests/fixtures/rules_inventory_baseline.txt`.
- [ADAPT] `tests/test_knowledge_bundle.py` - base-file constants only (documented).
- [MODIFY] skills: `docs-update/SKILL.md` (producer contract v2), `proposal-analysis/SKILL.md` (ground truth -> RULES.md + bundle).
- [FILL] `.specify/memory/constitution.md`.
- [REBUILD] `graphify-out/` via graphify update.

## Execution Steps

1. **[TEST][CC-5] (Opus)** Freeze inventory: extract every normative statement with anchor from GEMINI/PROJECT_LOGIC/CONTEXT_PROMPT/AGENTS to `tests/fixtures/rules_inventory_baseline.txt`; secret-scan GEMINI/AGENTS content; record sizes in baseline.md. Write `tests/test_governance.py`; run - MUST fail (no RULES.md/rule-map). Record red pattern.
2. **[CC-1][CC-4] (Opus)** Build `RULES.md`: absorb all inventory statements; merge the 11 duplicate groups per D4 (log each decision); assign tiers; write Tier-B enforcement pointers; emit `Legacy:` fields.
3. **[CC-1] (Opus)** Generate `docs/knowledge/rule-map.md` from Legacy fields + D6 descriptive destinations; adapt `test_knowledge_bundle.py` constants; governance tests for IDs/map/duplicates flip green.
4. **[CC-2] (Opus)** Draft `AGENTS.md` constitution (sections per data-model.md) citing R-IDs; write shims; update `.gitignore`; run full suite + linter plan stage. **HARD STOP: report to the user (Шэф), await approval - executor handoff to Sonnet.**
5. **[CC-3] (Sonnet)** Execute D6 dissolution: create 7 knowledge files with verbatim moves + front matter + index/log atomicity; rewrite PROJECT_LOGIC/CONTEXT_PROMPT as redirect indexes; governance + bundle suites green.
6. **[CC-4][CC-7] (Sonnet)** Sync tooling: skills, spec-kit constitution fill; run mutation checks (quickstart); full regression; measure SC-001 (<=30 KB).
7. **(Sonnet)** Rebuild graph (graphify update); demo query resolving an R-ID (SC extension of 001's SC-006); complete task.md; linter checklist stage; walkthrough.md (Russian) + linter report stage; CHANGELOG entry; GW-1 local commit.

Chunking: steps 1-4 = Chunk 1 (Opus), steps 5-7 = Chunk 2 (Sonnet), boundary = HARD STOP.

## Verification Plan

- **New test file**: `tests/test_governance.py`; cases: `test_rule_ids_unique`, `test_no_duplicate_rule_text`, `test_rule_map_complete`, `test_tier_b_enforcement_exists`, `test_shims_are_pure`, `test_constitution_filled`. TDD reproducer: suite fails on pre-consolidation tree (no RULES.md) - observed and recorded in Step 1.
- **Commands**: quickstart.md sections 1-7 + mutation checks.
- **Manual checks**: spot-resolve two legacy anchors end-to-end via rule-map; read one merged duplicate group and confirm the most-restrictive-wins decision in baseline.md; confirm pre-read set reads coherently as onboarding (constitution -> rulebook -> index).
