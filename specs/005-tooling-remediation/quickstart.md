# Quickstart: Validating Feature 005 (AI Tooling Remediation)

End-to-end validation scenarios. Prerequisites: repo root, venv present, Docker Desktop
running (scenario 5 only).

## 0. Pre-fix reproduction (record once, before implementation)

```powershell
.\venv\Scripts\pytest -q          # EXPECT (pre-fix): ImportError in conftest — ModuleNotFoundError: database
.\venv\Scripts\python -m pytest -q  # EXPECT: suite runs; record counts as BASELINE
python local_scripts/prompt_linter.py --dir specs/004-spec-kit-only-graphify --stage plan
                                    # EXPECT (pre-fix): false Cyrillic warning on '-'
```

## 1. Canonical test invocation (US1 / SC-001)

```powershell
.\venv\Scripts\pytest -q            # EXPECT: collection OK, counts == BASELINE
.\venv\Scripts\python -m pytest -q  # EXPECT: unchanged, counts == BASELINE
```

Doc sweep: search living docs for test-invocation mentions → all use the canonical form
(see [contracts/canonical-test-invocation.md](contracts/canonical-test-invocation.md)).

## 2. Linter false positive gone (US4 / SC-002)

```powershell
.\venv\Scripts\pytest tests/test_services/test_prompt_linter.py -q   # EXPECT: all pass
foreach ($d in 1..4) { python local_scripts/prompt_linter.py --dir (Get-Item "specs/00$d-*").FullName --stage plan }
# EXPECT: "Plan is valid." x4, zero Cyrillic warnings
python local_scripts/prompt_linter.py --dir specs/005-tooling-remediation --stage plan
# EXPECT: valid, no warnings
```

Seeded-violation check: temporarily lint a scratch plan containing a genuine Russian word
→ warning names the word.

## 3. Plugin discovery (US2+US3 / SC-003)

In a **fresh** Claude Code session in this project:

1. Available skills list contains `tenirtoo-proposal-analysis` and
   `tenirtoo-docs-update` (each exactly once).
2. Available agent types contain `proposal-auditor`, `test-runner-and-debugger`,
   `cognitive-ux-auditor`.
3. Invoke `tenirtoo-docs-update` → engine content loads and matches
   `.agents/plugins/tenirtoo-plugin/skills/docs-update/SKILL.md`.

Contract: [contracts/plugin-registration.md](contracts/plugin-registration.md). If any
check fails → HARD-STOP, consult fallback clause (operator approval required).

## 4. Dev-deps install on Windows (US5 / SC-004a)

```powershell
.\venv\Scripts\pip install -r requirements-dev.txt --dry-run
# EXPECT: resolves without attempting semgrep on win32
```

## 5. Semgrep Docker gate (US5 / SC-004b)

```powershell
docker-compose --profile lint run --rm semgrep
# EXPECT: scan completes, 0 findings (exit code 0)
```

Record the result in the walkthrough artifact.

## 6. Dead-reference sweep (US6 / SC-005)

```powershell
# EXPECT: no hits in living agent-facing docs (specs/001-004 exempt)
Select-String -Path CLAUDE.md,AGENTS.md,RULES.md,docs\knowledge\*.md -Pattern "graphify-out/wiki"
```

## 7. Scope guard (SC-006)

```powershell
git diff --stat main -- handlers services middlewares database keyboards web
# EXPECT: empty output
```

## 8. Regression gates (every chunk boundary)

```powershell
.\venv\Scripts\pytest -q        # full suite green
.\venv\Scripts\ruff check .     # All checks passed
.\venv\Scripts\lint-imports     # Contracts: 1 kept, 0 broken
graphify update .               # AST-only graph refresh (R-PROC-12)
```
