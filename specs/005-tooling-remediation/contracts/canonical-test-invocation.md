# Contract: Canonical Test Invocation

**Consumers**: all AI agents (main session + subagents), human developers, governance
docs, `test-runner-and-debugger` agent definition.

## The one blessed form

```powershell
.\venv\Scripts\pytest            # full suite, from repo root
.\venv\Scripts\pytest <path>::<test>  # targeted
```

Backed by `pytest.ini` at repo root:

```ini
[pytest]
pythonpath = .
testpaths = tests
```

## Guarantees

1. Collection succeeds from a clean shell at the repository root — no
   `ModuleNotFoundError` for project packages (`database`, `services`, ...).
2. `python -m pytest` (legacy form) remains functional with identical results — no
   regression for existing muscle memory or scripts.
3. Every living governance/reference document that mentions test invocation prescribes
   the bare canonical form (FR-002). Historical specs 001-004 are exempt (read-only).
4. Bare `pytest` never collects outside `tests/` (`testpaths` guard — `venv/`,
   `scratch/`, `_nogit_*` excluded).

## Breaking-change policy

Changing the canonical form requires a Route B audit (it is cited by agent definitions
and multiple docs) and a sweep of all citing documents in the same feature.

## Verification

- `.\venv\Scripts\pytest` → full suite green, counts equal to the recorded
  `python -m pytest` baseline.
- Repo-wide search for `venv\Scripts\pytest` / `python -m pytest` mentions in living
  docs → all conform.
