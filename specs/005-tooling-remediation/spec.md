# Feature Specification: AI Tooling Remediation (July 2026 Audit)

**Feature Branch**: `005-tooling-remediation`

**Created**: 2026-07-05

**Status**: Draft

**Input**: User description: "Remediate AI tooling gaps found during the July 2026 tooling audit. Six verified findings: (1) pytest cannot be invoked as `.\venv\Scripts\pytest` — conftest fails with ModuleNotFoundError 'database'; only `python -m pytest` works, while docs instruct the broken form; (2) prompt_linter.py plan-stage Cyrillic regex false-positives on a bare hyphen; (3) tenirtoo-plugin skills live in .agents/plugins/ which the harness does not load, so Route B / Route C engines are not invocable; (4) the three subagents documented in docs/knowledge/subagents.md have no .claude/agents/ definitions; (5) the semgrep Docker gate is unverified and requirements-dev.txt pins semgrep on native Windows where it is unsatisfiable; (6) CLAUDE.md references graphify-out/wiki/index.md which graphify CLI 0.8.49 cannot produce. Scope: tooling/process infrastructure only, no bot production code changes. Planning on Fable; implementation on Opus/Sonnet."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Canonical test invocation works everywhere (Priority: P1)

Any AI agent (main session or subagent) or human developer runs the project test suite using the single documented invocation form, from the project root, and tests collect and execute without import errors. All governance documents that mention the test invocation agree on that one form.

**Why this priority**: Every Route A execution step carries a TDD sub-step; the reproducing-test rule (R-PROC-3) and the test-runner-and-debugger subagent both depend on tests being runnable. Today the documented form fails at collection, silently breaking the core delivery workflow.

**Independent Test**: From a clean shell at the project root, run the documented invocation against the full suite; collection succeeds (no ModuleNotFoundError) and results match the known-good `python -m pytest` baseline.

**Acceptance Scenarios**:

1. **Given** a clean shell at the project root, **When** the documented canonical test command is run, **Then** test collection succeeds and no import errors occur.
2. **Given** the fix is in place, **When** `python -m pytest` is run (the previously working form), **Then** it still passes with identical results (no regression).
3. **Given** the governance docs after the change, **When** searching for test-invocation instructions, **Then** every mention prescribes the same working form (no document still instructs a failing form).

---

### User Story 2 - Route B and Route C engines are invocable (Priority: P2)

An AI agent in a fresh session can invoke the architectural-audit engine (`tenirtoo-proposal-analysis`, commands PA-1/APA-1) and the documentation-sync engine (`tenirtoo-docs-update`, commands CMD-1..4) as first-class skills, because they are registered where the harness discovers them.

**Why this priority**: Two of the four constitutional routes (B and C) currently have no operational engine — their skills exist only as files in a location the harness never loads. The constitution promises capabilities the session cannot deliver.

**Independent Test**: In a fresh session, the two skills appear in the available-skills list and invoking each one loads the correct engine content; the content remains single-sourced (no divergent duplicate maintained by hand).

**Acceptance Scenarios**:

1. **Given** a fresh session in this project, **When** the available skills are listed, **Then** `tenirtoo-proposal-analysis` and `tenirtoo-docs-update` are present.
2. **Given** the registration is in place, **When** either skill is invoked, **Then** the engine content that loads is identical to the canonical source (no content drift between copies).
3. **Given** the canonical skill source is updated later, **When** the harness loads the skill, **Then** the update is reflected without a second manual edit, or a documented single-step sync procedure exists.

---

### User Story 3 - Documented subagents are actually delegable (Priority: P2)

An AI agent can delegate to `proposal-auditor`, `test-runner-and-debugger`, and `cognitive-ux-auditor` as named agents, because agent definitions exist in the location the harness reads, generated from the full configs already documented in `docs/knowledge/subagents.md`.

**Why this priority**: AGENTS.md § SUBAGENTS promises three specialized subagents; none is registered, so every delegation silently falls back to a generic agent without the documented constraints (e.g., the test-runner's "never edit tests" rule is not enforced).

**Independent Test**: In a fresh session, the three agents appear in the available agent types; each definition carries the constraints documented in `docs/knowledge/subagents.md` (roles, tool restrictions, iteration limits).

**Acceptance Scenarios**:

1. **Given** a fresh session, **When** available agent types are listed, **Then** the three named subagents are present.
2. **Given** the definitions exist, **When** each is compared with `docs/knowledge/subagents.md`, **Then** roles, constraints, and limits match (docs remain the descriptive source; definitions are the operational mirror).
3. **Given** the test-runner-and-debugger definition, **When** it is inspected, **Then** it prescribes the working test invocation form from User Story 1 (not the broken one).

---

### User Story 4 - Plan linter reports no false positives (Priority: P3)

The prompt-linter plan-stage check flags only genuine non-whitelisted Cyrillic words. A plan containing hyphens, dashes, or hyphenated English terms produces no Cyrillic-language warning.

**Why this priority**: The linter is a mandatory Route A gate (R-PROC-4); false positives train operators to ignore its warnings, eroding the gate's value. Impact is noise, not breakage, hence P3.

**Independent Test**: Run the plan-stage linter against a plan document containing bare hyphens and hyphenated English words but no Cyrillic text; no Cyrillic warning is emitted. Run it against a plan containing a genuine non-whitelisted Russian word; the warning correctly appears.

**Acceptance Scenarios**:

1. **Given** a plan with hyphens/dashes and no Cyrillic text, **When** the plan-stage lint runs, **Then** no Cyrillic-word warning is emitted.
2. **Given** a plan containing a non-whitelisted Russian word, **When** the plan-stage lint runs, **Then** the warning names that word.
3. **Given** a plan containing only whitelisted terms (e.g., "Шэф", "Теңир-Тоо"), **When** the plan-stage lint runs, **Then** no warning is emitted.
4. **Given** the fix, **When** the linter's own regression tests run, **Then** the false-positive case is covered by an automated test.

---

### User Story 5 - Architecture SAST gate is verified and honestly documented (Priority: P3)

The semgrep architecture-enforcement gate runs green through its canonical Docker channel, and the development-dependency manifest no longer promises a host install that is unsatisfiable on the native Windows dev environment. Documentation states clearly when the host-side check is expected to skip.

**Why this priority**: Five architecture rules (R-PROC-11) are enforced by this gate; it exists but has never been verified to run on this machine, and the dependency pin creates a false expectation. Verification plus documentation honesty — no new machinery — hence P3.

**Independent Test**: Execute the canonical Docker lint command once; it completes with a passing result on the current codebase. Inspect the dev-dependency manifest and docs; the Windows behavior (Docker = canonical, host check skips) is stated.

**Acceptance Scenarios**:

1. **Given** Docker is available, **When** the canonical semgrep lint command is executed, **Then** it completes successfully with zero rule violations on the current codebase.
2. **Given** the reconciled dev-dependency manifest, **When** a developer installs dev dependencies on native Windows, **Then** installation does not fail on account of semgrep, and the manifest/docs explain the Docker-canonical setup.
3. **Given** the docs after the change, **When** reading the testing/linting reference, **Then** the skip-on-Windows behavior of the host semgrep test is documented as intended behavior.

---

### User Story 6 - No dead references in agent-facing instructions (Priority: P4)

Agent-facing instruction files reference only artifacts the current toolchain can actually produce. The reference to a graphify wiki that the installed CLI cannot generate is removed or corrected.

**Why this priority**: Lowest impact — the reference is conditional and never triggers — but dead instructions accumulate as governance rot and mislead future audits.

**Independent Test**: Search agent-facing instruction files for references to artifacts; every referenced artifact is either present or producible by an installed tool.

**Acceptance Scenarios**:

1. **Given** the updated instruction file, **When** it is read by a fresh agent, **Then** no navigation channel is referenced that the installed toolchain cannot produce.
2. **Given** graphify later gains the capability, **When** the feature is reconsidered, **Then** nothing in this change blocks re-adding the reference.

---

### Edge Cases

- What happens when the test suite is invoked from a subdirectory rather than the project root? The canonical form must either work or the docs must state the root-only constraint explicitly.
- How does skill registration behave if the harness loads both the canonical source and a registered copy (duplicate skill names in one session)? Registration must not produce two competing skills with the same name.
- What if Docker is not running when the semgrep gate is invoked? The gate must fail loudly (clear error), not report a false pass; documentation should note the Docker-daemon prerequisite.
- What happens to the linter when a plan contains mixed tokens like "спек-kit" (Cyrillic+Latin+hyphen)? The check must still flag the Cyrillic fragment.
- If a future session runs on a harness that reads a different agents/skills location, the descriptive source of truth (`docs/knowledge/`) must still be accurate — operational registration is a mirror, not a fork.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST provide a single canonical test invocation that collects and runs the full suite from the project root without import errors.
- **FR-002**: All governance and reference documents that mention test invocation MUST prescribe exactly that canonical form.
- **FR-003**: The plan-stage language check MUST flag a token as Cyrillic only if it contains at least one Cyrillic letter; punctuation-only tokens MUST never be flagged.
- **FR-004**: The linter fix MUST be covered by automated regression tests exercising: punctuation-only tokens (pass), genuine Cyrillic words (flag), whitelisted terms (pass), and mixed Cyrillic-Latin tokens (flag).
- **FR-005**: The skills `tenirtoo-proposal-analysis` and `tenirtoo-docs-update` MUST be discoverable and invocable by the harness in a fresh session.
- **FR-006**: Skill registration MUST preserve a single source of truth: either one physical location, or an explicitly documented one-step sync mechanism; silent content forks are prohibited.
- **FR-007**: Agent definitions for `proposal-auditor`, `test-runner-and-debugger`, and `cognitive-ux-auditor` MUST exist in the location the harness reads, with constraints faithful to `docs/knowledge/subagents.md`.
- **FR-008**: The `test-runner-and-debugger` definition MUST prescribe the canonical test invocation from FR-001.
- **FR-009**: The semgrep architecture gate MUST be executed once via its canonical Docker channel and verified to pass on the current codebase; the verification result MUST be recorded in the feature's verification artifact.
- **FR-010**: The dev-dependency manifest MUST NOT require a package that is unsatisfiable on the supported native dev platform; the Docker-canonical channel and the host-check skip behavior MUST be documented.
- **FR-011**: Agent-facing instruction files MUST NOT reference artifacts that the installed toolchain cannot produce; the graphify-wiki reference MUST be removed or corrected.
- **FR-012**: No bot production code (handlers, services, middlewares, database, keyboards, web) may be modified by this feature.
- **FR-013**: Documentation updates triggered by these changes MUST follow the established content-ownership rules (rules in RULES.md, description in docs/knowledge/, process in AGENTS.md).

### Key Entities

- **Canonical test invocation**: The one blessed command form for running the suite; referenced by docs, subagent configs, and CI-like gates.
- **Skill registration**: The mapping between a skill's canonical content and the location(s) the harness scans; carries the single-source-of-truth constraint.
- **Agent definition**: Operational registration of a subagent (name, description, tool constraints, prompt); mirrors the descriptive registry in docs/knowledge/subagents.md.
- **Lint gate**: A mandatory automated check in the Route A workflow (prompt-linter stages, semgrep architecture rules, ruff, import-linter).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of test-invocation mentions across governance/reference docs use the canonical form, and that form runs the full suite from a clean shell with zero collection errors.
- **SC-002**: The plan-stage linter produces zero false-positive Cyrillic warnings on the four historical plan documents (specs 001–004) while still flagging a seeded genuine violation.
- **SC-003**: In a fresh session, both Route B/C engine skills and all three subagents appear in their respective availability lists (5/5 registered capabilities, up from 0/5).
- **SC-004**: The semgrep Docker gate completes with a pass on the current codebase, and dev-dependency installation on native Windows completes without a semgrep-related failure.
- **SC-005**: An artifact-reference sweep of agent-facing instruction files finds zero references to non-producible artifacts.
- **SC-006**: `git diff` for the feature touches zero files under the bot's production-code directories.

## Assumptions

- The harness discovery locations are `.claude/skills/` for skills and `.claude/agents/` for agent definitions (per current Claude Code conventions observed in this project — speckit skills under `.claude/skills/` are discovered today).
- The exact single-source mechanism for skill registration (move vs. link vs. documented sync) is a planning-phase decision; the spec constrains only the outcome (discoverable + no silent fork).
- Docker Desktop is available on the dev machine (verified: Docker 29.5.3) and may be started when the semgrep gate runs; the gate remains a dev-side check, not CI (the project has no CI workflows).
- Native Windows is the supported dev platform; WSL/Linux contributors are out of scope for the semgrep-host reconciliation.
- `docs/knowledge/subagents.md` remains the descriptive source of truth for subagent behavior; the new agent definitions operationalize it and must not introduce behavioral deltas beyond fixing the broken test-invocation instruction (FR-008).
- Historical spec directories 001–004 are read-only records and are not edited, even where they mention retired invocation forms; only living governance/reference docs are aligned (FR-002 scope).
- Implementation will be executed on Opus/Sonnet per the operator's workflow; this feature's planning artifacts are prepared in advance and carry HARD-STOP gates for approval.
