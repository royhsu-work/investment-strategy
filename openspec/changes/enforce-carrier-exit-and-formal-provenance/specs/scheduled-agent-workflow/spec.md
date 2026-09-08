## ADDED Requirements

### Requirement: Active formal transitions require repository-owned provenance

When a coordination Issue has `Change != unset`, the current formal
`action:*` routing transition and terminal/close boundary SHALL be accepted
only when fresh evidence qualifies the transition as the result of a
repository-owned GitHub Actions/application execution. The evidence MUST bind
the transition to the application's fresh authorization and observed durable
postcondition; syntactically valid Issue fields, labels, timestamps, or
connector-authored comments alone are insufficient.

A connector-authored or other out-of-band direct formal routing or
terminal/close mutation, and any transition whose repository-owned provenance
is missing, incomplete, stale, ambiguous, contradictory, or unverified, SHALL
be classified as `INDETERMINATE` and fail closed. The application MUST NOT
auto-accept it, auto-rewind it, or launder it through idempotent
reconciliation. A qualified repository-owned Actions/application transition
continues to use the existing finite Action/Result vocabulary and transition
model.

Connector ingress remains limited to the bounded untrusted
`EFFECT_REQUEST` transport needed by the current application bridge. Ingress
does not grant routing, successor, retry, merge, terminal, or success
authority; those effects remain application-derived and postcondition-bound.

Existing pre-activation behavior for `Change: unset` SHALL remain
compatible: Explore/Propose selection may use the current pre-activation
contract and does not require the active-formal provenance guard until a
Change is set.

#### Scenario: Connector-authored active routing fails closed

- GIVEN a coordination Issue has `Change != unset` and a connector-authored
  direct comment or label mutation makes a syntactically valid `action:*`
  route current
- WHEN the application freshly observes the active formal state
- THEN the transition is classified `INDETERMINATE`
- AND the application fails closed without accepting the route or deriving a
  successor
- AND it does not auto-rewind or launder the mutation through reconciliation

#### Scenario: Connector-authored premature close fails closed

- GIVEN a coordination Issue has `Change != unset` and a connector-authored
  direct mutation closes the Issue or presents terminal evidence
- WHEN the application freshly reconstructs the formal lifecycle
- THEN the close or terminal boundary is classified `INDETERMINATE`
- AND no terminal/success effect is accepted or derived
- AND the next legal handling remains governed by fresh repository-owned
  evidence rather than the connector mutation

#### Scenario: Repository-owned formal transition remains qualified

- GIVEN a coordination Issue has `Change != unset` and a repository-owned
  Actions/application run has fresh authorization, emits the formal transition,
  and its durable postcondition is observed
- WHEN the application reconstructs the current formal lifecycle
- THEN the `action:*` route or terminal/close boundary is classified
  `QUALIFIED`
- AND the existing executable Action/Role/transition model may proceed
- AND no new Action, Result kind, or routing state is introduced

#### Scenario: Change-unset pre-activation remains compatible

- GIVEN a coordination Issue still has `Change: unset` and is selected by the
  existing pre-activation Explore/Propose dispatch
- WHEN the application reconstructs the current pre-activation state
- THEN the existing compatibility contract remains applicable
- AND the active-formal provenance guard is not used to require a Change
  before the approved Propose transition

### Requirement: Corrective formal provenance preserves the verified-slice recovery outcome

This requirement records the same approved #227 correction against the exact Human evidence: rejection/root cause `issuecomment-5575078000`, latest minimal repair `issuecomment-5578787305`, and implementation decision record `issuecomment-5585904208`. Those records are retained as decision/evidence provenance; they do not authorize a lifecycle transition by themselves.

The formal provenance guard SHALL preserve the unchanged recovery sequence:

```text
verified slice → durable checkpoint → interruption
→ reconstruct current truth → no replay → first incomplete slice
```

One `implement-change` Action SHALL consume one bounded first-incomplete slice. Existing task and `SLICE_CHECKPOINT` evidence SHALL remain monotonic and bounded: `newly checked task IDs == SLICE_CHECKPOINT Completed-Tasks == first incomplete slice task set`. A later wake SHALL use current repository truth and exact postconditions; it MUST NOT replay a previously verified slice or advance to a later slice before the current durable checkpoint obligation is satisfied.

When `Change != unset`, an `ACTION_RESULT`, formal `action:*` routing, terminal/close boundary, or successor-related formal transition SHALL be accepted only after fresh repository-owned Actions/application provenance, exact postcondition observation, and the existing first-incomplete/monotonic evidence are qualified. Connector/out-of-band formal mutation SHALL be `INDETERMINATE` and fail closed: it MUST NOT be auto-accepted, rewound, or laundered through idempotent reconciliation. The merge-carrier case remains the repository-governance contract of historical exact-head read-only reconciliation plus fresh current-main authorization; stale authorization is not replayed.

Connector ingress remains only the bounded untrusted `EFFECT_REQUEST` transport. It grants no routing, successor, retry, merge, terminal, or success authority. The repository-owned application derives formal effects from fresh current truth and observed postconditions. The carrier hard-exit and application/carrier separation are owned by `repository-governance`; this requirement consumes that contract without moving or duplicating its ownership.

Existing pre-activation behavior for `Change: unset` SHALL remain compatible. Explore/Propose may use the current pre-activation contract, and the active-formal provenance guard SHALL NOT require a Change before the approved pre-activation transition.

The repair SHALL remain subtraction/reuse within the existing surfaces. It SHALL NOT introduce a new Action or Result kind, registry, cursor, lease, heartbeat, retry state, mailbox, second DAG, carrier protocol, generic recovery/provenance framework, dedicated GitHub App/token architecture, or unrelated #218, #207, or #180 scope.

#### Scenario: A later wake resumes only the first incomplete slice

- GIVEN a verified slice has a durable checkpoint, an interruption occurs, and the next slice remains incomplete
- WHEN a later fresh repository-owned Actions/application wake reconstructs the current Change, implementation head, task evidence, and postconditions
- THEN it selects the first incomplete slice
- AND it does not replay the verified slice or treat historical connector output as formal completion
- AND it may derive only the existing qualified transition after the current checkpoint obligation and postcondition are durable

#### Scenario: The approved formal boundary cannot be widened by connector ingress

- GIVEN an active Change receives a connector-authored direct route, terminal/close mutation, or success claim
- WHEN the application freshly reconstructs the active formal state
- THEN the direct mutation is classified `INDETERMINATE` and fails closed
- AND the bounded `EFFECT_REQUEST` transport remains untrusted and cannot authorize routing, successor, retry, merge, terminal, or success
- AND no new Action, Result, recovery state, or provenance framework is created
