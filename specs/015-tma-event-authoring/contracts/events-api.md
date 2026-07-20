# Contract: Events authoring API (`web/routers/events.py`)

New router, mounted `app.include_router(events.router, prefix="/api/events", tags=["Events"])`.
All responses are JSON DTOs (R-DATA-8); success is a structural field, never inferred from message
text. Identity comes only from validated init-data (`Depends(get_current_user_id)`, R-SEC-1).

## POST `/api/events` — create event

**Auth**: valid session only (no admin gate) — authority-parity with the bot's un-gated
`event_create`.

**Request body** (JSON):
```json
{
  "title": "Поход на Ала-Арчу",
  "date_text": "10-15 июня",
  "end_date_text": null
}
```
- `title` — required, non-empty after trim.
- `date_text` — required; free human text (may be a range). Parsed by
  `DateService.parse_smart_date` server-side.
- `end_date_text` — optional; explicit range end when `date_text` is a single day.

**Server flow**: parse dates (R-CODE-5) → `ManagementService.create_event_action(title, start_date,
creator_id=user_id, is_approved=0, end_date, start_iso, end_iso)` → on `event_id > 0`:
`submit_request(user_id, "event_approval", event_id)` + `EventService.notify_admins_for_approval(bot, event_id)`.

**Response 200**:
```json
{
  "success": true,
  "event_id": 42,
  "date_recognized": true,
  "message": "🚀 Поход создан и отправлен на модерацию!"
}
```
- `date_recognized: false` when `parse_smart_date` returned no `iso_start` — the client shows the
  "won't reach the calendar" hint; the event is still created (FR-004 parity).

**Errors**:
- `400` — empty title / unparseable-but-required field: `{ "detail": "<clear message>" }`.
- `401` — missing/invalid init-data.
- `500` — `event_id <= 0` (DB failure): `{ "detail": "Ошибка базы данных" }`.

## PUT `/api/events/{event_id}` — edit event

**Auth**: valid session **and** `EventService.can_edit_event(user_id, event_id)` (creator OR global
admin). Failure → `403`. This per-event re-check is the authority-parity invariant; **no blanket
`require_admin`**.

**Request body** (JSON):
```json
{
  "title": "Поход на Ала-Арчу (обновлено)",
  "date_text": "12 июня",
  "end_date_text": null
}
```

**Server flow**: `can_edit_event` (else 403) → parse dates → decompose range human parts
(`split_human_range`) → `ManagementService.update_event_details(event_id, title, start_date,
end_date, start_iso, end_iso)`. No approval re-notification (parity — edit does not re-audit).

**Response 200**:
```json
{ "success": true, "event_id": 42, "date_recognized": true, "message": "✅ Изменения сохранены!" }
```

**Errors**:
- `403` — `can_edit_event` false: `{ "detail": "❌ У вас нет прав на редактирование." }`.
- `404` — event does not exist.
- `400` — empty title / invalid payload.
- `401` — missing/invalid init-data.

## Reused GET reads (small `[MODIFY]` — display serialization + can_edit)

The authoring screens seed and refresh from existing endpoints. Their **logic is unchanged**; two
response-shape adjustments are applied (no new query, no new mutation):
- `GET /api/dashboard/events` — list. Display fields un-escaped for JSON (D3).
- `GET /api/dashboard/events/{event_id}` — card + edit-form seed. Display fields un-escaped (D3);
  **adds `can_edit`** (boolean, server-computed via `EventService.can_edit_event(user_id, event_id)`)
  so the client shows the edit affordance only to authorized users (D7 / U1). The flag is derived
  and non-authoritative — the `PUT` re-checks regardless.
- `GET /api/announcements/{ann_id}` — announcement card (entry via `?ann_id=`). Display fields
  un-escaped (D3).

Example `GET /api/dashboard/events/{id}` (added field in **bold** intent):
```json
{
  "id": 42, "title": "Поход на Ала-Арчу", "start_date": "10 июня", "end_date": "15 июня",
  "participants_count": 3, "is_participant": true, "status": "pending",
  "can_edit": true
}
```

## Serialization boundary (escape reconciliation, D3)

Display string fields returned to the Mini App are human-readable (un-escaped) so the
escape-by-default render layer shows correct glyphs. This applies to **all** display fields —
including the reused GET readers above, not only the new authoring responses (D3 scope note). The
shared `ManagementService` mutations are **not** modified — the un-escape is a web-layer
serialization concern. The render layer never trusts this and escapes at the DOM regardless
(defense in depth; FR-013).

**Canonical wire form (resolves A1)**: a title the user entered as `Поход <b>x</b>` is stored
HTML-escaped by `create_event_action` (`Поход &lt;b&gt;x&lt;/b&gt;`) but the JSON boundary returns
the **raw human-readable characters** `Поход <b>x</b>` (un-escaped once, never double-escaped). The
frontend render layer then emits those as a text node, so nothing executes. Tests assert this exact
raw form.

## Test contract (Level-A harness, R-TEST-3)

`tests/test_web/test_events_create.py`
- **positive**: seeded user creates via `web_call("POST", "/api/events", body, init_data=forge_init_data(uid))`
  → `success true`, event exists, creator is participant **and** lead, approval request submitted.
- **negative**: empty title → `400`; assert no event created.
- **date parity**: unrecognized `date_text` → `success true`, `date_recognized false`.

`tests/test_web/test_events_edit.py`
- **positive (authority-parity)**: creator who is **not** a global admin edits own event → `200`,
  fields updated.
- **negative**: unrelated non-admin user edits → `403`, event unchanged.
- **404**: edit of a non-existent event.

`tests/test_web/test_frontend_contract.py`
- **entry mapping**: `GET /api/announcements/{seeded}` returns the announcement DTO (the `?ann_id=`
  target survives) — pins FR-014's server contract.
- **escape (canonical form)**: create an event whose `title` contains markup (e.g. `Поход <b>x</b>`),
  then read it back via `GET /api/dashboard/events/{id}` — assert the response `title` equals the
  raw human-readable `Поход <b>x</b>` (un-escaped, not `&lt;b&gt;`, not double-escaped). The DOM-side
  escape-by-default is verified on the Level-B stand.
- **can_edit affordance (D7/U1)**: `GET /api/dashboard/events/{id}` returns `can_edit true` for the
  creator (non-admin) and `can_edit false` for an unrelated user — pins the affordance contract; the
  `PUT` authority gate is tested separately in `test_events_edit.py`.

All assertions check both positional `args` and `kwargs` on mocked `bot.*` calls (R-TEST-3).
