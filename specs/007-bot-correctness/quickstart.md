# Quickstart / Validation — Feature 007 Bot Correctness

Prerequisites: active `venv` (R-PROC-7). All commands from repo root.

~~~
.\venv\Scripts\python.exe -m pytest -q
~~~

Per-bug validation. For each bug the repro test is written FIRST and MUST fail on current code
(R-PROC-3), then pass after the fix.

## BUG-1 — date-range integrity

~~~
.\venv\Scripts\python.exe -m pytest tests/test_services/test_date_logic.py tests/test_handlers/test_event_edit_collision.py -q
~~~
Expected after fix: creating/editing `"10-15 июня"` persists `start_date="10 июня"`,
`end_date="15 июня"`, `start_iso="2026-06-10"`, `end_iso="2026-06-15"`. `DateService.split_human_range`
returns complete parts; single-date input unchanged.

## BUG-2 — active list order & past-filter

~~~
.\venv\Scripts\python.exe -m pytest tests/test_database/test_event_contracts.py -q
~~~
Expected after fix: seeded mix returns only current/ongoing/undated hikes, ordered by `start_iso`;
a fully-past hike is absent; an ongoing (started, not ended) hike is present; an undated hike is
present.

## BUG-3 — non-text FSM guard

~~~
.\venv\Scripts\python.exe -m pytest tests/test_handlers/test_fsm_nontext_guard.py -q
~~~
Expected after fix: a non-text message (`text=None`) into each of the 5 awaiting states yields a
graceful "введите текст" prompt and raises nothing; state preserved.

## BUG-4 — leave is remove-only

~~~
.\venv\Scripts\python.exe -m pytest tests/test_services/test_participation_guard.py -q
~~~
Expected after fix: non-participant "leave" → no participation row created, `(False, …)`;
participant "leave" → removed, `(True, …)`.

## BUG-5 — atomic resolution

~~~
.\venv\Scripts\python.exe -m pytest tests/test_services/test_audit_cas.py -q
~~~
Expected after fix: with one pending request, two `resolve_request` attempts → exactly one DB
side effect + one notification; second returns `(False, "…уже была обработана…")`. A second
resolve of an already-resolved request is a no-op (idempotent, `rowcount==0`).

## Tail — dead code & anonymous sender

Covered by the full suite staying green plus BUG-1/BUG-3 tests. The `AccessGuardMiddleware`
`from_user is None` path is exercised by `tests/test_journeys/test_middleware_pipeline_journey.py`
(extend if a senderless-message case is missing).

## Final gate

~~~
.\venv\Scripts\python.exe -m pytest -q
~~~
All green (R-TEST-4). Then run the prompt-linter checklist stage on `tasks.md` (R-PROC-4).
