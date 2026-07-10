# Internal Contracts — Feature 007 Bot Correctness

This is an internal layered app; the "contracts" are the function signatures added/changed by
this feature. No external API surface changes. Signatures below are the authoritative shape the
implementation and tests target.

## New — `services/date_service.py`

~~~python
@staticmethod
def split_human_range(text: str) -> tuple[str, Optional[str]]:
    """
    Decompose a human date string into (start_human, end_human).

    Reuses the same separator detection ("-" once, or spaced " - ") and month-inheritance
    used by parse_smart_date, so the start part is COMPLETE:
      "10-15 июня"   -> ("10 июня", "15 июня")
      "10 - 15 мая"  -> ("10 мая", "15 мая")
      "10 июня - 15 июня" -> ("10 июня", "15 июня")
      "15 мая"       -> ("15 мая", None)
    Non-range / unrecognized input returns (text, None).
    """
~~~

- Contract: never returns a fragment lacking the month when the counterpart carries one.
- Callers: `handlers/events.py::process_date_confirm`, `::process_editing_dates`.

## Changed — `database/events.py`

~~~python
def get_active_events(today: Optional[str] = None) -> List[EventDTO]:
    """
    Approved, non-past hikes ordered by ISO start date.

    today: 'YYYY-MM-DD'; defaults to datetime.date.today().isoformat().
    SQL: WHERE is_approved = 1
         AND (COALESCE(end_iso, start_iso) >= :today OR start_iso IS NULL)
         ORDER BY start_iso ASC
    Still returns EventDTO (R-DATA-8). Undated (start_iso IS NULL) always included.
    """
~~~

- Wrapper `services/event_service.py::get_active_events(today=None)` forwards `today`.
- Behavioral guarantee: ISO order (INV-3), past excluded except ongoing/undated (INV-2).

## Changed — `database/audit.py`

~~~python
def resolve_audit_request(request_id: int, status: str, comment: str = None) -> bool:
    """
    Atomic compare-and-swap: flip status pending -> {approved|rejected}.

    UPDATE audit_requests SET status=?, comment=?, updated_at=CURRENT_TIMESTAMP
    WHERE id=? AND status='pending'
    Returns True iff exactly this call performed the transition (cursor.rowcount > 0).
    """
~~~

- Contract change: return now means "I won the transition", not merely "no SQL error".

## Changed — `services/management_service.py`

~~~python
@staticmethod
async def resolve_request(bot: Bot, request_id: int, status: str, comment: str = None) -> tuple[bool, str]:
    """
    BUG-5: read request (entity_type/entity_id/user_id), then gate on the CAS.
    Order:
      1. request = db.get_audit_request(request_id); if missing -> (False, "не найдена").
      2. fast-fail if request["status"] != "pending" (friendly message).
      3. won = db.resolve_audit_request(request_id, status, comment)   # atomic CAS
         if not won -> (False, "⚠️ Эта заявка уже была обработана.")   # lost race / already resolved
      4. ONLY IF won: perform side effect (approve / add participant / delete draft) + single notify.
    """

@staticmethod
def leave_event_action(event_id: int, user_id: int) -> tuple[bool, str]:
    """
    BUG-4: remove-only. Never creates participation.
      - participant     -> remove, sync, (True,  "❌ Вы больше не участвуете.")
      - non-participant  -> no-op,  (False, "Вы не участвуете в этом походе.")
    """
~~~

- Caller: `handlers/events.py::leave_event` replaces `toggle_event_participation(...)` with
  `leave_event_action(...)`; announcement refresh + `callback.answer(msg)` unchanged.

## Changed — handlers (BUG-3 guard, no signature change)

Affected handlers gain, before any `message.text.strip()`:

~~~python
if not message.text:
    return await UIService.show_temp_message(state, message, "⚠️ Пожалуйста, введите текст.")
~~~

Sites: `handlers/moderator.py` (rename topic, direct-access search),
`handlers/common.py` (search query), `handlers/events.py` (editing title, editing dates).

## Changed — `middlewares/access_check.py` (tail, no signature change)

~~~python
if event.from_user is None or event.chat.type == "private" or event.from_user.id == event.bot.id:
    return await handler(event, data)
~~~
