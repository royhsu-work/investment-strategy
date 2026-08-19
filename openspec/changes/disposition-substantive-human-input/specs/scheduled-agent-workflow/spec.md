## ADDED Requirements

### Requirement: Consequential workflow boundaries disposition newer substantive direct-Human input

Before a Scheduled role persists a consequential workflow result, completes a routing ownership transition, or executes an unsafe merge mutation, it SHALL fresh-read the persistent coordination Issue for direct-Human comments newer than the durable workflow evidence boundary on which the pending decision relies.

A candidate comment SHALL count as direct-Human input for this requirement only when durable raw creation provenance identifies the designated Human actor and shows that creation was not performed via a GitHub App. This classification is an input-freshness safeguard only: it MUST NOT itself satisfy a Human-reserved admission, answer, authorization, resume, or risk/scope decision, all of which continue to require their separately governed provenance-bound predicate and exact decision reference.

If a newer direct-Human comment could materially affect correctness, approved scope, traceability, gate validity, lifecycle preparation, or mutation assumptions, the current role MUST NOT silently proceed from its older snapshot. Before the consequential boundary completes, the exact comment id SHALL have one reconstructable durable disposition that is legal for the current authority boundary:

- addressed within the current role's existing authority with a bounded answer/rationale;
- classified non-blocking with a bounded reason when the comment is clearly informational, administrative, or otherwise immaterial to the pending decision;
- converted into the existing action-defined finding/blocker/correction result when it exposes a defect owned by that path; or
- routed/escalated to the role or Human-reserved decision boundary that owns the unresolved meaning.

A role MUST NOT answer outside its existing authority merely to clear the disposition requirement. A durable disposition SHALL identify the exact Human comment id so later wakes can reconstruct that it has already been handled without a comment queue, unread counter, acknowledgement label, hidden registry, or new lifecycle state.

A direct-Human comment that appears after action start but before the consequential boundary SHALL be treated as newer evidence at the final fresh-read. When its materiality or legal disposition is ambiguous, the action SHALL fail closed at that boundary rather than emit a result or mutation that assumes the older snapshot remains complete.

#### Scenario: Human asks material question before implementation review PASS

- GIVEN Executor has handed an implementation PR to `Reviewer / review-implementation`
- AND a newer direct-Human coordination-Issue comment asks a question that may affect approved-scope or traceability correctness
- AND that exact comment has no durable disposition
- WHEN Reviewer evaluates PASS for the current implementation head
- THEN Reviewer MUST NOT record PASS while silently ignoring the comment
- AND Reviewer dispositions it through the legal review finding/answer/owner path before the gate can complete

#### Scenario: Human input arrives while Executor is preparing READY

- GIVEN Executor reconstructed an implementation snapshot and is correcting approved findings
- AND before Executor persists `READY`, a newer direct-Human comment appears that could materially affect correctness or scope
- WHEN Executor performs the consequential-boundary fresh-read
- THEN the older implementation snapshot is insufficient for READY
- AND Executor MUST disposition the exact comment within Executor authority or route the unresolved meaning to its legal owner before READY can be persisted

#### Scenario: Human input arrives after Reviewer PASS but before merge

- GIVEN Reviewer recorded exact-head PASS for revision R
- AND before `Executor / merge-pr` mutates the PR, a newer direct-Human comment appears that could invalidate a relied-upon merge assumption or the accepted meaning
- WHEN Executor performs mutation-time fresh-read
- THEN the older PASS alone is insufficient to authorize merge
- AND Executor MUST NOT merge until the exact comment is durably dispositioned through the legal owner/path and all resulting merge preconditions are current

#### Scenario: Clearly non-substantive Human comment does not create lifecycle waiting state

- GIVEN a newer direct-Human comment is administrative or clearly immaterial to the pending workflow decision
- WHEN the current role evaluates the consequential boundary
- THEN it MAY record a bounded non-blocking disposition referencing that exact comment id
- AND the workflow MAY continue without creating a new waiting status, lifecycle action, blocker label, or Human-approval ceremony

#### Scenario: Human-reserved decision remains provenance-bound

- GIVEN a newer direct-Human comment contains a statement about a decision that governance reserves to Human authority
- WHEN a Scheduled role evaluates that statement
- THEN this Human-input disposition requirement does not itself authorize the decision
- AND the existing exact `Human-Decision-For` plus qualifying provenance-bound approval predicate remains required at the mapped Human-reserved boundary

#### Scenario: Question belongs to another role authority

- GIVEN a newer direct-Human comment raises a material specification/scope question while Executor or Reviewer owns the current action
- WHEN the current role cannot legally resolve that meaning within its authority
- THEN it MUST NOT answer outside its role merely to mark the comment handled
- AND it dispositions the comment by using the existing finding/blocker and routing path to the legal owner

#### Scenario: Repeated wake recognizes prior exact-comment disposition

- GIVEN a direct-Human comment C was previously durably dispositioned by exact comment id under a legal action result, finding, answer, or routing boundary
- WHEN a later wake reconstructs the same coordination Issue
- THEN C does not require a duplicate acknowledgement or disposition
- AND only newer or materially unresolved direct-Human input remains relevant to the current consequential-boundary fresh-read

#### Scenario: Connector-authored workflow message is not reclassified as direct-Human input

- GIVEN a coordination-Issue comment is attributed to the designated account but raw creation provenance shows it was performed via a GitHub App
- WHEN a Scheduled role evaluates the Human-input freshness requirement
- THEN that comment is not classified as direct-Human input by this requirement
- AND its actor identity alone neither creates this disposition obligation nor grants Human authority