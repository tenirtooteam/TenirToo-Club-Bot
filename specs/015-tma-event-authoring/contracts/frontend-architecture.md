# Contract: Mini App frontend architecture (module boundaries + render + routing)

Native browser ES modules under `web/frontend/js/`. No framework, no bundler, no build step
(R-PROC-7, Footprint 0). `index.html` loads a single module entry (`<script type="module"
src="js/main.js">`); the monolithic `app.js` is deleted.

## Module boundaries

| Module | Responsibility | May import | MUST NOT |
|---|---|---|---|
| `main.js` | Bootstrap: Telegram SDK glue, read `?ann_id=`, start router | router, api | render HTML directly |
| `router.js` | Hash-route table, screen switch, back-history stack + `tg.BackButton` | screens | contain business logic |
| `api.js` | Fetch wrapper: init-data header, structural `success`, error surfacing | — | parse dates / apply business rules |
| `render.js` | Escape-by-default DOM helpers (text setter, safe list/template) | — | expose a raw-`innerHTML` path for server data |
| `screens/*` | One screen each: fetch via `api`, build DOM via `render` | api, render, ui | call `fetch` directly; set `innerHTML` with server strings |
| `ui/components.js` | Shared widgets: badge, date-range chip, status-by-shape | render | fetch data |

**One-way imports**: `main → router → screens → {api, render, ui}`. Screens never import each other;
shared visuals go through `ui/`. (Mirrors the backend's consumer→provider discipline, R-ARCH-4 in
spirit.)

## Routing contract (FR-012, FR-014)

- **Bootstrap entry** (`main.js`): read `new URLSearchParams(location.search).get('ann_id')`.
  - present → navigate to `#/ann/{ann_id}` (announcement card).
  - absent → navigate to `#/dashboard`.
  - This preserves today's two entry modes; live in-chat `web_app` buttons (`{WEBAPP_URL}/?ann_id={id}`)
    keep landing on the right card. **Breaking this contract orphans every sent announcement.**
- **Internal navigation**: hash routes only (no `pushState`, no server route fallbacks — the static
  mount stays untouched). Back button pops the history stack; empty stack hides `tg.BackButton`.
- Route table lives in `router.js`; a screen is looked up by exact route key (no substring
  matching), unknown route → dashboard fallback (defensive, mirrors R-UI-3 spirit).

## Render contract — escape-by-default (FR-013)

- **The only sanctioned path from data to DOM is `render.js`.** It sets user/server strings via
  `textContent` or a template helper that escapes interpolations.
- **Prohibited**: assigning server/user strings into `innerHTML` (the current `app.js:149/172`
  pattern). Static, developer-authored markup templates are fine; *interpolated data* is always
  escaped.
- Rationale: `tg.initData` shares the JS scope; an unescaped user-authored title = session theft
  within the TTL (R-SEC-1). Escape-by-default is a security invariant, independent of any backend
  escaping (defense in depth, D3).
- **Verification**: on the Level-B stand (port 8100), seed a persona and create/view an event whose
  title contains `<b>`/`<script>`-like text; confirm it renders as literal characters and nothing
  executes.

## Design-system v2 contract (FR-017, FR-018)

- Tokens (color, typography, radius, spacing) defined once as CSS custom properties in `style.css`,
  sourced from the approved v2 mockup (`_nogit_tma_mockup_v2.html`; cross-machine fallback: the
  published artifact). Screens consume tokens, never hard-coded values.
- **Status by shape, not color alone**: draft/active/moderation carry a distinct glyph/shape marker
  (accessibility / color-blindness), via `ui/components.js`.
- **Date-range chip**: a multi-day event shows a human range ("26 → 27"); single day shows one date.
- Applied to authoring + list/card screens in this feature; 016/017 screen styles land with those
  screens.

## Development & verification surfaces

- **Level-B stand** (`local_scripts/tma_audit_server.py`, port 8100): the browser dev/audit surface;
  serves the module frontend + real API with an injected `window.Telegram.WebApp` shim (offline).
  Primary loop for building screens.
- **Level-A harness** (`tests/test_web/`): backend endpoint coverage (see `events-api.md`).
- The frontend module split is behavior-preserving for the migrated read screens (Chunk B): the
  same data renders, only the source layout and the render path change.
