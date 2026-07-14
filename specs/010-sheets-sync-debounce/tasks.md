---
description: "Task list for feature 010 — Sheets-синк дебаунс и владение фоновой задачей (№17)"
---

# Tasks: Sheets-синк — дебаунс и владение фоновой задачей

**Input**: Design documents from `specs/010-sheets-sync-debounce/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md

**Tests**: ВКЛЮЧЕНЫ (R-PROC-3 TDD — репро/характеризационные тесты пишутся ПЕРВЫМИ, RED→GREEN; R-TEST-3 мок-ассерты по `args`+`kwargs`).

**Organization**: по user stories из spec.md. US2 (владение задачей) — субстрат-механизм, на котором строится US1 (коалесценция); поэтому реализуется первым из двух P1. US3 (shutdown-flush) — P2.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: можно параллельно (разные файлы, нет незакрытых зависимостей)
- **[Story]**: US1 / US2 / US3
- Пути к файлам — точные.

## Approval Gates (R-PROC-2 — MANDATORY)

`/speckit-implement` НЕ имеет права проходить за неотмеченный **HARD STOP** — останавливается, докладывает Шэфу, ждёт явного «да».

## Path Conventions

Single project: `services/`, `database/`, `tests/`, `main.py` в корне репозитория.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: заготовка тест-файла и общих моков.

- [x] T001 [P] Создать скелет `tests/test_sheets_sync_debounce.py`: импорты, фикстуры изолированной БД (переиспользовать из `tests/conftest.py`), общий helper для мока `GoogleSheetsService.export_users/export_groups/export_events/export_event_participants` и helper для патча окна `SHEETS_SYNC_DEBOUNCE_SECONDS` на малое значение (детерминизм, без реальных таймеров).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: пакетный фетч ролей (устранение N+1, FR-006) — нужен фазе экспорта пользователей во всех историях. Независим от механики дебаунса.

**⚠️ CRITICAL**: до завершения фазы истории US1/US2 не трогают путь экспорта пользователей.

- [x] T002 Написать ПАДАЮЩИЙ тест `db.get_roles_for_users(user_ids)` в `tests/test_sheets_sync_debounce.py`: возвращает `{user_id: [(role_name, topic_id), ...]}`; для `ADMIN_ID` синтезируется `('superadmin', None)` (паритет с `get_user_roles`); пустые роли обрабатываются. Мок-ассерты по `args`/`kwargs` (R-TEST-3). RED.
- [x] T003 Реализовать `get_roles_for_users(user_ids: list[int]) -> dict[int, list[tuple]]` в `database/roles.py`: один SQL `WHERE ur.user_id IN (...)` + JOIN на `roles`, группировка по `user_id` в питоне, синтез `superadmin` для `ADMIN_ID` (R-ARCH-1).
- [x] T004 Реэкспортировать `get_roles_for_users` через фасад в `database/db.py` (импорт из `.roles`, как соседние функции). GREEN для T002.

**Checkpoint**: фасад отдаёт роли пакетом; N+1-хелпер готов к использованию.

- [x] T004a **HARD STOP**: доложить Шэфу по-русски итог Setup+Foundational (тест ролей RED→GREEN, новый метод фасада) и ЖДАТЬ явного «да» перед началом US2. Не продолжать самостоятельно. (R-PROC-2)

---

## Phase 3: User Story 2 - Владение фоновой задачей, нет потери ошибок (Priority: P1)

**Goal**: `create_task` больше не теряется GC; ошибки задачи логируются; ноль «Task was destroyed». Это субстрат для коалесценции.

**Independent Test**: триггер синка удерживает ссылку на задачу до завершения; исключение внутри задачи попадает в `logger.error`; прогон не порождает предупреждения о разрушенной задаче.

### Tests for User Story 2 (RED первым) ⚠️

- [x] T005 [US2] Написать ПАДАЮЩИЙ репро-тест в `tests/test_sheets_sync_debounce.py`: (а) после `_trigger_sheets_sync(...)` ссылка на задачу удерживается системой до завершения и снимается после; (б) исключение внутри задачи логируется (`logger.error`, ассерт `args`/`kwargs`); (в) отсутствует предупреждение «Task was destroyed». RED.

### Implementation for User Story 2

- [x] T006 [US2] Добавить модульный реестр `_pending_syncs: dict[str, asyncio.Task]` и константу `SHEETS_SYNC_DEBOUNCE_SECONDS = 2.0` в `services/management_service.py` (data-model.md).
- [x] T007 [US2] Переписать `_trigger_sheets_sync` (сигнатура НЕ меняется, FR-007): создавать owned-задачу, класть в `_pending_syncs`, вешать `add_done_callback` для снятия ключа; сохранить `try/except` с `logger.error` внутри задачи (FR-003/FR-004) в `services/management_service.py`.
- [x] T008 [US2] Заменить N+1-цикл ролей (`for u in users: db.get_user_roles(...)`) на один вызов `db.get_roles_for_users(...)` в фазе экспорта пользователей `services/management_service.py` (FR-006). GREEN для T005.

**Checkpoint**: фоновый синк владеется, ошибки не теряются, N+1 устранён.

- [x] T008a **HARD STOP**: доложить Шэфу по-русски итог US2 и ЖДАТЬ явного «да» перед началом US1. (R-PROC-2)

---

## Phase 4: User Story 1 - Всплеск правок не плодит экспорты (Priority: P1) 🎯 MVP

**Goal**: N быстрых триггеров одного ключа в окне → ровно одна фактическая выгрузка.

**Independent Test**: N последовательных триггеров одного `mode` в окне коалесценции → `export_*` вызван 1 раз; разные ключи независимы.

### Tests for User Story 1 (RED первым) ⚠️

- [x] T009 [US1] Написать ПАДАЮЩИЕ тесты в `tests/test_sheets_sync_debounce.py`: (а) N (≥2) быстрых триггеров одного `mode` → `export_*` вызван ровно 1 раз (SC-001); (б) `users`+`groups` → каждый export по разу (FR-002); (в) `event_participants` с разными `entity_id` не склеиваются. Мок-ассерты `args`/`kwargs`. RED.

### Implementation for User Story 1

- [x] T010 [US1] Реализовать per-key дебаунс в `_trigger_sheets_sync` (`services/management_service.py`): вычислить sync key (`mode` либо `event_participants:{entity_id}`), отменить прежнюю pending-задачу этого ключа (если есть), создать новую задачу с `await asyncio.sleep(SHEETS_SYNC_DEBOUNCE_SECONDS)` перед экспортом (research R1/R3).
- [x] T011 [US1] Гарантировать чтение БД в момент фактического экспорта (свежие данные, FR-009) и безопасную отмену в фазе sleep (`CancelledError` не доходит до экспорта) в `services/management_service.py`. GREEN для T009.

**Checkpoint**: коалесценция работает; US1+US2 функциональны независимо.

- [x] T011a **HARD STOP**: доложить Шэфу по-русски итог US1 (коалесценция) и ЖДАТЬ явного «да» перед началом US3. (R-PROC-2)

---

## Phase 5: User Story 3 - Остановка бота не теряет последнюю выгрузку (Priority: P2)

**Goal**: штатная остановка немедленно прогоняет все pending-выгрузки.

**Independent Test**: триггер → до истечения окна `await flush_pending_syncs()` → export выполнен немедленно; пустой реестр → без выгрузок и без ошибок.

### Tests for User Story 3 (RED первым) ⚠️

- [x] T012 [US3] Написать ПАДАЮЩИЕ тесты в `tests/test_sheets_sync_debounce.py`: (а) с непустым реестром `await flush_pending_syncs()` немедленно выполняет export (SC-004); (б) пустой реестр → flush без выгрузок и без ошибок. RED.

### Implementation for User Story 3

- [x] T013 [US3] Реализовать `async def flush_pending_syncs()` в `services/management_service.py`: для каждой задачи реестра прервать фазу ожидания и немедленно выполнить экспорт ключа, дождаться, очистить реестр (research R4). GREEN для T012.
- [x] T014 [US3] Зарегистрировать shutdown-хук `dp.shutdown.register(ManagementService.flush_pending_syncs)` в `main.py`; **сверить фактический API `dp.shutdown.register` установленной версии aiogram** (research R4 [НЕ ПРОВЕРЕНО]); при отличии — эквивалентный shutdown-хук диспетчера.

**Checkpoint**: все три истории функциональны независимо.

- [x] T014a **HARD STOP**: доложить Шэфу по-русски итог US3 и ЖДАТЬ явного «да» перед Polish. (R-PROC-2)

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: регресс, статик-гейты, документация, финальные гейты.

- [x] T015 [P] Полный прогон `venv/Scripts/python.exe -m pytest -q`: все зелёные, ноль предупреждений «Task was destroyed»/«pending task» по синку (SC-006).
- [x] T016 Статик-гейты: semgrep (Docker-демон, native→docker fallback), `venv/Scripts/lint-imports.exe`, `venv/Scripts/python.exe -m ruff check .`, governance/knowledge (`tests/test_governance.py tests/test_knowledge_bundle.py`).
- [x] T017 Прогнать валидацию `specs/010-sheets-sync-debounce/quickstart.md` (5 сценариев GREEN).
- [x] T018 Route C документы: обновить `docs/knowledge/` (поведение Sheets-синка — дебаунс/владение/flush) и `CHANGELOG.md` (версия 1.11.0). Без git-операций в самой Route C.
- [x] T019 prompt-linter: plan-стадия пройдена (после `/speckit-plan`); report-стадия (`walkthrough.md`) в текущем spec-kit-only flow не применяется (выведена с фичи 007+). Финальный gate — checklist-стадия, пункт T021 ниже.

- [x] T020 **HARD STOP**: доложить Шэфу по-русски финальный итог (все гейты, докид), показать summary изменений и ЖДАТЬ явного «да» перед git-коммитом. Push — только по отдельному слову Шэфа (R-PROC-5). (R-PROC-2)

- [x] T021 запуск линтера-чеклиста (run checklist-linter): completion gate — все пункты `[x]`, затем `venv/Scripts/python.exe local_scripts/prompt_linter.py --dir specs/010-sheets-sync-debounce --stage checklist` зелёный. Выполняется последним, перед самим коммитом.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (P1)** → нет зависимостей.
- **Foundational (P2)**: зависит от Setup; даёт `get_roles_for_users`, используемый в US2 (T008).
- **US2 (Phase 3)**: зависит от Foundational (T008 использует T003/T004). Субстрат для US1.
- **US1 (Phase 4)**: зависит от US2 (дебаунс строится на owned-задаче/реестре из T006/T007).
- **US3 (Phase 5)**: зависит от US2 (реестр `_pending_syncs`); от US1 логически независим, но обычно после него.
- **Polish (Phase 6)**: после всех историй.

### Within Each User Story

- Тесты (RED) ПЕРЕД реализацией; проверить падение до фикса.
- Реестр/константа (T006) до дебаунса (T010) до flush (T013).

### Parallel Opportunities

- T001 (Setup) — параллелен подготовке.
- T015 (регресс) — [P] относительно правок докуметов.
- Внутри одной истории правки идут по одному файлу `services/management_service.py` — **последовательно** (конфликт файла), не параллелить.

---

## Implementation Strategy

### MVP (US2 + US1)

1. Setup + Foundational (роли пакетом).
2. US2 — владение задачей (устраняет «Task was destroyed», N+1).
3. US1 — коалесценция поверх owned-задачи → **MVP-ценность** (нет спама выгрузок).
4. STOP, валидировать независимо.

### Incremental

US3 (shutdown-flush) добавляется поверх, закрывает пробел жизненного цикла из PA-1. Затем Polish + Route C докид + гейты + коммит.

---

## Notes

- [P] = разные файлы, нет зависимостей.
- Все правки логики — в `services/management_service.py` (последовательно), плюс точечные: `database/roles.py`, `database/db.py`, `main.py`, тесты.
- Верифицировать падение тестов до реализации (R-PROC-3).
- Коммит — единый в конце после T020-«да»; push — по отдельному слову (R-PROC-5).
- Каждый HARD STOP — реальная остановка `/speckit-implement`.
