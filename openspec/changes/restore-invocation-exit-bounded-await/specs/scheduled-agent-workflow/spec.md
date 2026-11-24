## MODIFIED Requirements

### Requirement: External asynchronous waits are revalidated from the awaited resource

A selected Scheduled-Agent action MUST NOT classify any observation of an exact external resource as a real cross-invocation asynchronous wait merely because the resource is absent, queued, or in progress. Neither a first observation nor any fixed or arbitrary number of nonterminal observations proves exhaustion of execution opportunity.

When an exact external resource is required for the current selected Action's outstanding obligations, including a resource created or triggered by that Action or reconstructed on resume, and routing, authority, applicable revision/preconditions and bounded execution opportunity remain current, the action MUST continue bounded observation of that same exact resource until its terminal disposition can be consumed or an existing legal Invocation Exit boundary is established. Observation MUST NOT introduce durable waiter state or cross another Action, Role/Human authority, CarrierRequired or other existing hard boundary.

If the resource resolves while that bounded same-invocation opportunity remains, the action MUST verify its exact outcome and continue immediately actionable work under the shared work-conserving contract, including the applicable validation, postcondition, recovery or exception disposition obligations. A real external asynchronous-wait yield while the resource remains nonterminal requires current evidence that further lawful bounded observation or work is no longer possible within the actual available execution context. A Worker Result, an API success, an intermediate Application/CI observation or the Agent's decision to produce a progress report or return MUST NOT by itself prove Action completion or execution-opportunity exhaustion. The existing legal exit, stale/precondition, exception disposition and CarrierRequired contracts remain applicable.

When a scheduled invocation resumes work that previously yielded because a specific external asynchronous resource was not yet complete, the selected action SHALL fresh-read that awaited resource before concluding that the wait still exists. A prior coordination-Issue comment, checkpoint, or summarized observation that recorded the resource as `in_progress`, pending, or unavailable MUST be treated as historical evidence only and MUST NOT by itself justify another asynchronous-wait yield.

If the fresh-read resource shows that the awaited condition has resolved and the selected role/action has immediately actionable work under current routing and preconditions, the invocation MUST continue that work under the shared work-conserving contract.

This behavior MUST NOT create a polling service, durable timer, heartbeat, retry counter, hidden waiting state, or scheduler-side workflow state.

#### Scenario: Just-triggered CI settles during the same invocation

- GIVEN the selected action just created or triggered an exact-head validation resource
- AND the first fresh read observes it absent, queued, or in progress
- AND routing, revision, authority, and execution context remain current
- WHEN the resource reaches success while bounded same-invocation execution opportunity remains
- THEN the action continues the remaining immediately actionable work in the same invocation
- AND it continues bounded observation while those conditions hold
- AND the first nonterminal observation is not treated as an automatic cross-invocation yield boundary

#### Scenario: Exact resource remains nonterminal beyond bounded opportunity

- GIVEN the selected action is observing the exact external resource it just caused
- AND the resource remains queued or in progress
- WHEN the invocation can no longer continue bounded observation without exceeding its available execution context
- THEN yielding is a legal real external asynchronous wait based on the actual execution boundary, not the number of observations
- AND available current observations and the unfinished boundary are preserved through existing legal evidence paths
- AND the next wake MUST fresh-read that exact awaited resource before concluding that the wait still exists

#### Scenario: Resumed wait is revalidated from the exact awaited resource

- GIVEN a prior invocation yielded because a specific external asynchronous resource was not yet complete
- AND a later wake reconstructs the same selected action
- WHEN current wait status is evaluated
- THEN the selected action fresh-reads that exact awaited resource
- AND stale `in_progress`, pending, or unavailable evidence alone cannot justify another yield

#### Scenario: Awaited gate has completed successfully

- GIVEN a later wake fresh-reads the specific awaited validation run
- AND the run is now completed successfully for the required revision
- AND routing and other preconditions remain current
- WHEN the selected action evaluates continuation
- THEN the prior async-wait boundary no longer applies
- AND the action continues its immediately actionable work in the same invocation

#### Scenario: Nonterminal resource belongs to another authority boundary

- GIVEN a nonterminal external dependency is not part of the current selected action's bounded continuation or requires another role/Human authority
- WHEN the selected action evaluates whether to keep waiting locally
- THEN it does not invent same-invocation polling to cross that authority boundary
- AND it follows the existing legal handoff/escalation/async-wait contract

#### Scenario: Repeated pending observations do not prove exhaustion

- GIVEN an exact required Application or validation resource remains absent, queued or in progress after a Worker Result or other intermediate operation
- AND the current Action, applicable revision, preconditions, authority and bounded execution opportunity remain valid
- WHEN the Agent considers returning after one or more nonterminal observations or producing a progress report
- THEN it continues bounded observation of the exact resource
- AND it does not classify an intermediate result, arbitrary observation count or voluntary response as proof of exhaustion or Action completion

#### Scenario: Required resource resolves with actionable failure

- GIVEN an exact awaited resource reaches a terminal failure while the selected Action still has lawful execution opportunity
- WHEN its result and current preconditions are verified
- THEN the Agent completes the applicable legal same-Action diagnosis, recovery or exception disposition and remaining obligations
- AND it neither abandons actionable work merely because a failure was reported nor replays a completed or ambiguous mutation

#### Scenario: Required Application completes its formal obligations

- GIVEN the exact awaited Application has reached a terminal result
- WHEN the selected Action verifies that result and the required postconditions
- THEN intermediate Worker Result submission or run success alone is not treated as Action completion
- AND it completes the remaining legally required verification and result obligations
- AND any successor Action is executed only on a later fresh repository-owned dispatch

#### Scenario: Existing hard boundary is reached

- GIVEN current authoritative evidence establishes CarrierRequired, stale or lost preconditions, a reserved Human authority boundary or another existing hard Invocation Exit condition
- WHEN the Agent considers continued observation or effects
- THEN it follows that existing boundary and its applicable evidence or disposition contract
- AND does not cross that boundary to satisfy mandatory bounded observation
- AND completed work is not replayed or routing rewound on resume
