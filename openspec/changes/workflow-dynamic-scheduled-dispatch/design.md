# Design: Workflow-dynamic scheduled dispatch

## Context

The repository already has durable coordination Issues, one legal routing tuple, role/action skills, revision-bound evidence, and at-least-once reconstruction. The missing piece is dispatch: external Scheduled Tasks currently wake a fixed role and then perform role-local discovery. #23 accepted a workflow-first mode where the repository's active workflow selects the role while preserving the same lifecycle.

Implementation history also exposed coordination observability gaps. #21 consistently mirrored verified Executor slices into the persistent coordination Issue, while #25 demonstrated that task markers and PR commits alone can leave the coordination Issue looking unchanged even though implementation progressed. #21 also showed that native Archive PR closing can close the Issue while routing still says `Executor / merge-pr`, making the documented `Lead / finalize-archive` terminal reconstruction unreachable under an open-Issue-only dispatcher.

## Goals

- Make dispatch mode explicit and default-branch governed.
- Reuse existing routing and skills rather than build a scheduler/orchestrator subsystem.
- Enforce one active persisted Change while allowing queued Human-admitted proposals.
- Keep overlapping wakes safe without hidden ownership state.
- Make Human authority and escalation reconstructable from durable GitHub evidence.
- Keep Scheduled Task prompts thin and product-independent.
- Make `review-openspec` inspection order deterministic without changing its bidirectional correctness gate.
- Make each verified Executor slice reconstructable from the persistent coordination Issue as well as PR/task evidence, with one completion-boundary checkpoint rather than per-mutation logging.
- Make material workflow lifecycle ownership/state transitions reconstructable from bounded coordination journals.
- Preserve native Archive PR closing while keeping `Lead / finalize-archive` reachable as the terminal owner and preserving meaningful terminal routing history.

## Non-goals

- Per-commit, per-file, or per-mutation Issue logging inside an implementation slice.
- Multi-active workflow arbitration or dependency/conflict graphing.
- Global cross-role/action priority scoring.
- Locks, claims, leases, heartbeat, retry/progress state, or exactly-once execution.
- A generic repository fault classifier or Human wait-state machine.
- New lifecycle actions, completion/status labels, independent Reviewer authority changes, exact-revision PASS changes, merge-authority changes, or replacement of repository-owned archive automation.

## Decision 1: One explicit dispatch marker

`agents/AGENTS.md` owns a single marker: `Scheduled-Dispatch-Mode: fixed-role | workflow-dynamic`. The implementation change will switch the canonical marker to `workflow-dynamic` only when the rest of the contract is implemented and tested. No separate config file is introduced because one enum-valued governance decision does not justify a configuration subsystem.

Trace: proposal dispatch-mode change → spec `Default-branch governance declares the scheduled dispatch mode` → implementation slice 1.

## Decision 2: Thin workflow-first dispatch

A dynamic wake performs only enough bootstrap to load default-branch governance, determine mode, reconstruct active workflow identity/routing, and select one role/action/skill. It then executes that role normally. The invocation role is immutable after selection.

This avoids a second DAG: the dispatcher does not understand proposal/review/implementation semantics beyond the existing legal routing tuple and the narrow terminal reconstruction exception defined below. Handoff persists the next tuple and ends the invocation.

Trace: proposal thin dispatcher → specs `Workflow-dynamic dispatch derives one fixed invocation role` and modified selection requirement → slice 1.

## Decision 3: `Change:` persistence is activation, with one closed terminal-pending exception

The normal single-active invariant is defined over open coordination Issues with a valid routing tuple and persisted non-`unset` Change identity. Human-admitted `Lead / propose-change` Issues may queue with `Change: unset`. When no active workflow exists, oldest `created_at`, then lower Issue number selects the next proposal for Lead to activate.

One narrow exception preserves terminal reconstruction after native Archive PR close: a closed coordination Issue with persisted Change identity, routing exactly `agent:lead + action:finalize-archive`, an authorized merged Archive PR/native close, and no durable Lead `LIFECYCLE_COMPLETE` evidence for that archive merge remains terminal-pending workflow work. It blocks activation of queued proposals until Lead performs the existing `finalize-archive` reconstruction and records completion evidence. After that bounded Lead completion record exists, the closed tuple is terminal history, is not eligible work, and does not block later admission.

Trace: proposal activation boundary + native-close terminal handoff → specs `Persisted Change identity defines the single active workflow boundary` and `Native Archive close hands off to terminal Lead reconstruction` → slices 2 and 5.

## Decision 4: At-least-once overlap remains the concurrency model

Dynamic wake cadence can cause two invocations to see the same tuple. Scheduled Tasks are not assumed to serialize. Existing reconstruction/idempotency/revision-precondition semantics remain authoritative. Activation and other competing durable writes use first-valid-write-wins behavior where the backing mutation permits it; after any competing write, stale runs re-read and terminate rather than manufacture a second owner.

No lock/lease/claim state is introduced. If future evidence demonstrates these primitives are insufficient, that is a separate OpenSpec change.

Trace: proposal overlap policy → spec `Dynamic dispatch tolerates overlapping wakes without hidden ownership state` → slices 1-2 and regression validation.

## Decision 5: Minimal orphan guard, not fault orchestration

Before activating queued work, dynamic dispatch checks for durable evidence that indicates unresolved workflow work despite no active coordination Issue. The implementation should use the smallest repository-specific evidence set needed to prevent obvious unsafe activation, then route diagnosis to Lead. If classification requires Human judgment, Lead posts one bounded decision-ready escalation.

Trace: proposal orphan handling → spec `Unexplained durable workflow evidence fails closed to Lead diagnosis` → slice 3.

## Decision 6: Human authority is actor-bound

The repository's Human authority is GitHub actor `royhsu-work`. Human-required admission, answers, authorization, and resume decisions must be attributable to that actor. Other actors' comments/reactions/labels may be evidence but cannot cross a Human capability boundary. `human:notified` may be analytics metadata but is never a workflow predicate.

Trace: proposal Human boundary → specs `Human-required authority...` and `Lead Human-facing escalation...` → slice 3.

## Decision 7: Idle advisory adds a seven-day Issue lens

Idle advisory remains Lead-only and bounded. Its research context expands to relevant Issues created or materially active in the preceding seven days. This is an evidence window, not a new queue or routing source.

Trace: proposal idle exploration → spec idle requirements → slice 6.

## Decision 8: Simplicity/proportionality is a governance constraint

Implementation and future workflow changes must justify complexity with current approved requirements or demonstrated failures. Generalized orchestration machinery is explicitly deferred.

Trace: proposal scope boundary → spec proportionality requirement → slice 6 and final review.

## Decision 9: `review-openspec` is reverse-first, while PASS stays bidirectional

Reviewer inspection order is now deterministic: for each exact revision under `review-openspec`, inspect `tasks → design → specs → proposal` first, then inspect `proposal → specs → design → tasks`. PASS still requires both directions to be complete for the same exact revision.

Trace: proposal reverse-first review requirement → spec `OpenSpec review uses reverse-first inspection while retaining the bidirectional gate` → implementation slice 6 and OpenSpec completion gate.

## Decision 10: Verified slices journal exactly one bounded coordination checkpoint

After a vertical implementation slice reaches successful `VERIFY`, Executor must persist the satisfied task markers and exactly one bounded comment on the persistent coordination Issue before beginning another slice or handing off. The comment records completed slice/task IDs, verified/checkpoint revision, required gate result, and remaining work or handoff.

The Issue comment is not a second source of truth for code or task completion. PR commits and task markers remain the detailed implementation evidence. RED/GREEN/refactor/test-trigger/compatibility-correction commits and ordinary artifact/task edits inside the same not-yet-complete slice do not independently require Issue comments. If markers are durable but the Slice checkpoint was interrupted, a later Executor run repairs only the missing checkpoint from durable evidence before continuing.

Trace: proposal verified-slice checkpoint requirement → spec `Verified implementation slices persist a bounded coordination-Issue checkpoint` → implementation slice 4.

## Decision 11: Journal material lifecycle transitions, not every mutation

Coordination-Issue journaling has a separate lifecycle boundary. A Scheduled Agent records one bounded journal entry when it completes a material workflow lifecycle transition that changes durable workflow ownership/state: routing handoff, PR merge, Archive native close/post-merge terminal handoff, Lead `LIFECYCLE_COMPLETE`, or Human escalation/specification-resolution boundary.

Related low-level writes within one legal lifecycle transition are summarized by that one journal entry. Ordinary implementation mutations remain in Git/PR/task evidence and are surfaced to the coordination Issue only by Decision 10 after successful Slice VERIFY. This prevents the Issue from becoming a duplicate commit/activity log while preserving reconstructable ownership transitions.

If a lifecycle transition succeeds but its journal write is interrupted, a later eligible run reconstructs the durable transition and repairs only the missing journal before a later lifecycle transition or handoff; it does not replay a completed unsafe mutation.

Trace: proposal lifecycle-transition journal requirement → spec `Material workflow lifecycle transitions are journaled on the coordination Issue` → implementation slice 5.

## Decision 12: Native Archive close hands off to Lead on the closed Issue

The final Archive PR keeps repository-approved `Closes #N` linkage. Executor still owns only the authorized merge mutation. After merge succeeds, Executor fresh-reads the PR and coordination Issue. When the Archive PR is durably merged and the Issue is observed natively closed, Executor replaces the consumed `Executor / merge-pr` labels with `Lead / finalize-archive` even though the Issue is closed, then records the bounded merge/native-close/handoff lifecycle journal. Invocation role remains Executor and ends after that handoff.

The dispatcher admits exactly one closed-Issue exception: `closed + agent:lead + action:finalize-archive` with a matching authorized merged Archive PR and no durable Lead `LIFECYCLE_COMPLETE` result for that merge. Lead reconstructs canonical archived default-branch state, confirms expected native closure and exact archive evidence, and records one bounded `LIFECYCLE_COMPLETE` result comment. After that result exists, later wakes treat the tuple as completed terminal history.

If merge succeeded and native close happened but Executor was interrupted before relabel/comment, later reconstruction repairs only the missing post-merge terminal handoff/journal after proving exact authorized archive merge and native closure; it must not re-merge.

Trace: proposal native-close terminal handoff → specs `Native Archive close hands off to terminal Lead reconstruction` and modified work-selection/active-workflow requirements → implementation slice 5.

## Scheduled Task migration

The three existing external wake slots remain. Their prompts should converge on the same bootstrap contract: read `README.md` and `agents/AGENTS.md`, determine the declared mode, use the legacy assigned role only in `fixed-role`, and in `workflow-dynamic` derive role/action from durable workflow state. Once an invocation selects a role, it never switches role in that run.

Prompt configuration itself is external product state. Repository tests/docs can define the required bootstrap contract but cannot make Scheduled Task conversation/result surfacing part of GitHub workflow state.

## Validation strategy

Behavioral tests should exercise mode parsing, fixed-role compatibility, active-workflow selection, queued proposal activation ordering, invalid/multiple active fail-closed behavior, immutable invocation role, stale competing activation, actor-bound Human evidence, duplicate escalation suppression, seven-day advisory evidence, analytics-only notification metadata, reverse-first `review-openspec` inspection with unchanged exact-revision bidirectional PASS semantics, verified-Slice checkpoint persistence/recovery with no per-mutation implementation logging, lifecycle-transition journal recovery, native Archive close followed by closed-Issue `Lead / finalize-archive` handoff, terminal candidate selection before Lead completion evidence, and terminal exclusion after bounded `LIFECYCLE_COMPLETE` evidence. Repository quality checks and strict OpenSpec validation remain required.
