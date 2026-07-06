# AGENTS.md — Tenir-Too Bot Constitution

Single tracked entry point for every AI assistant working on this repository (open
`AGENTS.md` standard). Identity, routes, commands, process. **Behavioral rules are NOT
restated here** — they live once in [RULES.md](RULES.md), cited by ID (`R-<DOMAIN>-<n>`).
Descriptive reference lives in [docs/knowledge/](docs/knowledge/index.md). Legacy
`PL-x.y`/`CP-x.y` citations resolve via [docs/knowledge/rule-map.md](docs/knowledge/rule-map.md).

> Be concise. Be functional. Token-efficient always. Respond in Russian, address the user as
> **Шэф** (`R-PROC-8`).

## § ONBOARDING (START HERE)

1. **Project**: Tenir-Too is a Telegram Access Control Bot (Python 3.11, aiogram 3, FastAPI,
   SQLite/WAL, pytest) providing granular access control and stealth moderation for Forum
   Topics in a Supergroup, plus club administration and a Telegram Mini App.
2. **Pre-read set (always)**: this file + `RULES.md` + `docs/knowledge/index.md`. Open a
   knowledge concept file only when its topic is relevant (progressive disclosure).
3. **Skills**: to use `tenirtoo-proposal-analysis` or `tenirtoo-docs-update`, first read the
   skill's `SKILL.md`.
4. **Roadmap**: future plans live in `_nogit_roadmap.md` / `_nogit_*` (local).
5. **Knowledge graph**: when `graphify-out/` exists, `R-PROC-12` governs it — query the graph
   first for structural questions; see [docs/knowledge/graph.md](docs/knowledge/graph.md) for
   commands, the freshness channels, and the CLI-absent fallback.

## § FILE REGISTRY

| File | Role | Git |
|---|---|---|
| `AGENTS.md` | This file — constitution: identity, routes, commands, process. | **Public (tracked)** |
| `RULES.md` | Unified rulebook — every behavioral rule, once, with stable IDs. | **Public (tracked)** |
| `docs/knowledge/` | OKF reference bundle (architecture, schema, registry, FSM, constants, testing, features, design, subagents, rule-map). `index.md` = on-demand entry. | **Public (tracked)** |
| `.specify/memory/constitution.md` | Spec-kit constitution — top principles mirroring RULES.md. | Local |
| `CHANGELOG.md` | Version history. Read on onboarding/debugging, not pre-read. | **Public (tracked)** |
| `CLAUDE.md`, `GEMINI.md` | Compatibility shims → this file. | Local |
| `graphify-out/` | Local knowledge-graph artifacts (regenerable). | Local |
| `_nogit_*` | Local scratch/roadmap. | Local |
| `tenirtoo-plugin` | Local Claude Code plugin at `.agents/plugins/tenirtoo-plugin/` (manifest `.claude-plugin/plugin.json`). Bundles the Route B/C engine **skills** (`tenirtoo-proposal-analysis`, `tenirtoo-docs-update`) and the three **subagents** (`proposal-auditor`, `test-runner-and-debugger`, `cognitive-ux-auditor`). Registered via repo-root `.claude-plugin/marketplace.json` (`tenirtoo-local`) + `enabledPlugins` in `.claude/settings.json`. Subagent configs are mirrored from [subagents.md](docs/knowledge/subagents.md) (descriptive source). | Local |

## § CONTENT OWNERSHIP

| What | Home | Never restate in |
|---|---|---|
| Behavioral rules (imperative) | `RULES.md` (one `R-*` entry) | AGENTS.md / bundle / redirects |
| Descriptive reference (schema, registry, middleware/FSM behavior, constants, testing infra, feature detail, design tokens, subagent configs) | `docs/knowledge/` concept files | RULES.md / AGENTS.md |
| Routes, commands, process narrative, identity | `AGENTS.md` (cites `R-PROC-*`) | elsewhere |
| Legacy anchor resolution | `docs/knowledge/rule-map.md` | — |
| Shipped features/fixes | `CHANGELOG.md` | — |

## § EXECUTION WORKFLOW

Silently determine the route before acting.

### Route A — Feature / Bug Fix
- **Trigger**: code changes, features, fixes.
- **Pre-read**: the always-set (AGENTS.md + RULES.md + `docs/knowledge/index.md`); open
  relevant bundle concept files on demand.
- **Engine**: the spec-kit chain is the sole Route A process: `[PA-1 if architectural]` →
  `/speckit-specify` → `/speckit-clarify` (if requirements are underspecified) →
  `/speckit-plan` → `/speckit-tasks` → **approval** → `/speckit-implement`. (The legacy
  `RNA-1`/`implementation_plan.md` path was retired in feature 004 — see § INDEXING.)
- **Process rules**: align global/architectural options with Шэф first (`R-PROC-1`); the
  spec-kit `plan.md` carries the plan-content blueprint (`R-PROC-2`, see § PLAN CONTENT);
  bugs get a failing reproducing test first (`R-PROC-3`); run the prompt-linter gate after
  `/speckit-plan` (plan stage) and after `/speckit-tasks` completion (checklist stage)
  (`R-PROC-4`); TDD sub-step per execution step; `/speckit-implement` MUST stop at every
  HARD-STOP gate task in `tasks.md` and await approval before continuing.
- **Post**: flag docs updates (Route C) if the module registry, schema, or a rule changed.

### Route B — Architectural Proposal / Audit
- **Trigger**: user proposes logic/design, or invokes `PA-1`/`APA-1`.
- **HARD STOP**: no code — structured analysis only via `tenirtoo-proposal-analysis`
  (delegate to `proposal-auditor`). `PA-1` = Project Mode (ground truth: `RULES.md` +
  `docs/knowledge/`). `APA-1` = Abstract Mode (industry standards). Wait for approval
  before Route A (`R-PROC-1`).
- **Ordering**: `PA-1`/`APA-1` audits the idea BEFORE `/speckit-specify` (it gates whether a
  spec should exist at all); `/speckit-clarify` refines requirements AFTER a spec exists —
  the two are sequential, not alternatives.

### Route C — Documentation Update
- **Trigger**: source changed, files added/removed, features shipped.
- **Invoke** `tenirtoo-docs-update`: rules → `RULES.md`; description → `docs/knowledge/`;
  process → this file; `CMD-4` → `CHANGELOG.md`. No git operations during this route.

### Route D — Ambiguous
- Resolvable with context → Route A. Missing a critical parameter → ask one focused
  question, then proceed.

## § COMMAND REGISTRY

| Command | Route | Action |
|---|---|---|
| `PA-1` / `APA-1` | B | Project / Abstract mode audit |
| `/speckit-specify` | A | Create the feature spec (`spec.md`) from a description |
| `/speckit-clarify` | A | Resolve underspecified requirements in an existing spec |
| `/speckit-plan` | A | Generate `plan.md` (plan-content blueprint — see § PLAN CONTENT) |
| `/speckit-tasks` | A | Generate `tasks.md` (chunked, with HARD-STOP gates) |
| `/speckit-implement` | A | Execute `tasks.md`, honoring approval gates |
| `/speckit-analyze` | A | Cross-artifact consistency check (spec/plan/tasks) |
| `GW-1` | Git | Local commit at a milestone (`R-PROC-5`) |
| `CMD-1..4` | C | Update RULES/bundle · knowledge · README · CHANGELOG via docs-update |

## § PLAN CONTENT (blueprint inside plan.md)

Required for any change touching >1 file (`R-PROC-2`). The spec-kit `plan.md` template
carries this content under its own headings — it is the only plan artifact. Mapping:
**Base DNA** (OS/stack) → `Technical Context`;
**Task RNA** (logic, risks, edge cases) → `Summary` + `Technical Context`; **Contextual
Constraints** (cite rule IDs) → `Constitution Check`; **Proposed Changes**
(`[NEW]`/`[MODIFY]`/`[DELETE]`) → `Project Structure`; **Execution Steps** (numbered, 3–5
per chunk, each with a TDD sub-step and a rule-ID tag, HARD-STOP gate tasks at chunk
boundaries) → `tasks.md` (generated by `/speckit-tasks`, template-enforced — see
`.specify/templates/tasks-template.md`); **Verification** (name the reproducing test) →
`quickstart.md` / task descriptions. Plan updates are incremental (`R-PROC-2`): do not
rewrite the whole plan for a correction. Plan language: English. Mock assertions check
`args` and `kwargs` (`R-TEST-3`).

## § GIT WORKFLOW (GW-1)

`git status` → stage deletions → `git add .` → `git commit` (concise English). Local commits
at milestones are allowed; **`git push` requires explicit user request** (`R-PROC-5`).

## § INDEXING

`R-<DOMAIN>-<n>` → rule in `RULES.md`. Legacy `PL-x.y`/`CP-x.y` → `docs/knowledge/rule-map.md`.
Cite IDs in plans; never copy full rule text (`R-CODE-7`).

**Retired**: `RNA-1` (and its `implementation_plan.md`/`task.md` artifacts) — superseded by
`/speckit-plan` + `/speckit-tasks`; retired in feature 004. Historical specs 001–003 keep
their legacy artifacts as read-only records; the prompt-linter no longer accepts them.

## § SUBAGENTS

Three specialized subagents (full configs in
[docs/knowledge/subagents.md](docs/knowledge/subagents.md)):

- **proposal-auditor** — Route B dialectic audit (PA-1/APA-1) via `tenirtoo-proposal-analysis`.
- **test-runner-and-debugger** — runs `pytest`, applies minimal localized fixes to `[MODIFY]`
  files; may not edit tests/configs; max 3 debug loops.
- **cognitive-ux-auditor** — runtime cognitive walkthrough via
  `local_scripts/ux_cognitive_audit.py`; validates flows against the Frictionless UX checklist.

## § RESPONSE PROTOCOL

Per `R-PROC-8`: Russian, address «Шэф», concise, no preamble, no restating code; summarize
tool edits rather than pasting; production code in tilde blocks (`R-CODE-4`).
