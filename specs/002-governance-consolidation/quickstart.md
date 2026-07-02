# Quickstart: Validating Governance Consolidation

**Date**: 2026-07-02. Run from repo root `C:\TenirTooClub_Bot` in PowerShell. Pytest invocation is `.\venv\Scripts\python.exe -m pytest` (see feature-001 baseline note).

## 1. Governance suite (primary gate)

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_governance.py -v
```

**Expected**: red before Chunk 1 outputs exist (TDD baseline — record the failure pattern); all six tests green after Chunk 1; still green after Chunk 2.

## 2. Full regression

```powershell
.\venv\Scripts\python.exe -m pytest
```

**Expected**: entire suite green. `git status tests/` shows only `test_governance.py` + `fixtures/rules_inventory_baseline.txt` as new; `test_knowledge_bundle.py` diff limited to base-file constants (documented in baseline.md).

## 3. Pre-read size (SC-001)

```powershell
$s=(Get-Item AGENTS.md).Length+(Get-Item RULES.md).Length+(Get-Item docs/knowledge/index.md).Length
"Pre-read: {0:N1} KB (target <= 30)" -f ($s/1KB)
```

## 4. Tracking & shims (US2)

```powershell
git ls-files AGENTS.md RULES.md          # both listed
Get-Content CLAUDE.md; Get-Content GEMINI.md   # pointer-only shims
git check-ignore AGENTS.md; if ($?) { "FAIL: still ignored" } else { "OK" }
```

## 5. Zero-loss retention (SC-002/SC-003)

```powershell
# every frozen inventory line absorbed (test does this; manual spot-check):
Select-String -Path RULES.md -Pattern 'state\.clear' -SimpleMatch | Select-Object -First 1
Select-String -Path docs/knowledge/rule-map.md -Pattern 'PL-6.4','CP-3.19' | Select-Object -First 4
```

**Expected**: FSM-hygiene rule present once in RULES.md; both legacy anchors of a merged pair map to the same R-ID.

## 6. Linter gates

```powershell
.\venv\Scripts\python.exe local_scripts/prompt_linter.py --dir specs/002-governance-consolidation --stage plan
# after implementation: --stage checklist, then --stage report
```

## 7. Graph rebuild (Chunk 2)

Invoke graphify (`/graphify C:\TenirTooClub_Bot --update`); verify `graphify-out/GRAPH_REPORT.md` regenerated and a query about a rule (e.g. "what enforces the database facade rule?") resolves to R-IDs.

## Mutation checks (SC-006)

After green: (1) duplicate one Tier-A rule text into AGENTS.md → `test_no_duplicate_rule_text` fails; (2) change one R-ID to collide → `test_rule_ids_unique` fails; (3) delete one rule-map row → `test_rule_map_complete` fails; (4) add a "MUST" line to CLAUDE.md → `test_shims_are_pure` fails. Restore after each; suite green.
