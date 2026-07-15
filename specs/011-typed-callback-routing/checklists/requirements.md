# Specification Quality Checklist: Типизированный роутинг колбэков

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-14
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Items marked incomplete require spec updates before `/speckit-clarify` or `/speckit-plan`
- **Перепроверено после поправки Q-1/A (2026-07-14)**: добавление FR-015…FR-018 и SC-009 чеклист не ломает. Новые FR тестируемы и однозначны (каждый называет конкретный маршрут и наблюдаемый результат), SC-009 измерим (три RED→GREEN репро-теста), границы scope сузились явно, а не расширились неявно. Маркеров `[NEEDS CLARIFICATION]` по-прежнему нет.
- Сценарии, FR и SC сознательно сформулированы через «объявленный контракт маршрута» / «единственное объявление формата», а не через конкретный механизм стека — механизм выбирается на стадии `/speckit-plan`.
- Спека сознательно называет `UIService.generic_navigator`, `UIService.sterile_show` и цитирует `R-*` ID — это границы существующей системы и обязательные ограничения (`R-UI-3`, `R-UI-1`, `R-SEC-2`, `R-SEC-3`, `R-PROC-3`), а не выбор технологии реализации. Цитирование ID предписано Constitution V / `R-CODE-7`. Аналогично house style фичи 010.
- SC-008 называет semgrep / import-linter / ruff: это обязательные машинные гейты архитектуры (`R-ARCH-8`, `R-PROC-10`, `R-PROC-11`), т.е. приёмочное условие проекта, а не деталь реализации фичи.
- Упоминание aiogram 3 ограничено секцией Assumptions как фиксация существующей зависимости (фича не вводит новых); в сценариях, FR и SC его нет.
- SC-007 (сокращение объёма кода диспетчеризации) проверяется сравнением «до/после» на строках 250–388 `services/ui_service.py`; целевое число не задаётся намеренно — критерий фиксирует направление и проверяемость, а не произвольный порог.
