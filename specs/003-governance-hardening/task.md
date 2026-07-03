# Task Checklist: 003-governance-hardening

RNA execution checklist (legacy linter target; canonical checklist = tasks.md). Executor marks phases `[x]` as they complete.

- [x] Phase 1 (Sonnet): dispositions fixture created, `test_imperatives_map_to_rules` written and observed RED (18 anchors named, frozen inventory untouched) — T001–T003
- [x] Phase 2 (Sonnet, US1): R-ARCH-9 / R-UI-12 / R-UI-13 added + R-PROC-2 amended from verbatim git sources (8280d6f^); rule-map repaired (30 rows fixed, zero index.md rows, CP-5.1 retired); 12/12 governance+bundle tests green; mutation checks 1–2 pass; full regression 111 passed/0 failed — T004–T007
- [x] HARD STOP: Chunk A reported to Шэф, approval received before Chunk B
- [x] Phase 3 (Sonnet, US2): linter v2 TDD (red→green, 24/24 tests), backward compatibility proven live on specs/002 + specs/003; AGENTS.md Route A = spec-kit chain + command registry + § PLAN CONTENT; R-PROC-2/4 artifact names updated — T008–T012
- [x] Phase 4 (Sonnet, US3+final): tasks-template gate pattern (5 HARD STOP occurrences); full regression 122 passed/0 failed; mutation check 3 pass; walkthrough.md report-linted; CHANGELOG 1.4.0; GW-1 commit — T013–T016
- [x] запуск линтера-чеклиста (run checklist-linter) — T017
