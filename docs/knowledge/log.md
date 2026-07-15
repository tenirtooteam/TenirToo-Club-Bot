# Knowledge Bundle — Change Log

Chronological history of the OKF-style reference bundle. Newest entries at the bottom.

- 2026-07-02 — module-registry.md — extracted from PROJECT_LOGIC.md [PL-2.2] (imperative [PL-2.2.50] retained in core).
- 2026-07-02 — db-schema.md — extracted from PROJECT_LOGIC.md [PL-3.1] (constraint fact [PL-3.1.1] retained in core).
- 2026-07-02 — index.md, log.md — bundle skeleton created.
- 2026-07-02 — CONTEXT_PROMPT.md [CP-3] — repaired merge corruption at CP-2/CP-3 boundary; restored standalone `## [CP-3]` heading.
- 2026-07-02 — CONTEXT_PROMPT.md [CP-3.6]/[CP-3.7] — deduplicated against PROJECT_LOGIC [PL-4.5]/[PL-6.12] and [PL-6.1]/[PL-6.2]/[PL-6.18]; full rules stay in PROJECT_LOGIC, CP cites indices.
- 2026-07-02 — CONTEXT_PROMPT.md [CP-2] — compressed feature list to one line per feature (rule CP-2.2); detail retained in PROJECT_LOGIC/bundle.
- 2026-07-02 — features/design-system.md — extracted from CONTEXT_PROMPT.md [CP-4] (visual design tokens, reference data).
- 2026-07-02 — rule-map.md — created (feature 002): resolves 295 legacy PL/CP anchors to R-IDs (138) or bundle files (157).
- 2026-07-02 — subagents.md — created (feature 002): full subagent configs moved verbatim from the old AGENTS.md.
- 2026-07-02 — architecture.md, middleware.md, fsm-protocol.md, db-patterns.md, constants.md, testing.md, features-overview.md — created (feature 002, Chunk 2): dissolution of PROJECT_LOGIC.md/CONTEXT_PROMPT.md descriptive content per research.md D6 map.
- 2026-07-03 — RULES.md — added R-ARCH-9, R-UI-12, R-UI-13 (feature 003, audit F-1: rules PL-4.1/CP-3.11/CP-3.47 were lost during 002 consolidation, restored verbatim from git history at `8280d6f^`); amended R-PROC-2 with the CP-3.28.2 incremental-updates principle.
- 2026-07-03 — rule-map.md — repaired 30 rows (feature 003, audit F-1/F-2): 24 D2-table anchors + 6 additional anchors that fell back to `docs/knowledge/index.md`; zero index.md fallback rows remain; CP-5.1 marked retired (scope note obsolete after the 002 file split).
- 2026-07-04 — graph.md — created (feature 004): knowledge-graph usage guide — query/path/explain + rebuild commands, the two freshness channels (code=post-commit hook, docs/semantic=docs-update skill), CLI-absent fallback; supports R-PROC-12.
- 2026-07-14 — module-registry.md, fsm-protocol.md, testing.md, features-overview.md — updated (feature 011): registered the new leaf module `callbacks.py` (single source of truth for callback format, incl. the deliberate `HelpCB` `sep="|"` quirk and why it must not be unified); rewrote the `generic_navigator` entry for the `str | CallbackData` signature, the exact-match registry resolution order and the removal of `PAGINATED_CMDS`; documented the characterized FSM-reset asymmetry (top-level lists reset, detail cards do not) so it is not "evened out" later; added the four-file callback-routing test layer with the format-agnostic harness rationale.
- 2026-07-14 — RULES.md — added R-UI-14 (feature 011): single source of truth for callback format — one CallbackData declaration per parameterized route, `.pack()` on the producer side, `Factory.filter()` on the consumer side, pagination as a declared field; hand-assembling parameterized callback data is prohibited. Amended R-UI-3 (navigator accepts `str | CallbackData`; Defensive Routing now spells out exact-match lookup and by-name parameter access) and R-UI-11 (defensive parsing is the filter's duty; truncating callback data to fit 64 bytes is prohibited — overflow must fail loudly at build time). **ID note**: R-UI-13 was already taken (feature 003, Admin-creation UX branching) — the new rule took the next free ID rather than reusing it.
