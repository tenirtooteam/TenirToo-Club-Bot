---
type: bundle-index
title: Tenir-Too Knowledge Bundle — Index
description: Progressive-disclosure entry point for the OKF-style reference bundle.
timestamp: 2026-07-02
---

# Tenir-Too Knowledge Bundle

Reference documentation extracted from the normative core files (`PROJECT_LOGIC.md`,
`CONTEXT_PROMPT.md`). **Normative rules stay in the core files; this bundle holds
descriptive reference data only.** Read a concept file on demand when its topic is
relevant to the current task — do not pre-read the whole bundle.

For the change history of this bundle, see [log.md](log.md).

## Concept files

| File | Type | Description |
|---|---|---|
| [module-registry.md](module-registry.md) | module-registry | Complete file list with responsibilities and full function inventory (from [PL-2.2]). |
| [db-schema.md](db-schema.md) | db-schema | Full SQLite DDL — tables, foreign keys, indexes (from [PL-3.1]). |

## Feature details

Per-feature implementation detail files (extracted from oversized `CP-2` entries)
live under [`features/`](features/) and are listed below as they are added.

| File | Type | Description |
|---|---|---|
| [features/design-system.md](features/design-system.md) | feature-detail | WebApp visual design tokens — palette, typography, glassmorphism (from [CP-4]). |
