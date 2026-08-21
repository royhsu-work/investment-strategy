## MODIFIED Requirements

### Requirement: Selected Scheduled Agent actions are work-conserving within an invocation

After a Scheduled Agent invocation selects one legal role/action, continuation SHALL be the default and that selected action SHALL continue all immediately actionable work within the same invocation while the routing still matches the selected action, required revision/preconditions and authority remain current, and no legal blocking condition exists.

Before the invocation returns, it MUST positively classify and prove from current evidence one legal Invocation Exit. If no legal Exit class is proven, the invocation MUST continue the selected workflow under the fixed invocation role while routing, authority, revision/preconditions, and execution capability remain current.

A durable checkpoint, remaining approved local work, a recoverable same-role failure, or a failed-but-actionable validation MUST NOT by itself be treated as a voluntary yield point. When the correction is within the selected role/action authority and approved contract, the invocation SHALL perform that correction and continue the action instead of deferring it solely to a later wake.

A selected action MAY end before its normal completion only when current evidence positively proves at least one of these bounded Invocation Exit classes:

- a completed cross-role handoff with the target routing durably observed, or a true workflow/action terminal result under the authoritative lifecycle topology;
- a genuine Human-reserved authority boundary whose current contract prevents further same-invocation work;
- a genuine external asynchronous wait that cannot be further consumed within the current legal execution opportunity and identifies the exact awaited resource/evidence;
- stale routing, revision, concurrency, or precondition loss that makes continued execution unsafe;
- materially ambiguous or contradictory durable state requiring fail-closed disposition; or
- a hard tool, permission, runtime, or execution boundary after any applicable same-authority recovery/disposition procedure has been evaluated from current evidence and no legal local continuation remains.

Exit Proof SHALL be an internal execution precondition and MUST NOT require a new lifecycle action, workflow status, progress comment, timer, retry counter, heartbeat, lease, hidden runtime cursor, durable waiter state, or second workflow DAG. Existing action results, review results, handoffs, execution exceptions, exact-resource observations, and lifecycle journals remain the durable evidence surfaces.

The following intermediate facts MUST NOT independently constitute Exit Proof: an intended RED is established; GREEN or REFACTOR completes; validation fails but correction is actionable within current authority; a commit or push completes; the first observation of an exact external resource is absent, queued, or in progress; a verified Slice checkpoint exists while approved same-action work remains; an action completes with an immediately actionable successor owned by the fixed invocation role; or the exact next legal step is already known and executable.

For an exact required external resource just created or triggered by the selected action, ordinary asynchronous-wait Exit evidence MUST be sequence-derived. After the first current observation is absent, queued, or in progress, the same invocation MUST perform at least one subsequent fresh observation of the same exact target/resource before that resource can support the existing asynchronous-wait Exit class. If the subsequent observation is terminal, the selected action MUST consume that terminal result immediately. If the subsequent fresh observation remains absent or nonterminal, current routing/revision/preconditions remain valid, and no other same-authority work is immediately actionable, that completed bounded re-observation MAY establish the existing genuine asynchronous-wait Exit. This fixed minimum re-observation floor MUST NOT introduce a wall-clock delay policy, sleep requirement, polling counter, heartbeat, retry state, durable waiter, or hidden runtime state.

A catchable tool/runtime/execution failure does not by itself waive exception capture or invocation finalization and does not become a hard-boundary Exit merely because an exception occurred. If the invocation still has execution opportunity, it MUST first preserve the required raw exception evidence, then apply the existing action-specific recovery/disposition contract. When legal same-authority recovery is immediately actionable, it MUST recover and continue within the same selected role/action. Only when current evidence proves that applicable same-authority recovery/disposition cannot legally continue may the failure support a hard execution-boundary Exit. A genuinely uncatchable hard termination MAY prevent current-run persistence and is handled by later at-least-once reconstruction.

The generic continuation/termination, catchable-exception, and normal-finalization contracts SHALL be owned once by shared governance in `agents/AGENTS.md`. Role and skill documents MUST NOT duplicate or weaken these shared rules; they MAY define only action-specific results, authority boundaries, waits, local recovery, blockers, and handoffs.

#### Scenario: Failed validation is locally actionable

- GIVEN a selected action still owns the current routing
- AND its validation fails for a clear correction inside that same action's approved authority
- AND the execution revision/preconditions remain current
- WHEN the invocation evaluates whether to stop
- THEN the validation failure is not a voluntary yield point
- AND the invocation corrects the failure and reruns the required validation in the same invocation

#### Scenario: Verified implementation checkpoint has more approved work

- GIVEN Executor is selected for `implement-change`
- AND one approved Slice reaches successful VERIFY and its required checkpoint is persisted
- AND another approved Slice is immediately actionable under the same current routing and approved contract
- WHEN Executor completes the checkpoint boundary
- THEN the checkpoint is a durable recovery boundary rather than a scheduled-run termination boundary
- AND Executor continues the next approved Slice in the same invocation

#### Scenario: External asynchronous evidence is genuinely pending

- GIVEN Lead is selected for a finalize action
- AND the action has completed all immediately actionable Lead work
- AND legal continuation depends on repository automation that is still running and whose exact result is not yet available
- AND current evidence proves that exact resource cannot be further consumed within the current legal execution opportunity
- WHEN Lead evaluates continuation
- THEN retaining the current routing and ending the invocation is a legal external-wait outcome
- AND the Exit Proof identifies the exact awaited resource/evidence for later reconstruction

#### Scenario: Competing durable state invalidates the execution base

- GIVEN an invocation selected a role/action from durable revision R
- AND another run wins a competing durable mutation so the required base/preconditions are no longer current
- WHEN the first invocation rechecks its preconditions
- THEN it stops as stale rather than rebasing or continuing speculative work inside the same invocation

#### Scenario: RED with immediately actionable GREEN cannot exit

- GIVEN Executor has established an intended RED for approved implementation work
- AND the exact GREEN correction is already known and executable within `Executor / implement-change`
- WHEN the invocation evaluates whether it may return
- THEN RED is not valid Exit Proof
- AND Executor continues into GREEN while current routing and preconditions remain valid

#### Scenario: Failed but actionable validation cannot exit

- GIVEN a required validation fails for a correction that remains inside the selected role/action authority and approved contract
- AND the failure is actionable from current evidence
- WHEN the invocation evaluates Exit Proof
- THEN the failed validation is not a legal Exit by itself
- AND the invocation corrects and continues under the existing work-conserving contract

#### Scenario: First nonterminal exact-resource observation requires re-observation

- GIVEN the selected action has just created or triggered an exact required external resource such as a CI run
- AND its first current observation is absent, queued, or in progress
- AND current routing, authority, revision/preconditions, and execution capability remain valid
- WHEN the invocation evaluates Exit Proof
- THEN that first nonterminal observation is not a genuine asynchronous-wait Exit
- AND the invocation performs at least one subsequent fresh observation of the same exact target/resource before ordinary async-wait Exit can be classified

#### Scenario: Subsequent terminal success is consumed

- GIVEN the first observation of a just-triggered exact required resource was absent, queued, or in progress
- AND a subsequent fresh same-invocation observation of that exact resource is terminal success
- WHEN the selected action evaluates its next step
- THEN it consumes the terminal success in the same invocation
- AND it does not classify asynchronous-wait Exit from the earlier nonterminal observation

#### Scenario: Subsequent terminal actionable failure is consumed

- GIVEN the first observation of a just-triggered exact required resource was absent, queued, or in progress
- AND a subsequent fresh same-invocation observation of that exact resource is terminal failure
- AND the failure has a correction immediately actionable inside the selected action's approved authority
- WHEN the selected action evaluates its next step
- THEN it consumes the failure and performs the legal correction in the same invocation
- AND the terminal failure does not become asynchronous-wait Exit

#### Scenario: Genuine unconsumable external wait may exit after bounded re-observation

- GIVEN an exact required external resource was first observed absent, queued, or in progress
- AND the same invocation performs a subsequent fresh observation of the same exact target/resource
- AND that later observation remains absent or nonterminal
- AND no other same-authority work is immediately actionable
- AND current routing, revision, and preconditions remain valid
- WHEN the invocation evaluates Exit Proof
- THEN it MAY classify the existing genuine external asynchronous-wait Exit
- AND the Exit Proof identifies the exact awaited target/resource for later reconstruction

#### Scenario: Async wait without required re-observation is rejected

- GIVEN a just-triggered exact required resource has only one current absent, queued, or in-progress observation
- AND no subsequent fresh observation of that same exact target/resource has occurred in the invocation
- WHEN the invocation attempts to classify asynchronous-wait Exit
- THEN the Exit is not proven
- AND the invocation must continue the bounded observation procedure while current routing and preconditions remain valid

#### Scenario: Stale state during re-observation permits fail-closed exit

- GIVEN a just-triggered exact required resource had a first nonterminal observation
- AND before the required subsequent observation can be legally consumed the selected routing, head, or another required precondition becomes stale
- WHEN the invocation rechecks current state
- THEN it uses the existing stale/precondition fail-closed Exit
- AND it does not continue observing or acting from the obsolete revision

#### Scenario: Same-role successor continues

- GIVEN Lead durably completes one action on the selected coordination Issue
- AND the legal successor action remains Lead-owned on that same Issue
- AND the successor is immediately actionable under current routing and preconditions
- WHEN the invocation evaluates Exit Proof
- THEN action completion alone is not a legal Exit
- AND Lead continues into the successor action without a cross-role HANDOFF

#### Scenario: Completed cross-role handoff may exit

- GIVEN Reviewer has durably persisted its gate result
- AND routing has been legally transferred to another role
- AND the target routing is freshly observed
- WHEN the invocation evaluates Exit Proof
- THEN the completed cross-role handoff is a legal Invocation Exit
- AND Reviewer does not execute the target role's work in the same invocation

#### Scenario: Stale precondition permits fail-closed exit

- GIVEN the selected action fresh-reads routing, revision, or another required precondition
- AND discovers that the evidence relied on by the current invocation is stale or has been superseded
- WHEN continued execution would be unsafe
- THEN stale/precondition loss is a legal fail-closed Exit
- AND the invocation does not continue from the obsolete snapshot

#### Scenario: Hard execution boundary may exit only after legal local recovery is unavailable

- GIVEN a tool, permission, runtime, or execution failure prevents the next required operation
- AND any applicable same-authority recovery/disposition procedure has been evaluated from current evidence
- AND no legal local continuation can proceed without weakening a gate or crossing role authority
- WHEN the invocation evaluates Exit Proof
- THEN the hard execution boundary is a legal Exit
- AND the invocation preserves the existing exception/disposition evidence rather than inventing new workflow state

#### Scenario: No proven Exit class rejects return

- GIVEN the invocation remains on the selected workflow under current routing and authority
- AND none of the bounded legal Invocation Exit classes is proven from current evidence
- WHEN the invocation attempts to return
- THEN return is not authorized
- AND execution continues with the next immediately actionable legal step
