# Data Model: OKF Reference Bundle

**Date**: 2026-07-02. Entities are markdown documents and their machine-readable structures; there is no database involvement.

## Entity: Concept File

A markdown file in `docs/knowledge/` (or `docs/knowledge/features/`) holding exactly one reference topic.

**Front matter (YAML, required at top of file)**:

| Field | Type | Required | Constraint |
|---|---|---|---|
| `type` | string | yes | Non-empty. Vocabulary for this repo: `db-schema`, `module-registry`, `feature-detail` |
| `title` | string | yes | Human-readable topic name |
| `description` | string | yes | One sentence; reused verbatim as the index entry description |
| `source_anchor` | string | when extracted from core | Originating index, e.g. `PL-3.1`, `CP-2.22` |
| `timestamp` | string | yes | ISO 8601 date of last content change |
| `tags` | list of strings | no | Free-form |

**Body**: The extracted content, unchanged where possible (lossless move). No imperative statements — those stay in core files by the classification criterion.

**Validation rules** (enforced by `tests/test_knowledge_bundle.py`):
- Front matter parses; `type`, `title`, `description`, `timestamp` non-empty.
- File is listed in `index.md`.

## Entity: Bundle Index (`docs/knowledge/index.md`)

Progressive-disclosure entry point; the only bundle file included in the mandatory Route A pre-read.

**Structure**: One markdown table (or list) row per concept file: relative path, `type`, one-line description (mirrors front matter `description`).

**Validation rules**:
- Every concept file on disk has exactly one index entry (no orphans).
- Every index entry resolves to an existing file (no dangling entries).

## Entity: Bundle Log (`docs/knowledge/log.md`)

Chronological, append-only history of bundle changes: `YYYY-MM-DD — <file> — <one-line change summary>`.

**Validation rules**: File exists and is non-empty after migration (contains at least the initial extraction entries).

## Entity: Anchor Stub (in `PROJECT_LOGIC.md`)

A preserved heading for an extracted section.

**Structure**:

```text
### [PL-x.y] <Original Section Title>
<One-line summary of what the section contains.>
> Moved to docs/knowledge/<file>.md — read on demand.
```

**Validation rules**:
- The set of `[PL-x.y]` anchors in post-migration `PROJECT_LOGIC.md` is a superset of the pre-migration set (captured as a frozen list inside the test module).
- Every `docs/knowledge/...` path referenced from a core file exists on disk.

## Entity: Core File (post-migration `PROJECT_LOGIC.md`, `CONTEXT_PROMPT.md`)

**Invariants**:
- Contains every pre-migration imperative statement verbatim (rule inventory diff, SC-002).
- Contains no copy of content that lives in a concept file (one-sentence summaries in stubs are permitted).
- `CONTEXT_PROMPT.md` contains no `refer to **PROJ##` fragment; `## [CP-3]` renders as a standalone heading; each `CP-2` entry is a single line.
- Duplicated rule pairs resolved: full text in the authoritative file, index citation in the other (`CP-3.6`↔`PL-4.5`; `CP-3.7`↔`PL-6.2`/`PL-6.18`).

## Relationships

```text
Core File 1 ──(anchor stub)──▶ Concept File
Bundle Index ──(entry)──▶ Concept File          (1:1, bidirectional consistency)
Bundle Log ──(append entry)──▶ Concept File     (1:N over time)
Knowledge Graph (graphify-out/) ──derives from──▶ Core Files + Concept Files + Source Code
```

## State Transitions

Concept file lifecycle: `extracted` (initial migration, logged) → `updated` (via docs-update skill CMD-1/CMD-2, logged) → `retired` (content merged elsewhere; index entry removed, log entry added, stub in core updated). No other states.
