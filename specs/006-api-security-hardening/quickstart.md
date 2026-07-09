# Quickstart — Validating API Security Hardening (Фаза 1)

Run everything inside the venv (`R-PROC-7`). This is a validation guide; implementation code lives in `tasks.md` / the implementation phase.

## Prerequisites

- `.\venv\Scripts\python.exe` active environment.
- Test DB is isolated automatically via `conftest.py` `db_setup` — never touches `bot.db` (`R-TEST-1`).

## Run the feature's tests

~~~
.\venv\Scripts\python.exe -m pytest tests/test_web tests/test_services tests/test_journeys -q
~~~

Expected after implementation: all green. Before each fix, its reproducing test must be **red** first (`R-PROC-3`).

## Per-story validation

### US1 — Unified direct-join guard (P1)
- **Reproduce (red first)**: call `POST /api/dashboard/events/{id}/toggle` for a **pending** event as a valid member → currently toggles (bug). Test asserts it is denied and no `event_participants` row is created.
- **Also**: announcement join for a member without topic access → denied; approval now enforced on the announcement toggle too.
- **Positive**: authorized member + approved event → toggled, organizer notified, announcement refreshed (unchanged behavior, SC-003).
- **Check**: `EventService.check_direct_join_allowed` returns `(False, …)` for pending/no-access and `(True, "")` otherwise.

### US2 — Session freshness (P2)
- Build init-data signed with the test `BOT_TOKEN`, `auth_date = now - (TTL + 60)` → `validate_webapp_init_data` returns `None` → endpoint responds `401`.
- `auth_date = now` → returns the user dict → endpoint `200`.
- Omit `auth_date` → `None` → `401`.
- Toggle `WEBAPP_SESSION_TTL_SECONDS` via env/config in the test to confirm it is honored.

### US3 — Global error handler (P2)
- Patch a dashboard route to raise a plain `Exception`; issue the request → client gets HTTP `500` with JSON `{"detail": "Internal Server Error"}`; assert the handler itself did not raise and `logger.error` fired with `exc_info`.

### US4 — Callback defense-in-depth (P3)
- As a **non-admin** user, invoke `confirm_execution` with `confirm_exe_user_del:{id}:0` → assert `ManagementService.execute_deletion` is **not** called and a deny alert is answered (args+kwargs, `R-TEST-3`).
- As a **non-manager**, invoke `perform_search_pick` with `mod_add` for a topic → no role granted, deny alert.
- As an **admin/topic-manager**, same actions succeed (regression guard).

## Full-suite regression

~~~
.\venv\Scripts\python.exe -m pytest -q
~~~

Expected: previously-passing suite stays green (the pre-existing `test_semgrep_lint` failure is environmental — requires Docker — and is out of scope here).

## Governance gate

After `plan.md` is finalized, the prompt-linter plan stage must pass (`R-PROC-4`):

~~~
.\venv\Scripts\python.exe local_scripts/prompt_linter.py --stage plan
~~~
