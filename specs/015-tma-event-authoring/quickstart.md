# Quickstart & Validation: TMA event authoring + frontend modularization

Run everything inside the venv (R-PROC-7): `.\venv\Scripts\python.exe ...`.

## Prerequisites

- venv active; suite green at baseline (`.\venv\Scripts\python.exe -m pytest -q`).
- Level-B stand available: `.\venv\Scripts\python.exe local_scripts\tma_audit_server.py`
  (port 8100 or `TMA_AUDIT_PORT`); it prints per-persona URLs with forged init-data.

## Backend validation (Level-A harness, no Telegram)

Named tests (see `contracts/events-api.md` for the full contract):

| Test file | Scenario | Expected |
|---|---|---|
| `tests/test_web/test_events_create.py::test_create_positive` | seeded user POSTs valid event | `success true`; event exists; creator is participant **and** lead; approval request submitted |
| `tests/test_web/test_events_create.py::test_create_empty_title` | POST with blank title | `400`; no event created |
| `tests/test_web/test_events_create.py::test_create_unrecognized_date` | POST with unparseable date | `success true`, `date_recognized false` (parity — not blocked) |
| `tests/test_web/test_events_edit.py::test_edit_creator_non_admin` | creator (not global admin) PUTs own event | `200`; fields updated — **authority-parity** |
| `tests/test_web/test_events_edit.py::test_edit_no_rights` | unrelated non-admin PUTs event | `403`; event unchanged |
| `tests/test_web/test_events_edit.py::test_edit_missing_event` | PUT non-existent event | `404` |
| `tests/test_web/test_frontend_contract.py::test_annid_entry_target` | GET announcement by id | announcement DTO returned (`?ann_id=` target survives) |
| `tests/test_web/test_frontend_contract.py::test_markup_title_literal` | create title with markup, read back | raw human-readable characters returned (un-escaped, not `&lt;b&gt;`, canonical A1 form) |
| `tests/test_web/test_frontend_contract.py::test_can_edit_flag` | GET event-details as creator vs. unrelated | `can_edit` true for creator, false for unrelated (D7/U1) |

Run just this feature's web tests:
```text
.\venv\Scripts\python.exe -m pytest tests\test_web -q
```

Full suite (must stay green, SC-006):
```text
.\venv\Scripts\python.exe -m pytest -q
```

## Frontend validation (Level-B stand, browser)

1. Start the stand; open a printed persona URL (a non-admin creator persona) in a browser.
2. **US3 entry mapping**: open a persona URL with `?ann_id={seeded}` appended → the announcement
   card loads (not the dashboard). Remove the param → dashboard loads.
3. **US1 create**: from the events list, open the create form, enter a title + "10-15 июня", submit →
   the event appears; open it → creator is shown participating; a nonsense date submits with the
   "won't reach the calendar" hint. Submit with an empty title → error shown and the already-entered
   fields are preserved (FR-006).
4. **US2 edit (authority-parity)**: as the creator persona (non-admin), the edit control is visible
   (`can_edit`), edit the just-created event → change saved. As an unrelated persona, the edit
   control is absent, and a direct edit call is refused by the server (403 surfaced).
5. **US3 escape-by-default**: create an event titled `Поход <b>x</b>` → the list/card show the literal
   text; nothing renders as bold, nothing executes.
6. **US3 navigation**: move dashboard → list → card → back; transitions occur without a page reload;
   `tg.BackButton` follows the history.
7. **US4 design system**: authoring + list screens use v2 tokens; a moderation/draft status is
   distinguishable by shape (not color only); a multi-day event shows a date range.

## Gate & wrap-up

- After `/speckit-plan`: prompt-linter **plan** stage on `plan.md` (English).
- After `/speckit-tasks`: prompt-linter **checklist** stage on `tasks.md` (all boxes `[x]`, ASCII-safe).
- CHANGELOG entry via CMD-4 lands with Chunk D (design system) at feature close (R-PROC-6).
- Manual live-Telegram check (real HMAC + real webview render) remains an out-of-band tail, tracked
  in the handover — the backend is covered by Level-A, UI by Level-B.
