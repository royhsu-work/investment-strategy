## MODIFIED Requirements

### Requirement: Active formal transitions require repository-owned provenance

When a coordination Issue has Change != unset, current-state reconstruction SHALL first qualify the current formal action:* routing or terminal/close boundary before the state may participate in dispatch or an application-derived consequence. The state SHALL be accepted only when fresh evidence qualifies the transition as the result of a repository-owned GitHub Actions/application execution. The evidence MUST bind the accepted Action/Result, immutable Change, source and default-branch revisions, the model-derived next_action when a successor exists, and the exact observed durable postcondition. Syntactically valid Issue fields, labels, timestamps, or connector-authored comments alone are insufficient.

A connector-authored or other out-of-band direct formal routing or terminal/close mutation, and any transition whose repository-owned provenance is missing, incomplete, stale, ambiguous, contradictory, or unverified, SHALL be classified as INDETERMINATE and fail closed before dispatch or consequence. The application MUST NOT auto-accept it, auto-rewind it, or launder it through idempotent reconciliation. A qualified repository-owned Actions/application transition continues to use the existing finite Action/Result vocabulary and transition model.

Connector ingress remains limited to the bounded untrusted EFFECT_REQUEST transport needed by the current application bridge. Ingress does not grant routing, successor, retry, merge, terminal, or success authority; those effects remain application-derived and postcondition-bound.

Existing pre-activation behavior for Change: unset SHALL remain compatible: Explore/Propose selection may use the current pre-activation contract and does not require the active-formal provenance guard until a Change is set.

#### Scenario: Connector-authored active routing fails closed

- GIVEN a coordination Issue has Change != unset and a connector-authored direct comment or label mutation makes a syntactically valid action:* route current
- WHEN current-state reconstruction or dispatch observes the active formal state
- THEN the transition is classified INDETERMINATE
- AND the application fails closed without accepting the route or deriving a successor
- AND it does not auto-rewind or launder the mutation through reconciliation

#### Scenario: Connector-authored premature close fails closed

- GIVEN a coordination Issue has Change != unset and a connector-authored direct mutation closes the Issue or presents terminal evidence
- WHEN current-state reconstruction or the application freshly reconstructs the formal lifecycle
- THEN the close or terminal boundary is classified INDETERMINATE
- AND no terminal/success effect is accepted or derived
- AND the next legal handling remains governed by fresh repository-owned evidence rather than the connector mutation

#### Scenario: Repository-owned formal transition remains qualified

- GIVEN a coordination Issue has Change != unset and a repository-owned Actions/application run has fresh authorization, emits the accepted Action/Result, binds the source and default-branch revisions and model-derived next_action, and its exact durable postcondition is observed
- WHEN current-state reconstruction or the application reconstructs the current formal lifecycle
- THEN the action:* route or terminal/close boundary is classified QUALIFIED
- AND the existing executable Action/Role/transition model may proceed
- AND no new Action, Result kind, or routing state is introduced

#### Scenario: Equality without provenance is not qualification

- GIVEN a coordination Issue has Change != unset
- AND its current route equals the route requested by an application-derived effect
- BUT no fresh repository-owned Action/Result and exact postcondition bind that route
- WHEN dispatch or application evaluates the consequence
- THEN the current state is classified INDETERMINATE
- AND equality does not authorize the route, successor, or terminal consequence

#### Scenario: Exact carrier completion qualifies only after a later fresh wake

- GIVEN an exact repository-authorized CarrierPlan has been executed
- AND the later fresh wake observes its exact branch/PR/ref or terminal postcondition
- AND the application authorization and formal result bind the resulting route or terminal consequence
- WHEN current-state reconstruction evaluates the active formal state
- THEN the state is classified QUALIFIED
- AND only still-missing application-derived effects may proceed
- AND the carrier does not supply routing, successor, retry, terminal, or success authority

#### Scenario: Change-unset pre-activation remains compatible

- GIVEN a coordination Issue still has Change: unset and is selected by the existing pre-activation Explore/Propose dispatch
- WHEN the application reconstructs the current pre-activation state
- THEN the existing compatibility contract remains applicable
- AND the active-formal provenance guard is not used to require a Change before the approved Propose transition
