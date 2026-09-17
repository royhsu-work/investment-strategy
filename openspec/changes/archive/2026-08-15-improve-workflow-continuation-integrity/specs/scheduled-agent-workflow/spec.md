# scheduled-agent-workflow Delta Specification

## MODIFIED Requirements

### Requirement: Scheduled execution is at-least-once and state reconstructable

Every scheduled action SHALL reconstruct relevant durable repository, Issue, PR, OpenSpec, GitHub Actions, and any specifically awaited external resource state before deciding what remains to be done.

The workflow MUST NOT require previous conversation memory or a previous scheduled run to have exited cleanly.

Partial execution, interruption, tool failure, or missing final response MUST NOT transfer ownership merely because some work was attempted.

When a prior operation failed after only some durable mutations completed, recovery SHALL distinguish observed durable mutations from intended-but-uncompleted work. If the current invocation can still write repository evidence, it SHALL preserve the existing canonical action/result/`EXECUTION_EXCEPTION`/cross-role `HANDOFF` evidence required by the owning action. If no repository evidence surface is writable, the run MUST NOT manufacture a durable workflow transition from external Scheduled Task output; a later wake SHALL reconstruct correctness from the repository state that actually exists.

After a selected action persists its durable result and legally changes routing, the invocation MAY continue to the next action only when all of the following are true:

- the selected coordination Issue is unchanged;
- the target role equals the fixed invocation role;
- the target routing is current after a fresh read;
- the target action is immediately actionable without Human authority, a real external asynchronous wait, ambiguity, or unsafe/stale state; and
- the target action reloads its mapped default-branch skill and reconstructs its own required durable state and preconditions before mutation.

The invocation MUST stop at the first cross-role transfer, unresolved Human boundary, real external asynchronous wait, ambiguity/unsafe state, stale/concurrency loss, or actual execution interruption. Same-role continuation MUST NOT process a second coordination Issue or introduce a timer, continuation counter, lease, heartbeat, hidden dispatcher, or second workflow state machine.

A first `absent`, `queued`, or `in_progress` observation of the exact required external resource just created or triggered by the selected action MUST NOT by itself be treated as a real cross-invocation asynchronous wait while bounded same-invocation execution opportunity remains. The action SHALL confine bounded observation to that same exact resource and, if it becomes terminal during the invocation, SHALL consume that terminal result immediately when the current action remains authorized. A later wake resuming a real wait SHALL fresh-read the exact awaited resource before yielding again.

#### Scenario: Run stops after durable work but before handoff

- GIVEN a scheduled role completes durable action work
- AND the run terminates before routing changes
- WHEN a later run observes the same routing tuple
- THEN it reconstructs whether the durable action work already exists
- AND it performs only remaining legal work or the missing transition/handoff
- AND it does not require memory of the previous run

#### Scenario: Normal evidence write itself is unavailable

- GIVEN a catchable execution failure occurs
- AND the current invocation cannot write the normal coordination-Issue evidence surface
- WHEN no other repository-governed durable evidence surface is legally available
- THEN the invocation does not claim that a result, handoff, or ownership transfer became durable merely because external Scheduled Task output exists
- AND a later wake reconstructs from actual repository mutations and current routing

#### Scenario: Same-role action becomes immediately actionable

- GIVEN one invocation selected coordination Issue I with fixed role Lead
- AND Lead action A persisted its result and legally routed I to another Lead action B
- AND no Human, asynchronous, ambiguous, stale, or unsafe boundary exists
- WHEN the invocation fresh-reads I and reconstructs B
- THEN it loads B's mapped default-branch skill
- AND continues B in the same invocation
- AND it does not select another Issue or redispatch to another role

#### Scenario: Cross-role routing ends the invocation

- GIVEN an invocation selected Issue I with fixed role Lead
- AND the current action legally routes I to Reviewer
- WHEN the routing mutation succeeds
- THEN the Lead invocation records the required cross-role handoff evidence
- AND ends without executing Reviewer work

#### Scenario: Just-triggered exact validation completes quickly

- GIVEN the selected action created or triggered exact required validation resource R
- AND the first observation of R is queued or in progress
- AND bounded same-invocation execution opportunity remains
- WHEN R becomes terminal during that invocation
- THEN the action consumes R's terminal result immediately when still authorized
- AND it does not voluntarily yield merely because the first observation was nonterminal

#### Scenario: Later wake resumes a real asynchronous wait

- GIVEN an earlier invocation yielded because exact awaited resource R remained nonterminal after bounded execution opportunity ended
- WHEN a later wake reconstructs the selected action
- THEN it fresh-reads R itself before concluding the wait still exists
- AND historical waiting evidence alone cannot justify another yield

### Requirement: Routing handoff persists evidence before ownership transfer

A scheduled role SHALL persist the required action/review result, governed artifact state, and revision-aware evidence before changing the logical routing tuple. The result evidence MAY therefore exist while the source routing tuple is still current and MUST NOT by itself be treated as proof that ownership transferred.

Before the routing mutation, the role SHALL fresh-read current Issue routing. If routing no longer matches the source action being completed, the role MUST NOT overwrite the newer routing and MUST stop as stale/contradictory rather than manufacture a transition.

If the source tuple still matches and the target role differs from the fixed invocation role, the role SHALL replace the routing tuple with the target owner/action and observe the successful routing mutation. After the routing mutation succeeds, the role SHALL persist the handoff lifecycle-journal evidence required by the currently authoritative presentation contract and SHALL describe the resulting target ownership. When the canonical template contract is active on the default branch, this record uses `HANDOFF`. A required cross-role handoff is durably complete only when both target routing and required handoff evidence are durable, and the invocation SHALL end without executing the target role.

If the source tuple still matches and the target role equals the fixed invocation role, the role SHALL replace the routing tuple with the target action and observe the successful routing mutation. The source action result plus successful routing mutation is sufficient transition evidence; the workflow MUST NOT require a synthetic `HANDOFF` or a new transition message type. After fresh reconstruction, same-role continuation follows the at-least-once requirement above.

The workflow MUST NOT intentionally expose an intermediate state with two role owners or two action owners during either a same-role transition or a cross-role handoff. Routing labels remain canonical workflow ownership; handoff evidence is reconstructable evidence of a completed cross-role transfer rather than a substitute for routing state.

If an actual interruption occurs after result evidence is durable but before routing mutation completes, a later eligible run SHALL preserve the completed result and perform only the missing legal routing work. If a cross-role routing mutation already succeeded but the handoff write was interrupted, recovery SHALL preserve the target routing and repair only the missing handoff evidence; it MUST NOT replay the completed source action merely to recreate the journal. If a same-role routing mutation already succeeded, recovery SHALL reconstruct the target action from current routing without manufacturing a `HANDOFF`.

#### Scenario: Result is durable before ownership transfer

- GIVEN a role has durably persisted the action/review result and required revision-aware evidence
- AND the coordination Issue still carries the matching source routing tuple
- AND the legal target belongs to a different role
- WHEN the role performs the required cross-role handoff
- THEN it fresh-reads the source routing
- AND changes routing to the legal target tuple
- AND observes the successful routing mutation
- AND only then persists the required handoff evidence using the currently authoritative presentation contract

#### Scenario: Another run has already changed routing

- GIVEN a role has completed work and persisted its result/revision evidence
- AND a fresh read shows that another run has already changed the Issue routing tuple
- WHEN the first run reaches its routing transition step
- THEN it does not overwrite the newer routing
- AND it does not persist false handoff evidence claiming a cross-role transition it did not perform
- AND it stops for later reconstruction under the current durable owner/action

#### Scenario: Routing changed but handoff write was interrupted

- GIVEN a legal cross-role handoff already changed routing to the target tuple
- BUT the run ended before required handoff evidence was persisted
- WHEN a later eligible run reconstructs the durable state
- THEN it preserves the already changed routing
- AND repairs only the missing handoff evidence before a later lifecycle transition
- AND it does not replay the completed source action

#### Scenario: Same-role transition does not create synthetic handoff

- GIVEN Lead action A has durable result evidence
- AND A legally routes the same Issue to Lead action B
- WHEN the routing mutation succeeds
- THEN no `HANDOFF` is required solely for the same-role action transition
- AND B reconstructs from durable result, current routing, and current repository state

#### Scenario: Cross-role transfer still requires handoff

- GIVEN Executor completes an action and legally routes the Issue to Lead
- WHEN the routing mutation succeeds
- THEN Executor persists canonical `HANDOFF` evidence describing Lead ownership
- AND Executor does not execute Lead work in the same invocation

## ADDED Requirements

### Requirement: Explicit required deferred follow-up becomes durable before lifecycle completion

When an approved Lead-owned specification or scope decision explicitly classifies work as required separate follow-up or work that MUST still be handled later, the workflow SHALL treat that decision as a durable tracking obligation.

Ordinary out-of-scope statements, non-goals, optional future ideas, and work merely not selected for the current change MUST NOT create this obligation by themselves.

Lead SHALL create or reuse a durable tracking Issue at the defer-decision boundary and SHALL link it to reconstructable source evidence identifying the source coordination Issue/Change and the exact defer decision. Creation of that tracker MUST NOT itself Human-admit the tracker or add normal workflow routing.

`Reviewer / review-openspec` SHALL treat an approved required-defer decision without reconstructable durable tracker/linkage as a material finding. `Lead / finalize-archive` SHALL reconstruct still-applicable required-defer obligations before `LIFECYCLE_COMPLETE` and MUST NOT complete the lifecycle while a required tracker is missing. If the obligation and intended tracker are unambiguous and only the tracker write was missed, Lead MAY perform an idempotent repair; it MUST NOT reinterpret ambiguous scope or auto-admit the tracker.

Tracker idempotency SHALL rely on durable source linkage rather than title similarity alone.

#### Scenario: Ordinary scope exclusion creates no tracker obligation

- GIVEN an approved change marks an idea as out of scope without saying it must be handled later
- WHEN Reviewer and Lead reconstruct deferred work
- THEN no required follow-up tracker is demanded for that statement

#### Scenario: Required deferred work must have a durable tracker

- GIVEN an approved Lead decision explicitly says work W must be handled in a separate later change
- WHEN Lead records that defer decision
- THEN Lead creates or reuses a tracker linked to the source Change/Issue and decision evidence
- AND the tracker is not automatically Human-admitted or routed into active workflow

#### Scenario: OpenSpec review catches a missing required tracker

- GIVEN the OpenSpec artifacts contain an approved required-defer obligation
- AND no reconstructable linked tracker exists
- WHEN Reviewer executes `review-openspec`
- THEN Reviewer records a material finding
- AND does not treat ordinary unrelated scope exclusions as missing trackers

#### Scenario: Lifecycle completion fails safe on missing required tracker

- GIVEN a Change is otherwise ready for `LIFECYCLE_COMPLETE`
- AND a still-applicable required-defer obligation lacks a durable tracker
- WHEN Lead executes terminal archive finalization
- THEN lifecycle completion is blocked until the tracker is durably established or the obligation is authoritatively superseded
