# Design: Workflow-dynamic scheduled dispatch

## Context

The repository already has durable coordination Issues, one legal routing tuple, role/action skills, revision-bound evidence, and at-least-once reconstruction. The missing piece is dispatch: external Scheduled Tasks currently wake a fixed role and then perform role-local discovery. #23 accepted a workflow-first mode where the repository's active workflow selects the role while preserving the same lifecycle.

## Goals

- Make dispatch mode explicit and default-branch governed.
- Reuse existing routing and skills rather than build a scheduler/orchestrator subsystem.
- Enforce one active persisted Change while allowing queued Human-admitted proposals.
- Keep overlapping wakes safe without hidden ownership state.
- Make Human authority and escalation reconstructable from durable GitHub evidence.
- Keep Scheduled Task prompts thin and product-independent.
- Make `review-openspec` inspection order deterministic without changing its bidirectional correctness gate.

## Non-goals

- Multi-active workflow arbitration or dependency/conflict graphing.
- Global cross-role/action priority scoring.
- Locks, claims, leases, heartbeat, retry/progress state, or exactly-once execution.
- A generic repository fault classifier or Human wait-state machine.
- Changes to the nine actions, OpenSpec lifecycle, independent Reviewer authority, exact-revision PASS semantics, merge authority, or archive automation.

## Decision 1: One explicit dispatch marker

`agents/AGENTS.md` owns a single marker:

```text
Scheduled-Dispatch-Mode: fixed-role
```

or

```text
Scheduled-Dispatch-Mode: workflow-dynamic
```

The implementation change will switch the canonical marker to `workflow-dynamic` only when the rest of the contract is implemented and tested. No separate config file is introduced because one enum-valued governance decision does not justify a configuration subsystem.

Trace: proposal dispatch-mode change → spec `Default-branch governance declares the scheduled dispatch mode` → implementation slice 1.

## Decision 2: Thin workflow-first dispatch

A dynamic wake performs only enough bootstrap to load default-branch governance, determine mode, reconstruct active workflow identity/routing, and select one role/action/skill. It then executes that role normally. The invocation role is immutable after selection.

This avoids a second DAG: the dispatcher does not understand proposal/review/implementation semantics beyond the existing legal routing tuple. Handoff persists the next tuple and ends the invocation.

Trace: proposal thin dispatcher → specs `Workflow-dynamic dispatch derives one fixed invocation role` and modified selection requirement → slice 1.

## Decision 3: `Change:` persistence is activation

The single-active invariant is defined over open coordination Issues with a valid routing tuple and persisted non-`unset` Change identity. Human-admitted `Lead / propose-change` Issues may queue with `Change: unset`. When no active workflow exists, oldest `created_at`, then lower Issue number selects the next proposal for Lead to activate.

This is deliberately not multi-workflow arbitration: queued proposals are not active changes, and no conflict graph or urgency engine is needed.

Trace: proposal activation boundary → spec `Persisted Change identity defines the single active workflow boundary` → slice 2.

## Decision 4: At-least-once overlap remains the concurrency model

Dynamic wake cadence can cause two invocations to see the same tuple. Scheduled Tasks are not assumed to serialize. Existing reconstruction/idempotency/revision-precondition semantics remain authoritative. Activation and other competing durable writes use first-valid-write-wins behavior where the backing mutation permits it; after any competing write, stale runs re-read and terminate rather than manufacture a second owner.

No lock/lease/claim state is introduced. If future evidence demonstrates these primitives are insufficient, that is a separate OpenSpec change.

Trace: proposal overlap policy → spec `Dynamic dispatch tolerates overlapping wakes without hidden ownership state` → slices 1-2 and regression validation.

## Decision 5: Minimal orphan guard, not fault orchestration

Before activating queued work, dynamic dispatch checks for durable evidence that indicates unresolved workflow work despite no active coordination Issue. The implementation should use the smallest repository-specific evidence set needed to prevent obvious unsafe activation, then route diagnosis to Lead. If classification requires Human judgment, Lead posts one bounded decision-ready escalation.

This guard is not a taxonomy of all repository failures and does not persist generic runtime states.

Trace: proposal orphan handling → spec `Unexplained durable workflow evidence fails closed to Lead diagnosis` → slice 3.

## Decision 6: Human authority is actor-bound

The repository's Human authority is GitHub actor `royhsu-work`. Human-required admission, answers, authorization, and resume decisions must be attributable to that actor. Other actors' comments/reactions/labels may be evidence but cannot cross a Human capability boundary.

`human:notified` may be emitted/maintained for analytics but is never a workflow predicate. Duplicate-notification suppression is based on durable unresolved question/evidence equivalence, not a waiting state machine.

Trace: proposal Human boundary → specs `Human-required authority...` and `Lead Human-facing escalation...` → slice 3.

## Decision 7: Idle advisory adds a seven-day Issue lens

Idle advisory remains Lead-only and bounded. Its research context expands to relevant Issues created or materially active in the preceding seven days. This is an evidence window, not a new queue or routing source.

Trace: proposal idle exploration → spec idle requirements → slice 4.

## Decision 8: Simplicity/proportionality is a governance constraint

Implementation and future workflow changes must justify complexity with current approved requirements or demonstrated failures. Generalized orchestration machinery is explicitly deferred.

Trace: proposal scope boundary → spec proportionality requirement → slice 4 and final review.

## Decision 9: `review-openspec` is reverse-first, while PASS stays bidirectional

Reviewer inspection order is now deterministic: for each exact revision under `review-openspec`, inspect `tasks → design → specs → proposal` first, then inspect `proposal → specs → design → tasks`.

This is deliberately an inspection-order contract rather than a different correctness rule. Reviewer independence and revision binding remain unchanged, and `PASS` still requires both directions to be complete for the same exact revision. Reverse-first must therefore be reflected in Reviewer governance/skill guidance and regression or contract coverage, but it must not be used to waive forward traceability.

Trace: proposal reverse-first review requirement → spec `OpenSpec review uses reverse-first inspection while retaining the bidirectional gate` → implementation slice 4 and OpenSpec completion gate.

## Scheduled Task migration

The three existing external wake slots remain. Their prompts should converge on the same bootstrap contract: read `README.md` and `agents/AGENTS.md`, determine the declared mode, use the legacy assigned role only in `fixed-role`, and in `workflow-dynamic` derive role/action from durable workflow state. Once an invocation selects a role, it never switches role in that run.

Prompt configuration itself is external product state. Repository tests/docs can define the required bootstrap contract but cannot make Scheduled Task conversation/result surfacing part of GitHub workflow state.

## Validation strategy

Behavioral tests should exercise mode parsing, fixed-role compatibility, active-workflow selection, queued proposal activation ordering, invalid/multiple active fail-closed behavior, immutable invocation role, stale competing activation, actor-bound Human evidence, duplicate escalation suppression, seven-day advisory evidence, analytics-only notification metadata, and reverse-first `review-openspec` inspection with unchanged exact-revision bidirectional PASS semantics. Repository quality checks and strict OpenSpec validation remain required.
