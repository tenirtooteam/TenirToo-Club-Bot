# Implementation Plan: Sheets-синк — дебаунс и владение фоновой задачей

**Branch**: `010-sheets-sync-debounce` | **Date**: 2026-07-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/010-sheets-sync-debounce/spec.md`

## Summary

Рефактор `ManagementService._trigger_sheets_sync` (№17). Три связанных дефекта: (1) `asyncio.create_task` без хранения ссылки → GC-гонка и проглоченные ошибки («Task was destroyed» в тестах, корень тест-патча из 007); (2) полный ре-экспорт на каждую единичную мутацию → «спам» выгрузок; (3) N+1 по ролям в цикле выгрузки пользователей.

**Технический подход (вариант B из PA-1, утверждён Шэфом):** per-`mode` дебаунс с коалесценцией. На каждый ключ синка (`users`/`groups`/`events`/`all` + `event_participants:<entity_id>`) держим одну owned-задачу в модульном реестре `ManagementService`. Повторный триггер того же ключа в окне ожидания перезапускает таймер, не плодя задач; ссылка снимается в `add_done_callback`. Ошибки логируются внутри задачи (сохраняем существующий `try/except`). Добавляем `flush_pending_syncs()` + регистрацию через `dp.shutdown.register(...)` в `main.py`, чтобы штатная остановка не теряла отложенную выгрузку. N+1 добивается новым пакетным методом фасада `db.get_roles_for_users(user_ids)` (реализация в `database/roles.py`, экспорт через `database/db.py`).

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: aiogram 3 (`Dispatcher.shutdown` signal), gspread_asyncio (существующий), asyncio (stdlib: `create_task`, `TimerHandle`/`call_later` или `sleep`-таск)

**Storage**: SQLite (WAL), доступ только через фасад `database.db`; единое переиспользуемое соединение из фичи 008 (№15)

**Testing**: pytest + pytest-asyncio; изолированная БД через фикстуры (`tests/conftest.py`), мок `GoogleSheetsService.export_*`

**Target Platform**: Linux/Windows-хост, длительно живущий процесс бота

**Project Type**: Single project (Telegram-бот, слоистая архитектура handlers→services→database)

**Performance Goals**: N последовательных триггеров одного ключа в окне коалесценции → ровно 1 фактическая выгрузка (SC-001); получение ролей — 1 пакетный запрос вместо N (SC-005)

**Constraints**: сигнатура `_trigger_sheets_sync(mode, entity_id)` неизменна (FR-007, ~77 call-site'ов); фасад `db` неприкосновенен (R-ARCH-1); окно коалесценции — короткое (см. research.md, `SHEETS_SYNC_DEBOUNCE_SECONDS`); `to_thread` и rate-limit — вне scope

**Scale/Scope**: клубный масштаб; 1 файл сервиса (`services/management_service.py`), +1 функция в `database/roles.py`, +экспорт в `database/db.py`, +хук в `main.py`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Layered Isolation (R-ARCH-1/2/4/8)** — PASS. Новый пакетный запрос ролей живёт в `database/roles.py` и экспортируется через фасад `database.db`; сервис вызывает только `db.*`. Прямого доступа к низкоуровневым модулям нет. Направление импортов сохранено (`services`→`database`).
- **II. Sterile Interface (R-UI/R-FSM)** — N/A. Фича не затрагивает UI-переходы и FSM.
- **III. Service-Mediated Mutation (R-DATA-1)** — PASS. Точка входа синка остаётся в `ManagementService`; сигнатура и `(bool,str)`-контракт мутаций не меняются (синк — фоновый побочный эффект, не мутация).
- **IV. Test-First (R-PROC-3, R-TEST-3)** — PASS by plan. Характеризационный/репро-тест на «Task was destroyed» и на коалесценцию пишется ПЕРВЫМ (RED→GREEN). Мок-ассерты проверяют `args`+`kwargs` (R-TEST-3).
- **V. SSOT & Traceability (R-CODE-7)** — PASS. План цитирует R-ID, текст правил не копируется.
- **Efficiency (R-DATA-10 «No N+1»)** — устранение N+1 по ролям прямо соответствует духу правила (перенос из UI-контекста в экспортный, тот же анти-N+1 принцип).
- **Static gates (R-ARCH-8, R-PROC-10/11)** — semgrep(Docker)/import-linter/ruff/governance гоняются в конце implement.

**Итог: GATE PASSED, нарушений нет. Complexity Tracking не требуется.**

## Project Structure

### Documentation (this feature)

```text
specs/010-sheets-sync-debounce/
├── plan.md              # This file
├── spec.md              # Feature spec
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks — НЕ создаётся здесь)
```

### Source Code (repository root)

```text
services/
└── management_service.py     # [MODIFY] реестр pending-задач, дебаунс-планировщик,
                              #          flush_pending_syncs(), owned create_task,
                              #          батч-фетч ролей вместо N+1-цикла

database/
├── roles.py                  # [MODIFY] +get_roles_for_users(user_ids) — пакетный запрос
└── db.py                     # [MODIFY] +реэкспорт get_roles_for_users в фасаде

main.py                       # [MODIFY] dp.shutdown.register(ManagementService.flush_pending_syncs)

tests/
└── test_sheets_sync_debounce.py  # [NEW] репро «Task was destroyed» + коалесценция +
                                  #       flush + отсутствие N+1 (мок export_/get_roles_for_users)
```

**Structure Decision**: Single-project слоистая архитектура. Изменение локализовано в сервисном слое (`services/management_service.py`) + минимальная точечная добавка в фасад данных (`database/roles.py`, `database/db.py`) и одна строка wiring в `main.py`. `loader.py` (объект `dp`) не меняется — регистрация shutdown-хука делается в `main.py`, где уже происходит вся сборка диспетчера. `contracts/` не создаётся: внешнего интерфейса фича не вводит.

## Complexity Tracking

> Нарушений Constitution Check нет — таблица не заполняется.
