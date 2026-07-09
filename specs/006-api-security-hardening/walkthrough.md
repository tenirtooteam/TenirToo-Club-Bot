# Walkthrough — API Security Hardening (Phase 1, feature 006)

Отчёт о реализации Фазы 1: закрытие эксплуатируемой authz-дыры и связанного харденинга веб-слоя и колбэков. Все правки шли по TDD (сначала падающий тест, R-PROC-3).

## Changes made

**US1 — единый гард прямой записи на поход (P1, MVP):**
- `services/event_service.py`: добавлен `EventService.check_direct_join_allowed(user_id, event_id, topic_id)` — событие существует и одобрено; при наличии топик-контекста — `can_user_write_in_topic` (Default-Deny, R-DB-1). Логика в сервисном слое (R-DATA-1), права через `PermissionService`.
- `web/routers/dashboard.py`: `toggle_event_participation_direct` вызывает гард (`topic_id=None`) до мутации; отказ → `logger.warning` (FR-011) + `HTTPException(403)`.
- `web/routers/announcements.py`: inline-проверка топика заменена на гард (`topic_id=ann.topic_id`) — добавлена проверка одобрения; отказ → лог + 403.
- `handlers/announcements.py`: `ann_join` гейтится гардом (топик анонса + одобрение) + лог отказа; бот-карточка (`event_join`, аудит-модель) не тронута.

**US2 — anti-replay сессии WebApp (P2):**
- `config.py`: `WEBAPP_SESSION_TTL_SECONDS` (env, default 86400; `<=0` отключает).
- `web/auth.py`: в `validate_webapp_init_data` после HMAC — проверка свежести `auth_date` (нет/битый → None; старше TTL → None; из будущего дальше 300 с → None).

**US3 — корректный глобальный 500-хендлер (P2):**
- `web/main.py`: `global_exception_handler` возвращает `JSONResponse(500, {"detail": ...})` вместо объекта `HTTPException`; лишний импорт `HTTPException` убран.

**US4 — defense-in-depth колбэков (P3):**
- `handlers/common.py`: `confirm_execution` получил серверную проверку прав через `_confirm_action_authorized` (per-action: `mod_topic_del`/`mod_rem` → `can_manage_topic`; `event_del` → `can_edit_event`; остальное → `is_global_admin`); `perform_search_pick` проверяет `can_manage_topic` перед `mod_add`/`dir_add`. Права через `PermissionService` (R-ARCH-7).

Изменений схемы БД нет. Новых модулей/слоёв нет.

## What was tested

Новые тесты (TDD, сначала красные):
- `tests/test_services/test_participation_guard.py` — 5 unit-кейсов гарда.
- `tests/test_web/test_dashboard_participation.py` — веб-дашборд: pending → 403, approved → запись.
- `tests/test_journeys/test_announcement_join_guard.py` — анонс: неодобренный/без-доступа → отказ, участник не добавлен (args+kwargs, R-TEST-3).
- `tests/test_web/test_auth_freshness.py` — свежесть/устаревание/отсутствие/будущее `auth_date`.
- `tests/test_web/test_error_handler.py` — 500-хендлер возвращает `JSONResponse`, лог с `exc_info`.
- `tests/test_journeys/test_callback_defense.py` — не-админ/не-менеджер не выполняют удаление/выдачу прав; авторизованные проходят.

Обновлены два существующих теста, кодировавших прежнее небезопасное/устаревшее поведение: `test_ux_journeys.py::test_fsm_reset_after_search_pick` (актор сделан авторизованным) и `test_web/test_auth.py` (динамическая свежая `auth_date`).

## Validation results

- Целевые тест-файлы фичи: все зелёные (SC-001…SC-007 подтверждены).
- Полный прогон: **146 passed, 0 failed** (Docker поднят, SAST-гейт `test_semgrep_lint` зелёный).
- Semgrep поймал реальное нарушение в первой версии правки — прямой `event.answer()` в `perform_search_pick` под `ban-direct-ui-calls`; исправлено переименованием параметра в `event_or_msg` (по whitelist правила и конвенции кодовой базы), без ослабления линтера.
- Архитектурные гейты: `test_import_lint.py`, `test_ruff_lint.py`, `test_semgrep_lint.py` — зелёные (границы слоёв, R-ARCH-8/R-PROC-11).
- Регрессий в затронутых потоках (анонсы, события, роли, модерация, поиск, удаления) не выявлено.
