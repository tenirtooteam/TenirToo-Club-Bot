# Research — Feature 007 Bot Correctness

No external/unknown technologies are introduced. "Research" here = design decisions that
resolve the *how* for each bug, with the alternative considered and why it was rejected.
All decisions stay inside the current stack and layering.

---

## BUG-1 — Multi-day date-range corruption

**Decision**: Add `DateService.split_human_range(text: str) -> Tuple[str, Optional[str]]` that
decomposes a human range string into `(start_human, end_human)` reusing the *same* separator
detection (`count("-") == 1`, plus the spaced `" - "` form) and month-inheritance logic already
in `parse_smart_date`. For `"10-15 июня"` it returns `("10 июня", "15 июня")`; for a single date
it returns `(text, None)`. Both `process_date_confirm` and `process_editing_dates` call this
helper instead of splitting on `-` inline.

**Rationale**: R-CODE-5 forbids ad-hoc date splitting in handlers — date parsing/decomposition
belongs in `DateService`. The current handler bug is precisely an in-handler `dates.split("-")`
that (a) drops the month from the start part and (b) in the editing path discards the split
result entirely (`_s_human`/`pass`). Centralizing gives one correct implementation, unit-testable
in `test_date_logic.py`, and makes the start human *complete* (`"10 июня"`) rather than a
fragment — which is stored raw per R-CODE-6 (month-inheritance is data completion, not UI
decoration).

**Alternatives considered**:
- *Change `parse_smart_date` to also return the two human parts (5-tuple).* Rejected: ripples
  through every caller (`process_event_dates`, `process_date_preset`, `process_event_end_date`,
  edit path) and breaks the documented `(human, start_iso, end_iso)` contract for no gain.
- *Fix the split inline in the handler.* Rejected: violates R-CODE-5 and duplicates logic across
  the create and edit handlers.

---

## BUG-2 — Active list ordering & past-filtering

**Decision**: `get_active_events(today: Optional[str] = None)`; SQL becomes
`... WHERE is_approved = 1 AND (COALESCE(end_iso, start_iso) >= :today OR start_iso IS NULL)
ORDER BY start_iso ASC`. `today` defaults to `datetime.date.today().isoformat()`; tests inject a
fixed value. `EventService.get_active_events()` passes through (optionally forwarding `today`).

**Rationale**: `start_iso`/`end_iso` are stored `YYYY-MM-DD`, so lexicographic `ORDER BY` equals
chronological order (Assumption in spec). `COALESCE(end_iso, start_iso)` treats a multi-day hike
as past only after its *end* (ongoing hikes stay visible); `OR start_iso IS NULL` keeps undated
hikes always-visible (spec FR-005, never silently drop). Injecting `today` keeps the query
deterministic under `db_setup` isolation (R-TEST-1) without freezing the system clock.

**Alternatives considered**:
- *`date('now','localtime')` in SQL.* Rejected: non-deterministic in tests; timezone coupling.
- *Filter/sort in Python after fetch.* Rejected: pushes ordering logic out of the data layer and
  is less efficient; the DB expresses this cleanly.
- *Sort by `start_date` (human) with a parser.* Rejected: that is the bug; ISO already exists.

**Note on NULL ordering**: SQLite sorts `NULL` first on `ASC`. Undated hikes will surface at the
top of the list. Accepted as reasonable (undated = "whenever / ongoing"); can be revisited if UX
prefers them last (`ORDER BY start_iso IS NULL, start_iso ASC`) — recorded as an optional refinement.

---

## BUG-3 — Non-text input crashes FSM handlers

**Decision**: In each of the five awaiting handlers, guard before `.strip()`:
`if not message.text: return await UIService.show_temp_message(state, message, "⚠️ Пожалуйста,
введите текст.")`, staying in the same state. Reuse the exact pattern already present in
`process_event_title`/`process_event_dates`.

**Rationale**: aiogram dispatches a state-bound `@router.message(State)` handler for *any* content
type; `message.text` is `None` for photo/sticker/voice → `AttributeError`. The codebase already
has the sanctioned graceful pattern; consistency (R-UI-8 tone, R-UI-1 via `show_temp_message`)
and minimal change argue for replicating it rather than inventing a decorator.

**Alternatives considered**:
- *Add an `F.text` filter to each handler.* Rejected: a non-text message would then fall through
  to no handler (silent no-op) — worse UX than an explicit "send text" nudge, and could hit the
  global fallback with a confusing alert.
- *A shared decorator/middleware.* Rejected as over-engineering for five call sites; larger blast
  radius and harder to keep each state's bespoke prompt.

---

## BUG-4 — `leave` must be remove-only

**Decision**: Add `ManagementService.leave_event_action(event_id, user_id) -> tuple[bool, str]`
that removes participation only if the user is a participant, else returns
`(False, "Вы не участвуете в этом походе.")` — it never adds. Repoint `handlers/events.py::
leave_event` from `toggle_event_participation` to this method.

**Rationale**: Joining a hike is gated behind a request→admin-approval flow; `toggle` turns the
"Leave" button (reachable from a stale keyboard) into a silent, audit-bypassing join — an
integrity/authority defect in the spirit of R-SEC-3 (single guarded write-path) and R-DATA-1
(mutation intent owned by the service). Remove-only makes the operation monotonic. Existing
`remove_event_participation_action` returns a bare `str`; a dedicated `(bool,str)` method keeps
the handler's `success, msg =` contract and the announcement refresh unchanged.

**Alternatives considered**:
- *Guard in the handler ("if not participant: return").* Rejected: puts mutation-precondition
  logic in a handler (R-DATA-1) and duplicates the participant check the service already owns.
- *Reuse `remove_event_participation_action` (str).* Rejected: loses the `(bool,str)` contract the
  handler and R-DATA-1 expect; message wording ("Вы еще не записались чтобы не идти!") is a UX
  mismatch for a leave action.

---

## BUG-5 — TOCTOU on request resolution

**Decision**: Make the status transition an atomic compare-and-swap at the DB layer:
`database/audit.py::resolve_audit_request(request_id, status, comment)` executes
`UPDATE audit_requests SET status=?, comment=?, updated_at=CURRENT_TIMESTAMP
WHERE id=? AND status='pending'` and returns `cursor.rowcount > 0`. In
`ManagementService.resolve_request`, read the request (for `entity_type`/`entity_id`/`user_id`),
then call the CAS; **only if it returns True** perform the DB side effect (approve / add
participant / delete draft) and send the single notification. The early
`request["status"] != "pending"` check is kept as a friendly fast-fail, but the CAS `rowcount` is
the authoritative gate.

**Rationale**: In single-process asyncio, two admin coroutines can both pass the pre-check across
an `await` boundary before either writes. A conditional UPDATE lets SQLite serialize the winner:
exactly one coroutine flips `pending→approved/rejected` and sees `rowcount==1`; the loser sees
`rowcount==0` and does nothing. This removes duplicate side effects and duplicate notifications
(spec FR-009/FR-010) without locks or new infrastructure. Also fixes the current unconditional
`WHERE id=?` which would happily re-resolve an already-resolved row.

**Alternatives considered**:
- *`asyncio.Lock` around resolve.* Rejected: process-local only, doesn't reflect the real
  invariant (which is on the row), and serializes unrelated requests.
- *`SELECT ... FOR UPDATE`.* Rejected: not meaningfully supported by SQLite; the conditional UPDATE
  is the idiomatic atomic CAS here.

---

## Tail — dead code & anonymous-sender guard

**Decision**:
- Remove no-effect expressions: `handlers/events.py` bare `data['new_title']` (~352) and the
  discarded `_s_human/_e_human`/`pass` branch (~364-372, subsumed by the BUG-1 rewrite);
  `services/ui_service.py` the two evaluated-and-discarded ternaries (~115-116).
- `middlewares/access_check.py`: change the guard to
  `if event.from_user is None or event.chat.type == "private" or event.from_user.id == event.bot.id:
  return await handler(event, data)` — messages with no sender (channel/automatic posts) pass
  through untouched.

**Rationale**: Dead expressions are pure noise and, in the edit path, actively hid BUG-1; removing
them changes no observable behavior (proven by the suite staying green — R-TEST-4). `from_user` is
`None` for channel posts / some automatic messages; the current `.id` access crashes the stealth
guard. Pass-through is the safe posture — access control keys off a real user, and a senderless
message is not an unauthorized *user* action.

**Alternatives considered**:
- *Silently delete senderless messages.* Rejected: could delete legitimate system/channel content
  and diverges from the Default-Deny model (R-DB-1), which is about *user* topic access.
