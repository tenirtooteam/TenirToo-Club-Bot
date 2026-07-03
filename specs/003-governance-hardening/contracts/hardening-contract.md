# Contract: Governance Hardening

**Date**: 2026-07-03. Test names are binding.

## Retention contract

| Clause | Test |
|---|---|
| Every imperative frozen anchor resolves to an existing R-ID, or is dispositioned `descriptive`/`retired` in the override file | `test_imperatives_map_to_rules` (new, in tests/test_governance.py) |
| Zero rule-map rows target `docs/knowledge/index.md` | asserted inside `test_imperatives_map_to_rules` (map hygiene sub-check) |
| Existing governance/bundle invariants unchanged | existing 11 tests stay green |

Override file format (`tests/fixtures/imperative_dispositions.txt`), one row per line:
`<anchor><TAB><descriptive|retired><TAB><one-line justification>`

## Linter v2 contract

| Stage | Preferred target (v2) | Legacy fallback | Structure enforced |
|---|---|---|---|
| plan | `plan.md` | `implementation_plan.md` | v2: H1 + H2s `Summary`, `Technical Context`, `Constitution Check`, `Project Structure`; legacy: existing H2 set. Cyrillic warning both |
| checklist | `tasks.md` | `task.md` | ≥1 checkbox; zero incomplete; last checkbox contains «запуск линтера-чеклиста» / "run checklist-linter" |
| report | `walkthrough.md` | — | unchanged |

Binding test additions: `test_plan_v2_speckit_file`, `test_plan_legacy_fallback`, `test_checklist_v2_tasks_file`, `test_checklist_legacy_fallback` (unit, tests/test_prompt_linter.py) + one v2 CLI case per stage in the journey file. All pre-existing linter test cases MUST pass unmodified except where they construct fixtures (fixture dirs may need both-absent handling).

## Constitution/template contract (manual checks, quickstart §4)

- AGENTS.md § COMMAND REGISTRY contains `speckit-specify|plan|tasks|implement|clarify|analyze`; Route A names the spec-kit chain; `RNA-1` marked legacy alias.
- `.specify/templates/tasks-template.md` contains a `HARD STOP` gate-task block requirement citing R-PROC-2.
- RULES.md: R-UI-12, R-UI-13, R-ARCH-9 defined; R-PROC-2 contains the incremental principle; R-PROC-2/R-PROC-4 name `plan.md`/`tasks.md`.

## Mutation checks (SC-001)

1. Point one imperative anchor's rule-map row at `features-overview.md` → `test_imperatives_map_to_rules` FAIL → restore.
2. Delete one override row → FAIL → restore.
3. Remove `Constitution Check` H2 from a v2 plan fixture → plan stage FAIL → restore.
