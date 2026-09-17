# scheduled-agent-workflow Delta Specification

## MODIFIED Requirements

### Requirement: Scheduled execution is at-least-once and state reconstructable

Every scheduled action SHALL reconstruct relevant durable repository, Issue, PR, OpenSpec, GitHub Actions, and any specifically awaited external resource state before deciding what remains to be done.

The workflow MUST NOT require previous conversation memory or a previous scheduled run to have exited cleanly.

Partial execution, interruption, tool failure, or missing final response MUST NOT transfer ownership merely because some work was attempted.

When a prior operation failed after only some durable mutations completed, recovery SHALL distinguish observed durable mutations from intended-but-uncompleted work. If the current invocation can still write repository evidence, it SHALL preserve the existing canonical action/result/`EXECUTION_EXCEPTION`/cross-role `HANDOFF` evidence required by the owning action. If no repository evidence surface is writable, the run MUST NOT manufacture a durable workflow transition from external Scheduled Task output; a later wake SHALL reconstruct correctness from the repository state that actually exists.

When recovery evaluates an already-completed durable mutation or handoff, it SHALL also reconstruct whether valid causal-descendant evidence within the same coordination workflow proves that exact transition was already consumed by later lifecycle work. If such descendant evidence exists, recovery MUST NOT overwrite canonical routing to replay the earlier transition. It MAY repair only still-required non-routing journal evidence when that repair is non-contradictory. Ambiguous or contradictory consumption evidence MUST fail closed rather than authorize backward routing repair.

This consumed-transition guard is recovery-specific and MUST NOT be interpreted as a generic forward-only lifecycle rule; normal governed correction loops remain legal.

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

#### Scenario: Earlier merge transition already has causal descendants

- GIVEN merge mutation M and its accepted revision are already durable
- AND valid later lifecycle evidence in the same coordination workflow proves M's handoff was consumed
- AND a stale recovery attempt reconstructs M as already completed
- WHEN recovery evaluates whether to repair M's routing transition
- THEN recovery does not rewrite canonical routing back to M's immediate downstream owner/action
- AND it may repair only still-required non-routing journal evidence when safe
- AND legitimate separately governed correction loops remain unaffected

#### Scenario: Consumption evidence is contradictory

- GIVEN recovery reconstructs an already-completed durable mutation
- AND available same-workflow evidence is contradictory about whether its transition was consumed
- WHEN recovery evaluates routing repair
- THEN it fails closed
- AND it does not choose a lifecycle position by model inference
