# Quickstart / Validation: Dedup Permission Layer (feature 008 №20)

Валидация того, что cleanup не изменил наблюдаемое поведение слоя прав.

## Prerequisites

- venv активирован; pytest доступен (`venv/Scripts/python.exe -m pytest`).
- Изолированная тестовая БД через существующие фикстуры (`R-TEST-1`).

## Validation scenarios

### V1 — Характеризация ДО правки (R-PROC-3)

Новый тест-файл `tests/test_permission_layer_dedup.py` фиксирует текущее поведение и должен пройти **на неизменённом коде** (baseline):

- **US1 / `can_write`**:
  - пользователь с записью в `direct_topic_access(user_id, topic_id)` → `can_write(...) is True`;
  - без записи → `can_write(...) is False`.
- **US1 / эквивалентность дубля** (проверяется ДО удаления): `has_direct_access(u, t) == can_write(u, t)` для обоих входов — подтверждает идентичность перед удалением. Этот under-test убирается вместе с функцией; остаётся его смысл в виде поведенческих проверок `can_write`.
- **US2 / `is_superadmin`**:
  - `user_id == ADMIN_ID`, роль `superadmin` в БД присутствует → `True`;
  - `user_id == ADMIN_ID`, роли в БД НЕТ → `True` (ключевой характеризационный кейс — фиксирует, что результат не зависит от БД);
  - `user_id != ADMIN_ID` → `False`.

### V2 — После правки

- Удалён `has_direct_access` и его импорт из `database/db.py`; поиск по коду не находит определения/импорта.
- `is_superadmin` не содержит ветви, недостижимой по результату; поведенческие кейсы V1/US2 (True/True/False) остаются зелёными.
- `can_write`-кейсы V1/US1 остаются зелёными.

### V3 — Регрессия существующих тестов

Полный прогон затрагивающих слой прав сьютов зелёный без изменения ожиданий:

```
venv/Scripts/python.exe -m pytest tests/test_journeys -q
venv/Scripts/python.exe -m pytest tests/test_permission_layer_dedup.py -q
```

## Expected outcome

- Baseline (V1) зелёный до правки; V2/V3 зелёные после правки.
- 0 неиспользуемых дублей прямого доступа; 0 мёртвых по результату ветвей в `is_superadmin`.
- Публичный контракт слоя прав неизменен; поведение бота для пользователей идентично.

## Gates (перед завершением)

- import-linter / ruff / semgrep (архитектурные гейты, `R-ARCH-8`, `R-PROC-10/11`) — без новых нарушений.
- checklist-linter — completion-gate в самом конце (после `/speckit-tasks`).
