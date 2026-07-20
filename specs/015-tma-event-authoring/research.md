# Phase 0 Research: TMA event authoring + frontend modularization

All decisions below resolve unknowns before design. No `NEEDS CLARIFICATION` remain.

## D1 — Authorization model for the events domain (authority-parity)

**Decision**: Per-action authorization, no blanket gate.
- **Create** (`POST /api/events`): requires only a valid session (`Depends(get_current_user_id)`).
- **Edit** (`PUT /api/events/{event_id}`): requires a valid session **and** a server-side
  `EventService.can_edit_event(user_id, event_id)` check that returns 403 on failure.

**Rationale**: The bot's `event_create` handler (`handlers/events.py:65`) has **no** admin gate —
any private-chat user creates an event that lands in moderation (`is_approved=0`). The bot's edit
init (`handlers/events.py:305-311`) gates on `EventService.can_edit_event`, which allows the
creator OR any global admin. Mirroring both exactly is the authority-parity invariant (R-SEC-3,
R-ARCH-7): a blanket `Depends(require_admin)` on the events domain would strip a plain creator of
the ability to edit their own event — a rights regression and channel divergence. `require_admin`
remains a tool for the admin domain (feature 017), not events.

**Alternatives considered**:
- *Blanket `require_admin` on the events router* — rejected: breaks creator edit, contradicts the
  bot, violates the invariant.
- *Client-sent "is_admin"/"can_edit" flag* — rejected: identity/authority from the client is
  never trusted (R-SEC-1); authority is recomputed server-side per event.

## D2 — Form shape and date handling

**Decision**: The authoring form submits raw human strings; the server parses.
- Payload fields: `title` (string), `date_text` (string, the "when" — may itself be a range like
  "10-15 июня"), optional `end_date_text` (string).
- The endpoint reproduces the handler's parsing chain server-side: `DateService.parse_smart_date`
  on `date_text` (yields `human`, `iso_start`, `iso_end`); when a range is detected,
  `DateService.split_human_range` decomposes the human start/end (mirrors `handlers/events.py:190`);
  an explicit `end_date_text`, when present, is parsed the same way.
- An unrecognized date does **not** block save: the event is created with the raw human string and
  no ISO, and the response signals the "won't reach the calendar" warning — parity with the bot
  (`handlers/events.py:109-120`).

**Rationale**: R-CODE-5 forbids ad-hoc date parsing outside `DateService`; the client must carry no
date business logic (R-SEC-3). Submitting human text and parsing server-side keeps the single
smart-date protocol and reuses the exact code path the bot already trusts. The multi-step FSM
(title → dates → confirm → optional end) collapses into one screen because the *confirmation* and
*add-end-date* steps were UI scaffolding around a parser that already returns ranges in one call.

**Alternatives considered**:
- *Client sends ISO dates from a date-picker* — rejected: moves normalization to the client,
  violates R-CODE-5, and loses the natural-language parity ("завтра", "15 мая").
- *Keep a server-side confirm round-trip* — rejected: the confirm step existed only because the
  bot cannot show a form; a form previews locally and submits once.

## D3 — Escape reconciliation between bot HTML context and TMA text context

**Decision**: Escape at the render layer (text nodes / safe templating); un-escape at the web
serialization boundary when serving JSON to the Mini App.

**Context / problem**: `ManagementService.create_event_action` and `update_event_details`
`html.escape(...)` the title/dates before storage, because the bot renders with `parse_mode=HTML`.
Stored data is therefore HTML-escaped (`Поход &lt;3`). If the TMA render layer (correctly) writes
text via `textContent`, an escaped entity would display literally (`Поход &lt;3`).

**Resolution**:
- The **render layer is escape-by-default** unconditionally: all server/user strings reach the DOM
  as text (`textContent` or an escaping template helper), never via raw `innerHTML`. This is the
  security invariant and does not depend on what the backend stored.
- Because JSON is not an HTML context, the web **serialization boundary** returns human-readable
  (un-escaped) strings for display fields, so the escape-by-default text layer shows the correct
  glyphs. This is a small web-layer concern (a serialization helper), and it does **not** modify the
  shared `ManagementService` mutation methods — the bot keeps its HTML-escaped storage untouched.
- **Scope note (resolves I1)**: the un-escape helper applies to **every** display field the Mini App
  renders, which includes the *reused* GET readers (`/api/dashboard/events`,
  `/api/dashboard/events/{id}`, `/api/announcements/{id}`), not only the new authoring responses.
  Today the monolith renders those stored (escaped) strings via `innerHTML`, which silently resolves
  the entities; once the render layer switches to `textContent` (escape-by-default), the same strings
  would otherwise show a literal `&lt;`. So the reused readers get the same small serialization
  `[MODIFY]` (response shape only; no logic change) — this is why `dashboard.py` / `announcements.py`
  are `[MODIFY]`, not `[UNCHANGED]`.

**Rationale**: Cleanly separates presentation contexts (the spirit of R-CODE-6: decorations/encoding
belong to the presentation layer, not the stored datum). The security property (no markup executes)
is enforced at render independently of storage; the display-correctness property is handled at the
JSON boundary without disturbing bot behavior.

**Alternatives considered**:
- *Change `create_event_action` to stop escaping* — rejected: would touch the bot's trusted HTML
  render path and risk a bot-side injection regression; out of this feature's footprint.
- *Render stored value via `innerHTML` so entities resolve* — rejected: this **is** the XSS hole
  (FR-013); non-negotiable.

## D4 — Frontend module architecture and entry mapping

**Decision**: Native ES modules, file-per-screen, plus a tiny hash router; `?ann_id=` query is read
once at bootstrap and mapped to the announcement-card route.
- `main.js` bootstraps: reads `?ann_id=` from `location.search`; if present, routes to the
  announcement card; else to the dashboard (preserves today's two-way entry, FR-014).
- `router.js`: hash-based screen switching, back-history stack (reusing today's `viewStack` +
  `tg.BackButton` behavior), no page reload.
- `api.js`: the single fetch wrapper — attaches the init-data header, treats `success` structurally,
  surfaces errors uniformly.
- `render.js`: escape-by-default helpers (a text-setter and a safe list/template builder) — the one
  sanctioned path from data to DOM.
- `screens/*`: one module per screen; a screen exports an `init/render` it owns; shared widgets
  (badges, date-range chip, status-by-shape) live in `ui/components.js`.

**Rationale**: No framework/bundler (R-PROC-7, Footprint 0). Hash routing needs no server-side route
fallbacks, so FastAPI keeps serving static files unchanged. `?ann_id=` mapping at bootstrap is the
explicit contract keeping already-sent announcement buttons alive (FR-014). File-per-screen creates
the landing pads that 016/017 screens plug into without growing a monolith (SC-007).

**Alternatives considered**:
- *React/Vue/Svelte* — rejected in PA-1: drags a node toolchain + build step into a repo that has
  none (2/6 on Footprint); the payload is a handful of screens.
- *History API (pushState) routing* — rejected: needs server-side catch-all routes for deep links
  and complicates the static mount; hash routing is footprint-free here.
- *Keep the monolith, only add forms* — rejected: every future screen lengthens `app.js`; the
  modularization is the enabling architecture (US3, SC-007).

## D5 — Where authoring endpoints live + participation untouched

**Decision**: New `web/routers/events.py` (router-per-domain), mounted at `/api/events` in
`web/main.py`. Participation toggle endpoints stay in `dashboard.py` / `announcements.py` and keep
calling `EventService.apply_participation_change` (feature 014) — no new code duplicates
participation consequences.

**Rationale**: Router-per-domain matches the roadmap's API decomposition and keeps authoring
separate from participation and from the (future) admin domain. Reusing the 014 orchestration point
honors FR-016 and avoids re-introducing the drift 014 just eliminated.

**Linter parity (R-PROC-10)**: verified — `.ruff.toml` already globs `web/**/*.py` (TID251
allowance), and neither `.importlinter` nor `semgrep-rules.yaml` declares a web-layer contract
(`ban-db-in-handlers` targets `handlers/`). A new file in the existing `web/routers/` package needs
no config edit.

## D6 — Test strategy (Level-A harness)

**Decision**: Every new endpoint gets a `tests/test_web` module driven by `web_call` +
`forge_init_data`; each has a positive and a negative path. Authority-parity is asserted directly:
edit as the creator (non-admin) succeeds; edit as an unrelated user 403s. A `test_frontend_contract`
module pins the two frontend invariants that are server-observable in shape: the `?ann_id=` entry
maps to the announcement route, and a title containing markup is returned/rendered as text.

**Rationale**: R-PROC-3 / R-TEST-3 — tests precede the frontend consumer; the harness needs no
Telegram and no httpx (R-TEST-2). New authoring endpoints have no prior behavior to characterize, so
these are forward specification tests plus an authority-parity assertion; the `?ann_id=` mapping is
characterized because it is *existing* behavior that must survive the rewrite.

**Note on frontend render assertions**: the escape-by-default DOM behavior is exercised
interactively on the Level-B stand (port 8100); the server-side test asserts the API returns the
literal string, and the render contract is documented in `contracts/frontend-architecture.md` and
verified on the stand during Chunk B/C.

## D7 — Edit-affordance visibility (resolves U1)

**Decision**: The edit affordance is driven by a server-computed `can_edit` boolean added to the
event-details DTO (`GET /api/dashboard/events/{id}`), computed via `EventService.can_edit_event`.
The client shows the edit control only when `can_edit` is true; the server remains the sole
authority and re-checks on `PUT` regardless (defense in depth).

**Rationale**: The client cannot compute edit authority from the existing DTO (no `creator_id` /
role data is exposed), and it must not be given raw authority inputs to decide for itself
(R-SEC-1). Exposing a single derived, non-authoritative `can_edit` flag lets the UI hide a control
the user cannot use (Frictionless UX — no dead button that only 403s), while the true gate stays on
the server (R-SEC-3, authority-parity). This is the roadmap's DTO-contract discipline (R-DATA-8):
one derived field, not a leak of the underlying rule.

**Alternatives considered**:
- *Show edit to everyone, rely on the 403* (option "a") — rejected by Шэф: a visible control that
  always fails for non-authors is a UX dead end.
- *Client computes edit rights from creator_id/roles* — rejected: pushes an authority decision to
  the client and widens the trusted surface (R-SEC-1); the flag is derived server-side and never
  trusted for the actual mutation.
