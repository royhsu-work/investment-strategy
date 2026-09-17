# scheduled-agent-workflow Delta Specification

## ADDED Requirements

### Requirement: External asynchronous waits are revalidated from the awaited resource

When a scheduled invocation resumes work that previously yielded because a specific external asynchronous resource was not yet complete, the selected action SHALL fresh-read that awaited resource before concluding that the wait still exists.

A prior coordination-Issue comment, checkpoint, or summarized observation that recorded the resource as `in_progress`, pending, or unavailable MUST be treated as historical evidence only and MUST NOT by itself justify another asynchronous-wait yield.

If the fresh-read resource shows that the awaited condition has resolved and the selected role/action has immediately actionable work under current routing and preconditions, the invocation MUST continue that work under the shared work-conserving contract.

This requirement MUST NOT create a polling loop, heartbeat, retry counter, hidden waiting state, or scheduler-side workflow state.

#### Scenario: Prior waiting evidence is stale after Actions completion

- GIVEN a selected action previously yielded because an identified GitHub Actions run was still in progress
- AND a durable coordination comment still describes that run as in progress
- WHEN a later scheduled invocation reconstructs the same action
- THEN it fresh-reads the identified Actions run before deciding whether the wait still exists
- AND the older progress comment is not treated as authoritative current status

#### Scenario: Awaited gate has completed successfully

- GIVEN a later wake fresh-reads the specific awaited validation run
- AND the run is now completed successfully for the required revision
- AND routing and other preconditions remain current
- WHEN the selected action evaluates continuation
- THEN the prior async-wait boundary no longer applies
- AND the action continues its immediately actionable work in the same invocation

### Requirement: Constrained branch integration preserves reviewed semantics and fail-closed gates

When `Executor / implement-change` must reconcile its implementation branch with a newer default branch, Executor SHALL treat any constrained-tool reconciliation as an implementation correction and MAY use a repository mutation path that does not require ordinary local git merge/rebase tooling only when the operation is non-force, its source head and current default-branch base are fresh-read and still current, and the resulting commit/tree can be verified to preserve the intended approved implementation semantics.

Such reconciliation MUST remain implementation-owned and MUST NOT redefine OpenSpec requirements, bypass independent Reviewer coverage, weaken exact-head validation, or manufacture merge authorization.

If no available repository-governed mutation surface can safely perform the required reconciliation, Executor MUST preserve the observable execution failure and converge to bounded `Lead / resolve-question` diagnosis under the existing exception/finalization contract instead of repeatedly attempting an unchanged rejected operation or weakening gates.

#### Scenario: Non-force reconciliation is available through constrained tooling

- GIVEN Executor owns the current implementation action
- AND the implementation PR requires integration with a newer default branch
- AND a repository mutation surface can construct and move the branch to a non-force reconciliation commit using the still-current implementation head and default-branch head
- WHEN Executor performs the correction
- THEN the resulting branch ancestry is reconciled without force update
- AND approved implementation semantics remain unchanged unless separately authorized
- AND all exact-head quality/review readiness evidence must be obtained for the resulting new head

#### Scenario: No legal constrained integration path exists

- GIVEN branch integration is required before implementation can become review-ready
- AND ordinary local git integration is unavailable
- AND available repository mutation surfaces cannot safely complete the correction under current preconditions
- WHEN Executor evaluates recovery
- THEN it records the catchable execution evidence when possible
- AND does not weaken revision-bound review or merge gates
- AND hands bounded unresolved diagnosis to `Lead / resolve-question`

### Requirement: Implementation PR is Ready before implementation review handoff

Before `Executor / implement-change` hands an implementation PR to `Reviewer / review-implementation`, the current implementation PR SHALL be open and non-Draft at the exact handoff head.

Executor owns the Draft-to-Ready transition as part of completing implementation presentation state. If the transition cannot be performed because the mutation is denied, unsupported, stale, or otherwise fails, the action MUST process that failure through the existing catchable-exception/finalization contract and MUST NOT claim implementation readiness.

Reviewer implementation PASS and Lead merge authorization MUST NOT be used to paper over a Draft implementation PR that never completed the required Ready transition.

#### Scenario: Executor completes implementation readiness

- GIVEN all approved implementation work and required exact-head gates are complete for PR head R
- AND the PR is still Draft
- WHEN Executor prepares the `review-implementation` handoff
- THEN Executor marks the PR Ready for review
- AND fresh-read PR state is non-Draft at head R before the handoff is completed

#### Scenario: Ready transition fails

- GIVEN implementation work is otherwise ready for review
- AND the PR remains Draft
- WHEN the Draft-to-Ready mutation is denied or unavailable
- THEN Executor does not hand the PR to Reviewer as implementation-ready
- AND it preserves the observable failure and follows the legal recovery/diagnosis path

### Requirement: Human escalation creates analytics-only notified observability

After Lead durably records a canonical `HUMAN_DECISION_REQUIRED` escalation, Lead SHALL idempotently ensure the coordination Issue has the `human:notified` label when the repository label mutation surface is available.

`human:notified` SHALL remain historical/analytics observability metadata only. Its presence or absence MUST NOT determine routing, waiting, authorization, resume eligibility, active-workflow identity, or whether Human has answered. A later Human answer or workflow resumption SHOULD NOT remove the label merely because the escalation was resolved.

Failure to add the analytics label MUST NOT erase or invalidate already-durable `HUMAN_DECISION_REQUIRED` evidence. The label mutation failure SHALL be handled through the same execution-exception/minimum-evidence rules without repeated unchanged retries.

#### Scenario: Escalation evidence exists and label is absent

- GIVEN Lead has durably persisted `HUMAN_DECISION_REQUIRED`
- AND `human:notified` is absent
- WHEN Lead completes the escalation boundary
- THEN it idempotently adds `human:notified`
- AND routing/authorization semantics remain unchanged

#### Scenario: Historical notified label remains after Human response

- GIVEN `human:notified` was added for an earlier durable Human escalation
- AND authoritative Human activity later resolves the decision
- WHEN workflow routing advances
- THEN the label MAY remain as historical observability metadata
- AND current routing/evidence, not the label, determines whether Human input is still pending

#### Scenario: Notified label alone does not create waiting state

- GIVEN a coordination Issue has `human:notified`
- AND no current durable Human-decision-required routing/evidence applies
- WHEN a scheduled role reconstructs the workflow
- THEN it does not infer that the workflow is waiting for Human merely from the label

### Requirement: Workflow-owned temporary recovery branches are safely retired before terminal completion

A temporary integration/recovery branch created or adopted as an intermediate workflow recovery surface SHALL have reconstructable workflow ownership and purpose from existing durable repository evidence. Branch naming alone MUST NOT establish temporary-branch identity or deletion authority, and this requirement MUST NOT introduce a hidden branch registry or second workflow state store.

Normal feature and archive PR heads SHALL continue to use their existing PR/native branch lifecycle. This cleanup contract applies only to a separately workflow-owned temporary recovery/integration branch that is not the normal surviving implementation/archive PR head.

Before deleting such a temporary branch, the responsible action MUST fresh-read branch, PR, and workflow state and MUST verify that the branch is not an open PR head or base, is not still referenced by active recovery/integration work, and has no commits outside canonical `main` or an explicitly retained successor branch. An `ahead_by == 0` comparison or equivalent no-unique-commits proof MAY satisfy the containment check. Stale observations, branch-name patterns, or an assumption that the workflow is finished MUST NOT by themselves authorize deletion.

A force update/delete MUST NOT be used to hide unintegrated commits. If unique commits remain, branch ownership/use is ambiguous, or the branch is still active input, cleanup MUST fail closed and preserve the branch while routing to the legal recovery/diagnosis owner.

If a temporary-branch delete mutation is denied, unsupported, or unavailable, the action MUST preserve minimum durable evidence and apply the same evidence-based no-identical-retry rule as other constrained mutations.

Before Lead persists terminal `LIFECYCLE_COMPLETE`, Lead SHALL verify that no temporary branch still owned by that workflow is both unused and safely deletable. An intentionally retained branch is compatible with terminal completion only when a durable reconstructable reason and legal ownership/next disposition remain recorded. Lead's verification MUST NOT grant Lead authority to perform Executor-owned implementation/recovery branch mutations.

#### Scenario: Temporary integration branch becomes cleanup-eligible

- GIVEN a workflow-owned temporary integration branch is no longer an open PR head/base or active recovery input
- AND a fresh comparison proves it has no commits not already contained in canonical `main`
- WHEN the responsible recovery action evaluates terminal cleanup
- THEN the branch is eligible for non-force deletion
- AND deletion is not authorized merely by its name or an older progress comment

#### Scenario: Temporary branch still has unique commits

- GIVEN a workflow-owned temporary recovery branch still contains commits not present in canonical `main` or an explicitly retained successor
- WHEN cleanup is evaluated
- THEN the branch is not deleted
- AND the workflow fails closed to the legal recovery/diagnosis owner rather than using force deletion

#### Scenario: Temporary branch remains active workflow input

- GIVEN a temporary branch is still an open PR head/base or is referenced by active recovery/integration work
- WHEN cleanup is evaluated
- THEN the branch is retained
- AND terminal cleanup does not treat it as unused

#### Scenario: Cleanup mutation is blocked by restricted tooling

- GIVEN all safe-delete preconditions are satisfied
- AND the repository branch-delete mutation is denied or unavailable
- WHEN the responsible action handles the failure
- THEN it preserves the cleanup obligation and observable minimum durable evidence
- AND it does not repeatedly attempt the identical delete without a materially changed precondition or different legal operation surface

#### Scenario: Terminal completion checks unresolved temporary residue

- GIVEN Lead is preparing to persist `LIFECYCLE_COMPLETE`
- AND a branch remains durably attributable to the workflow as a temporary recovery branch
- WHEN Lead reconstructs terminal state
- THEN Lead verifies whether the branch is still needed, safely deleted, or durably retained for a stated reason
- AND Lead does not claim lifecycle completion while an unused safely deletable temporary branch remains without disposition

## MODIFIED Requirements

### Requirement: Scheduled execution is at-least-once and state reconstructable

Every scheduled action SHALL reconstruct relevant durable repository, Issue, PR, OpenSpec, GitHub Actions, and any specifically awaited external resource state before deciding what remains to be done.

The workflow MUST NOT require previous conversation memory or a previous scheduled run to have exited cleanly.

Partial execution, interruption, tool failure, or missing final response MUST NOT transfer ownership merely because some work was attempted.

When a prior operation failed after only some durable mutations completed, recovery SHALL distinguish observed durable mutations from intended-but-uncompleted work. If the current invocation can still write repository evidence, it SHALL preserve the existing canonical action/result/`EXECUTION_EXCEPTION`/`HANDOFF` evidence required by the owning action. If no repository evidence surface is writable, the run MUST NOT manufacture a durable workflow transition from external Scheduled Task output; a later wake SHALL reconstruct correctness from the repository state that actually exists.

#### Scenario: Run stops after durable work but before handoff

- GIVEN a scheduled role completes durable action work
- AND the run terminates before routing changes
- WHEN a later run observes the same routing tuple
- THEN it reconstructs whether the durable action work already exists
- AND it performs only remaining legal work or the missing handoff
- AND it does not require memory of the previous run

#### Scenario: Normal evidence write itself is unavailable

- GIVEN a catchable execution failure occurs
- AND the current invocation cannot write the normal coordination-Issue evidence surface
- WHEN no other repository-governed durable evidence surface is legally available
- THEN the invocation does not claim that a result, handoff, or ownership transfer became durable merely because external Scheduled Task output exists
- AND a later wake reconstructs from actual repository mutations and current routing

### Requirement: Catchable execution exceptions are dispositioned before normal invocation exit

After a catchable execution exception is durably captured, the selected role/action SHALL determine whether the failure can be legally recovered within the same authority while routing, revision/preconditions, and execution context remain current.

If local recovery is legal and immediately actionable, the role MUST perform that recovery and continue the selected action under the shared work-conserving contract. Recording `EXECUTION_EXCEPTION` MUST NOT become a voluntary yield point.

A retry of the same failed repository operation is legal only when there is a materially changed, fresh-read precondition that can affect the outcome, or when the role selects a different repository-governed operation path that is legal for the same action. A denial, permission failure, unsupported tool surface, or equivalent unchanged failure condition MUST NOT trigger repeated identical mutation attempts merely to keep the invocation busy.

If local recovery is not legal or not sufficient, the invocation MUST, while it still has execution opportunity, persist the action-defined legal blocked/disposition result or route to the contract-defined diagnosis owner, then complete any required routing handoff under the canonical handoff contract before normal exit. The shared contract MUST NOT invent one universal blocked-result enum for all actions.

When a newly observed catchable failure has no existing legal action-specific disposition or recovery path, bounded Lead diagnosis SHALL be the fallback specification/authority path. The captured raw evidence SHALL be the durable input to that diagnosis; Scheduled Task conversation memory MUST NOT be required.

This requirement MUST NOT create a generic retry engine, failure-state machine, retry counter, automatic fault classifier, or hidden execution status. A truly uncatchable hard termination remains a later-reconstruction case rather than a falsely guaranteed `finally` block.

#### Scenario: Captured exception is locally recoverable

- GIVEN a role has persisted `EXECUTION_EXCEPTION`
- AND the failure has a legal same-role/action recovery under the current contract
- AND routing and preconditions remain current
- WHEN the role evaluates disposition
- THEN it performs the recovery
- AND continues the current action in the same invocation
- AND does not hand off merely because the exception record exists

#### Scenario: Identical denied mutation has no changed precondition

- GIVEN a repository mutation was denied or unsupported
- AND the denial condition has not materially changed after a fresh read
- AND no different legal repository-governed operation path is available
- WHEN the selected action evaluates another attempt
- THEN it does not repeat the identical mutation merely to avoid yielding or handing off
- AND it preserves evidence and converges to the action-defined disposition or bounded Lead diagnosis

#### Scenario: Captured exception has no current action-specific path

- GIVEN a role has persisted `EXECUTION_EXCEPTION`
- AND the current role/action has no legal local recovery or existing disposition for the observed failure
- WHEN the invocation still has execution opportunity
- THEN it preserves completed durable work
- AND routes the bounded unresolved execution diagnosis to `Lead / resolve-question`
- AND completes the required routing/HANDOFF boundary
- AND it does not repeatedly retry the rejected operation merely to avoid handoff
