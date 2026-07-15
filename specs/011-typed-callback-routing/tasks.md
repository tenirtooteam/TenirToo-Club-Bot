---

description: "Task list for feature 011 — typed callback routing"
---

# Tasks: Typed Callback Routing

**Input**: Design documents from `/specs/011-typed-callback-routing/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/callback-routes.md](contracts/callback-routes.md), [quickstart.md](quickstart.md)

**Tests**: REQUIRED (not optional). FR-018 mandates failing repro tests before the fix; FR-012 mandates a characterization layer green at every step. Constitution IV / `R-PROC-3`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task serves (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Approval Gates (R-PROC-2 — MANDATORY)

Every chunk boundary ends with a **HARD-STOP** task. `/speckit-implement` MUST NOT proceed past an unchecked HARD-STOP under any circumstance; it stops, reports in Russian, and waits for explicit approval.

## Structural note: why phases are route families, not one-per-story

This is a **migration**, not a greenfield feature. US1 (exact matching), US2 (single source of truth) and US4 (pagination as a field) are not separable deliverables — they are properties of one mechanism, and the producer (`keyboards/*`) and consumer (navigator) are coupled through the wire format: neither side can change alone for a given route.

The genuinely independent increments are therefore **route families**, each migrated end-to-end (factory + producer + navigator entry + handler filter) in one phase. Each phase delivers US1 + US2 for its family and is independently testable. Story labels mark which story each task serves.

**Transient dual-path**: from Phase 3 until Phase 5 the navigator resolves both the new `:` format (migrated routes, via registry) and the old `_` format (not-yet-migrated routes, via the surviving if-chain). This is what makes each phase shippable. Phase 5 deletes the old path once it is provably dead.

## Standing invariants (apply to EVERY task)

1. **CHAR-OK stays green at every step.** Needing to edit a characterization test mid-migration is a signal of unplanned behavior drift → STOP and investigate, never adjust the test to match (FR-012).
2. **CHAR-OK and repro tests are format-agnostic**: they drive `keyboard → wire → navigator`, never a hardcoded wire string. A test that hardcodes `"user_info_5"` is a defect in the test.
3. All commands run via `venv/Scripts/python.exe` (`R-PROC-7`).
4. Route inventory and per-route fields: [data-model.md](data-model.md). Contract obligations: [contracts/callback-routes.md](contracts/callback-routes.md).

---

## Phase 1: Setup

**Purpose**: Establish the baseline the whole migration is measured against.

- [x] T001 Record the pre-migration baseline: run `venv/Scripts/python.exe -m pytest -q` from repo root and confirm green; note the known third-party warnings (Pydantic `__fields__`, tzlocal, git CRLF) as pre-existing and out of scope.
- [x] T002 Confirm Docker Desktop is running so the semgrep gate can execute (`docker info`). A skipped semgrep is NOT a green — there is no CI in this project.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the safety net and the format declarations before a single line of production routing changes.

**⚠️ CRITICAL**: No route family may migrate until this phase is complete.

### Safety net (written FIRST, on unmodified production code)

> Naming, per [research.md](research.md) D-3: **CHAR-OK** = characterization of currently-correct behavior (green throughout, `test_callback_routing_characterization.py`). **CHAR-DEF** = the RED repro tests for DEF-1/2/3 (red before, green after, `test_callback_routing_defects.py`). "Repro test" below always means CHAR-DEF.

- [x] T003 [US1] Create the format-agnostic round-trip harness in `tests/test_services/test_callback_routing_characterization.py`: a helper that builds a real keyboard via `keyboards/*`, extracts a button's `callback_data` by button text, feeds it to `UIService.generic_navigator`, and captures (a) which `UIService` screen was invoked with which arguments, (b) whether `sterile_show` was the transition path (FR-009), and (c) whether `state.set_state(None)` and `clear_fsm_data_safely` were called (FR-007). Patch `sterile_show`; `R-TEST-3` — mock assertions check `args` and `kwargs`.
- [x] T004 [US1] Extend `tests/test_services/test_callback_routing_characterization.py` with CHAR-OK cases for every currently-correct route in [data-model.md](data-model.md) §A/§B — excluding the routes named by FR-015…FR-017. **Include the FSM-reset asymmetry as a locked characteristic (FR-007): constant routes DO reset FSM state, parameterized routes DO NOT (`services/ui_service.py:279-281`). This asymmetry MUST survive the migration unchanged — do not "fix" it.** Confirm the suite is GREEN on unmodified code.
- [x] T005 [US4] Create `tests/test_services/test_callback_routing_defects.py` with the DEF-1 repro (FR-015): build `kb.moderator_group_list_kb(topic_id=55, page=1)`, take the next-page arrow button's data, assert the navigator opens topic **55** page **2**. Confirm it FAILS on current code (topic_id arrives as 3).
- [x] T006 [US4] Add the DEF-2 repro (FR-016) to `tests/test_services/test_callback_routing_defects.py`: build `kb.topic_selection_for_role_kb(user_id=777)` with >7 topics, take the next-page arrow button's data, assert the navigator opens the topic picker for user **777** page **2**. Confirm it FAILS on current code (route falls through to the navigation-error fallback).
- [x] T007 [US1] Add the DEF-3 repro (FR-017) to `tests/test_services/test_callback_routing_defects.py`: build `kb.group_topics_list_kb(group_id=9)` containing topic 5, take topic 5's button data, assert `show_topic_detail` is called with `topic_id=5, group_id=9`. Confirm it FAILS on current code (arguments inverted).

- [x] T008 **HARD STOP**: Report progress to Шэф in Russian — the safety net is in place, CHAR-OK green, three repro tests RED as predicted (or report any divergence from the predicted failure modes, which would mean the plan's defect analysis is wrong) — and AWAIT EXPLICIT APPROVAL before declaring the format. (R-PROC-2)

### Format declarations

- [x] T009 [US2] Create `callbacks.py` at repository root declaring `CallbackData` factories for all 21 legacy-navigator routes per [data-model.md](data-model.md) §A/§B, using the default `:` separator. Paginated factories carry a `page: int` field. `tmpl_act_start` uses an `Enum` for `action` (apply/sync). The module MUST NOT import `services`, `handlers`, or `database` (leaf node, `R-ARCH-4`).
- [x] T010 [US2] Create `tests/test_services/test_callback_contract.py` covering invariants R-2 (prefixes unique), C-1 (no constant route contains `:`), P-1 (every factory passed to the paginator has a `page` field), FR-011 (`pack()` does not raise at maximum expected field values — assert on `pack()`, do not hand-count bytes), and roundtrip (`unpack(pack(x)) == x` for every factory). Invariant R-1 (factory-to-registry completeness) is deferred to T028, when the registry is complete.
- [x] T011 [US2] Run `venv/Scripts/python.exe -m lint_imports` and confirm `callbacks.py` introduces no import-contract violation (`R-PROC-11`).

**Checkpoint**: Safety net green, repro tests red, format declared and self-tested. Production routing untouched.

- [x] T012 **HARD STOP**: Report progress to Шэф in Russian — summarize the foundational phase — and AWAIT EXPLICIT APPROVAL before starting the first route family. (R-PROC-2)

---

## Phase 3: Non-paginated routes (US1, US2) 🎯 MVP

**Goal**: Migrate the 8 non-paginated parameterized routes end-to-end, proving the pattern on the smaller surface. Closes DEF-3 (FR-017).

**Independent Test**: CHAR-OK cases for these 8 routes stay green without edits, and the DEF-3 repro (T007) flips to green, while all paginated routes continue working through the surviving old path.

**Routes**: `user_info`, `group_info`, `topic_global_view`, `topic_in_group` (DEF-3), `u_topic_info`, `mod_topic_select`, `user_roles_manage`, `help`.

- [x] T013 [US1] Add the route registry to `services/ui_service.py` as a module-level `{prefix: (Factory, render_fn)}` dict, resolved by exact key lookup, populated for the 8 non-paginated routes. Leave the existing if-chain in place as the fallback path for not-yet-migrated routes (transient dual-path).
- [x] T014 [US1] Change `UIService.generic_navigator` in `services/ui_service.py` to accept `str | CallbackData` (parameter name `callback_data` preserved per `R-UI-3`/D-6) and resolve in the order defined by [contracts/callback-routes.md](contracts/callback-routes.md) §C-4: object used directly; `str` without `:` resolved via the constants dict; `str` with `:` resolved by prefix lookup in the registry then `unpack()`; a miss or `(TypeError, ValueError)` falls through to the existing warning fallback. **T017 depends on this.**
- [x] T015 [P] [US2] Migrate the 8 non-paginated routes' producers in `keyboards/admin_kb.py` and `keyboards/user_kb.py` from f-string `callback_data` to `Factory(...).pack()`.
- [x] T016 [P] [US2] Migrate the `help:` producer in `keyboards/pagination_util.py::add_nav_footer` to `HelpCB(...).pack()` and DELETE the manual 64-byte truncation (lines 26-29) — `pack()` raises loudly instead of silently emitting a broken route (FR-011).

- [x] T017 **HARD STOP**: Report progress to Шэф in Russian — registry and dual-path navigator in place, non-paginated producers migrated — and AWAIT EXPLICIT APPROVAL before migrating the handler filters. (R-PROC-2)

- [x] T018 [US2] Migrate the input filters for the 8 non-paginated routes in `handlers/admin.py`, `handlers/moderator.py` and `handlers/user.py` from `F.data.startswith(...)` to `Factory.filter()` (FR-010), passing the injected `callback_data` object straight to the navigator.
- [x] T019 [US2] Migrate synthetic transitions for these routes (route strings built by hand in message handlers and services) to factory objects: `handlers/admin.py:167` (`f"group_info_{group_id}"`), `handlers/moderator.py:118` (`f"mod_topic_select_{topic_id}"`), `handlers/common.py::perform_search_pick:239` (`f"{s_type}_info_{item_id}"` — note this builds a route name by string concatenation of the entity type; replace with explicit per-type factory selection), and `services/ui_service.py::get_confirmation_ui:508,515`.
- [x] T020 [US1] Verify: DEF-3 repro (T007) is GREEN; CHAR-OK is GREEN with no test edits; run `venv/Scripts/python.exe -m pytest tests/ -q`.

**Checkpoint**: 8 routes fully typed end-to-end; DEF-3 closed; paginated routes still served by the old path.

- [x] T021 **HARD STOP**: Report progress to Шэф in Russian — summarize the non-paginated family and the DEF-3 fix — and AWAIT EXPLICIT APPROVAL before starting the paginated family. (R-PROC-2)

---

## Phase 4: Paginated routes + paginator contract (US1, US2, US4)

**Goal**: Migrate the 13 paginated routes and change the paginator contract so the page number becomes a declared field. Closes DEF-1 (FR-015) and DEF-2 (FR-016).

**Independent Test**: DEF-1 and DEF-2 repros (T005, T006) flip to green; CHAR-OK stays green without edits; every paginated list navigates to page 2 showing the same entity.

**Routes**: `manage_groups`, `manage_users`, `all_topics_list`, `list_users_roles`, `user_topics`, `group_topics_list` (DEF-1), `mod_topic_groups` (DEF-1), `mod_gr_addlist` (DEF-1), `mod_users_manage` (DEF-1), `mod_topic_moderators` (DEF-1), `user_templates_manage`, `tmpl_act_start`, `topic_assign_pg` (DEF-2).

- [x] T022 [US4] Change `build_paginated_menu` in `keyboards/pagination_util.py` to accept `page_cb: CallbackData` instead of `callback_prefix: str`, building arrows as `page_cb.model_copy(update={"page": n}).pack()` per [contracts/callback-routes.md](contracts/callback-routes.md) §C-5. Migrate the two prefix-dependent branches in the same function: the back-button match at line 91 (`s_btn.callback_data == callback_prefix`) and the `help:` parse at lines 95-99. Accept the legacy `callback_prefix` kwarg transitionally so callers migrate incrementally; T027 removes it.
- [x] T023 [P] [US4] Migrate the 9 `build_paginated_menu` callers in `keyboards/admin_kb.py` to pass `page_cb` factory instances, and their item-button `callback_data` to `.pack()`. **Includes `topic_assign_pg_{user_id}` (line 281), which becomes `TopicAssignCB(user_id=..., page=...)`: the route name loses the `_pg` infix entirely (FR-016).**
- [x] T024 [P] [US4] Migrate the 6 `build_paginated_menu` callers in `keyboards/moderator_kb.py` to `page_cb` factory instances, and their item-button `callback_data` to `.pack()`.
- [x] T025 [P] [US4] Migrate the 1 `build_paginated_menu` caller in `keyboards/user_kb.py` to a `page_cb` factory instance, and its item-button `callback_data` to `.pack()`. Note `user_topics` pagination is currently dead (route absent from `PAGINATED_CMDS`); after migration it works — this is a consequence of FR-005, and its CHAR case must be updated from "page ignored" to "page honored".

- [x] T026 **HARD STOP**: Report progress to Шэф in Russian — paginator contract changed and all 16 callers migrated — and AWAIT EXPLICIT APPROVAL before wiring the navigator and handlers. (R-PROC-2)

- [x] T027 [US4] Register the 13 paginated routes in the `services/ui_service.py` registry with their render functions, and remove the transitional `callback_prefix` kwarg from `build_paginated_menu` in `keyboards/pagination_util.py` now that all callers pass `page_cb`.
- [x] T028 [US2] Migrate the input filters for the paginated routes in `handlers/admin.py`, `handlers/moderator.py` and `handlers/user.py` to `Factory.filter()`, and add invariant R-1 to `tests/test_services/test_callback_contract.py` (every factory in `callbacks.py` appears in the navigator registry exactly once).
- [x] T029 [US4] Verify: DEF-1 repro (T005) and DEF-2 repro (T006) are GREEN; CHAR-OK is GREEN with no test edits other than the `user_topics` case noted in T025; run `venv/Scripts/python.exe -m pytest tests/ -q`.

**Checkpoint**: All 21 routes typed end-to-end. All three defects closed. The old if-chain should now be unreachable.

- [x] T030 **HARD STOP**: Report progress to Шэф in Russian — summarize the paginated family and the DEF-1/DEF-2 fixes — and AWAIT EXPLICIT APPROVAL before removing the old mechanism. (R-PROC-2)

---

## Phase 5: Remove the old mechanism (US1, US3)

**Goal**: Delete the substring/positional machinery now that it is dead, and harden defensive routing on the new format.

**Independent Test**: Every class of malformed input yields a logged warning and a safe return to the main menu, with no exception escaping; no substring or positional parsing remains anywhere in the navigator.

- [x] T031 [US1] Delete the dead machinery from `services/ui_service.py`: the substring if-chain (lines ~308-385), `PAGINATED_CMDS` (line 13), `cmd = callback_data.split("_pg_")[0]` and `page = int(...)` (lines 277-278), and every `p[-1]` / `p[-2]` / `p[3]` / `p[4]` extraction. Prove deadness first: no registry miss occurs across the full CHAR-OK run.
- [x] T032 [US2] ~~Delete `extract_topic_id_from_callback` from `handlers/moderator.py`~~ — **SKIPPED, out of scope.** Its only two callers (`mod_topic_rename_`, `mod_moderator_add_`) are action routes outside the navigator family (D-4). FR-003 scopes positional-parsing removal to the navigator and the handlers *serving the family*; these serve neither. Deleting it would require migrating two out-of-scope routes — an unsanctioned scope expansion. Logged to the roadmap in T043 instead.
- [x] T033 [US3] Update `tests/test_services/test_ui_fuzzer.py` and `tests/test_journeys/test_callback_defense.py` for the new format, covering every malformed class from [quickstart.md](quickstart.md) §4: unknown prefix, failing type coercion (`ValidationError`), wrong arity (`TypeError`), old-format data (chat-history button), and a negative page. Each MUST produce a logged warning plus a safe return, with no exception escaping (FR-008). Reconcile `test_callback_defense.py`'s `generic_navigator` patch with the new signature.
- [x] T034 [US3] Update `tests/test_services/test_ui_integrity.py` for `R-UI-11`: colon-callback parsing is now `unpack()`-based; the defensive-split requirement is satisfied by the factory, not by hand-rolled splitting.

- [x] T035 **HARD STOP**: Report progress to Шэф in Russian — old mechanism removed, defensive behavior re-verified — and AWAIT EXPLICIT APPROVAL before the final gates. (R-PROC-2)

---

## Phase 6: Gates & Polish

**Purpose**: Prove the whole thing, per SC-001…SC-009.

- [x] T036 [P] Create `tests/test_services/test_callback_static_guard.py` asserting SC-001/SC-002/SC-003 over the routes in scope: no substring route matching (`in cmd`) and no positional extraction (`p[-1]`, `p[3]`, `p[4]`) in `services/ui_service.py`, and no hand-built parameterized `callback_data` in `keyboards/*` for family routes. Scope the assertions to the family per spec.md § Границы применимости требований — `keyboards/event_kb.py` and `keyboards/announcements_kb.py` are OUT of scope (D-4) and MUST NOT be flagged. Follow the existing gate-test style in `tests/test_services/test_import_lint.py` (`R-ARCH-8`, `R-PROC-10`).
- [x] T037 [P] Verify SC-007 by recording the line count of the navigator's dispatch section before and after, in the PR/commit message.
- [x] T038 Run the full gate set from [quickstart.md](quickstart.md) §5: `pytest tests/test_services/test_import_lint.py tests/test_services/test_ruff_lint.py tests/test_services/test_semgrep_lint.py tests/test_services/test_callback_static_guard.py`, plus `ruff check .` and `lint_imports` directly. Confirm no new violations (SC-008). A semgrep `skip` is NOT a pass — bring Docker up and re-run.
- [x] T039 Run the full suite `venv/Scripts/python.exe -m pytest -q` and confirm green with no new warnings beyond the known third-party ones recorded in T001.
- [x] T040 ~~Walk the three manual scenarios against a running bot~~ — **substituted, and the substitute is weaker in one specific way.** A live Telegram walkthrough was not possible in this session (no bot token, no live supergroup). Instead the three scenarios now run end-to-end through the real `Dispatcher` with real routers in `tests/test_journeys/test_callback_routing_journey.py`: keyboard button -> `Factory.filter()` -> navigator -> screen, with only the Telegram transport mocked. This is strictly stronger than the CHAR-DEF tests (which call the navigator directly and bypass handler filters), but it does NOT exercise the actual Telegram round-trip — notably the real 64-byte limit enforcement by Telegram itself and real button rendering. **Шэф should still click through §7 once on a live bot before this ships.**

- [x] T041 **HARD STOP**: Report progress to Шэф in Russian — all gates green — and AWAIT EXPLICIT APPROVAL before the documentation route. (R-PROC-2)

- [x] T042 Flag Route C (`tenirtoo-docs-update`) scope: `R-UI-3` description may need to reflect the `str | CallbackData` navigator signature; `docs/knowledge/` needs the `callbacks.py` module registered; `CHANGELOG.md` gets the feature plus the three fixes (`CMD-4`). Do not perform git operations during Route C.
- [x] T043 Add the follow-ups discovered during this feature to `_nogit_roadmap.md`: (a) migrate the `event_*` / `ann_*` / `date_*` families off positional `split(":")[1]` — same defect class, out of scope per D-4; (b) migrate the `search_start_*` / `search_pick_*` parsing; (c) remove the dead `mod_back_to_topic_` route — handler and navigator branch exist with no producer (D-7).
- [x] T044 Run the checklist linter (run checklist-linter): `venv/Scripts/python.exe local_scripts/prompt_linter.py --dir specs/011-typed-callback-routing --stage checklist` and confirm it passes with every task above marked `[x]` (lowercase).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: no dependencies.
- **Phase 2 (Foundational)**: depends on Phase 1. **BLOCKS everything** — the safety net must exist before production routing changes.
- **Phase 3 (Non-paginated)**: depends on Phase 2. Deliverable increment (MVP).
- **Phase 4 (Paginated)**: depends on Phase 2. Technically independent of Phase 3 — different routes — but sequenced after it deliberately: Phase 3 proves the pattern on 8 routes before committing it to 13 more plus a shared contract change.
- **Phase 5 (Removal)**: depends on **both** Phase 3 and Phase 4 — the old path cannot be deleted while any route still needs it.
- **Phase 6 (Gates)**: depends on Phase 5.

### Honest note on story independence

Unlike a greenfield feature, the user stories here are **not** independently deliverable — see the structural note above. US1 and US2 are co-delivered by every route-family phase; US4 lands with Phase 4; US3 is verified in Phase 5 but its behavior is preserved from the first line of Phase 3 onward (the fallback never stops working). Do not attempt to reorder phases by story priority.

### Critical path

T003 → T004 (harness before cases) → T009 (factories) → T013/T014 (registry + signature) → T015-T016 (producers) → T018 (filters) → T022 (paginator contract) → T023-T025 (callers) → T027-T028 (registry + filters) → T031 (removal) → T038 (gates).

T014 blocks T017's gate: the dual-path resolution must exist before any producer emits the new format.

### Parallel Opportunities

- T015 ∥ T016 — different files (`admin_kb.py`/`user_kb.py` vs `pagination_util.py`).
- T023 ∥ T024 ∥ T025 — different keyboard modules, after T022 lands the contract.
- T036 ∥ T037 — different concerns, no shared files.
- T005, T006, T007 are **not** parallel — same file (`test_callback_routing_defects.py`).
- T003, T004 are **not** parallel — same file, and T004 depends on T003's harness.

---

## Implementation Strategy

### MVP (Phase 1 + 2 + 3)

Safety net, format declarations, and 8 routes migrated end-to-end with DEF-3 fixed. This is a genuine, shippable increment: the remaining 13 routes keep working through the surviving old path. It proves the pattern at the smallest cost, and if the approach turns out to be wrong, only 8 routes and one dual-path branch need reverting.

### Incremental Delivery

1. Phase 1+2 → safety net green, repros red, format declared.
2. Phase 3 → 8 routes typed, DEF-3 closed. **Shippable.**
3. Phase 4 → 13 routes typed, DEF-1 and DEF-2 closed. **Shippable.**
4. Phase 5 → old mechanism deleted, dual-path gone.
5. Phase 6 → gates, docs, roadmap follow-ups.

### Rollback posture

Through the end of Phase 4 the old path still exists, so any phase can be reverted without touching the others. Phase 5 is the point of no return — take it only once Phase 4's checkpoint is green and approved.

---

## Notes

- [P] = different files, no dependencies.
- Commit at logical groups (`GW-1`); `git push` requires an explicit request from Шэф (`R-PROC-5`).
- Verify repro tests FAIL before implementing the fix (`R-PROC-3`). If a repro passes on unmodified code, the plan's defect analysis is wrong — stop and report, do not adjust the test.
- Mock assertions check `args` and `kwargs` (`R-TEST-3`).
- Clean service-level global state via an autouse conftest fixture, following `reset_registration_cache` / `reset_sheets_sync_state`.
