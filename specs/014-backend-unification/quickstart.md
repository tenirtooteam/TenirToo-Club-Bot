# Quickstart / Validation: Backend unification (feature 014)

How to prove the feature works end to end. All tests run in-process (no live Telegram, no
HTTP server — R-TEST-2); endpoints are called as plain async functions; Telegram side effects
are mocked and asserted on `args`/`kwargs` (R-TEST-3).

## Prerequisites

- venv active: `venv\Scripts\python.exe -m pytest` (global Python has no pytest — R-PROC-7).
- Isolated DB per test via the existing conftest fixtures; service caches reset by the
  established autouse fixtures.

## Test-first order (R-PROC-3)

1. **Characterization first, format-agnostic.** Before touching any callsite, capture current
   behavior of all four surfaces by driving the real producer (endpoint fn / handler), not by
   asserting hard-coded wire strings. Record: did the participant set change, was
   `refresh_announcements` called, was `notify_organizers_of_direct_join` called, how many
   announcement copies were refreshed. These are the "before" locks; two of them encode
   today's defects (dashboard leave refreshes nothing; announcement TMA refreshes one copy).
2. Add the new method's unit tests (they fail until the method exists).
3. Implement `apply_participation_change`; migrate callsites; evolve the characterization
   tests into parity tests asserting the unified consequence set.

## Validation scenarios → named tests

### `tests/test_services/test_participation_orchestration.py` (C1)

- **join changes state**: non-participant + `join` on an approved event → participant added,
  `notify_organizers_of_direct_join` called once, `refresh_announcements` called once,
  `success is True`.
- **join no-op**: already-participant + `join` → no add, **no** notify, **no** refresh,
  `success is True`, informative message.
- **leave changes state**: participant + `leave` → participant removed, **no** notify,
  `refresh_announcements` called once, `success is True`.
- **leave no-op is not a join (№7 core)**: non-participant + `leave` → participant set
  unchanged, **no** add, **no** notify, **no** refresh, `success is True`.
- **refresh covers all copies**: event with 2 announcements in different topics + `join` →
  the refresh path targets both (assert via `refresh_announcements` fetching all copies).
- **structural detection**: outcome classification does not depend on the message text
  (INV-5) — verify by exercising both directions and asserting on participant state.
- **unknown intent**: `intent="toggle"` (or any non-join/leave) → `(False, refusal)`, no
  mutation, no side effects (FR-011).
- **side-effect failure isolation**: `refresh_announcements` raising → mutation persists,
  `success` still reflects end state, no exception escapes (FR-008).

### `tests/test_web/test_dashboard_participation.py` (C2 — [MODIFY])

- Keep the feature-006 guard tests (pending event → 403; approved → allowed).
- **explicit intent**: approved event + `action="join"` → participant added; then
  `action="leave"` → removed **and** `refresh_announcements` called (today's gap: dashboard
  leave refreshed nothing).
- **№7 no silent join via web**: non-participant + `action="leave"` → no add, no notify.
- **missing/invalid action** → 400 (FR-011).

### `tests/test_web/test_announcement_participation.py` (C3 — [NEW])

- Guard: no topic access → 403; non-event announcement → 400; missing announcement → 404.
- **all copies refresh**: event with ≥2 announcements + `action="join"` via one announcement
  → all copies refreshed (today's gap: only the clicked one).
- **explicit intent + №7**: `action="leave"` for a non-participant → safe no-op, no notify.
- **missing/invalid action** → 400.

### `tests/test_journeys/test_participation_parity_journey.py` (parity — [NEW])

- **Cross-surface parity**: for the same approved event, drive `join` then `leave` through
  each of the four surfaces (dashboard endpoint, announcement endpoint, `ann_join` handler,
  `leave_event` handler) and assert the consequence set is identical and complete:
  participant state correct, `refresh_announcements` invoked on every change, organizer
  notification invoked on join only. This is SC-001/SC-002/SC-003 in one place.

### `tests/test_journeys/test_tma_bridge_journey.py` ([MODIFY])

- Follow the endpoint signature change (pass `action`); assert refresh-all behavior.

## Static / governance gates (run before commit)

- `venv\Scripts\python.exe -m pytest` — full suite green (SC-005).
- `venv\Scripts\lint-imports.exe` — no new import contract break; R-ARCH-4 held by lazy
  imports (D6).
- `ruff` and the semgrep lint tests (`tests/test_services/test_{import,ruff,semgrep}_lint.py`).
- Governance: `tests/test_governance.py`, `tests/test_knowledge_bundle.py`.
- prompt-linter: plan stage now; checklist stage at the very end of `/speckit-tasks`
  (ASCII-safe checklist items, all `[x]`).

## Manual (post-merge, cannot be automated without live Telegram)

- On a real bot, click a chat announcement button "иду"/"не иду" and confirm every published
  copy of that event's announcement (in different topics) updates, not just the clicked one.
- In the Mini App, open a stale event card, tap "leave" when already removed, confirm a polite
  no-op and no phantom join.
