# Research: Governance Hardening

**Date**: 2026-07-03. All judgment calls are resolved HERE (by the Fable audit); the executor applies them mechanically. No open questions.

## D1. Verbatim sources for restored rules

- **Decision**: Restore from the pre-dissolution git state: `git show 8280d6f^:CONTEXT_PROMPT.md` (CP-3.11, CP-3.47, CP-3.28.2 full texts with rationale lines) and `git show 8280d6f^:PROJECT_LOGIC.md` (PL-4.1). Reformat into the RULES.md entry schema; do not paraphrase the imperative content.
- **Rationale**: `8280d6f^` = the tree immediately before dissolution — the exact state the frozen inventory was built from; zero interpretation needed.

## D2. Disposition table for all 24 bundle-mapped imperative anchors (THE LAW for Chunk A)

Verified against RULES.md/AGENTS.md/bundle content during the 2026-07-03 audit. `map→` = fix the rule-map row to this target. `override:` = add to `tests/fixtures/imperative_dispositions.txt`.

| # | Anchor | Verdict | Action |
|---|---|---|---|
| 1 | PL-1.2 | descriptive (stack fact; heuristic over-capture of "Required") | override: descriptive |
| 2 | PL-2.4.1 | content lives in R-ARCH-1 | map→ R-ARCH-1 |
| 3 | PL-2.5.1 | content lives in R-ARCH-3 | map→ R-ARCH-3 |
| 4 | PL-3.5.4 | descriptive (background-failure behavior, in db-patterns.md) | override: descriptive |
| 5 | PL-4.1 | **LOST** — pipeline order invariant softened to "fixed by design" | **restore as R-ARCH-9**; map→ R-ARCH-9 |
| 6 | PL-4.5.1 | content lives in R-ARCH-6 | map→ R-ARCH-6 |
| 7 | PL-4.6.2 | covered by R-DB-5 (init_db fail-closed fuse) | map→ R-DB-5 |
| 8 | PL-4.7.1 | descriptive (FsmButtonGuard behavior, in middleware.md) | override: descriptive |
| 9 | PL-5.3.1 | content lives in R-FSM-1 | map→ R-FSM-1 |
| 10 | CP-2.17 | descriptive (feature description) | override: descriptive |
| 11 | CP-3.7 | parent anchor of merged facade rules | map→ R-ARCH-1 |
| 12 | CP-3.11 | **LOST** (isolated cancel keyboards; terminate_input before independent transitions; sterile_command for commands) | **restore as R-UI-12**; map→ R-UI-12 |
| 13 | CP-3.28.1 | covered by R-PROC-2 (header logic) | map→ R-PROC-2 |
| 14 | CP-3.28.2 | **LOST** (incremental plan updates) | **amend R-PROC-2**; map→ R-PROC-2 |
| 15 | CP-3.28.3 | covered by R-PROC-2 + AGENTS § RNA (rule-ID tags) | map→ R-PROC-2 |
| 16 | CP-3.28.5 | covered by R-PROC-2 (3–5 steps + approval) | map→ R-PROC-2 |
| 17 | CP-3.42 | descriptive (shipped `/an` format, in features-overview.md; guarded by tests) | override: descriptive |
| 18 | CP-3.47 | **LOST** (admin-creation UX branching: clean success message instead of entity card for admin creators) | **restore as R-UI-13**; map→ R-UI-13 |
| 19 | CP-3.53.1 | covered by R-UI-11 | map→ R-UI-11 |
| 20 | CP-3.53.2 | covered by R-UI-11 | map→ R-UI-11 |
| 21 | CP-3.53.3 | covered by R-UI-11 (verified verbatim) | map→ R-UI-11 |
| 22 | CP-3.60.1 | covered by R-PROC-11 | map→ R-PROC-11 |
| 23 | CP-5.1 | retired — the CP-vs-GEMINI scope split died with the file split | map→ `retired (scope note obsolete — see log.md)`; override: retired |
| 24 | CP-6.3 | covered by R-PROC-8 (verified) | map→ R-PROC-8 |

Additionally fix the remaining `index.md`-fallback rows found by `grep "| docs/knowledge/index.md |" docs/knowledge/rule-map.md` (10 rows total; the non-imperative ones among them): CP-6.1 → R-CODE-4; CP-6.2 → R-PROC-6; CP-6 → R-PROC-8; any residual PL sub-anchor → the R-ID of its parent per RULES.md `Legacy:` fields. After the fix, zero rows may target `index.md`.

## D3. Retention test design (deterministic, no n-gram fuzz)

- **Decision**: `test_imperatives_map_to_rules`: for every anchor flagged `IMP` in the frozen inventory — resolve via rule-map: (a) target is `R-<DOMAIN>-<n>` → assert that ID is defined in RULES.md; (b) else anchor MUST appear in `tests/fixtures/imperative_dispositions.txt` as `descriptive` or `retired`; (c) otherwise FAIL naming the anchor. The frozen inventory file is never edited.
- **Rationale**: Content-similarity probes false-positive on the intentional 002 rephrasings; trusting the curated map + a small explicit override file is deterministic and mutation-testable. The override file stays tiny (~7 rows), so every exception is human-visible.

## D4. Linter v2 contract

- **Decision**: `--stage plan`: if `plan.md` exists in `--dir`, validate it (H1 present; required H2s: `Summary`, `Technical Context`, `Constitution Check`, `Project Structure`; Cyrillic warning as today); else fall back to `implementation_plan.md` with the legacy H2 set. `--stage checklist`: if `tasks.md` exists, validate it (≥1 checkbox; zero incomplete `[ ]`/`[/]`; last checkbox line contains "запуск линтера-чеклиста" or "run checklist-linter"); else fall back to `task.md`. `--stage report`: unchanged. Preference order is fixed (spec-kit file wins when both exist) — EXCEPT both-present is exactly the dual-format transition case, so during THIS feature the executor runs plan-stage before creating no conflict: this feature dir contains both; v2 will validate `plan.md`/`tasks.md`, which are also compliant.
- **Rationale**: Kills К-2 without a flag day: features 001/002 lint as before; 004+ needs only spec-kit artifacts.

## D5. Constitution & template changes (К-1, К-3)

- **Decision**: `AGENTS.md`: Route A = `[PA-1 if architectural] → /speckit-specify → /speckit-clarify (if needed) → /speckit-plan → /speckit-tasks → approval → /speckit-implement`, with prompt-linter gates named per stage; § COMMAND REGISTRY gains a `speckit-*` row block; `RNA-1` row marked "legacy alias — RNA content lives in plan.md sections"; § RNA-BLUEPRINT section retitled "§ PLAN CONTENT (RNA-Blueprint inside plan.md)". Route B note: PA-1 precedes specify; clarify follows it. Template: add a `### HARD STOP` gate-task block requirement (every 3–5 executable tasks; text: report to Шэф in Russian + await approval; executor MUST NOT proceed past an unchecked gate), citing R-PROC-2.
- **Rationale**: The constitution finally describes the process actually used; the gate moves from author memory into the artifact generator.

## D6. Rule text drafts (executor copies these, adjusting only formatting)

- **R-ARCH-9 [A] Middleware pipeline order invariant** — Rule: "The sequential middleware pipeline is registered as `outer_middleware` on `dp.message` — the order (UserManager → ForumUtility → AccessGuard) is fixed and MUST NOT be changed." Why: later stages assume earlier guarantees (registration before access checks). Legacy: PL-4.1.
- **R-UI-12 [A] Sterile input entry points** — Rule (from CP-3.11 verbatim base): "Every transition between independent FSM flows, disambiguation steps, or generation of new interactive elements MUST be preceded by `await UIService.terminate_input(state, message)`. Every FSM entry point that requires text input MUST use an isolated cancel keyboard (e.g., `get_event_cancel_kb`, `get_admin_cancel_kb`). Command-level handlers use the `@UIService.sterile_command` decorator." Why: centralizes redirect/cleanup/tracking; isolated cancel keyboards prevent bypass via functional buttons. Legacy: CP-3.11.
- **R-UI-13 [A] Admin-creation UX branching** — Rule (from CP-3.47 verbatim base): "When an entity creation triggers an automatic audit notification to admins, the creation handler MUST NOT immediately show the final entity card to an admin creator — show a clean success message instead." Why: prevents double-notification clutter for admins. Legacy: CP-3.47.
- **R-PROC-2 amendment** — append: "Plans are updated incrementally: do not rewrite the entire plan for a correction; update only the affected parts." Legacy add: CP-3.28.2.

## D7. Executor

- **Decision**: Sonnet end-to-end; two chunks (A: Phases 1–2 = F-group; HARD STOP; B: Phases 3–4 = К-group). Opus not needed — D2/D6 remove classification and drafting judgment; linter v2 is a mechanical refactor with pinned tests.
