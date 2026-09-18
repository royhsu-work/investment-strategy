# scheduled-agent-workflow delta

## MODIFIED Requirements

### Requirement: One persistent coordination Issue represents the normal OpenSpec workflow lifecycle

The workflow SHALL use one persistent coordination Issue for one routed work item through any optional pre-Propose Explore and, when a formal Change is authorized, through proposal, review, implementation, merge, archive review, archive merge, and final closure.

Before the change id exists, `explore-change` and `propose-change` MAY operate with `Change: unset`. `explore-change` MUST keep `Change: unset` and MUST NOT create a formal OpenSpec change solely to represent research. The normal route into Propose SHALL be a same-Issue `Lead / explore-change` result of evidence-backed `PROPOSAL_READY` followed by the repository-owned routing effect to `Lead / propose-change`. Once Lead persists a change id during `propose-change`, that identity MUST remain immutable for that Issue.

For an explicit Human request, established by the interaction layer, to materialize one bounded Formal Explore, materialization authority SHALL follow that qualified source decision rather than the physical connector/Agent writer. The requested materialization SHALL be complete only when fresh postconditions establish one open coordination Issue with `Change: unset` and exactly `action:explore-change`. A connector/Agent acting only as mutation carrier neither gains Human authority nor loses the source decision's bounded materialization authority because it is the physical writer. After complete materialization, ordinary pre-activation dispatch SHALL evaluate current canonical routing, WIP=1, and finish-first predicates without treating creator identity as an additional queue-eligibility dimension. An Agent recommendation without an explicit Human request or another repository-qualified producer remains advisory and MUST NOT recursively authorize routed work. Connector-authored materialization evidence MUST NOT satisfy a later Human-reserved decision that requires provenance-bound Human authority.

A coherently routed `Lead / propose-change + Change: unset` Issue MAY be selected operationally from current routing, including after an out-of-band routing mutation, but selection alone MUST NOT satisfy Propose's action-local semantic preconditions. Before persisting a Change identity, Propose MUST dereference the exact durable same-Issue Explore `ACTION_RESULT(PROPOSAL_READY)` and independently/reversely verify that each still-applicable material formalization claim is supported by the Explore claim's identified source/evidence and that feasibility evidence is sufficient for the meaning being formalized. `PROPOSAL_READY` MUST NOT be treated as permission to blindly trust unsupported Explore interpretation.

If that pre-activation source/evidence/feasibility chain is missing, ambiguous, stale, contradictory, unsupported, or incomplete but the same bounded problem remains researchable without a new Human-reserved decision, no Change identity SHALL be persisted and the legal correction SHALL route the same Issue to `Lead / explore-change` with `Change: unset`. This correction preserves the same Issue identity and original queue position; it is not dispatcher fallback and MUST NOT cause dispatch to authorize a later pre-activation Issue merely because more research is required. If resolving the gap requires a genuinely new Human-reserved requirement, scope/risk/architecture commitment, Lead MUST use the existing Human decision boundary instead. Once `Change:` is non-`unset`, material semantic correction MUST use the formal `Lead / resolve-question` / independent review loop rather than the pre-Change Explore correction path.

Normal clarification and review-correction transitions SHALL remain in the same coordination Issue unless a later repository contract explicitly introduces child workflow items.

A terminal Explore result that concludes `NO_CHANGE_REQUIRED` or `NO_GO` MAY complete and close the coordination/research Issue without creating or archiving a fake OpenSpec Change.

#### Scenario: Human-requested bounded Explore materializes atomically through a connector

- GIVEN the interaction layer has established an explicit Human request to create one bounded Formal Explore
- AND a connector/Agent is the physical GitHub mutation carrier
- WHEN the requested Explore is materialized
- THEN fresh postconditions establish one open coordination Issue with `Change: unset`
- AND exactly `action:explore-change` is present as canonical routing
- AND physical writer identity neither grants nor removes the bounded source-decision authority
- AND an Issue that exists without the requested routing is not treated as successful complete materialization

#### Scenario: Coherently routed connector-materialized Explore is origin-neutral for dispatch

- GIVEN a bounded Explore was materialized from an explicit Human request through a connector
- AND its current state is open with `Change: unset + action:explore-change`
- WHEN repository-owned dispatch evaluates pre-activation work
- THEN it applies the same current routing, formal-first, WIP=1, and finish-first predicates used for other coherently routed Explore work
- AND creator identity is not an additional queue-eligibility dimension

#### Scenario: Agent recommendation does not recursively authorize routed work

- GIVEN an Agent recommends a new Explore
- AND there is no explicit Human materialization request or other repository-qualified producer for that bounded work
- WHEN the recommendation is evaluated
- THEN the recommendation remains advisory
- AND it does not by itself authorize creation of a routed coordination Issue

#### Scenario: Connector materialization does not satisfy later reserved Human authority

- GIVEN a connector materialized a bounded Explore from an explicit Human request
- WHEN a later workflow boundary requires provenance-bound Human authority for a new commitment, scope, risk, or architecture decision
- THEN the connector-created Issue/event alone is insufficient Human proof
- AND the existing reserved Human authority contract remains required

#### Scenario: Explore remains pre-Change

- GIVEN an open coordination Issue is coherently routed to `Lead / explore-change`
- AND `Change:` is unset
- WHEN Lead investigates the problem
- THEN the Issue remains `Change: unset`
- AND no `openspec/changes/<id>/` artifact set is created by Explore
- AND generic Human admission is not required solely to execute that bounded research action

#### Scenario: Lead selects a change id only after Propose entry

- GIVEN a coordination Issue has reached current `Lead / propose-change` routing
- AND `Change:` is not yet set
- AND the exact durable same-Issue Explore result is evidence-backed `PROPOSAL_READY`
- AND Propose independently verifies the material source/evidence chain and feasibility support the current formalization direction
- WHEN Lead creates or selects the OpenSpec change id
- THEN Lead persists that change id on the coordination Issue
- AND later scheduled runs treat the persisted change id as immutable workflow identity
- AND no direct Human-to-Propose admission path is available as an alternative normal intake route

#### Scenario: Researchable Propose evidence gap returns the same Issue to Explore

- GIVEN an open coordination Issue is coherently routed to `Lead / propose-change + Change: unset`
- AND dispatch selects it from current operational routing
- AND Propose finds the material Explore source/evidence/feasibility chain incomplete, unsupported, stale, ambiguous, or contradictory
- AND the same bounded problem remains researchable without a new Human-reserved decision
- WHEN Lead evaluates formal activation
- THEN no Change identity is persisted
- AND repository-owned application routes the same Issue to `Lead / explore-change + Change: unset`
- AND the Issue retains its original GitHub identity and `created_at` queue position
- AND dispatch does not authorize a later queued Issue merely because this action-local evidence requires more research

#### Scenario: Propose evidence gap requiring Human authority does not invent a correction

- GIVEN a selected pre-activation Propose cannot complete its evidence/feasibility basis
- AND resolving the gap requires a genuinely new Human-reserved requirement, scope, risk, or architecture decision
- WHEN Lead evaluates the gap
- THEN Lead uses the existing provenance-bound Human decision boundary
- AND the model does not weaken the requirement or choose a new commitment merely to avoid Human escalation
- AND a later queued Issue is not selected as semantic fallback

#### Scenario: Activated Change does not return to pre-Change Explore

- GIVEN the coordination Issue already has a non-`unset` immutable Change identity
- AND a material semantic correction is required
- WHEN the workflow resolves that correction
- THEN it uses `Lead / resolve-question` and independent `Reviewer / review-openspec` as governed
- AND it does not route backward to pre-Change Explore

#### Scenario: Explore concludes without a repository change

- GIVEN Lead has reached a decision-complete `NO_CHANGE_REQUIRED` or `NO_GO` Explore conclusion
- AND no formal Change identity was created
- WHEN Lead persists the bounded terminal research evidence
- THEN Lead may close the coordination/research Issue as completed
- AND the workflow does not create a fake OpenSpec Change only to obtain archive semantics
