## ADDED Requirements

### Requirement: Invocation exit requires positive proof

After a Scheduled Agent invocation selects a legal workflow/action, continuation SHALL be the default. Before the invocation returns, it MUST positively classify and prove from current evidence one legal Invocation Exit. If no legal Exit class is proven, the invocation MUST continue the selected workflow under the fixed invocation role while routing, authority, revision/preconditions, and execution capability remain current.

Legal Invocation Exit classes SHALL be limited to:

- a completed cross-role handoff with the target routing durably observed;
- a true workflow/action terminal result under the authoritative lifecycle topology;
- a genuine Human-reserved authority boundary whose current contract prevents further same-invocation work;
- a genuine external asynchronous wait that cannot be further consumed within the current legal execution opportunity and identifies the exact awaited resource/evidence;
- stale routing, revision, concurrency, or precondition loss that makes continued execution unsafe;
- materially ambiguous or contradictory durable state requiring fail-closed disposition; or
- a hard tool, permission, or runtime boundary after applicable same-authority recovery is unavailable or cannot legally proceed from current evidence.

Exit Proof SHALL be an internal execution precondition and MUST NOT require a new lifecycle action, workflow status, progress comment, timer, retry counter, heartbeat, lease, hidden runtime cursor, durable waiter state, or second workflow DAG. Existing action results, review results, handoffs, execution exceptions, exact-resource observations, and lifecycle journals remain the durable evidence surfaces.

The following intermediate facts MUST NOT independently constitute Exit Proof: an intended RED is established; GREEN or REFACTOR completes; validation fails but correction is actionable within current authority; a commit or push completes; the first observation of an exact external resource is absent, queued, or in progress; a verified Slice checkpoint exists while approved same-action work remains; an action completes with an immediately actionable successor owned by the fixed invocation role; or the exact next legal step is already known and executable.

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

#### Scenario: First nonterminal exact-resource observation cannot exit

- GIVEN the selected action has just created or triggered an exact external resource such as a required CI run
- AND its first current observation is absent, queued, or in progress
- AND current routing, authority, and execution opportunity still allow bounded consumption of that exact resource
- WHEN the invocation evaluates Exit Proof
- THEN that first nonterminal observation is not a genuine asynchronous-wait Exit
- AND the invocation continues bounded observation of the same exact resource

#### Scenario: Genuine unconsumable external wait may exit

- GIVEN an exact required external resource remains nonterminal
- AND the current legal execution opportunity cannot further consume it without inventing waiter state or crossing an authority boundary
- WHEN the invocation evaluates Exit Proof
- THEN it MAY classify a genuine external asynchronous wait
- AND the Exit Proof identifies the exact awaited resource/evidence for later reconstruction

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

- GIVEN a tool, permission, or runtime failure prevents the next required mutation
- AND any applicable same-authority recovery procedure has been evaluated from current evidence
- AND no legal local recovery can proceed without weakening a gate or crossing role authority
- WHEN the invocation evaluates Exit Proof
- THEN the hard execution boundary is a legal Exit
- AND the invocation preserves the existing exception/disposition evidence rather than inventing new workflow state

#### Scenario: No proven Exit class rejects return

- GIVEN the invocation remains on the selected workflow under current routing and authority
- AND none of the bounded legal Invocation Exit classes is proven from current evidence
- WHEN the invocation attempts to return
- THEN return is not authorized
- AND execution continues with the next immediately actionable legal step
