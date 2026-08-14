# scheduled-agent-workflow

## MODIFIED Requirements

### Requirement: External asynchronous wait is a cross-invocation boundary, not any nonterminal read

A selected Scheduled-Agent action MUST NOT classify the first observation of an exact external resource as a real cross-invocation asynchronous wait merely because the resource is absent, queued, or in progress.

When the exact resource was created or triggered by the current selected action, routing/preconditions remain current, no different role/Human authority boundary is required, and the invocation still has bounded execution opportunity, the action MAY continue bounded observation of that same exact resource without introducing durable waiter state.

If the resource resolves while that bounded same-invocation opportunity remains, the action MUST continue immediately actionable work under the shared work-conserving contract. If bounded execution opportunity is exhausted while the resource remains nonterminal, the action MAY yield as a real external asynchronous wait. A later wake then applies the existing fresh-read-on-resume contract.

This behavior MUST NOT create a polling service, durable timer, heartbeat, retry counter, hidden waiting state, or scheduler-side workflow state.

#### Scenario: Just-triggered CI settles during the same invocation

- GIVEN the selected action just created or triggered an exact-head validation resource
- AND the first fresh read observes it absent, queued, or in progress
- AND routing, revision, authority, and execution context remain current
- WHEN the resource reaches success while bounded same-invocation execution opportunity remains
- THEN the action continues the remaining immediately actionable work in the same invocation
- AND the first nonterminal observation is not treated as an automatic cross-invocation yield boundary

#### Scenario: Exact resource remains nonterminal beyond bounded opportunity

- GIVEN the selected action is observing the exact external resource it just caused
- AND the resource remains queued or in progress
- WHEN the invocation can no longer continue bounded observation without exceeding its available execution context
- THEN yielding is a legal real external asynchronous wait
- AND the next wake MUST fresh-read that exact awaited resource before concluding that the wait still exists

#### Scenario: Nonterminal resource belongs to another authority boundary

- GIVEN a nonterminal external dependency is not part of the current selected action's bounded continuation or requires another role/Human authority
- WHEN the selected action evaluates whether to keep waiting locally
- THEN it does not invent same-invocation polling to cross that authority boundary
- AND it follows the existing legal handoff/escalation/async-wait contract

### Requirement: External wake topology is deployment configuration, not repository workflow state

The repository SHALL define the bootstrap and dynamic-dispatch behavior a Scheduled Task must follow, but SHALL NOT require an exact number of external wake slots, exact cadence, or scheduler topology as durable workflow state or permanent runtime governance.

Repository migration documentation MAY record the currently deployed slot arrangement as informational context. Changing slot count or cadence is an external product/deployment decision unless a separate Human-approved repository requirement explicitly defines an observable responsiveness target.

#### Scenario: Dynamic dispatch uses a different number of wake slots

- GIVEN default-branch governance is `workflow-dynamic`
- AND the external product configuration uses one, two, three, or another supported number of wake slots
- WHEN a wake runs
- THEN repository dispatch semantics are derived from durable workflow state and default-branch governance
- AND the slot count itself does not become repository routing, ownership, waiting, or completion state

#### Scenario: Repository has no approved responsiveness SLO

- GIVEN no Human-approved repository requirement defines a workflow reaction-time SLO
- WHEN scheduler cadence is discussed or changed externally
- THEN repository governance does not invent a fixed slot count or cadence as a normative requirement

### Requirement: Final Archive native-close occurs only after known terminal cleanup obligations are cleared

Before Lead authorizes merge of the final Archive PR, Lead SHALL reconstruct workflow-owned temporary integration/recovery branches known from durable provenance and identify any terminal cleanup obligation that would become unreachable after native Issue closure.

For an Archive PR merge, `Executor / merge-pr` SHALL fresh-read the identified workflow-owned temporary branches before the Archive PR merge mutation. Any branch that is already unused, safely deletable, and Executor-owned under the existing temporary-branch contract SHALL be deleted before the final Archive PR merge. If deletion is blocked, unsupported, stale, or unsafe, Executor MUST NOT merge the Archive PR; while the coordination Issue is still open it SHALL follow the existing exception/disposition path and, when required, return bounded diagnosis to Lead.

The workflow SHALL prefer this pre-close ordering over adding a generic post-close Executor route. The change MUST NOT introduce a new post-close action, broad Issue reopen lifecycle, hidden cleanup state, or branch registry.

#### Scenario: Safely deletable temporary branch exists before Archive merge

- GIVEN Lead reconstructs a known workflow-owned temporary integration/recovery branch before final Archive authorization
- AND the branch is no longer an open PR head/base or active recovery input
- AND fresh comparison proves it has no unique commits outside canonical `main` or an explicitly retained successor
- WHEN final Archive merge is prepared
- THEN Executor removes that branch before merging the final Archive PR
- AND native close cannot make that known cleanup obligation unreachable

#### Scenario: Pre-close cleanup mutation is unavailable

- GIVEN a known temporary branch is safely deletable and must be retired before terminal completion
- AND Executor cannot perform the required deletion with the current legal repository mutation surface
- WHEN `Executor / merge-pr` prepares the final Archive merge
- THEN it does not merge the Archive PR
- AND the coordination Issue remains open
- AND the failure follows existing durable exception/disposition and Lead diagnosis rules

#### Scenario: No known temporary cleanup obligation remains

- GIVEN Lead and Executor fresh-read the known workflow-owned temporary branch provenance
- AND no unresolved unused safely deletable branch remains
- WHEN all independent archive review and exact-head merge gates also pass
- THEN the final Archive PR may be merged and its closing linkage may natively close the coordination Issue
- AND normal closed-Issue `Lead / finalize-archive` reconstruction may proceed
