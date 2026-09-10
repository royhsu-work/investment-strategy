## MODIFIED Requirements

### Requirement: Active formal transitions require repository-owned provenance

When a coordination Issue has `Change != unset`, the existing scheduled-agent current-state owner SHALL build one current formal qualification input from:

- the exact current Issue, immutable Change, and Action or terminal/close candidate;
- the accepted typed Action/Result and model-derived consequence;
- the exact application-owned correlation for that authorization and consequence;
- the exact durable postcondition;
- a complete relevant lifecycle observation; and
- the absence of a later relevant mutation that supersedes the binding, including ABA.

The owner SHALL evaluate that input through one executable qualification decision and return only the existing `QUALIFIED` or `INDETERMINATE` provenance result. Every dispatch, routing, successor, terminal, and close consumer SHALL consume that same decision and SHALL NOT independently reconstruct consequence eligibility. All dimensions must be coherent and fresh for `QUALIFIED`; missing, incomplete, stale, ambiguous, contradictory, unverified, equality-only, or superseded evidence produces `INDETERMINATE` and uses the existing fail-closed path.

Lifecycle evidence SHALL establish relevant ordering and supersession only. Actor, connector, carrier, timestamp, physical writer, structural validity, and value equality do not supply application authorization. Equality MAY support postcondition reconciliation after qualification; it SHALL NOT authorize the consequence.

Qualification decides consequence eligibility and remains separate from mutation execution. Fresh application reauthorization, exact necessary effects, carrier separation, and fresh postcondition observation remain required after a `QUALIFIED` decision. The existing finite Action/Role/Result model remains the workflow owner.

This contract activates prospectively on default-branch merge. Workflows terminal before activation remain terminal. Existing `Change: unset` pre-activation admission does not require the active-formal qualification input.

#### Scenario: Connector-authored active routing fails closed

- GIVEN a coordination Issue has `Change != unset`
- AND an out-of-band mutation makes a syntactically valid `action:*` route current without one exact application binding
- WHEN the single qualification decision evaluates the active formal state
- THEN it returns `INDETERMINATE`
- AND dispatch and application consumers use that result without deriving a successor

#### Scenario: Connector-authored premature close fails closed

- GIVEN a coordination Issue has `Change != unset`
- AND an out-of-band mutation closes the Issue or presents terminal evidence without one exact application binding
- WHEN the single qualification decision evaluates the terminal boundary
- THEN it returns `INDETERMINATE`
- AND no terminal or success consequence is accepted

#### Scenario: Repository-owned formal transition remains qualified

- GIVEN a coordination Issue has `Change != unset`
- AND one current binding coherently identifies the accepted Action/Result, exact application authorization and correlation, model-derived consequence, durable postcondition, and complete relevant lifecycle ordering
- AND no later relevant mutation supersedes that binding
- WHEN the single qualification decision evaluates the current routing or terminal boundary
- THEN it returns `QUALIFIED`
- AND every consequence consumer reuses that result
- AND any mutation still requires fresh application reauthorization and postcondition observation

#### Scenario: Equality and ABA do not inherit historical qualification

- GIVEN a repository-authorized transition changes A to B
- AND a complete later lifecycle observation shows B changes to C and then returns to B without a later application binding
- WHEN fresh current value equals B
- THEN the historical A-to-B binding does not qualify the current consequence
- AND the single qualification decision returns `INDETERMINATE`

#### Scenario: Incomplete lifecycle observation fails closed

- GIVEN a coordination Issue has `Change != unset`
- AND relevant lifecycle ordering is incomplete or cannot prove that no later mutation superseded the candidate binding
- WHEN the single qualification decision evaluates the current consequence
- THEN it returns `INDETERMINATE`
- AND all consequence consumers use the existing fail-closed path

#### Scenario: Exact carrier completion qualifies only after a later fresh wake

- GIVEN an exact repository-authorized CarrierPlan has been executed
- AND a later fresh wake observes its exact postcondition and reconstructs the same application binding with complete lifecycle ordering
- WHEN the single qualification decision evaluates the current consequence
- THEN it returns `QUALIFIED`
- AND the carrier supplies no independent routing, successor, terminal, or success authority

#### Scenario: Change-unset pre-activation remains compatible

- GIVEN a coordination Issue still has `Change: unset` and is selected by the existing pre-activation Explore or Propose dispatch
- WHEN the application reconstructs the current pre-activation state
- THEN the existing compatibility contract remains applicable
- AND the active-formal qualification input is not required
