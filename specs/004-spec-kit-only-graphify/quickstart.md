# Quickstart / Validation Guide: 004-spec-kit-only-graphify

Prerequisites: project `venv`; global `graphify` 0.8.49 on PATH; run from repo root `C:\TenirTooClub_Bot`.

## Chunk A — spec-kit-only Route A

~~~powershell
# 1. Linter rejects legacy names (should ERROR + exit 1 after the change)
New-Item -ItemType Directory -Force _nogit_lintcheck | Out-Null
"# x`n## Summary" | Out-File _nogit_lintcheck/implementation_plan.md -Encoding utf8
.\venv\Scripts\python.exe local_scripts/prompt_linter.py --dir _nogit_lintcheck --stage plan   # expect: Error: no plan.md found

# 2. Linter still accepts spec-kit plan.md
.\venv\Scripts\python.exe local_scripts/prompt_linter.py --dir specs/004-spec-kit-only-graphify --stage plan  # expect: Plan is valid.

# 3. No PLAN_LEGACY symbol remains
Select-String -Path local_scripts/prompt_linter.py -Pattern "PLAN_LEGACY|implementation_plan|task\.md"   # expect: no matches

# 4. Governance prose clean of RNA-1 / legacy acceptance
Select-String -Path AGENTS.md,RULES.md -Pattern "RNA-1|implementation_plan|task\.md"   # expect: only retired-disposition note in AGENTS INDEXING

# 5. Linter + governance suites green
.\venv\Scripts\python.exe -m pytest tests/test_prompt_linter.py tests/test_journeys/test_prompt_linter_journey.py tests/test_governance.py tests/test_knowledge_bundle.py -q
Remove-Item -Recurse -Force _nogit_lintcheck
~~~

**HARD STOP** — report Chunk A to Шэф, await approval.

## Chunk B — graphify integration

~~~powershell
# 6. CLI present & graph queryable
graphify --version                                          # expect: 0.8.49
graphify query "which modules depend on the database facade?"   # expect: facade node, no source opened

# 7. Claude Code native integration (writes CLAUDE.md section + PreToolUse hook)
Get-Content CLAUDE.md                                        # BEFORE: note @AGENTS.md shim present
graphify claude install
Get-Content CLAUDE.md                                        # AFTER: @AGENTS.md shim STILL present + ## graphify section

# 8. Git auto-rebuild hooks
graphify hook install
graphify hook status                                        # expect: hooks installed

# 9. Refresh graph now (code + semantic via skill flow; CLI code-only shown here)
graphify update .                                           # code layer; semantic refresh via /graphify --update skill flow

# 10. Governance additions present
Select-String -Path RULES.md -Pattern "R-PROC-12"           # expect: match
Test-Path docs/knowledge/graph.md                           # expect: True
Select-String -Path docs/knowledge/index.md -Pattern "graph.md"   # expect: match

# 11. Full regression
.\venv\Scripts\python.exe -m pytest -q                      # expect: all green, 0 failed
~~~

**HARD STOP** — report Chunk B to Шэф; on approval, CHANGELOG (CMD-4) + GW-1 local commit (no push).

## Success mapping

- SC-001/002 → steps 1–5
- SC-003/004 → steps 6–8
- SC-005/006 → steps 7, 9, 10
- SC-007 → step 11
