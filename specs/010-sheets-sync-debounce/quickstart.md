# Quickstart / Validation: Sheets-синк дебаунс (№17)

Валидация того, что рефактор `_trigger_sheets_sync` работает end-to-end. Реализационные детали — в `plan.md`/`data-model.md`/`tasks.md`.

## Prerequisites

- Активирован `venv` (R-PROC-7). pytest запускается интерпретатором venv:
  - `venv/Scripts/python.exe -m pytest` (Windows-хост проекта).
- Изолированная тестовая БД и мок Telegram — через существующие фикстуры `tests/conftest.py`.
- Экспорты Google Sheets мокаются (`GoogleSheetsService.export_users/groups/events/event_participants`); реальный Google API не дёргается.

## Validation scenarios

Все сценарии — в `tests/test_sheets_sync_debounce.py` (детали — research.md R6). Мок-ассерты проверяют `args`+`kwargs` (R-TEST-3).

1. **Владение задачей / нет «Task was destroyed» (репро, RED первым)** — FR-003/FR-004, SC-002/SC-003/SC-006.
   Триггер синка → задача удерживается до завершения; исключение внутри задачи попадает в `logger.error`; прогон не порождает предупреждения о разрушенной задаче.

2. **Коалесценция всплеска** — FR-001, SC-001.
   N (≥2) быстрых триггеров одного `mode` в окне → соответствующий `export_*` вызван ровно 1 раз.

3. **Независимость ключей** — FR-002.
   Триггеры `users` и `groups` → каждый export по разу; `event_participants` с разными `entity_id` не склеиваются.

4. **Shutdown-flush** — FR-005, SC-004.
   Триггер → до истечения окна `await ManagementService.flush_pending_syncs()` → export выполнен немедленно. Пустой реестр → flush без выгрузок и без ошибок.

5. **N+1 устранён** — FR-006, SC-005.
   Выгрузка `users` вызывает `db.get_roles_for_users` один раз; `get_user_roles` в цикле по пользователям не вызывается.

## Run commands

```bash
# Полный прогон целевого файла
venv/Scripts/python.exe -m pytest tests/test_sheets_sync_debounce.py -v

# Регресс всего набора (не должно быть новых предупреждений о задачах)
venv/Scripts/python.exe -m pytest -q
```

## Expected outcomes

- Все сценарии выше — GREEN.
- Полный набор проходит без регрессий и без предупреждений «Task was destroyed»/«pending task» по синку (SC-006).
- Число `export_*` при всплеске = 1 на ключ (SC-001); число запросов ролей = 1 пакетный (SC-005).

## Static gates (в конце implement)

```bash
# semgrep — через Docker-демон (native→docker fallback, см. историю проекта)
# import-linter
venv/Scripts/lint-imports.exe
# ruff
venv/Scripts/python.exe -m ruff check .
# governance / knowledge bundle
venv/Scripts/python.exe -m pytest tests/test_governance.py tests/test_knowledge_bundle.py -q
```

Ожидание: все статик-гейты зелёные; фасадная граница (R-ARCH-1) и направление импортов (R-ARCH-4) не нарушены новым `get_roles_for_users`.
