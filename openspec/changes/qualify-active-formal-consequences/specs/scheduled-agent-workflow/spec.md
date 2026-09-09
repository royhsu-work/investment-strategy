## MODIFIED Requirements

### Requirement: Active formal transitions require repository-owned provenance

When a coordination Issue has `Change != unset`, the existing scheduled-agent current-state owner SHALL classify the current formal routing or terminal/close boundary through one affirmative qualification chain before dispatch or an application-derived consequence may use it:

```text
accepted Action / Result
→ exact repository application authorization and mandatory application-owned correlation
→ model-derived routing or terminal consequence
→ exact durable postcondition
```

The qualification SHALL use the latest applicable binding for the same Issue and immutable Change and SHALL consume a complete relevant lifecycle observation for the current evaluation. Existing GitHub Issue lifecycle events MAY establish the order of relevant mutations and whether a later mutation superseded an earlier binding, including ABA analysis; event actor and timestamp are ordering metadata and do not supply authorization. If the relevant lifecycle observation is incomplete, contradictory, stale, or cannot establish one unique current binding, the current formal observation is `INDETERMINATE` and the existing fail-closed dispatch/application boundary applies. A unique current binding is `QUALIFIED`.

The physical writer, connector, carrier, or GitHub Actions identity is not itself the qualification predicate. Connector-authored `EFFECT_REQUEST` remains bounded untrusted transport, and a carrier remains an actuator under an application-authorized plan. The existing finite Action/Role/Result vocabulary and transition model remain the executable workflow owner.

#### Scenario: Connector-authored active routing fails closed

- GIVEN a coordination Issue has `Change != unset` and an out-of-band mutation makes a syntactically valid `action:*` route current without the exact application correlation and postcondition binding
- WHEN current-state reconstruction evaluates the active formal state
- THEN the state is `INDETERMINATE`
- AND the application does not accept the route or derive a successor

#### Scenario: Connector-authored premature close fails closed

- GIVEN a coordination Issue has `Change != unset` and an out-of-band mutation closes the Issue or presents terminal evidence without the exact application correlation and postcondition binding
- WHEN current-state reconstruction evaluates the formal lifecycle
- THEN the terminal boundary is `INDETERMINATE`
- AND no terminal or success consequence is accepted

#### Scenario: Incomplete lifecycle observation fails closed

- GIVEN a coordination Issue has `Change != unset`
- AND the lifecycle observation needed to determine whether a later relevant mutation superseded the candidate binding is incomplete or unavailable
- WHEN current-state reconstruction evaluates the formal lifecycle
- THEN the observation is `INDETERMINATE`
- AND no route, successor, terminal, or success consequence is accepted

#### Scenario: Repository-owned formal transition remains qualified

- GIVEN a coordination Issue has `Change != unset`
- AND existing formal evidence binds an accepted Action/Result to exact repository application authorization, mandatory application correlation, the model-derived consequence, and its durable postcondition
- AND a complete lifecycle observation identifies that binding as the latest applicable transition
- WHEN the application reconstructs the current formal lifecycle
- THEN the action route or terminal boundary is `QUALIFIED`
- AND the existing executable Action/Role/transition model may proceed
- AND no new Action, Result kind, or routing state is introduced

#### Scenario: Equality without current provenance is not qualification

- GIVEN a coordination Issue has `Change != unset`
- AND its current route equals a requested application-derived target
- BUT the current observation has no unique application-correlation binding and exact postcondition
- WHEN dispatch or application evaluates the consequence
- THEN the observation is `INDETERMINATE`
- AND value equality does not authorize the route, successor, or terminal consequence

#### Scenario: An ABA return does not inherit historical qualification

- GIVEN a repository-authorized transition changes a value from A to B
- AND a complete later lifecycle observation shows a relevant out-of-band sequence changes B to C and then C back to B
- WHEN fresh current state equals B
- THEN the earlier A-to-B binding is not the latest applicable qualification
- AND the current active formal state remains `INDETERMINATE` unless a later repository-authorized binding and exact postcondition qualify it

#### Scenario: Exact carrier completion qualifies only after a later fresh wake

- GIVEN an exact repository-authorized CarrierPlan has been executed
- AND a later fresh wake observes its exact branch, PR, ref, or terminal postcondition
- AND existing formal evidence binds that consequence to the application authorization
- WHEN current-state reconstruction evaluates the active formal state
- THEN the state is `QUALIFIED`
- AND only still-missing application-derived effects may proceed
- AND the carrier does not supply routing, successor, retry, terminal, or success authority

#### Scenario: Change-unset pre-activation remains compatible

- GIVEN a coordination Issue still has `Change: unset` and is selected by the existing pre-activation Explore or Propose dispatch
- WHEN the application reconstructs the current pre-activation state
- THEN the existing compatibility contract remains applicable
- AND the active-formal qualification chain is not used to require a Change before the approved Propose transition
