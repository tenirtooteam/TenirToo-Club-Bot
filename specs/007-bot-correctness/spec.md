# Feature Specification: Bot Correctness (Correctness Fixes)

**Feature Branch**: `007-bot-correctness`

**Created**: 2026-07-09

**Status**: Draft

**Input**: User description: "Feature 007 «Корректность бота» (Фаза 2, набор баг-фиксов). Пять подтверждённых аудитом багов + хвост уборки. Каждому багу — падающий репро-тест первым (R-PROC-3)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Multi-day hike keeps its real dates (Priority: P1)

A club member creates (or edits) a hike spanning several days, e.g. "10-15 июня". After confirming the recognized date, the hike must retain the **full** human-readable range and its start/end calendar dates. Today the stored start date is silently truncated to a meaningless fragment ("10"), corrupting the event record and any downstream export/calendar.

**Why this priority**: Silent data corruption on a core creation flow — the damage is persistent (written to the database), user-invisible at the moment it happens, and affects the primary product function (organizing hikes). Highest blast radius.

**Independent Test**: Drive the date-confirmation flow with a range input and assert the persisted start date equals the full start portion (not a truncated fragment), and the end date/ISO values are present and correct. Fully testable via the creation and the editing paths in isolation.

**Acceptance Scenarios**:

1. **Given** a member entered "10-15 июня" and the range was recognized, **When** they confirm the date, **Then** the stored human start date is "10 июня" (not "10"), the stored human end date is "15 июня", and both start/end calendar dates are persisted.
2. **Given** a member is editing an existing hike and enters a range "3-7 августа", **When** they confirm, **Then** the updated record holds the full start/end human dates and calendar dates — the confirmation split is actually applied (no discarded computation).
3. **Given** a single-day input "15 мая", **When** confirmed, **Then** start human = "15 мая", end human is empty, end calendar date is empty — no regression for the single-date path.

---

### User Story 2 - Active hikes list is ordered and current (Priority: P2)

A member opens the club hikes list and sees **upcoming** hikes ordered by their actual calendar date (soonest first). Today the list is sorted by raw human text (so "10 июня" sorts before "5 мая"), and hikes whose date has already passed remain in the active list indefinitely.

**Why this priority**: Visible, everyday incorrectness that erodes trust in the list, but non-destructive (no data loss). Ranks below the corruption bug.

**Independent Test**: Seed hikes with mixed calendar dates (some past, some future) and assert the active list returns only current/future hikes, ordered ascending by calendar date. Testable purely at the data-access layer.

**Acceptance Scenarios**:

1. **Given** approved hikes with calendar start dates 2026-05-05, 2026-06-10 and 2026-06-02, **When** the active list is requested, **Then** they appear in calendar order (2026-05-05, 2026-06-02, 2026-06-10), not text order.
2. **Given** an approved hike whose date has fully passed relative to "today", **When** the active list is requested, **Then** that hike is excluded from the active list.
3. **Given** a multi-day hike that started yesterday but ends in the future, **When** the active list is requested, **Then** it is still shown (an ongoing hike is not "past").
4. **Given** an approved hike with no recognizable calendar date, **When** the active list is requested, **Then** it is still shown (undated hikes are not silently dropped) and does not crash sorting.

---

### User Story 3 - Non-text input never crashes an input step (Priority: P2)

While the bot is waiting for a member/admin/moderator to type something (a topic name, a search query, a hike title, hike dates), the user instead sends a photo, sticker, or voice message. The bot must respond with a gentle "please send text" prompt and stay in the same step — it must not crash the handler.

**Why this priority**: Reliability defect that any user can trigger accidentally; a crash aborts the flow and can leave the interaction stuck. Same tier as the race condition.

**Independent Test**: Invoke each affected input handler with a non-text message and assert it returns a graceful "enter text" response without raising, and the awaiting state is preserved. Testable per handler in isolation.

**Acceptance Scenarios**:

1. **Given** the bot is awaiting a topic rename, **When** a non-text message arrives, **Then** the user is asked to send text and no exception is raised.
2. **Given** the bot is awaiting a direct-access user search, **When** a non-text message arrives, **Then** the user is asked to send text and no exception is raised.
3. **Given** the bot is awaiting a search query, **When** a non-text message arrives, **Then** the user is asked to send text and no exception is raised.
4. **Given** the bot is awaiting a hike title or hike dates while editing, **When** a non-text message arrives, **Then** the user is asked to send text and no exception is raised.

---

### User Story 4 - "Leave hike" can only remove, never join (Priority: P3)

A member taps "Leave" on a hike they are not actually a participant of (e.g. from a stale message keyboard). The action must be a no-op (or a clear "you are not participating" message) — it must never enroll them as a participant, because joining a hike requires a request that goes through admin approval. Today "Leave" toggles participation, so a non-participant is silently added, bypassing the approval audit.

**Why this priority**: Integrity/audit-bypass defect, but narrow trigger (stale keyboard) and no data loss. Lowest of the functional fixes.

**Independent Test**: Invoke the leave action as a non-participant and assert participation is not created and the audit/approval path is not bypassed; invoke as a participant and assert removal still works. Testable at the service layer.

**Acceptance Scenarios**:

1. **Given** a user who is NOT a participant of a hike, **When** they trigger "Leave", **Then** they are NOT added as a participant and receive an appropriate message.
2. **Given** a user who IS a participant, **When** they trigger "Leave", **Then** they are removed from the hike.
3. **Given** the approval flow, **When** a user wants to join, **Then** the only way in remains the request→approval path (leave never becomes a back-door join).

---

### User Story 5 - An approval request is resolved exactly once (Priority: P2)

Two admins open the same pending request (hike approval or participation) and both tap approve/reject at nearly the same time. The request must be resolved and acted upon **once**: the second attempt must see it as already handled and produce no duplicate database action and no duplicate user notification.

**Why this priority**: Concurrency/integrity defect that can double-notify users and, for some request types, double-apply effects. Realistic with multiple admins; same tier as the crash fix.

**Independent Test**: Simulate the status check and the resolution as separate steps with an interleaving between them, and assert only the first resolution takes effect (the second reports "already handled"). Testable at the service/data layer via the compare-and-swap behavior.

**Acceptance Scenarios**:

1. **Given** a pending request, **When** two resolutions are attempted concurrently, **Then** exactly one succeeds and performs the DB action + notification; the other reports the request as already processed.
2. **Given** a request already resolved (approved/rejected), **When** a further resolution is attempted, **Then** it is rejected as already handled with no side effects (idempotent).
3. **Given** a resolution that loses the race, **When** it is rejected, **Then** no duplicate participant addition, no duplicate approval, and no second notification are produced.

---

### Edge Cases

- **BUG-1**: Human range text uses a spaced separator (" - ") vs a bare "-"; input where only the end part carries the month ("10-15 июня") vs both parts carry it ("10 июня - 15 июня"). The single stored range string must be decomposed into start/end human parts correctly in both the creation and the editing confirmation paths.
- **BUG-2**: Hikes with an empty/unrecognized calendar date (parser failed) must still appear and must not break ordering; hikes spanning "today" (started, not yet ended) count as active.
- **BUG-3**: The affected awaiting states must gracefully handle any non-text content type (photo, sticker, voice, document, location) — not only "no caption".
- **BUG-5**: A request that was deleted/cancelled between the status read and the write must not be resolved; the compare-and-swap must fail closed.
- **Tail — anonymous sender**: A message with no associated sender (anonymous group admin post, channel post) reaching the stealth-moderation guard must not crash; it should be handled safely rather than raising.
- **Tail — dead code**: Removing no-effect expressions must not change any observable behavior (pure cleanup; covered by the existing/updated suite passing).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** (BUG-1): When a confirmed hike date represents a multi-day range, the system MUST persist the complete human-readable start and end portions (never a truncated fragment) together with the corresponding start and end calendar dates, in BOTH the creation and the editing confirmation flows.
- **FR-002** (BUG-1): When a confirmed hike date is a single day, the system MUST persist the full human date as the start, with no end portion — preserving current single-date behavior.
- **FR-003** (BUG-1): The editing confirmation flow MUST actually apply the start/end decomposition it computes (no discarded/dead computation of the split result).
- **FR-004** (BUG-2): The active hikes list MUST be ordered by the hikes' calendar (ISO) start date ascending, not by raw human text.
- **FR-005** (BUG-2): The active hikes list MUST exclude hikes whose scheduled date has already fully passed relative to the current date, while still including hikes that are ongoing (started but not yet ended) and hikes lacking a recognizable calendar date.
- **FR-006** (BUG-3): Every input-awaiting handler that reads typed text (topic rename, direct-access user search, search query, hike editing title, hike editing dates) MUST gracefully handle a non-text message by prompting the user to send text and remaining in the same awaiting state, without raising an error.
- **FR-007** (BUG-4): The "leave hike" action MUST use remove-only semantics: it MUST NOT create participation for a user who is not already a participant, so it can never bypass the request→approval flow.
- **FR-008** (BUG-4): The "leave hike" action MUST still remove an existing participant successfully.
- **FR-009** (BUG-5): Resolving an approval request MUST be atomic with respect to its pending-status check: the status transition MUST succeed for exactly one resolver, using a conditional update that only applies while the request is still pending.
- **FR-010** (BUG-5): When a resolution attempt does not win the atomic transition (already resolved, cancelled, or lost the race), the system MUST perform no database side effect and no user notification, and MUST report the request as already handled.
- **FR-011** (Tail): The stealth-moderation guard MUST safely handle messages that have no associated sender (anonymous admin / channel posts) without raising.
- **FR-012** (Tail): Identified dead/no-effect code (redundant expressions with no side effect, and the discarded range-split branch) MUST be removed without changing any observable behavior.
- **FR-013** (Process, R-PROC-3): Each of BUG-1..BUG-5 MUST be accompanied by a failing reproducing test written before its fix; the test MUST fail on the current code and pass after the fix.

### Key Entities *(include if feature involves data)*

- **Hike (Event)**: A club outing. Relevant attributes for this feature — human-readable start date text, human-readable end date text, start calendar date (ISO), end calendar date (ISO), approval status. The correctness of the human/ISO date pair and the approval status is the crux of BUG-1, BUG-2, and BUG-5.
- **Participation**: The relationship linking a member to a hike. BUG-4 concerns whether this relationship can be created through the wrong action.
- **Approval Request (Audit Request)**: A pending item an admin approves or rejects. Its status field (pending → approved/rejected) and the atomicity of that transition are the crux of BUG-5.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of multi-day hikes created or edited through the confirmation flow retain their full start/end dates (0 truncated-fragment records), verified by the reproducing tests for both creation and editing paths.
- **SC-002**: The active hikes list is ordered by actual calendar date and contains 0 already-past hikes, across a seeded mix of past/ongoing/future/undated hikes.
- **SC-003**: Sending any non-text message during any of the five affected input steps yields a graceful prompt and 0 handler crashes.
- **SC-004**: The "leave" action creates 0 new participations for non-participants while still removing 100% of genuine participants.
- **SC-005**: Under a simulated concurrent double-resolution, exactly 1 resolution takes effect (1 DB action, 1 notification) and the other is reported as already handled — 0 duplicates.
- **SC-006**: Every one of BUG-1..BUG-5 has a test that demonstrably fails before its fix and passes after (5/5), and the full existing test suite remains green.

## Assumptions

- Calendar/ISO dates are stored in `YYYY-MM-DD` form, making lexicographic and chronological ordering equivalent for the sort in BUG-2 (existing `start_iso`/`end_iso` fields are reused).
- "Already passed" for BUG-2 is evaluated against the server's current date; a hike with an end calendar date is considered past only after its end date, and one with only a start calendar date is past only after that start date. Undated hikes are treated as always-active (never auto-hidden).
- The runtime is a single-process asyncio application over SQLite (WAL); "concurrency" in BUG-5 means interleaving across `await` points rather than OS-thread parallelism, so an atomic conditional UPDATE at the database layer is sufficient to serialize the transition.
- Graceful non-text handling reuses the existing pattern already present in the hike title/dates creation handlers (a "please send text" temporary message), for behavioral consistency.
- The tail cleanup items are pure refactors with no intended behavior change; their safety is demonstrated by the unchanged/passing test suite rather than by new feature tests.
- No database schema changes are required; all needed columns (`start_iso`, `end_iso`, request `status`) already exist.
