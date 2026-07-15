# Implementation Plan: Typed Callback Routing

**Branch**: `011-typed-callback-routing` | **Date**: 2026-07-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/011-typed-callback-routing/spec.md`

**Note**: Supporting artifacts ([research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/callback-routes.md), [quickstart.md](quickstart.md)) are written in Russian per the project's response protocol; this plan is English per AGENTS.md § PLAN CONTENT.

## Summary

Replace substring matching and positional parsing in `UIService.generic_navigator` with a single source of truth for callback format: aiogram 3 `CallbackData` factories in a new `callbacks.py` module, a declarative "factory → screen" registry inside the navigator, keyboard generation exclusively via `.pack()`, and handler input filters on `Factory.filter()`. The navigator remains the sole entry point for UI transitions (`R-UI-3` is not revised — see D-6). Approved by PA-1 (Finalist 3, 4/6 — Compliance 2 / Value 2 / Footprint 0); the elevated footprint is a deliberate, sanctioned trade.

**Discovered during planning**: item №19 sits on **three confirmed live defects**, each reproduced executably ([research.md](research.md) §2). Per Q-1/variant A (approved), the feature is widened from "refactor" to "refactor + 3 fixes"; the spec was amended accordingly (FR-012 carve-out, new FR-015…FR-018, SC-009, User Story 1 scenario 5).

| ID | Defect | User-visible effect |
|---|---|---|
| **DEF-1** | Five paginated routes take the page number as the entity ID: `p = callback_data.split("_")` runs over the full string including the `_pg_{n}` tail, then `int(p[-1])` | "Next ▶️" on the group list of topic 55 opens topic **3** |
| **DEF-2** | `topic_assign_pg_{uid}`: the route prefix itself contains `_pg`, so `split("_pg_")` eats it and the route never matches | Paginating the role-assignment topic picker throws the admin back to the main menu |
| **DEF-3** | `topic_in_group_{tid}_{gid}`: `p[-1]`/`p[-2]` are passed to `show_topic_detail(topic_id, group_id)` inverted | A topic opened from a group's topic list shows a **different** topic's card |

Adjacent finding: the correct parse (strip `_pg_` first, then take the tail, guarded by `try/except`) **already exists** at `handlers/moderator.py:44-51` and the navigator does not use it — a literal confirmation of the spec's "format lives in two heads" premise (User Story 2).

Fix ownership: DEF-1 and DEF-2 are resolved by the paginator contract change (D-5); DEF-3 is resolved by the navigator registry (D-6). No defect requires a bespoke patch — each disappears as a consequence of typing, which is the core argument for variant A.

## Technical Context

**Language/Version**: Python 3.11 (`venv` mandatory, `R-PROC-7`)

**Primary Dependencies**: aiogram 3.4.1, pydantic 2.5.3 `[VERIFIED: requirements.txt + runtime import in venv]`. No new dependencies: `aiogram.filters.callback_data.CallbackData` is a stock stack mechanism, currently unused anywhere in the project `[VERIFIED: grep for "CallbackData" outside venv → 0 hits]`.

**Storage**: untouched. The `database.db` facade, schema, and mutation contract are unchanged (FR-014, `R-ARCH-1/2`, `R-DATA-1`).

**Testing**: pytest, pytest-asyncio 0.23.6 (strict). Service-level global state is reset via an autouse conftest fixture, following the existing `reset_registration_cache` / `reset_sheets_sync_state` pattern. Telegram calls are mocked through `mock_bot`; aiogram 3 models are frozen, so `callback.answer` is patched via `patch("aiogram.types.CallbackQuery.answer", ...)` (`R-TEST-3`).

**Target Platform**: Telegram bot (long polling) plus FastAPI mini-app; Linux/Windows.

**Project Type**: Monolithic Telegram bot, layered architecture (`handlers` → `services` → `database` facade).

**Performance Goals**: not a goal of this feature. An exact `dict` lookup by prefix replacing a linear chain of substring `if`s is an incidental improvement to the routing hot path; no metrics are set.

**Constraints**:
- Telegram: `callback_data` ≤ 64 bytes — enforced by `pack()`, which raises `ValueError` on overflow `[VERIFIED]`;
- `CallbackData` separator is `:`; a prefix may not contain it `[VERIFIED]` — existing `_`-style route names stay legal, no renaming needed;
- `unpack()` requires **exact** arity — there is no short form of a route (D-2), so every synthetic transition must pack all fields including `page`;
- `unpack()` failures are fully covered by the tuple `(TypeError, ValueError)` — `ValidationError ⊂ ValueError` `[VERIFIED]`.

**Key risks**:
- *Regression across the 79 `router.callback_query` filters.* Mitigated by the CHAR-OK characterization layer landing before any production edit, and by migrating handlers last (chunk 5), after the paginator and navigator already accept the new form.
- *Silent behavior drift hidden by test edits.* Mitigated by FR-012: editing a characterization test mid-migration is a stop-and-investigate signal, not a fix.
- *64-byte overflow.* Low: all fields are short integer IDs. `pack()` converts the risk from a silent truncation (current `pagination_util.py:26-29` truncates and produces a broken route) into a loud build-time failure caught by tests.

**Scale/Scope**: 21 legacy-navigator routes (13 paginated + 8 non-paginated), 18 constant routes staying as plain strings, 16 `build_paginated_menu` callers, ~40 delegating navigator calls, 79 `router.callback_query` decorators (only those in the family migrate). Full registry in [data-model.md](data-model.md).

**Out of scope** (D-4): the `event_*` / `ann_*` / `date_*` families and the `search_start_*` / `search_pick_*` parsing — these are parsed directly in handlers, bypassing the navigator; same defect class, separate feature. Permissions and authorization (FR-013).

## Constitution Check

*GATE: passed before Phase 0; re-checked after Phase 1.*

| Principle | Status | Justification |
|---|---|---|
| **I. Layered Isolation** (`R-ARCH-1/2/4`) | PASS | `callbacks.py` is a leaf node in the import graph: pure format declarations, importing none of `services` / `handlers` / `database`. The DB facade is untouched; import direction is unchanged. Enforced by import-linter (`R-PROC-11`). |
| **II. Sterile Interface** (`R-UI-1`, `R-FSM-1`, `R-UI-2`) | PASS | All transitions still route through `sterile_show` (FR-009). The single FSM-reset point is preserved inside the navigator (FR-007). `state.clear()` is not introduced. |
| **III. Service-Mediated Mutation** (`R-DATA-1/4`) | PASS | The feature does not touch mutations. A route is transport, not a write. |
| **IV. Test-First** (`R-PROC-3`, `R-TEST-1/3`) | PASS *(unblocked by Q-1/A)* | DEF-1/2/3 are bugs, so `R-PROC-3` demands a failing reproducing test before the fix. Resolved by decision D-3 and the spec amendment: FR-012 now carves out the three defects, FR-018 mandates RED-before-GREEN repro tests, and the characterization layer splits into CHAR-OK (green throughout) and CHAR-DEF (red → green). |
| **V. Single Source of Truth** (`R-CODE-7`) | PASS | The feature is exactly this principle applied to callback format. This plan cites rule IDs rather than restating them. |
| **`R-UI-3`** (single navigator + Defensive Routing) | PASS | The navigator stays the sole transition entry point; the `callback_data` parameter name is preserved; Defensive Routing is strengthened (exact lookup plus typed validation instead of an `in` chain). Rationale: D-6. **Caveat**: should review find FR-010 outside the letter of `R-UI-3`, a Route C rule amendment is required **before** implementation — never a silent deviation. |
| **`R-SEC-2/3`, `R-ARCH-7`** | PASS | The unhandled-callback fallback and server-side authority re-verification are unchanged (FR-013). Typing is not authorization; the roadmap's claimed "removes a class of permission bugs" bonus was excluded as unsubstantiated (PA-1). |
| **`R-ARCH-8`, `R-PROC-10/11`** | PASS | semgrep / ruff / import-linter / AST tests must show no new violations (SC-008). Docker must be up: a `skip` is not a green. |

**Gate verdict**: PASS on all principles. Complexity Tracking is not filled in — there are no unjustified violations; the elevated Footprint is a sanctioned decision under an explicitly granted trade, not a breach.

## Project Structure

### Documentation (this feature)

```text
specs/011-typed-callback-routing/
├── plan.md              # This file
├── spec.md              # Spec (amended 2026-07-14 per Q-1/A)
├── research.md          # Phase 0: stack mechanics, 3 confirmed defects, decisions D-1..D-7
├── data-model.md        # Phase 1: route registry, invariants
├── quickstart.md        # Phase 1: how to validate
├── contracts/
│   └── callback-routes.md   # Phase 1: producer/consumer contract
└── tasks.md             # Phase 2 (/speckit-tasks — NOT created by this command)
```

### Source Code (repository root)

```text
callbacks.py                          # [NEW] CallbackData factories — single source of truth for format.
                                      #       Leaf node: no imports of services/handlers/database.

keyboards/
├── pagination_util.py                # [MODIFY] build_paginated_menu: callback_prefix:str -> page_cb:CallbackData.
│                                     #          Arrows via model_copy(update={"page": n}).pack().
│                                     #          Manual 64-byte truncation -> pack(). help:/back branches -> factories.
├── admin_kb.py                       # [MODIFY] ~57 callback_data -> .pack(); 9 paginator calls.
├── moderator_kb.py                   # [MODIFY] ~22 callback_data -> .pack(); 6 paginator calls.
└── user_kb.py                        # [MODIFY] ~5 callback_data -> .pack(); 1 paginator call.

services/
└── ui_service.py                     # [MODIFY] generic_navigator: substring if-chain (250-388) -> registry.
                                      #          Signature -> str | CallbackData (parameter name preserved).
                                      #          get_confirmation_ui (490+) builds route f-strings -> .pack().
                                      # [DELETE] PAGINATED_CMDS (line 13) — duplicate registry of paginated names.
                                      # [DELETE] split("_pg_") / split("_") / p[-1] / p[3] / p[4] (lines 277-278, 308+).

handlers/
├── admin.py                          # [MODIFY] F.data.startswith(...) -> Factory.filter() for family routes.
│                                     #          Synthetic transitions (f"group_info_{id}") -> factory objects.
├── moderator.py                      # [MODIFY] same.
│                                     # [DELETE] extract_topic_id_from_callback (44-51) — duty moves to the factory.
├── user.py                           # [MODIFY] same.
└── common.py                         # [MODIFY] landing/roles_* are constants, stay strings.
                                      #          perform_search_pick (236+) builds route f-strings -> .pack().
                                      #          search_start_/search_pick_ parsing is OUT OF SCOPE (D-4).

tests/
├── test_services/
│   ├── test_callback_routing_defects.py          # [NEW] RED repro for DEF-1/2/3 (R-PROC-3, FR-018). Written FIRST.
│   ├── test_callback_routing_characterization.py # [NEW] CHAR-OK: "callback_data -> screen", green throughout.
│   ├── test_callback_contract.py                 # [NEW] Invariants R-1, R-2, C-1, P-1, 64-byte, roundtrip.
│   ├── test_callback_static_guard.py             # [NEW] SC-001/002/003: no substring matching, no positional
│   │                                             #       extraction, no hand-built parameterized callback_data.
│   ├── test_ui_integrity.py                      # [MODIFY] R-UI-11: colon parsing now goes through unpack().
│   └── test_ui_fuzzer.py                         # [MODIFY] Malformed-input classes under the new format.
│   # NOTE: existing machine gates live at tests/test_services/test_{import,ruff,semgrep}_lint.py.
│   # There is no tests/test_architecture.py in this repo, and no AST-based test file exists
│   # despite the constitution's wording — do not reference one.
├── test_journeys/
│   └── test_callback_defense.py                  # [MODIFY] Patches generic_navigator — reconcile with new signature.
└── conftest.py                                   # [MODIFY] If needed: autouse reset of the route registry.
```

**Structure Decision**: `callbacks.py` goes in the **repository root**, not inside `keyboards/` or `services/`. Reason: the module must be reachable by both sides of the contract (`keyboards/*` build, `services/ui_service.py` and `handlers/*` parse) while importing neither. Placing it inside either package would create an import direction that does not exist today and would breach `R-ARCH-4`. The root is where the shared leaf modules already live (`config.py`, `loader.py`). Enforced by import-linter (`R-PROC-11`).

## Execution Order (realized in `tasks.md`)

Chunks of 3–5 steps with a HARD-STOP gate at every boundary (`R-PROC-2`). Standing invariant: **CHAR-OK stays green at every step**; needing to edit it mid-migration signals unplanned behavior drift — stop and investigate (FR-012).

### Increments are route families, not layers

An earlier draft of this plan sequenced the work by layer ("paginator → navigator → handlers"). That order does not survive contact with the wire format: the producer (`keyboards/*`) and the consumer (navigator) are **coupled through it**, so neither side can migrate alone for a given route. A layer-wise chunk would leave buttons emitting a format nothing parses.

The genuinely independent increments are therefore **route families**, each migrated end-to-end (factory + producer + navigator entry + handler filter) within one phase.

| Phase | Content | Exit condition |
|---|---|---|
| **1** | Baseline: full pytest green recorded; Docker up for the semgrep gate | Known-good starting point |
| **2** | Format-agnostic round-trip harness + CHAR-OK on current code (green) + RED repro tests for DEF-1/2/3 (FR-018); then `callbacks.py` factories + contract tests (R-2, C-1, P-1, 64-byte, roundtrip) | Safety net exists and format is declared, before a single line of production routing changes |
| **3** | Non-paginated family (8 routes) end-to-end: registry + `str \| CallbackData` signature + producers + handler filters | DEF-3 repro → GREEN (FR-017). **Shippable**: paginated routes still served by the surviving old path |
| **4** | Paginated family (13 routes) end-to-end + paginator contract on `page_cb` + all 16 callers | DEF-1, DEF-2 repros → GREEN (FR-015, FR-016) |
| **5** | Remove the old mechanism: if-chain, `PAGINATED_CMDS`, `split("_pg_")`, positional extraction, `extract_topic_id_from_callback`; defensive routing re-verified on the new format | FR-002/003/005/010 closed; dual-path gone |
| **6** | Gates: ruff, import-linter, semgrep (Docker up), static guard test, full pytest; checklist-linter as the final item | SC-008 |

### Two properties that make this work

**Format-agnostic characterization.** CHAR-OK must never feed a hardcoded wire string — the format itself is what changes. It drives `keyboard → wire → navigator`: build the real keyboard, take the real button's `callback_data`, assert which screen the navigator opens. This is format-agnostic by construction, which is what makes FR-012's "green at every step, without edits" actually satisfiable, and it catches producer/consumer desync (US2) for free.

**Transient dual-path.** From Phase 3 until Phase 5 the navigator resolves both the new `:` format (migrated routes, via registry) and the old `_` format (not-yet-migrated routes, via the surviving if-chain). This is what makes each phase shippable, and it is the rollback posture: through the end of Phase 4 any phase can be reverted independently. Phase 5 is the point of no return.

Phase 4 is technically independent of Phase 3 (different routes) but is sequenced after it deliberately: Phase 3 proves the pattern on 8 routes before committing it to 13 more plus a shared contract change.

## Complexity Tracking

Not applicable: no Constitution Check violations require justification. The elevated Footprint (0/2 on the PA-1 scale) is a sanctioned decision taken under an explicitly granted trade, not a departure from a principle.
