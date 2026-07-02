# Quickstart: Validating the Two-Tier Documentation Migration

**Date**: 2026-07-02. Run everything from the repository root `C:\TenirTooClub_Bot` in PowerShell.

## Prerequisites

- Existing venv at `.\venv` (pytest installed).
- User-level `graphify` skill available to the executing agent (Story 4 only).

## 1. Bundle validation suite (primary gate)

```powershell
.\venv\Scripts\pytest tests/test_knowledge_bundle.py -v
```

**Expected**: All tests pass. Before migration (TDD baseline) the suite MUST fail with "bundle missing" class errors — record that failure before creating the bundle.

## 2. Full regression

```powershell
.\venv\Scripts\pytest
```

**Expected**: Entire suite green; zero modifications to pre-existing test files (`git status tests/` shows only the new `test_knowledge_bundle.py`).

## 3. Pre-read size target (SC-001)

```powershell
$core = (Get-Item PROJECT_LOGIC.md).Length + (Get-Item CONTEXT_PROMPT.md).Length + (Get-Item docs/knowledge/index.md).Length
"Pre-read: {0:N1} KB (baseline 89.8 KB, target <= 53.9 KB)" -f ($core/1KB)
```

**Expected**: Reported size ≤ 53.9 KB (≥40% reduction).

## 4. Rule retention check (SC-002)

```powershell
Select-String -Path CONTEXT_PROMPT.md -Pattern 'refer to \*\*PROJ##' -SimpleMatch:$false
```

**Expected**: No output (corruption gone). The imperative-statement inventory diff is covered by `test_pl_anchors_preserved` plus manual spot-check of `[PL-6]` rules remaining intact.

## 5. Artifact linter gates (GEMINI.md process)

```powershell
.\venv\Scripts\python.exe local_scripts/prompt_linter.py --dir specs/001-okf-docs-graphify --stage plan
# after implementation completes:
.\venv\Scripts\python.exe local_scripts/prompt_linter.py --dir specs/001-okf-docs-graphify --stage checklist
.\venv\Scripts\python.exe local_scripts/prompt_linter.py --dir specs/001-okf-docs-graphify --stage report
```

**Expected**: "Plan is valid." / "Checklist is valid." / "Report is valid."

## 6. Knowledge graph (Story 4)

Invoke the `graphify` skill over the repository root (`/graphify C:\TenirTooClub_Bot`). Then:

```powershell
Test-Path graphify-out/GRAPH_REPORT.md
git check-ignore graphify-out
```

**Expected**: `True` for the report; `git check-ignore` prints `graphify-out` (directory is ignored). Answer one architecture question via a graphify query (SC-006) and record it in `walkthrough.md`.

## Mutation checks (SC-003)

After the suite is green, verify it actually guards:

1. Temporarily delete the `type:` line from one concept file → suite must fail naming the file → restore.
2. Temporarily remove one `index.md` entry → suite must fail on index divergence → restore.
3. Temporarily rename one `[PL-x.y]` stub anchor in `PROJECT_LOGIC.md` → suite must fail on anchor loss → restore.
