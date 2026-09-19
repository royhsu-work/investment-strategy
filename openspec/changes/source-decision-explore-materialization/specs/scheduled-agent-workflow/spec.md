## MODIFIED Requirements

### Requirement: One persistent coordination Issue represents the normal OpenSpec workflow lifecycle

The workflow SHALL use one persistent coordination Issue for one routed work item through any optional pre-Propose Explore and, when a formal Change is authorized, through proposal, review, implementation, merge, archive review, archive merge, and final closure.

Before the change id exists, `explore-change` and `propose-change` MAY operate with `Change: unset`. `explore-change` MUST keep `Change: unset` and MUST NOT create a formal OpenSpec change solely to represent research. The normal route into Propose SHALL be a same-Issue `Lead / explore-change` result of evidence-backed `PROPOSAL_READY` followed by the repository-owned routing effect to `Lead / propose-change`. Once Lead persists a change id during `propose-change`, that identity MUST remain immutable for that Issue.

For an explicit Human request, established by the interaction layer, to open one bounded Formal Explore, materialization authority SHALL follow that qualified source decision rather than the physical GitHub writer. The interaction-layer producer that owns the requested GitHub mutation MUST materialize one open coordination Issue with `Change: unset` and exactly one `action:explore-change` routing label, and MUST NOT report materialization complete until a fresh GitHub read observes that complete tuple. This requirement does not grant Issue-creation or routing mutation capability to a Scheduled-Agent worker or repository application that does not already own it. A connector or Agent MAY physically perform the interaction-layer mutation without becoming the authority source. Physical writer identity MUST NOT remove the qualified Human materialization authority and MUST NOT by itself grant authority to an autonomous Agent recommendation. Issue prose alone MUST NOT be treated as the authority classifier for this boundary.

After coherent materialization, ordinary pre-activation queue eligibility SHALL be determined from current repository routing and existing formal-first, WIP=1, finish-first, and deterministic selection predicates without classifying the Issue by Human-versus-connector origin. The materialization event or connector writer identity MUST NOT satisfy a later Human-reserved decision; those decisions remain subject to the existing provenance-bound Human authority contract. An Agent-originated recommendation without an explicit Human request or another repository-qualified producer remains advisory and MUST NOT recursively authorize creation or routing of additional work.

A coherently routed `Lead / propose-change + Change: unset` Issue MAY be selected operationally from current routing, including after an out-of-band routing mutation, but selection alone MUST NOT satisfy Propose's action-local semantic preconditions. Before persisting a Change identity, Propose MUST dereference the exact durable same-Issue Explore `ACTION_RESULT(PROPOSAL_READY)` and independently/reversely verify that each still-applicable material formalization claim is supported by the Explore claim's identified source/evidence and that feasibility evidence is sufficient for the meaning being formalized. `PROPOSAL_READY` MUST NOT be treated as permission to blindly trust unsupported Explore interpretation.

If that pre-activation source/evidence/feasibility chain is missing, ambiguous, stale, contradictory, unsupported, or incomplete but the same bounded problem remains researchable without a new Human-reserved decision, no Change identity SHALL be persisted and the legal correction SHALL route the same Issue to `Lead / explore-change` with `Change: unset`. This correction preserves the same Issue identity and original queue position; it is not dispatcher fallback and MUST NOT cause dispatch to authorize a later pre-activation Issue merely because more research is required. If resolving the gap requires a genuinely new Human-reserved requirement, scope/risk/architecture commitment, Lead MUST use the existing Human decision boundary instead. Once `Change:` is non-`unset`, material semantic correction MUST use the formal `Lead / resolve-question` / independent review loop rather than the pre-Change Explore correction path.

Normal clarification and review-correction transitions SHALL remain in the same coordination Issue unless a later repository contract explicitly introduces child workflow items.

A terminal Explore result that concludes `NO_CHANGE_REQUIRED` or `NO_GO` MAY complete and close the coordination/research Issue without creating or archiving a fake OpenSpec Change.

#### Scenario: Human-requested bounded Explore is atomically materialized

- GIVEN the interaction layer has established an explicit Human request to open one bounded Formal Explore
- WHEN that interaction layer uses its available connector or other mutation capability to materialize the request
- THEN the resulting coordination Issue is open
- AND its body records `Change: unset`
- AND it has exactly one `action:explore-change` routing label
- AND the interaction layer does not report materialization complete until a fresh GitHub read observes that complete tuple
- AND this does not grant Issue-creation capability to Scheduled-Agent repository application

#### Scenario: Physical writer does not redefine materialization authority

- GIVEN an explicit Human request has qualified one bounded Formal Explore for materialization
- AND a connector or Agent is the physical GitHub writer for the interaction layer
- WHEN the bounded tuple is materialized
- THEN writer identity does not remove the qualified source-decision authority
- AND writer identity does not become Human proof for any later Human-reserved decision

#### Scenario: Autonomous recommendation remains advisory

- GIVEN an Agent recommends a new Explore
- AND there is no explicit Human materialization request or other repository-qualified producer
- WHEN materialization authority is evaluated
- THEN the recommendation alone does not authorize Issue creation or routing
- AND it cannot recursively create additional queue work

#### Scenario: Materialized Explore remains subject to ordinary queue ordering

- GIVEN a connector-materialized bounded Explore has the coherent `Change: unset + action:explore-change` tuple
- AND another formal workflow currently occupies WIP
- WHEN dispatch evaluates current repository state
- THEN the Explore remains queued under existing formal-first and finish-first semantics
- AND its physical writer or origin does not bypass those predicates

#### Scenario: Incomplete materialization is not success

- GIVEN an explicit Human request requires a bounded Formal Explore
- AND an Issue exists but `Change: unset` or the required `action:explore-change` routing is absent or ambiguous
- WHEN the interaction layer observes the materialization postcondition
- THEN materialization is incomplete and fails closed
- AND the incomplete Issue is not reported as successful Formal Explore materialization

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
