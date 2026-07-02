---
type: bundle-index
title: Tenir-Too Knowledge Bundle — Index
description: Progressive-disclosure entry point for the OKF-style reference bundle.
timestamp: 2026-07-02
---

# Tenir-Too Knowledge Bundle

Reference documentation for the project. **Normative rules live in [RULES.md](../../RULES.md);
this bundle holds descriptive reference data only.** Read a concept file on demand when its
topic is relevant to the current task — do not pre-read the whole bundle. Legacy `PL-x.y`/`CP-x.y`
citations resolve via [rule-map.md](rule-map.md).

For the change history of this bundle, see [log.md](log.md).

## Concept files

| File | Type | Description |
|---|---|---|
| [rule-map.md](rule-map.md) | rule-map | Resolves every legacy `PL-x.y`/`CP-x.y` anchor to a rule ID or bundle file. |
| [module-registry.md](module-registry.md) | module-registry | Complete file list with responsibilities and full function inventory (from [PL-2.2]). |
| [db-schema.md](db-schema.md) | db-schema | Full SQLite DDL — tables, foreign keys, indexes (from [PL-3.1]). |
| [subagents.md](subagents.md) | subagents | Full configurations of the three workspace subagents (summarized in AGENTS.md). |
| [architecture.md](architecture.md) | architecture | Stack facts, five-layer decomposition, import graph, connection-manager behavior (from [PL-1], [PL-2.1], [PL-2.3], [PL-2.6]). |
| [middleware.md](middleware.md) | middleware | Four-stage middleware pipeline behavior (from [PL-4]). |
| [fsm-protocol.md](fsm-protocol.md) | fsm-protocol | Sterile Interface UIService mechanics, FSM data keys, callback resilience, Traffic Controller (from [PL-5.1], [PL-5.2], [PL-5.5], [PL-5.6]). |
| [db-patterns.md](db-patterns.md) | db-patterns | FK-integrity fact, upsert pattern, indexes, background Sheets sync (from [PL-3.1.1], [PL-3.3]–[PL-3.5]). |
| [constants.md](constants.md) | constants | Environment-sourced constants — types, sources, usage (from [PL-7]). |
| [testing.md](testing.md) | testing | conftest fixtures, test-category map, Docker dev sandbox (from [PL-8.1], [PL-8.2], [PL-8.4], [PL-8.6]). |
| [features-overview.md](features-overview.md) | feature-detail | Full descriptive feature list (from [CP-2]). |

## Feature details

Per-feature implementation detail files live under [`features/`](features/) and are listed
below as they are added.

| File | Type | Description |
|---|---|---|
| [features/design-system.md](features/design-system.md) | feature-detail | WebApp visual design tokens — palette, typography, glassmorphism (from [CP-4]). |
