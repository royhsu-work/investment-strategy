## MODIFIED Requirements

### Requirement: Explicit required deferred follow-up becomes durable before lifecycle completion

When an approved Lead-owned specification or scope decision explicitly classifies work as required separate follow-up or work that MUST still be handled later, the workflow SHALL treat that decision as a durable tracking obligation.

Ordinary out-of-scope statements, non-goals, optional future ideas, and work merely not selected for the current change MUST NOT create this obligation by themselves.

Lead SHALL explicitly classify required separate work and identify its bounded identity, exact source coordination Issue/Change and decision/reference, and affected dependent Issue identities, if any, within the approved decision authority. The repository Application SHALL consume the qualified durable decision at the defer boundary and create or reuse its tracker under the routing-complete requirement. That decision permits only the canonical pre-activation Explore tuple; it MUST NOT manufacture a reserved Human approval or formal activation.

`Reviewer / review-openspec` SHALL treat an approved required-defer decision without reconstructable durable tracker/linkage as a material finding. `Lead / finalize-archive` SHALL reconstruct still-applicable required-defer obligations before `LIFECYCLE_COMPLETE` and MUST NOT complete the lifecycle while a required tracker is missing. If the obligation and intended tracker are unambiguous and only materialization was missed, the mapped Lead MAY request the existing Application-owned idempotent repair; it MUST NOT reinterpret ambiguous scope, directly mutate the tracker or manufacture Human admission. Independent review SHALL verify the exact source, tracker and prerequisite evidence, rather than merely trusting a prior READY or worker summary.

Tracker idempotency SHALL rely on durable source linkage rather than title similarity alone.

#### Scenario: Ordinary scope exclusion creates no tracker obligation

- GIVEN an approved change marks an idea as out of scope without saying it must be handled later
- WHEN Reviewer and Lead reconstruct deferred work
- THEN no required follow-up tracker is demanded for that statement

#### Scenario: Required deferred work must have a durable tracker

- GIVEN an approved Lead decision explicitly says work W must be handled in a separate later change
- WHEN Lead records that defer decision
- THEN Application creates or reuses a tracker linked to the source Change/Issue and decision evidence
- AND the tracker receives only the authorized pre-activation Explore tuple, not reserved Human approval or formal activation

#### Scenario: OpenSpec review catches a missing required tracker

- GIVEN the OpenSpec artifacts contain an approved required-defer obligation
- AND no reconstructable linked tracker exists
- WHEN Reviewer executes `review-openspec`
- THEN Reviewer records a material finding
- AND does not treat ordinary unrelated scope exclusions as missing trackers

#### Scenario: Lifecycle completion fails safe on missing required tracker

- GIVEN a Change is otherwise ready for `LIFECYCLE_COMPLETE`
- AND a still-applicable required-defer obligation lacks a durable tracker
- WHEN Lead executes terminal archive finalization
- THEN lifecycle completion is blocked until the tracker is durably established or the obligation is authoritatively superseded

#### Scenario: Required classification is not inferred from arbitrary text

- GIVEN a qualified decision explicitly registers a required follow-up and its bounded identity and affected dependents
- AND a worker omits the obligation from its requested effects or subsequent summary
- WHEN Application or Reviewer reconstructs the consequential boundary
- THEN the exact registered obligation remains applicable and must be accounted for
- AND ordinary unregistered prose or a merely optional proposal is not mechanically elevated into a registered obligation
- AND an independent Reviewer identifies a substantive unregistered required decision as a finding rather than treating machine silence as semantic acceptance

### Requirement: Operational execution eligibility remains orthogonal to lifecycle state

A Scheduled-Agent work item SHALL derive whether its next legal action is currently executable from the durable preconditions and evidence owned by that action without introducing a parallel lifecycle state for ordinary waits or blockers.

A formal workflow with a qualified unsatisfied Issue prerequisite or declared external prerequisite SHALL remain the same formal workflow, but SHALL be suspended and consume no execution slot. Other runnable work MAY progress under the existing admission, independent review, merge and mutation boundaries. WIP is not a count of unfinished Changes. A generic BLOCKED result or a transient/unknown observation alone is not proof of a persistent prerequisite; existing action-specific result, wait, exception, escalation and recovery evidence remains authoritative and MUST NOT be bypassed. An external declaration is operational and reversible by a qualified Lead/maintainer after fresh evidence that the actual condition clears; no universal external-condition evaluator, new lifecycle label, or Human approval per dependency is introduced.

Dispatch and Application SHALL reconstruct one dependency projection combining the current qualified explicit complete-set declaration and every still-applicable mandatory prerequisite derived from exact qualified required-follow-up decisions. A required follow-up decision SHALL identify the affected dependent Issue(s) within approved authority; split delivery MUST preserve those necessary prerequisites. Independently registered mandatory contributions MUST survive unrelated explicit-set replacements and concurrent independent contributions until exactly and authoritatively superseded. Explicit complete-set declarations retain their existing meaning for explicit edges; a source-derived mandatory edge is not withdrawn by omission from an explicit set. No second persisted dependency registry is introduced. When a qualified required obligation lacks its tracker, the affected dependent is suspended even if no earlier prerequisite was declared; no fabricated Issue node or persistent waiting state is introduced. If a producer itself is a dependent, the producer's exact already-accepted materialization continuation remains eligible only to complete its missing authorized effect, not to start a new semantic Action or bypass other prerequisites or cycle validation. After that completion, subsequent eligibility is evaluated normally. Only qualified terminal lifecycle completion, not closure alone, releases a still-required Issue prerequisite.

#### Scenario: Active workflow waits for an exact external gate

- GIVEN one formal workflow has a qualified external prerequisite declaration based on an observed nonterminal exact gate
- WHEN the scheduler evaluates other queued runnable work
- THEN the suspended workflow retains its formal identity and Action but consumes no execution slot
- AND another qualified runnable workflow may advance without bypassing its own gates
- AND the suspended workflow resumes only after a fresh qualified correction based on actual cleared gate evidence and current action reauthorization
- AND the wait does not create a new lifecycle state

#### Scenario: Multiple and shared prerequisites release independently

- GIVEN formal A depends on B and C, and B and C depend on D
- AND each is coherently routed and D has no outstanding prerequisite
- WHEN dispatch reconstructs current prerequisites
- THEN D is runnable while A, B and C are suspended
- AND after D's qualified completion, B and C are runnable and one is selected deterministically
- AND after B and C both qualify as completed, A resumes its original Action
- AND no completed work is replayed or historical Change identity rewritten

#### Scenario: All routed workflows are suspended

- GIVEN every routed workflow is suspended by a valid outstanding prerequisite
- WHEN complete current dispatch reconstructs eligibility
- THEN dispatch returns NO_WORK with reason `dependencies-unsatisfied`
- AND this result is not the idle-discovery `no-routed-work` envelope
- AND a later fresh dispatch recomputes readiness from current evidence
- AND closure without qualified successful completion does not satisfy an Issue prerequisite

#### Scenario: Cyclic declarations are invalid, not completed prerequisites

- GIVEN current qualified Issue declarations form a cycle
- WHEN dispatch reconstructs dependencies
- THEN no Action is authorized from that invalid graph
- AND a qualified corrected declaration may restore selection on a later fresh wake without a Human-reserved decision

#### Scenario: Human authority is genuinely required

- GIVEN the next legal action cannot continue without a Human-reserved decision
- WHEN Lead persists the governed Human escalation
- THEN the workflow remains the same active workflow
- AND the Human boundary is represented by the existing provenance-bound escalation/resume contract
- AND optional advice that is not legally required does not create equivalent blocking semantics

#### Scenario: Necessary prerequisite survives concurrent independent contributions

- GIVEN dependent A has a qualified explicit prerequisite B
- AND two independently qualified required-follow-up decisions identify A and distinct prerequisite trackers C and D
- WHEN the shared dependency projection is reconstructed in any observation order with complete current evidence
- THEN A retains B, C and D unless an exact applicable authority supersedes one of them
- AND an unrelated explicit-set replacement cannot erase C or D
- AND no whole-set rewrite or second dependency store is required to preserve the derived edges

#### Scenario: Missing tracker blocks its dependent without a pre-existing blocker

- GIVEN an exact registered necessary follow-up identifies A as dependent
- AND no source-linked tracker is yet durably observable
- AND A had no prior dependency declaration
- WHEN Dispatch and Application reconstruct current eligibility
- THEN A cannot advance past the required prerequisite
- AND unrelated runnable work is not suspended merely by that obligation
- AND no fake tracker number or graph node is inferred

#### Scenario: Producer-self obligation does not deadlock accepted completion

- GIVEN a producer is itself the identified dependent of a required follow-up
- AND its exact Application intent was accepted before the tracker postcondition was complete
- WHEN the same accepted materialization is reconstructed
- THEN only the authorized missing effect may continue under the existing continuation contract
- AND any independent blocker or graph cycle still prevents unsafe advancement
- AND the producer's later semantic work remains subject to the qualified prerequisite until it is satisfied

#### Scenario: Bare closure cannot release a mandatory source-derived prerequisite

- GIVEN a source-linked mandatory tracker is closed without qualified formal lifecycle completion
- WHEN eligibility is reconstructed
- THEN its dependent remains suspended
- AND exact qualified lifecycle completion of that same tracker releases the prerequisite without a dependency comment mutation

### Requirement: Required separate follow-up is directly queueable for fresh Explore revalidation

When an approved Explore, specification, or lifecycle decision explicitly classifies work as a still-applicable required separate follow-up, that exact qualified durable defer decision SHALL be sufficient repository authority for Application to create or reuse one corresponding tracker as `Change: unset + action:explore-change` pre-activation work. Lead remains the derived Role and semantic owner.

The tracker MUST retain reconstructable linkage to the source coordination Issue/Change and exact defer decision/reference. Ordinary out-of-scope work, non-goals, optional ideas, speculative cleanup, and merely deferred/uncommitted prose MUST NOT gain admission from this requirement.

Materialization MUST be idempotent and MUST participate in the existing combined pre-activation queue; it MUST NOT create a parallel backlog/status vocabulary.

#### Scenario: Required follow-up is created at the defer boundary

- GIVEN an approved decision states that bounded work is required to be handled separately
- AND no equivalent unresolved tracker exists
- WHEN Lead persists the defer obligation
- THEN Application creates one tracker with reconstructable source linkage
- AND establishes `Change: unset + action:explore-change`
- AND later Explore fresh-reads whether the obligation remains warranted before any formal Change activation

#### Scenario: Optional future work is mentioned

- GIVEN a proposal or discussion identifies optional future work or a non-goal
- WHEN the current Change records that scope boundary
- THEN no pre-activation workflow admission is created solely from that mention

### Requirement: Required separate follow-up work is materialized as one routing-complete postcondition

When an approved specification, scope, or lifecycle decision explicitly classifies work as a required separate/deferred follow-up, the repository Application MUST derive the necessary effects of that obligation independently of the worker's requested-effects list. Completion is one logical postcondition consisting of exactly one deduplicated durable tracker with `Change: unset`, exact source coordination/change and defer-decision/reference linkage, canonical `action:explore-change` routing for new admission, and the applicable dependency preservation contract. Role is derived, not an additional routing label. A valid later qualified descendant or terminal completion of that same tracker MUST be adopted without rewinding it to Explore.

Creating or reusing the tracker without completing the required routing MUST NOT satisfy the obligation. Before creating a new tracker or repairing an incomplete one, Application MUST fresh-read the relevant durable trackers and exact qualified source obligation. If exactly one matching tracker exists and is incomplete only in materialization fields the source authority permits, Application MUST repair that tracker idempotently rather than create a duplicate. If multiple or ambiguous matching candidates exist, or the source obligation cannot be reconstructed exactly, Application MUST reject the unsafe mutation rather than guess, duplicate, or infer authority from tracker prose. An incomplete read is not proof of absence. After an unknown response, Application MUST adopt a uniquely qualified positive postcondition and continue only missing effects, or reissue only on qualified proof of non-attempt/noncommit and exact fresh reauthorization. Absence, repeated reads, elapsed time, and run completion alone MUST NOT manufacture such proof. Recoverable evidence gaps use the existing continuation/reconstruction boundary, not a new permanent terminal state. Eventual delivery and correctness remain the approved acceptance outcomes; if the lawful actuator cannot satisfy them under the relevant failure model, the unresolved limitation MUST be returned through the existing Lead/Human decision authority instead of waiving the requirement or claiming completion.

Lifecycle preparation that is already responsible for reconstructing required separate-follow-up obligations MUST verify this same routing-complete postcondition. When a unique matching tracker is incomplete and the approved source obligation still supplies the required authority, the Lead lifecycle owner MAY request the existing Application-owned repair before review handoff. Lifecycle preparation MUST NOT introduce a contradictory local rule that preserves an unrouted required tracker as complete.

Dispatcher admission remains unchanged: scheduled dispatch MUST consume canonical action-only routing and MUST NOT infer missing `action:*` routing from Issue body text, source linkage, or the existence of a required-follow-up obligation. The same reconstructed obligation and dependency completeness predicate SHALL protect applicable READY, PASS, lifecycle completion and successor persistence. A final accepted readiness/review outcome cannot substitute for the missing postcondition; the Explore source-result ordering below remains applicable.

#### Scenario: Required follow-up is created and routed as one logical result

- GIVEN an approved decision explicitly requires a separate follow-up
- AND no matching tracker exists
- WHEN Application materializes the obligation
- THEN exactly one tracker exists with `Change: unset`
- AND it records the exact source coordination/change and defer-decision/reference linkage
- AND it is routed to `action:explore-change`
- AND applicable prerequisite preservation is established
- AND the producer does not report the obligation complete before those properties are durably observable

#### Scenario: Interrupted create-before-route is repaired idempotently

- GIVEN an approved required separate-follow-up obligation remains applicable
- AND exactly one matching tracker already exists with exact source linkage and `Change: unset`
- AND the tracker is missing its required canonical Explore routing because an earlier materialization was interrupted
- WHEN Application reconstructs the obligation
- THEN it repairs that same tracker to `action:explore-change`
- AND it does not create a second tracker
- AND completion is recognized only after the repaired durable state is re-observed

#### Scenario: Ambiguous matching trackers fail closed

- GIVEN an approved required separate-follow-up obligation remains applicable
- AND more than one tracker plausibly matches the same required obligation
- WHEN Lead attempts materialization or repair
- THEN Lead does not choose a tracker by model judgment
- AND Lead does not create another tracker
- AND the obligation remains incomplete pending legal resolution of the ambiguity

#### Scenario: Tracker prose does not create routing authority

- GIVEN an Issue body describes itself as a required follow-up
- AND canonical `action:*` routing is absent
- WHEN scheduled dispatch reconstructs eligibility
- THEN the dispatcher does not infer `Lead / explore-change` from the prose
- AND the Issue is not admitted solely because its text resembles a required follow-up

#### Scenario: Optional or ordinary deferred work creates no required tracker

- GIVEN approved artifacts describe work only as optional, non-goal, ordinary out-of-scope, or uncommitted future work
- WHEN Lead evaluates separate-follow-up materialization
- THEN no required tracker/routing obligation is created from that text alone

#### Scenario: Lifecycle preparation repairs one uniquely incomplete required tracker

- GIVEN lifecycle preparation reconstructs an applicable approved required separate-follow-up obligation
- AND exactly one matching tracker exists with exact source linkage and `Change: unset`
- AND the tracker lacks canonical `Lead / explore-change` routing
- WHEN Lead prepares the lifecycle boundary for independent review
- THEN Lead treats the obligation as incomplete
- AND requests Application to repair the same tracker to the required routing when current authoritative source evidence still permits that repair
- AND does not hand off lifecycle review while the required postcondition remains incomplete

#### Scenario: Omitted effect cannot bypass READY or PASS

- GIVEN an independently qualified registered obligation applies at a consequential boundary
- AND the worker submits READY or PASS with no requested tracker effect
- AND the exact tracker or required dependency is incomplete
- WHEN Application reconstructs completion
- THEN the result cannot qualify the consequential boundary or advance the successor before the required postcondition
- AND Application derives only authorized missing effects or preserves the existing recovery boundary
- AND Reviewer independently records material findings for a missing required postcondition

#### Scenario: Unknown create outcome is reconciled from source evidence

- GIVEN an authorized create may have committed but its response was lost
- WHEN a later Application invocation reconstructs that exact accepted intent
- THEN incomplete or negative reads alone do not authorize another create
- AND a unique qualified source-linked committed tracker is reused and only the missing suffix is applied
- AND a first or repeated create is authorized only when its exact non-attempt or noncommit is qualified and the current source and target preconditions still hold
- AND multiple matches are a conflict, not permission to create or guess

#### Scenario: Already advanced tracker is not rewound

- GIVEN the source-linked tracker has qualified later routing or terminal completion
- WHEN a producer or reviewer reconstructs its obligation
- THEN that exact tracker remains the one target
- AND no new tracker, replay, or rewind to Explore is authorized

### Requirement: Explore-originated required follow-up decisions are materialized before Propose and preserved through formalization

When decision-complete `Lead / explore-change` explicitly classifies bounded later work as a **required separate follow-up**, the exact durable Explore `ACTION_RESULT` that establishes `PROPOSAL_READY` SHALL record that required-follow-up decision and sufficient bounded identity to reconstruct the intended separate work. After that result is durable and therefore supplies the exact defer-decision reference, Application MUST create, reuse, or repair the required tracker under the existing routing-complete required-follow-up contract and MUST NOT complete routing of the source Issue to `Lead / propose-change` until a fresh observation proves the required tracker and applicable prerequisite postcondition. Where the Explore result is the source reference, persisting that source result before materialization supplies evidence only and MUST NOT by itself qualify completion, successor eligibility, or replay authorization.

Ordinary deferred, optional, non-goal, or out-of-scope work MUST NOT gain a tracker obligation merely from presentation wording such as `Deferred work`, `follow-up`, `out of scope`, or `separately reviewable`. Work whose exact separate tracker is already durably established MUST reuse that tracker and MUST NOT create a duplicate.

If the Explore result is durable but materialization or successor routing is interrupted, reconstruction SHALL consume that same exact Explore result and complete only the missing idempotent materialization/routing effects. It MUST NOT create a second defer decision, infer a replacement classification from prose, or treat a partially materialized tracker as complete.

For an Explore-originated `Lead / propose-change`, Lead MUST dereference the exact durable Explore `ACTION_RESULT`, preserve every still-applicable required-follow-up classification from that result in proposal/readiness evidence, and fresh-verify the corresponding routing-complete tracker state before declaring OpenSpec readiness. If exactly one matching tracker is incomplete only in fields/routing that current source authority permits Lead to establish, Propose MAY request Application to repair only those missing parts under the existing idempotent materialization contract. Missing source authority, multiple/ambiguous matches, or contradictory tracker evidence MUST fail closed.

Propose MUST NOT downgrade a required separate-follow-up decision into ordinary deferred prose merely by excluding that later work from the current Change, and MUST NOT upgrade ordinary deferred/optional prose into a required follow-up without the approved source decision. Reviewer and lifecycle responsibilities remain those of the existing global required-follow-up contract; this requirement adds no new Reviewer producer authority or lifecycle topology.

#### Scenario: Explore materializes a newly required separate follow-up before successor routing

- GIVEN `Lead / explore-change` reaches a decision-complete direction
- AND that decision explicitly requires bounded later work to be handled as a separate follow-up change
- WHEN Lead records the durable `PROPOSAL_READY` Explore `ACTION_RESULT`
- THEN that exact result records the required-follow-up classification and bounded follow-up identity
- AND Application creates, reuses, or repairs exactly one tracker linked to the exact source coordination/change and that durable defer-decision reference
- AND a fresh observation proves `Change: unset` plus `action:explore-change` on the tracker
- AND only after that postcondition is complete may the source Issue complete routing to `Lead / propose-change`

#### Scenario: Interrupted Explore materialization resumes from the same durable decision

- GIVEN the exact Explore `ACTION_RESULT` already durably records `PROPOSAL_READY` and one required separate-follow-up decision
- AND the source Issue remains routed to `Lead / explore-change` because tracker materialization or successor routing was interrupted
- WHEN a later Explore invocation reconstructs that source
- THEN it consumes the existing exact Explore result rather than creating a new defer decision
- AND it fresh-reads matching trackers
- AND Application creates or repairs only the missing routing-complete postcondition when uniquely authorized
- AND multiple or ambiguous matches fail closed rather than creating another tracker

#### Scenario: Ordinary deferred wording creates no tracker obligation

- GIVEN an Explore result or formal proposal describes later work as `Deferred work`, `out of scope`, `follow-up`, or `separately reviewable`
- BUT the approved Explore decision does not classify that work as required separate follow-up
- WHEN Explore or Propose evaluates tracker materialization
- THEN no required tracker is created from that wording alone
- AND the existing semantic distinction between ordinary deferred work and required separate follow-up is preserved

#### Scenario: Propose preserves a required follow-up while keeping it outside current implementation scope

- GIVEN exact Explore result E records one required separate-follow-up decision
- AND the required tracker is routing-complete and linked to E
- WHEN the same coordination Issue enters `Lead / propose-change`
- THEN Lead dereferences E exactly
- AND proposal/readiness evidence preserves the required-follow-up classification and tracker reference
- AND the separate work MAY remain outside the current Change implementation scope
- BUT its required status is not downgraded to ordinary deferred prose
- AND Reviewer can independently reconstruct the same approved obligation and tracker at `review-openspec`

#### Scenario: Propose repairs only a unique incomplete required tracker

- GIVEN exact Explore result E records a required separate-follow-up decision
- AND exactly one source-linked matching tracker exists
- AND that tracker is incomplete only in durable materialization fields or canonical routing that current source authority permits Lead to establish
- WHEN `Lead / propose-change` prepares OpenSpec readiness
- THEN Lead requests Application to repair only the missing fields/routing
- AND does not create a duplicate tracker
- AND readiness is not reported until a fresh observation proves the routing-complete postcondition
- AND multiple or ambiguous matching trackers instead fail closed
