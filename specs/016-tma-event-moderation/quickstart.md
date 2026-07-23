# Quickstart & Validation: TMA event moderation + audit-request queue

Validation guide only — no implementation code here. Each scenario names the test that proves it and
maps to Success Criteria. Backend tests run in-process (Level A, no Telegram); the frontend is checked
against the Level-B browser stand.

## Prerequisites

```powershell
# From repo root, inside the mandatory venv (R-PROC-7)
.\venv\Scripts\python.exe -m pytest -q          # full suite baseline (expect green before starting)
```

Level-A harness: `tests/test_web/conftest.py` (`web_call`, `forge_init_data`, `seed_*`) — no
httpx/TestClient (R-TEST-2). Level-B stand: `local_scripts/tma_audit_server.py` (port 8100).

## Scenario 1 — узел-3: approved participation refreshes the announcement (SC-002) — **write FIRST**

Seed an approved event with an active announcement + a pending `event_participation` request; mock
`AnnouncementService.refresh_announcements` and `EventService.notify_organizers_of_direct_join`; call
`ManagementService.resolve_request(bot, req_id, "approved")`.

- Expect: `refresh_announcements` called once with `("event", event_id)` (assert `args`); direct-join
  notice **not** called; applicant added; single user notification.
- **Fails today** (approval never refreshes) → passes after the Chunk-A fix (R-PROC-3).

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_services/test_participation_approve_refresh.py -q
```

## Scenario 2 — Queue is viewer-scoped (SC-001, SC-004)

Seed a pending draft (`event_approval`) and a pending participation for event X.

- As **global admin**: `GET /queue` returns the draft, **not** the foreign participation.
- As **organizer of X** (non-admin): `GET /queue` returns the participation for X, **not** the draft.
- Ordering is oldest-first.

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_web/test_moderation_queue.py -q
```

## Scenario 3 — Resolve authority-parity + exactly-once (SC-003, SC-004)

- Admin approves a draft → event approved, applicant/author notified (positive).
- Non-organizer POSTs resolve on a participation request → **403** (negative).
- Organizer approves participation for own event → applicant added, announcement refreshed.
- Two concurrent approves of the same request → exactly one action + one notification; the loser gets
  `success:false` "уже обработана" (reuses feature-007 CAS via the web path).

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_web/test_moderation_resolve.py -q
```

## Scenario 4 — Roster view + participant removal (SC-007)

- Organizer `GET /events/{id}/participants` → roster with names + organizer marks.
- Non-organizer → **403**.
- Organizer `DELETE …/participants/{uid}` → participant removed, announcement refreshed.
- Remove a non-participant (stale button) → no-op, no silent enroll (BUG-4).

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_web/test_moderation_participants.py -q
```

## Scenario 5 — Frontend moderation screens (SC-006 review + manual)

Serve the module frontend via the Level-B stand and open the moderation queue:

```powershell
.\venv\Scripts\python.exe local_scripts/tma_audit_server.py    # http://127.0.0.1:8100
```

- Queue renders request cards with Принять/Отклонить; a request whose title contains markup shows the
  markup as **literal text** (escape-by-default, inherited from 015).
- Status/type is distinguishable by **shape**, not color alone (FR-015).
- Adding these screens does not modify unrelated screen modules (SC-006, structure review).
- Empty queue shows a friendly empty-state.

## Manual tail (outside automation)

Live Telegram client (real HMAC init-data, real webview render, real 64-byte callback limits) is not
covered by Level-A/B. Manual pass: open the Mini App as an organizer and as a global admin, confirm
each sees only their scoped queue and that approving a participation updates the in-chat announcement
roster/capacity live.

## Coverage map

| Success Criterion | Proven by |
|---|---|
| SC-001 resolve every type from TMA | Scenario 2 + 3 |
| SC-002 approval refreshes announcement (0%→100%) | Scenario 1 |
| SC-003 exactly-once under concurrency | Scenario 3 |
| SC-004 authority-parity both directions | Scenario 2 + 3 |
| SC-005 every route has +/- Level-A test | Scenarios 2–4 |
| SC-006 cross-entity queue, facade-only, additive front | Scenario 2 (data) + 5 (structure) |
| SC-007 roster view + removal refreshes announcement | Scenario 4 |
