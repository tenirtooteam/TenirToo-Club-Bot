# Contract: Moderation frontend (screen modules inside the feature-015 architecture)

Additive only. New screens plug into the existing `web/frontend/js/` module architecture from feature
015 (hash router, `api.js` fetch wrapper with init-data header + structural success, `render.js`
escape-by-default DOM helpers). **No unrelated screen module is modified** (FR-014); no framework or
build step is added (R-PROC-7).

## New screen modules

### `js/screens/moderation-queue.js` (US1/US2/US4)

- On enter: `GET /api/moderation/queue` via `api.js`; render each `QueueItemDTO` as a **request card**.
- Request card: event title + requester + submitted-time (all via `render.js` text nodes — never
  `innerHTML` of server strings), a **type badge encoded by shape** (not color alone: e.g. leading dot
  vs. square — status-by-shape, FR-015), and explicit **Принять / Отклонить** actions.
- Action → `POST /api/moderation/requests/{id}/resolve` with `{status}` (+ optional comment). On
  `success:true` remove the card and toast; on `success:false` toast "уже обработана" and refresh the
  queue (stale item). On 403 toast the denial.
- Empty queue → friendly empty-state, not a blank screen.
- Lists > 7 items paginate/scroll.

### `js/screens/participants.js` (US3)

- On enter: `GET /api/moderation/events/{id}/participants`; render roster (names via text nodes),
  organizers marked, optional capacity meter (presentational).
- Remove → an explicit **confirm step** fires first (R-DATA-4; cancel = no request sent, no roster
  change), then `DELETE /api/moderation/events/{id}/participants/{uid}`; on success remove the row +
  toast; stale remove (no-op) handled gracefully.

## Router / nav wiring (`js/router.js` [MODIFY], `index.html` [MODIFY])

- Add routes for the moderation queue and the participants screen.
- A **nav affordance** (e.g. a "Модерация" tab/entry) is shown only when the viewer has something to
  moderate — the simplest gate is presence of items from `GET /queue` (authority is enforced server-
  side regardless; the affordance is a UX hint, never a security boundary, R-SEC-3).
- **Optional** (D9, not required): map a `start_param` deep-link to the queue route on first load. The
  feature-015 `?ann_id=` entry contract is untouched.

## Design system (`style.css` [MODIFY], `ui/components.js` [MODIFY])

- Request-card component + status-by-shape badge + capacity/roster tokens per the approved v2 mockup
  (`_nogit_tma_mockup_v2.html`).
- Reuse existing v2 tokens (color/typography/radius/spacing) from feature 015; add only the moderation-
  specific component styles. No token redefinition.

## Invariants inherited from feature 015 (not re-specified here)

- **Escape-by-default**: every server/user string (event titles, requester/display names) reaches the
  DOM as literal text.
- **Structural success**: `api.js` decides success by the response flag, never by message text.
- **Init-data header**: every request carries the validated init-data header; identity is server-side.
