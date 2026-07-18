---
description: "Task list — Broadcast Rate-Limiting & Reliability (013)"
---

# Tasks: Broadcast Rate-Limiting & Reliability

**Input**: Design documents from `specs/013-broadcast-rate-limiting/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/notification_service.md

**Tests**: INCLUDED — feature is a set of defect fixes; every fix gets a failing reproducing test first
(R-PROC-3 TDD).

**Organization**: grouped by user story (US1..US4) for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files / independent, no dependency on an incomplete task)
- **[Story]**: US1..US4 map to spec.md user stories
- Exact file paths in each task

## Approval Gates (R-PROC-2 — MANDATORY)

Execution is chunked into 3-5 tasks. Every chunk boundary ends with a HARD-STOP gate task.
`/speckit-implement` MUST NOT proceed past an unchecked HARD-STOP: it stops, reports in Russian, and
awaits explicit approval from Шэф. Task checklist lines are kept ASCII-safe (prompt-linter crashes on
non-cp1251 glyphs inside task text).

---

## Phase 1: Setup

**Purpose**: verify the external API surface the fix depends on (R-CODE-3 verify-before-change).

- [x] T001 Verify installed aiogram exception API in venv: confirm `aiogram.exceptions.TelegramRetryAfter`
  exists, is a subclass of `TelegramAPIError`, and exposes integer attr `retry_after`; note the exact
  constructor signature for test construction. Record findings inline in
  specs/013-broadcast-rate-limiting/research.md (D-1/D-10).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: shared scaffolding used by all stories — constants, the resilient single-send helper,
in-memory state containers, and test isolation. No consumer behavior changes yet.

**CRITICAL**: no user-story work begins until this phase is complete.

- [x] T002 [P] Add the module-level constants block to services/notification_service.py per the
  data-model.md table: BROADCAST_PACING_SECONDS, FLOOD_WAIT_CAP_SECONDS, FLOOD_WAIT_MAX_RETRIES,
  MENTION_BATCH_SIZE, ALL_MENTION_COOLDOWN_SECONDS, DEFAULT_DENY_WINDOW_SECONDS,
  MEMBER_DENY_WINDOW_SECONDS, ALERT_CACHE_TTL_SECONDS, ALERT_CACHE_MAX_ENTRIES (FR-015).
- [x] T003 Add class attr `_all_cooldown: dict[int, float] = {}` and the private helper
  `_send_message_resilient(bot, **send_kwargs) -> bool` to NotificationService in
  services/notification_service.py: on TelegramRetryAfter sleep min(retry_after, FLOOD_WAIT_CAP_SECONDS)
  and retry up to FLOOD_WAIT_MAX_RETRIES; on other TelegramAPIError log warning and return False
  (contracts C-4, research D-1). Order except clauses TelegramRetryAfter before TelegramAPIError.
- [x] T004 Add `reset_notification_state()` module function in services/notification_service.py that
  clears `NotificationService._alert_cache` and `NotificationService._all_cooldown` (contract C-5).
- [x] T005 Wire `reset_notification_state()` into tests/conftest.py `db_setup` fixture next to
  `reset_registration_cache()` / `reset_sheets_sync_state()` (R-TEST-1 isolation).
- [x] T006 **HARD STOP**: Доложить Шэфу по-русски — перечислить, что сделано в Foundational (константы,
  resilient-хелпер, состояние, reset в conftest) и что дальше US1 — и ЖДАТЬ ЯВНОГО ОДОБРЕНИЯ перед US1.
  Не продолжать самому. (R-PROC-2)

---

## Phase 3: User Story 1 - Массовое ЛС-уведомление доходит под нагрузкой (Priority: P1)

**Goal**: `send_to_users` соблюдает flood-wait и доставляет всем достижимым адресатам; пауза между
отправками; дедуп сохранён.

**Independent Test**: смоделировать 429 на части отправок; убедиться, что адресаты в итоге получены и
список дошёл до конца.

### Tests for User Story 1 (write first, must FAIL)

- [x] T007 [P] [US1] Write failing test `test_send_to_users_survives_flood_wait` in
  tests/test_services/test_notification_service.py: mock_bot.send_message raises TelegramRetryAfter on
  the 2nd call then succeeds; patch asyncio.sleep; assert the 2nd recipient is ultimately delivered and
  asyncio.sleep was called with the capped wait. Verify it FAILS against current code.
- [x] T008 [P] [US1] Write failing tests `test_send_to_users_paces_between_sends` and
  `test_send_to_users_skips_unreachable` in tests/test_services/test_notification_service.py: (a) assert
  asyncio.sleep(BROADCAST_PACING_SECONDS) is invoked between sends and set()-dedup keeps one message per
  unique id; (b) FR-003 — the 2nd of three recipients raises a non-retryable error (e.g.
  TelegramForbiddenError, blocked bot), the 3rd is still delivered and the failure is logged, not
  raised. Verify they FAIL (no pacing / current swallow-and-continue not asserted).

### Implementation for User Story 1

- [x] T009 [US1] Rewire `send_to_users` in services/notification_service.py to route each send through
  `_send_message_resilient` and `await asyncio.sleep(BROADCAST_PACING_SECONDS)` between sends; keep
  `set()` dedup with int-cast recipient ids (R-DATA-9, FR-001..004).
- [x] T010 [US1] Run US1 tests green, then full corpus `venv/Scripts/python.exe -m pytest -q` to confirm
  the audit call site (services/management_service.py:760) is unaffected (SC-008).
- [x] T011 **HARD STOP**: Доложить Шэфу по-русски итог US1 и ЖДАТЬ ЯВНОГО ОДОБРЕНИЯ перед US2. (R-PROC-2)

---

## Phase 4: User Story 2 - @all доходит до всех авторизованных (Priority: P1)

**Goal**: `send_native_all` разбивает упоминания на батчи и покрывает 100% авторизованных; тихий срез
на 50 устранён; сигнатура получает `sender_id` (задел под гейт US3), хендлер прокидывает отправителя.

**Independent Test**: топик со 120 авторизованными -> 3 сообщения, каждый UID упомянут один раз.

### Tests for User Story 2 (write first, must FAIL)

- [x] T012 [P] [US2] Write failing tests `test_send_native_all_covers_all_authorized` and
  `test_send_native_all_single_message_when_small` in tests/test_services/test_notification_service.py:
  (a) 120 authorized users -> expect 3 send_message calls (50/50/20), union of mentioned ids covers all
  120; (b) FR-008 / US2 scenario 2 — 30 authorized users -> exactly 1 send_message call. Verify (a)
  FAILS (current [:50] truncation).
- [x] T013 [P] [US2] Write failing tests `test_send_native_all_batch_flood_wait`,
  `test_send_native_all_no_empty_trailing_batch` (N == 100, exact multiple -> exactly 2 messages) and
  `test_send_native_all_empty_authorized` (FR-008 / US2 scenario 4 — empty list -> 0 send_message calls)
  in tests/test_services/test_notification_service.py. Verify they FAIL where a fix is required.

### Implementation for User Story 2

- [x] T014 [US2] Rewrite `send_native_all` in services/notification_service.py: add `sender_id: int`
  param; chunk authorized_users by MENTION_BATCH_SIZE via range stepping (no [:50]); one
  `_send_message_resilient` send per batch with asyncio.sleep(BROADCAST_PACING_SECONDS) between batches;
  empty list still sends nothing (FR-005..008, contract C-2).
- [x] T015 [US2] Update `handle_all_mention` in handlers/user.py to pass
  `sender_id=message.from_user.id` to send_native_all; keep trigger-message deletion first (contract C-3).
- [x] T016 [US2] Run US2 tests green, then full corpus to confirm no regression in US1 or the handler.
- [x] T017 **HARD STOP**: Доложить Шэфу по-русски итог US2 и ЖДАТЬ ЯВНОГО ОДОБРЕНИЯ перед US3. (R-PROC-2)

---

## Phase 5: User Story 3 - @all защищён от злоупотребления (Priority: P2)

**Goal**: @all выполняется только модератором топика или суперадмином; кулдаун на отправителя-модератора;
суперадмин от кулдауна освобождён; отказ тихий.

**Independent Test**: @all от не-модератора -> 0 рассылок, триггер удалён; повтор в пределах кулдауна ->
0 рассылок; суперадмин дважды подряд -> обе уходят.

### Tests for User Story 3 (write first, must FAIL)

- [x] T018 [P] [US3] Write failing journey tests in tests/test_journeys/test_all_mention_journey.py
  covering Input->Gate->Broadcast (R-TEST-3, positive + negative): `test_all_mention_moderator_broadcasts`
  (moderator @all -> broadcast messages sent through the real handler, trigger deleted; assert both args
  and kwargs of bot.send_message) and `test_all_mention_requires_moderator` (non-moderator, write-capable
  @all -> 0 broadcast messages, trigger still deleted). Verify the negative case FAILS against current
  ungated code.
- [x] T019 [P] [US3] Write failing tests `test_all_mention_cooldown` and
  `test_all_mention_superadmin_exempt` in tests/test_services/test_notification_service.py. Verify FAIL.

### Implementation for User Story 3

- [x] T020 [US3] Add the gate at the top of `send_native_all` in services/notification_service.py:
  require `PermissionService.is_moderator_of_topic(sender_id, topic_id) or
  PermissionService.is_global_admin(sender_id)`, else return without sending; per-sender cooldown via
  `_all_cooldown` skipped for superadmin; record `_all_cooldown[sender_id] = now` only after a
  successful moderator broadcast (FR-009..011, research D-4/D-6). Import PermissionService at top
  (acyclic).
- [x] T021 [US3] Run US3 tests green, then full corpus to confirm US2 batching still passes.
- [x] T022 **HARD STOP**: Доложить Шэфу по-русски итог US3 и ЖДАТЬ ЯВНОГО ОДОБРЕНИЯ перед US4. (R-PROC-2)

---

## Phase 6: User Story 4 - Кэш анти-спам-алертов не течёт (Priority: P3)

**Goal**: `_alert_cache` ограничен по росту (очистка протухших по TTL + потолок); окна дедупа 60/3600 с
вынесены в константы и работают как прежде.

**Independent Test**: наполнить кэш множеством протухших пар, вызвать алерт -> размер ограничен;
подавление в пределах окна сохранено.

### Tests for User Story 4

- [x] T023 [P] [US4] Write failing test `test_alert_cache_bounded` in
  tests/test_services/test_notification_service.py: seed _alert_cache with many pairs whose ts is older
  than ALERT_CACHE_TTL_SECONDS, trigger an alert -> assert cache size is bounded (not order-K). Verify
  it FAILS (current unbounded growth).
- [x] T024 [P] [US4] Write guard test `test_alert_cache_dedup_preserved` in
  tests/test_services/test_notification_service.py: within-window second event is suppressed, after-window
  event re-sends. This guard MUST pass both before and after (FR-013 characterization, format-agnostic).

### Implementation for User Story 4

- [x] T025 [US4] Add `_prune_alert_cache(now)` classmethod to services/notification_service.py (drop ts
  older than ALERT_CACHE_TTL_SECONDS; evict oldest down to ALERT_CACHE_MAX_ENTRIES) and call it at the
  top of send_default_deny_alert and send_member_deny_alert; replace inline 60 / 3600 literals with
  DEFAULT_DENY_WINDOW_SECONDS / MEMBER_DENY_WINDOW_SECONDS (FR-012/FR-013).
- [x] T026 [US4] Run US4 tests green, then full corpus.
- [x] T027 **HARD STOP**: Доложить Шэфу по-русски итог US4 и ЖДАТЬ ЯВНОГО ОДОБРЕНИЯ перед Polish. (R-PROC-2)

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T028 [P] Run static gates and record results: `venv/Scripts/lint-imports.exe`,
  `venv/Scripts/python.exe -m ruff check .`, governance
  `venv/Scripts/python.exe -m pytest tests/test_governance.py tests/test_knowledge_bundle.py -q`.
  semgrep gate needs a live Docker daemon (skip is not green).
- [x] T029 Flag Route C docs-update (no git during Route C): note the send_native_all signature change
  and the new broadcast constants for docs/knowledge/module-registry.md, and a CHANGELOG.md entry
  (CMD-4). Do not edit governance docs inside this implement run unless Шэф approves folding Route C in.
- [x] T030 Run quickstart.md validation commands and confirm the SC mapping (SC-001..SC-008) holds.
- [x] T031 **HARD STOP**: Доложить Шэфу по-русски финальный итог фичи 013 (все US, гейты, Route C
  флаг) и ЖДАТЬ решения по GW-1 (локальный коммит) и push. Push только по явному слову (R-PROC-5).
  (R-PROC-2)
- [x] T032 Convert any `[X]` to lowercase `[x]` across this tasks.md, then run checklist-linter
  `venv/Scripts/python.exe local_scripts/prompt_linter.py --dir specs/013-broadcast-rate-limiting
  --stage checklist` and confirm it passes (completion gate, LAST item; keep lines ASCII-safe).

---

## Dependencies & Execution Order

- **Phase 1 (Setup)**: no deps.
- **Phase 2 (Foundational)**: depends on Setup; BLOCKS all user stories (constants + resilient helper +
  reset are shared).
- **US1 (P1)**: after Foundational. Independent.
- **US2 (P1)**: after Foundational. Independent of US1 at runtime (shares only the foundational helper).
- **US3 (P2)**: edits the same `send_native_all` as US2 -> must follow US2 (sequential, same file).
- **US4 (P3)**: after Foundational. Independent of US1..US3 (touches alert methods only).
- **Polish**: after all desired stories.

### Within each story

- Reproducing tests written and FAILING before implementation (R-PROC-3).
- Run the story's tests green, then the full corpus, before the HARD STOP.

### Parallel opportunities

- Foundational: T002 [P] independent of the helper edits.
- Within a story, the `[P]` test-authoring tasks touch the same test module — treat `[P]` as "no logic
  dependency", but write them in one editing pass to avoid file churn.
- US4 is fully parallelizable against US1/US2/US3 if staffed separately (different methods).

## Implementation Strategy

- **MVP** = Foundational + US1 + US2 (both P1): rassылки перестают терять адресатов (flood-wait) и
  доходят до всех авторизованных (батчи). US3 (анти-абьюз) и US4 (память) — инкременты поверх MVP.
- Deliver incrementally, stopping at each HARD STOP for approval.

## Notes

- `[P]` = different files / no logic dependency; `[Story]` = traceability to spec.md.
- Verify each reproducing test FAILS before implementing its fix.
- Commit is a milestone decision for Шэф (GW-1); push only on explicit request (R-PROC-5).
- All Telegram calls mocked (R-TEST-2); isolated temp DB (R-TEST-1).
