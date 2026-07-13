# Quickstart: Validating DB Connection Reuse & Registration Caching

Validation/run guide. Implementation details live in `tasks.md`. All commands run inside the
project `venv` (`R-PROC-7`).

## Prerequisites

- `venv` active; `pytest` installed.
- No schema migration or config change required (feature adds in-memory state only).

## Reproducing test (write FIRST — `R-PROC-3`)

The P1 reproducing test proves the churn before the fix and locks in the target after it.

- **File**: `tests/test_database/test_connection_reuse.py`
- **Approach**: patch/spy `sqlite3.connect` (e.g. via `monkeypatch`/`unittest.mock`) to count
  invocations, then drive one message through the full middleware access-check chain
  (`UserManagerMiddleware` → `ForumUtilityMiddleware` → `AccessGuardMiddleware`) using existing
  journey fixtures.
- **Before fix**: assert count ≈6 (documents current churn) — RED expectation flips to the
  target below.
- **After fix**: assert **new `sqlite3.connect` count ≤ 1** per message once the shared
  connection is warm (SC-001).

Run:

```bash
pytest tests/test_database/test_connection_reuse.py -v
```

## Registration cache test

- **File**: `tests/test_services/test_registration_cache.py`
- **Scenarios**:
  - Two consecutive identical messages (same user, same topic) → second causes **0**
    registration DB hits (spy `db.user_exists` / `db.register_topic_if_not_exists`) — SC-002.
  - Expired memo (advance monotonic clock past `REGISTRATION_TTL_SECONDS`) → registration
    re-hits DB — FR-005.
  - `reset_registration_cache()` clears both memos — test-isolation guard.

Run:

```bash
pytest tests/test_services/test_registration_cache.py -v
```

## Integrity regression (SC-005)

Confirm a write that raises `IntegrityError` still rolls back and leaves the shared
connection usable for the next operation. Prefer an existing permissions/write test path
(`database/permissions.py` grant/duplicate) executed against the reused connection.

## Full regression (SC-003)

The whole existing suite must stay green with **no changes to business-logic tests**:

```bash
pytest -q
```

## Static architecture gates (must stay green)

Facade boundaries and signatures unchanged (SC-004, `R-ARCH-8`, `R-PROC-10/11`):

```bash
# whatever the repo wires for these — e.g.:
semgrep --config .semgrep ; import-linter ; ruff check . ; pytest tests/test_governance.py
```

## Expected outcome

- New connections per message: **≈6 → ≤1**.
- Registration DB hits on a repeat message: **2 → 0** (within TTL).
- All existing tests green; facade contract and 77 call-sites untouched.
