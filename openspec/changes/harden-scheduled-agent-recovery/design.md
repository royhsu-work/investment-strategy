# Design: Scheduled-agent recovery hardening

## Context

The #25 workflow demonstrated that the current at-least-once model is fundamentally sound, but several failures occurred at ownership boundaries rather than inside the main lifecycle DAG. The repository already has shared reconstruction, work-conserving execution, canonical exception capture, exact-head gates, and bounded Lead diagnosis. This change therefore extends those contracts rather than introducing new runtime state.

The authoritative incident set is #28 plus its Human-authored additions, with source durable evidence in #25 / PR #26 / Archive PR #33.

## Goals

- Make constrained execution failures converge to a reconstructable legal owner/action.
- Prevent stale asynchronous-wait evidence from causing avoidable scheduled no-op/yield behavior.
- Prevent repeated identical denied mutations when no outcome-changing precondition has changed.
- Keep branch-integration recovery inside Executor authority when semantics are unchanged and the mutation is safely verifiable.
- Align GitHub PR Draft/Ready presentation state with the implementation-review lifecycle boundary.
- Make Human escalation observability consistently produced without turning `human:notified` into workflow state.

## Non-goals

- no retry engine/counter/backoff state machine;
- no lock, claim, lease, heartbeat, or hidden progress/wait state;
- no new workflow action/result enum solely for tooling failures;
- no weakening of independent review, exact-head validation, or merge authorization;
- no broad documentation/SSOT restructuring owned by #29.

## Decision 1: Async-wait resume belongs in shared reconstruction governance

**Requirements:** `External asynchronous waits are revalidated from the awaited resource`; modified `Scheduled execution is at-least-once and state reconstructable`.

A real asynchronous wait is a legal invocation termination boundary only while the awaited condition is actually unresolved. Because the same stale-evidence failure pattern can affect Lead waiting for archive/validation automation, Reviewer waiting for gates, and Executor waiting for mergeability or checks, the rule belongs once in shared reconstruction governance rather than in one Lead skill.

A resumed wake must fresh-read the specific awaited resource. The workflow does not poll continuously; it performs one normal reconstruction read per wake. Historical `in_progress` evidence remains useful provenance but is not current status authority.

## Decision 2: Retry eligibility is evidence-based, not counter-based

**Requirement:** modified `Catchable execution exceptions are dispositioned before normal invocation exit`.

The workflow does not need a retry counter. It needs a legality test: retry the same operation only when a fresh-read material precondition changed in a way that can alter the outcome, or use a different legal operation surface. Otherwise preserve the exception/result evidence and converge to the current action's disposition or bounded Lead diagnosis.

This keeps the existing work-conserving contract intact: recoverable work still continues immediately, while unchanged hard/tool boundaries do not create busy-loop behavior.

## Decision 3: Constrained branch integration stays Executor-owned when semantics do not change

**Requirement:** `Constrained branch integration preserves reviewed semantics and fail-closed gates`.

The #25 conflict incident showed that a restricted environment may still expose repository-level primitives capable of constructing a two-parent/non-force reconciliation commit and moving a branch ref even when ordinary local git merge/rebase is unavailable.

Executor may use such a path only after fresh-reading the implementation head and default-branch head and only when the resulting tree/commit can be verified as a pure integration correction under the approved OpenSpec meaning. Any new head invalidates exact-head implementation readiness evidence and must obtain new current gates/review as required.

If the available mutation surface cannot safely complete the correction, the failure is no longer ordinary implementation progress. Executor captures the observable failure and hands bounded diagnosis to Lead. Lead does not perform the implementation mutation itself.

## Decision 4: Minimum durable fallback reuses existing repository evidence surfaces

**Requirement:** modified `Scheduled execution is at-least-once and state reconstructable`.

There is no new fallback state store. When a normal mutation/result/handoff step partly fails, the role records what actually completed through the existing canonical action/result/`EXECUTION_EXCEPTION`/`HANDOFF` surfaces while any legal repository write surface remains available.

If no repository surface can be written, external Scheduled Task output may inform Human observation but is explicitly non-authoritative. The next wake reconstructs from actual Issue labels, PR/branch state, OpenSpec state, Actions, and durable comments that did succeed.

This preserves the repository as the only workflow state authority.

## Decision 5: Executor owns Draft-to-Ready before implementation review

**Requirement:** `Implementation PR is Ready before implementation review handoff`.

Draft status describes whether the implementation PR is being presented as ready for independent implementation review. Therefore the narrowest correct ownership layer is the end of `Executor / implement-change`, before routing to Reviewer.

Reviewer should not need to repair presentation state, and Lead should not issue merge authorization for a PR that never completed its implementation-ready transition. A failed Ready mutation is an execution failure handled before handoff.

This decision intentionally does not add Ready state as a new routing label or workflow action.

## Decision 6: `human:notified` is produced by Lead escalation but remains analytics-only

**Requirement:** `Human escalation creates analytics-only notified observability`.

Only Lead may emit canonical `HUMAN_DECISION_REQUIRED`; therefore Lead is the producer that idempotently ensures `human:notified` immediately after durable escalation evidence. The shared governance continues to define the label as analytics-only so every action interprets it consistently.

The label is historical observability and is not cleared on ordinary resolution. Current waiting/resume semantics remain expressed by routing and durable Human-decision evidence. If the label mutation fails, the already-durable escalation remains authoritative and the failure follows the ordinary exception/disposition contract.

## Bounded blast-radius analysis

### Shared governance

Affected: at-least-once reconstruction, async-wait legality, exception disposition, and Human-label semantics. These rules apply across all roles because stale external evidence and denied mutations are not action-specific failure classes.

### Executor role / implementation skill

Affected: constrained branch-integration procedure and the Draft-to-Ready completion boundary. These are implementation-action responsibilities and should not be copied into Lead/Reviewer procedures.

### Reviewer actions

No new Reviewer authority. Reviewer benefits from receiving a non-Draft implementation PR and from fresh current gate reads after any real wait; independent gate semantics remain unchanged.

### Lead actions

Lead remains the bounded diagnosis owner when an execution failure has no legal local path. Lead also owns the `human:notified` producer step because Lead alone persists `HUMAN_DECISION_REQUIRED`.

### Merge lifecycle

Exact-head review and `MERGE_AUTHORIZED` semantics remain unchanged. Any branch reconciliation changes the PR head and therefore requires current gate evidence before later authorization.

## Alternatives considered

### Add retry counters/backoff labels

Rejected. The incidents need changed-precondition reasoning, not persistent retry state. Counters would add another state machine without solving whether a retry is legally meaningful.

### Always require Human for branch conflicts

Rejected. #25 demonstrated a semantics-preserving repository-level reconciliation path can exist. Automatically escalating every integration correction would unnecessarily weaken Executor's implementation ownership.

### Let Reviewer or Lead mark PR Ready

Rejected. Ready is the implementation presentation completion boundary; repairing it later would blur ownership and allow contradictory durable state.

### Use Scheduled Task output as fallback workflow state

Rejected. Product result surfacing is not repository workflow authority and cannot provide at-least-once reconstruction guarantees.

## Validation strategy

Implementation should add repository contract tests covering:

1. async-wait resume requires fresh read of the identified resource and stale waiting comments cannot justify another yield;
2. unchanged denied mutation is not repeatedly retried without changed preconditions or a different legal operation path;
3. constrained branch integration remains non-force, head/base precondition-bound, semantics-preserving, and followed by new exact-head gates;
4. no legal integration mutation path routes bounded diagnosis to Lead without weakening gates;
5. implementation review handoff requires current PR `draft == false` and failed Ready transition follows exception/finalization semantics;
6. `HUMAN_DECISION_REQUIRED` idempotently ensures `human:notified`, preserves the label after resolution, and never uses it as routing/waiting/authorization evidence;
7. no writable repository evidence surface does not turn Scheduled Task output into durable workflow state.

Final verification follows `openspec/config.yaml`: strict OpenSpec validation plus repository quality/lint/type gates after implementation.
