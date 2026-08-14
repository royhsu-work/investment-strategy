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
- Ensure workflow-owned temporary integration/recovery branches cannot remain indefinitely after their purpose is consumed without a reconstructable retention reason.

## Non-goals

- no retry engine/counter/backoff state machine;
- no lock, claim, lease, heartbeat, or hidden progress/wait state;
- no branch registry or branch-cleanup daemon;
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

## Decision 7: Temporary recovery branches have an explicit terminal cleanup obligation

**Requirement:** `Workflow-owned temporary recovery branches are safely retired before terminal completion`.

The #25 residue `agent/integrate-main-workflow-dynamic` demonstrates a lifecycle gap distinct from normal feature/archive PR heads. GitHub native delete-on-merge can clean the merged PR head, but it cannot clean a temporary integration/recovery branch that was never the final merged PR head.

The contract therefore distinguishes two classes by durable usage, not by branch-name pattern:

- normal feature/archive PR heads remain governed by their existing PR/native lifecycle;
- a temporary integration/recovery branch is one created as an intermediate recovery/integration surface whose owning workflow, coordination Issue/PR relation, and purpose are reconstructable from durable repository evidence and which is not the normal surviving implementation/archive PR head.

No hidden branch registry is added. Reconstructable ownership comes from existing durable Issue/PR comments, branch/commit ancestry, and the recovery operation evidence that created or adopted the branch.

Cleanup mutation stays with the Executor action that owns the recovery/integration correction when cleanup becomes immediately possible in that action. Lead owns terminal lifecycle verification: before `LIFECYCLE_COMPLETE`, Lead must verify that no still-owned temporary recovery branch is both unused and safely deletable, or that a branch intentionally retained has a durable reconstructable reason and legal next owner. Lead does not delete implementation branches merely because it performs this verification.

Safe deletion requires a fresh read proving all of the following:

1. the branch is still the identified workflow-owned temporary branch;
2. it is not an open PR head or base and is not referenced by active recovery/integration work;
3. its commits are fully contained by canonical `main` or an explicitly retained successor (`ahead_by == 0` or equivalent no-unique-commits proof);
4. no stale comment, naming convention, or historical observation is being used as the sole deletion authority.

No force update/delete may be used to hide unintegrated commits. If unique commits remain or ownership/use is ambiguous, cleanup fails closed and routes to the legal recovery/diagnosis owner. If deletion is blocked by the tool/permission surface, the existing minimum durable evidence and changed-precondition retry rules apply; the workflow does not busy-loop on the same denied delete.

A terminal completion claim with an unused, safely deletable, still workflow-owned temporary recovery branch is incomplete. This makes branch cleanup a bounded lifecycle obligation rather than a repository-wide garbage collector.

## Bounded blast-radius analysis

### Shared governance

Affected: at-least-once reconstruction, async-wait legality, exception disposition, Human-label semantics, and the terminal invariant that workflow-owned temporary recovery obligations must be resolved or durably retained. These rules apply across roles only where they describe shared reconstruction/lifecycle meaning.

### Executor role / implementation skill

Affected: constrained branch-integration procedure, Draft-to-Ready completion boundary, and cleanup of temporary recovery/integration branches created or adopted by Executor when safe-delete preconditions become true. These are implementation/recovery responsibilities and should not be copied into Reviewer procedures.

### Reviewer actions

No new Reviewer authority. Reviewer benefits from receiving a non-Draft implementation PR and from fresh current gate reads after any real wait; independent gate semantics remain unchanged. Reviewer does not delete branches.

### Lead actions

Lead remains the bounded diagnosis owner when an execution failure has no legal local path. Lead owns the `human:notified` producer step because Lead alone persists `HUMAN_DECISION_REQUIRED`, and Lead final lifecycle verification checks that temporary recovery-branch obligations are cleared or have a durable retention reason before `LIFECYCLE_COMPLETE`.

### Merge lifecycle

Exact-head review and `MERGE_AUTHORIZED` semantics remain unchanged. Any branch reconciliation changes the PR head and therefore requires current gate evidence before later authorization. Normal merged implementation/archive PR heads continue to rely on native/PR cleanup; the new terminal check covers only separately created/adopted temporary recovery branches.

## Alternatives considered

### Add retry counters/backoff labels

Rejected. The incidents need changed-precondition reasoning, not persistent retry state. Counters would add another state machine without solving whether a retry is legally meaningful.

### Always require Human for branch conflicts

Rejected. #25 demonstrated a semantics-preserving repository-level reconciliation path can exist. Automatically escalating every integration correction would unnecessarily weaken Executor's implementation ownership.

### Let Reviewer or Lead mark PR Ready

Rejected. Ready is the implementation presentation completion boundary; repairing it later would blur ownership and allow contradictory durable state.

### Use Scheduled Task output as fallback workflow state

Rejected. Product result surfacing is not repository workflow authority and cannot provide at-least-once reconstruction guarantees.

### Delete every `agent/*` branch at lifecycle completion

Rejected. Branch names do not prove ownership, use, or commit containment. Broad deletion would blur normal PR/native cleanup with recovery cleanup and could destroy unique work. Cleanup must be provenance- and containment-based.

## Validation strategy

Implementation should add repository contract tests covering:

1. async-wait resume requires fresh read of the identified resource and stale waiting comments cannot justify another yield;
2. unchanged denied mutation is not repeatedly retried without changed preconditions or a different legal operation path;
3. constrained branch integration remains non-force, head/base precondition-bound, semantics-preserving, and followed by new exact-head gates;
4. no legal integration mutation path routes bounded diagnosis to Lead without weakening gates;
5. implementation review handoff requires current PR `draft == false` and failed Ready transition follows exception/finalization semantics;
6. `HUMAN_DECISION_REQUIRED` idempotently ensures `human:notified`, preserves the label after resolution, and never uses it as routing/waiting/authorization evidence;
7. no writable repository evidence surface does not turn Scheduled Task output into durable workflow state;
8. a workflow-owned temporary recovery branch with no open PR/active recovery use and no unique commits becomes cleanup-eligible, while a branch with unique commits or active use fails closed;
9. blocked temporary-branch deletion preserves minimum durable evidence and is not identically retried without changed preconditions;
10. terminal lifecycle verification rejects `LIFECYCLE_COMPLETE` while an unused safely deletable workflow-owned temporary recovery branch remains, but accepts an intentionally retained branch only with a durable reconstructable reason.

Final verification follows `openspec/config.yaml`: strict OpenSpec validation plus repository quality/lint/type gates after implementation.
