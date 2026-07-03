# Quickstart: Validating Governance Hardening

**Date**: 2026-07-03. Repo root, PowerShell. Pytest via `.\venv\Scripts\python.exe -m pytest`.

## 1. Retention gate (primary)

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_governance.py -v
```

**Expected**: `test_imperatives_map_to_rules` RED before Chunk A fixes (must name CP-3.11, CP-3.47, CP-3.28.2, PL-4.1 at minimum — record the exact list in baseline.md); GREEN after; all pre-existing tests green throughout.

## 2. Linter v2

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_prompt_linter.py tests/test_journeys/test_prompt_linter_journey.py -v
# live checks against real feature dirs:
.\venv\Scripts\python.exe local_scripts/prompt_linter.py --dir specs/002-governance-consolidation --stage plan      # legacy path still valid
.\venv\Scripts\python.exe local_scripts/prompt_linter.py --dir specs/003-governance-hardening --stage plan          # v2 path (plan.md)
```

**Expected**: all green; 002 lints via legacy fallback, 003 via `plan.md`.

## 3. Full regression

```powershell
.\venv\Scripts\python.exe -m pytest
```

**Expected**: 0 failed; only the files listed in plan.md § Source Code changed (`git status`).

## 4. Manual checks (К-group)

- `Select-String -Path AGENTS.md -Pattern 'speckit-implement','speckit-specify'` → rows present in § COMMAND REGISTRY; Route A text names the chain.
- `Select-String -Path .specify/templates/tasks-template.md -Pattern 'HARD STOP','R-PROC-2'` → gate pattern present.
- `Select-String -Path RULES.md -Pattern 'R-UI-12','R-UI-13','R-ARCH-9','incremental'` → all four hits.
- `Select-String -Path docs/knowledge/rule-map.md -Pattern '\| docs/knowledge/index.md \|'` → **no output**.

## 5. Mutation checks

Run the three checks from contracts/hardening-contract.md § Mutation checks; each must fail-then-restore-green. Record in baseline.md.

## 6. Gates for this feature (dual-format)

```powershell
.\venv\Scripts\python.exe local_scripts/prompt_linter.py --dir specs/003-governance-hardening --stage checklist   # tasks.md via v2
.\venv\Scripts\python.exe local_scripts/prompt_linter.py --dir specs/003-governance-hardening --stage report
```
