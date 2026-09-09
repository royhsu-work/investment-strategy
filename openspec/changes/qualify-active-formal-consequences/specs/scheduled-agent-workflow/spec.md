## MODIFIED Requirements

### Requirement: Active formal transitions require repository-owned provenance

When a coordination Issue has Change != unset, current-state reconstruction SHALL first qualify the current formal action:* routing or terminal/close boundary before the state may participate in dispatch or an application-derived consequence. Qualification SHALL bind the fresh current observation to the latest applicable repository-authorized transition and its exact durable postcondition, including the immutable Change, current Action/Role identity, relevant source and default-branch revisions, the accepted Action/Result, and the model-derived next_action when a successor exists.

The physical writer, connector, carrier, or GitHub Actions identity is not itself the qualification predicate. Connector-authored EFFECT_REQUEST remains only bounded untrusted transport; a carrier can write only under an application-authorized plan, while application authorization and the observed postcondition provide the qualification. A current route or terminal state that is merely structurally valid, equal to a requested target, or supported only by actor or timestamp identity is not qualified.

If no unique current binding to the latest applicable qualified transition and postcondition can be reconstructed, or if a later relevant mutation supersedes that binding, the current active formal state SHALL be classified as INDETERMINATE and fail closed before dispatch or consequence. A prior qualified transition MUST NOT qualify a later state merely because its value is equal, including an ABA return. The application MUST NOT auto-accept, auto-rewind, or launder such state through idempotent reconciliation. A qualified transition continues to use the existing finite Action/Result vocabulary and transition model.

Connector ingress remains limited to the bounded untrusted EFFECT_REQUEST transport needed by the current application bridge. Ingress does not grant routing, successor, retry, merge, terminal, or success authority; those effects remain application-derived and postcondition-bound.

Existing pre-activation behavior for Change: unset SHALL remain compatible: legitimate bounded Explore/Propose intake follows the current pre-activation contract and does not require active-formal provenance before Change is persisted.

#### Scenario: Direct active routing without application binding fails closed

- GIVEN a coordination Issue has Change != unset and a direct connector or other out-of-band mutation makes a syntactically valid action:* route current without the applicable application authorization and exact postcondition
- WHEN current-state reconstruction or dispatch observes the active formal state
- THEN the transition is classified INDETERMINATE
- AND the application fails closed without accepting the route or deriving a successor
- AND it does not auto-rewind or launder the mutation through reconciliation

#### Scenario: Premature close without application binding fails closed

- GIVEN a coordination Issue has Change != unset and a direct connector or other out-of-band mutation closes the Issue or presents terminal evidence without the applicable application authorization and exact postcondition
- WHEN current-state reconstruction or the application freshly reconstructs the formal lifecycle
- THEN the close or terminal boundary is classified INDETERMINATE
- AND no terminal or success effect is accepted or derived
- AND the next legal handling remains governed by fresh repository-owned evidence rather than the direct mutation

#### Scenario: Repository-authorized formal transition remains qualified

- GIVEN a coordination Issue has Change != unset and the application has fresh authorization, emits the accepted Action/Result, binds the source and default-branch revisions and model-derived next_action, and observes its exact durable postcondition
- AND the physical writer may be a replaceable carrier acting under that authorization
- WHEN current-state reconstruction or the application reconstructs the current formal lifecycle
- THEN the action:* route or terminal/close boundary is classified QUALIFIED
- AND the existing executable Action/Role/transition model may proceed
- AND no new Action, Result kind, or routing state is introduced

#### Scenario: Equality without provenance is not qualification

- GIVEN a coordination Issue has Change != unset
- AND its current route equals the route requested by an application-derived effect
- BUT no fresh repository-authorized Action/Result and exact postcondition bind that route
- WHEN dispatch or application evaluates the consequence
- THEN the current state is classified INDETERMINATE
- AND equality does not authorize the route, successor, or terminal consequence

#### Scenario: An ABA return does not inherit historical qualification

- GIVEN a repository-authorized transition changes a value from A to B
- AND a later out-of-band sequence changes B to C and then C back to B
- WHEN fresh current state equals B
- THEN the earlier A-to-B qualification is not applicable to the current B
- AND the current active formal state is INDETERMINATE unless a later applicable repository-authorized transition and exact postcondition qualify it

#### Scenario: Exact carrier completion qualifies only after a later fresh wake

- GIVEN an exact repository-authorized CarrierPlan has been executed
- AND a later fresh wake observes its exact branch, PR, ref, or terminal postcondition
- AND the application authorization and formal Action/Result bind the resulting route or terminal consequence
- WHEN current-state reconstruction evaluates the active formal state
- THEN the state is classified QUALIFIED
- AND only still-missing application-derived effects may proceed
- AND the carrier does not supply routing, successor, retry, terminal, or success authority

#### Scenario: Change-unset pre-activation remains compatible

- GIVEN a coordination Issue still has Change: unset and is selected by the existing pre-activation Explore or Propose dispatch
- WHEN the application reconstructs the current pre-activation state
- THEN the existing compatibility contract remains applicable
- AND the active-formal provenance predicate is not used to require a Change before the approved Propose transition
