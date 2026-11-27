## MODIFIED Requirements

### Requirement: One persistent coordination Issue represents the normal OpenSpec workflow lifecycle

The workflow SHALL use one persistent coordination Issue for one routed work item through any optional pre-Propose Explore and, when a formal Change is authorized, through proposal, review, implementation, merge, archive review, archive merge, and final closure.

Before the change id exists, `explore-change` and `propose-change` MAY operate with `Change: unset`. Pre-activation `explore-change` MUST keep `Change: unset` and MUST NOT create a formal OpenSpec change solely to represent research. The normal route into Propose SHALL be a same-Issue `Lead / explore-change` result of evidence-backed `PROPOSAL_READY` followed by the repository-owned routing effect to `Lead / propose-change`. Once Lead persists a change id during `propose-change`, that identity MUST remain immutable for that Issue.

For an explicit Human request, established by the interaction layer, to open one bounded Formal Explore, materialization authority SHALL follow that qualified source decision rather than the physical GitHub writer. The interaction-layer producer that owns the requested GitHub mutation MUST materialize one open coordination Issue with `Change: unset` and exactly one `action:explore-change` routing label, and MUST NOT report materialization complete until a fresh GitHub read observes that complete tuple. This requirement does not grant Issue-creation or routing mutation capability to a Scheduled-Agent worker or repository application that does not already own it. A connector or Agent MAY physically perform the interaction-layer mutation without becoming the authority source. Physical writer identity MUST NOT remove the qualified Human materialization authority and MUST NOT by itself grant authority to an autonomous Agent recommendation. Issue prose alone MUST NOT be treated as the authority classifier for this boundary.

After coherent materialization, ordinary pre-activation queue eligibility SHALL be determined from current repository routing and existing formal-first, WIP=1, finish-first, and deterministic selection predicates without classifying the Issue by Human-versus-connector origin. The materialization event or connector writer identity MUST NOT satisfy a later Human-reserved decision; those decisions remain subject to the existing provenance-bound Human authority contract. An Agent-originated recommendation without an explicit Human request or another repository-qualified producer remains advisory and MUST NOT recursively authorize creation or routing of additional work.

A coherently routed `Lead / propose-change + Change: unset` Issue MAY be selected operationally from current routing, including after an out-of-band routing mutation, but selection alone MUST NOT satisfy Propose's action-local semantic preconditions. Before persisting a Change identity, Propose MUST dereference the exact durable same-Issue Explore `ACTION_RESULT(PROPOSAL_READY)` and independently/reversely verify that each still-applicable material formalization claim is supported by the Explore claim's identified source/evidence and that feasibility evidence is sufficient for the meaning being formalized. `PROPOSAL_READY` MUST NOT be treated as permission to blindly trust unsupported Explore interpretation.

If that pre-activation source/evidence/feasibility chain is missing, ambiguous, stale, contradictory, unsupported, or incomplete but the same bounded problem remains researchable without a new Human-reserved decision, no Change identity SHALL be persisted and the legal correction SHALL route the same Issue to `Lead / explore-change` with `Change: unset`. This correction preserves the same Issue identity and original queue position; it is not dispatcher fallback and MUST NOT cause dispatch to authorize a later pre-activation Issue merely because more research is required. If resolving the gap requires a genuinely new Human-reserved requirement, scope/risk/architecture commitment, Lead MUST use the existing Human decision boundary instead. Once `Change:` is non-`unset`, ordinary material artifact correction SHALL use the formal `Lead / resolve-question` / independent review loop. When the current executable model derives `explore-change` from a truthful nonterminal research disposition for that same activated Change, research SHALL preserve the existing Issue and immutable Change rather than using the pre-Change reset path. Such research does not accept revised artifacts, create a new Change, or authorize replacement materialization. Any later new or materially revised candidate SHALL obtain its own exact-revision validation and independent OpenSpec acceptance through the applicable deployed authoring capability.

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
- THEN ordinary material artifact correction uses `Lead / resolve-question` and independent `Reviewer / review-openspec` as governed
- AND any model-derived return to research preserves the same non-`unset` Change as formal research
- AND it never resets activation or treats that research as pre-Change intake

#### Scenario: Explore concludes without a repository change

- GIVEN Lead has reached a decision-complete `NO_CHANGE_REQUIRED` or `NO_GO` Explore conclusion
- AND no formal Change identity was created
- WHEN Lead persists the bounded terminal research evidence
- THEN Lead may close the coordination/research Issue as completed
- AND the workflow does not create a fake OpenSpec Change only to obtain archive semantics

#### Scenario: Activated research preserves identity without a replacement

- GIVEN an activated coordination Issue has one immutable Change and a qualified candidate withdrawal
- AND the remaining candidate work requires further research
- WHEN the existing model derives explore-change from the accepted truthful research result
- THEN the Issue remains open with the same immutable Change and one action:explore-change label
- AND no replacement PR or fresh artifact set is required to establish that research frontier
- AND accepted history, remaining requirements, dependencies, and recovery obligations remain intact

#### Scenario: Candidate withdrawal does not accept a replacement

- GIVEN an activated Change has withdrawn one exact unmerged candidate
- WHEN later work forms a new or materially different candidate under the same Change
- THEN the applicable authoring owner must use a separately qualified carrier and new exact-revision validation and independent semantic acceptance
- AND neither withdrawal nor the retired candidate's previous artifacts, tests, completion markers, review, or CI establishes acceptance of the new candidate

### Requirement: Explore exits on decision-complete dispositions

Lead SHALL treat an Explore invocation as complete when it can choose the next legal bounded disposition, rather than requiring exhaustive knowledge or a fixed research checklist. Completing an invocation does not by itself complete the investigation or the parent Change.

Before returning a result, each material unresolved question that could change the selected disposition MUST be resolved by evidence, shown to be non-blocking, identified as a genuine Human intent/authority decision, identified as remaining bounded research or a current blocking condition, or sufficient to establish a qualified no-change/no-go conclusion.

The legal Explore dispositions SHALL be the existing executable model's proposal-ready, research-required, human-decision-required, no-change-required, no-go, and blocked results. PROPOSAL_READY requires evidence for a concrete buildable direction that can be formally authored without inventing a material requirement or solution decision; within an existing valid authority envelope it does not require a second generic Human proceed decision. RESEARCH_REQUIRED states that bounded material investigation remains. HUMAN_DECISION_REQUIRED identifies a remaining decision belonging to Human intent or authority. BLOCKED identifies a current impediment without inventing readiness or terminal completion. NO_CHANGE_REQUIRED and NO_GO require their actual decision-complete semantic grounds and applicable lifecycle authority.

A withdrawn candidate or failed implementation mechanism SHALL NOT by itself establish that an activated parent outcome is complete, unnecessary, infeasible, or abandoned. In an activated Change, nonterminal research preserves the same immutable Change and remaining approved outcome. Pre-activation terminal research may close without creating a fake Change only through the existing applicable terminal contract. SPECIFICATION_BLOCKED is not a new Explore result and MUST NOT substitute for a decision-complete no-change/no-go conclusion.

Repository application SHALL derive the successor or terminal projection from the existing executable next_action model. Lead SHALL return truthful semantic progress and SHALL NOT claim readiness merely to obtain candidate withdrawal capability. Any successor executes only in a later fresh wake.

#### Scenario: Explore is proposal-ready inside authority envelope

- GIVEN Lead has resolved all material questions that would alter the proposed direction
- AND a bounded proposal can be authored without inventing material requirements or solution choices
- AND the result remains inside valid Human- or repository-authorized admission authority
- WHEN Lead evaluates the Explore disposition
- THEN the result is PROPOSAL_READY
- AND repository application derives the same-Issue Propose successor through the existing model
- AND that successor waits for a later fresh wake

#### Scenario: Explore finds no change is required

- GIVEN repository evidence already satisfies the problem or shows it is informational only
- AND the research Issue remains pre-activation with Change unset
- WHEN no material question remains that could require a repository change
- THEN Lead records NO_CHANGE_REQUIRED
- AND the existing qualified terminal contract may close the research Issue without creating a fake Change

#### Scenario: Explore reaches a current no-go

- GIVEN evidence shows the contemplated direction is currently infeasible or unjustified
- AND the research Issue remains pre-activation with Change unset
- WHEN that evidence is sufficient to choose the disposition
- THEN Lead records NO_GO
- AND records a material reconsideration condition when one is identifiable
- AND the existing qualified terminal contract may close the research Issue without creating a fake Change

#### Scenario: Remaining decision belongs to Human intent

- GIVEN technical/repository investigation has narrowed the problem and options
- AND the remaining material choice cannot be resolved without Human intent or authority
- WHEN Lead exits the current investigation step
- THEN Lead uses HUMAN_DECISION_REQUIRED
- AND repository application derives the existing resolve-question successor
- AND the exact provenance-bound Human decision remains required before that unresolved decision is treated as resolved

#### Scenario: Further bounded investigation remains

- GIVEN the same approved problem remains researchable
- AND material questions still require repository or technical evidence without a new Human commitment
- WHEN Lead returns the current bounded result
- THEN Lead uses RESEARCH_REQUIRED
- AND the existing model retains Explore for a later fresh wake
- AND the current pre-activation or formal Change identity is preserved

#### Scenario: Current impediment is not readiness or terminal completion

- GIVEN a current condition prevents completion of the bounded investigation
- WHEN Lead cannot truthfully claim proposal readiness or a qualified terminal conclusion
- THEN Lead records BLOCKED with the actual boundary and evidence
- AND application derives only the existing model's consequence
- AND the blocked result does not cancel the approved parent outcome or release its dependencies

### Requirement: Explore dispositions are structured bounded results with repository-derived effects

Lead / explore-change SHALL return exactly one structured bounded disposition from the current executable model: proposal-ready, research-required, human-decision-required, no-change-required, no-go, or blocked. Lead remains responsible for the semantic judgment. PROPOSAL_READY is valid only when the material evidence traceability contract is satisfied. Narrative result content MAY remain durable audit/traceability evidence, including material source/evidence references, but repository application MUST consume the bounded disposition directly and MUST NOT re-extract machine control state from free-form Markdown, Issue comments, or another model call.

After fresh source-action reauthorization, repository application SHALL derive the successor or terminal projection through the existing next_action model and preserve the current Issue and applicable immutable Change identity. The Human-readable workflow projection SHALL NOT become a second executable authority. The existing model derives Propose for proposal-ready, Explore for research-required or blocked, and resolve-question for human-decision-required. Qualified pre-activation no-change-required and no-go results use the existing terminal research contract; a withdrawn formal candidate does not itself supply terminal authority for its parent.

The worker MUST NOT independently choose an arbitrary successor routing tuple. Inconsistent or additional worker routing requests SHALL be rejected. The same repository-owned principle applies to Propose research correction: initial pre-activation correction preserves Change unset; a model-derived research correction of an existing Change preserves that same immutable identity. Neither correction grants a new authoring capability or replacement PR merely because its successor is selected.

An independently authorized exact candidate withdrawal MAY accompany an eligible truthful result only under the candidate-withdrawal contract. It SHALL remain one untrusted close-only semantic effect, independent of the model-derived route. It MUST NOT create a new Result, select routing, relax readiness or review gates, or make pre-activation research a formal artifact authoring action. These bounded capabilities SHALL reuse the existing application and finite model rather than create a second workflow DAG, generic workflow engine, model-call classifier, or hidden result state.

#### Scenario: Structured proposal-ready result derives Propose routing

- GIVEN current machine dispatch authorizes Lead / explore-change for pre-activation Issue N
- AND Lead returns valid evidence-backed structured PROPOSAL_READY
- AND application freshly reauthorizes the same source Action
- WHEN the Explore effect is applied
- THEN application derives same-Issue Lead / propose-change
- AND Change remains unset
- AND a later fresh dispatch consumes the new current routing

#### Scenario: Conflicting worker-chosen successor cannot override result

- GIVEN current machine dispatch authorizes Lead / explore-change
- AND the worker returns structured PROPOSAL_READY
- BUT also requests an inconsistent successor
- WHEN application validates effects
- THEN the worker-chosen successor is rejected
- AND only the result-derived legal Explore effect may be applied

#### Scenario: Propose correction cannot choose an arbitrary successor

- GIVEN current machine dispatch authorizes pre-activation Lead / propose-change for Issue N
- AND Propose validly concludes that additional bounded research is required under the same-Issue correction contract
- AND application freshly reauthorizes that same source Action
- WHEN the correction effect is applied
- THEN application derives only same-Issue Lead / explore-change with Change unset
- AND a worker-supplied different Issue or successor Action is rejected
- AND the original Issue and queue identity are preserved

#### Scenario: Human-decision result retains Explore ownership

- GIVEN current machine dispatch authorizes Lead / explore-change
- AND Lead returns structured HUMAN_DECISION_REQUIRED
- WHEN application consumes the result
- THEN the existing executable model derives Lead / resolve-question
- AND the existing provenance-bound Human escalation and response contract remains authoritative

#### Scenario: Terminal research results derive terminal effects

- GIVEN current machine dispatch authorizes pre-activation Lead / explore-change with Change unset
- AND Lead returns a semantically qualified structured NO_CHANGE_REQUIRED or NO_GO
- WHEN application consumes the result
- THEN it derives the existing legal pre-Change terminal research close and routing retirement
- AND no fake Change identity is created

#### Scenario: Narrative Markdown cannot redefine the bounded result

- GIVEN the structured worker disposition is one legal Explore result
- AND narrative content contains another Workflow, Action, or Result-looking field
- WHEN application determines the workflow effect
- THEN it uses only the validated structured disposition
- AND it does not parse narrative Markdown to reconstruct machine control state

#### Scenario: Existing-Change research uses the same model without a reset

- GIVEN current machine dispatch authorizes candidate work for an existing immutable Change
- AND a truthful accepted result derives Explore or Propose through the existing model
- WHEN application persists and observes that consequence
- THEN it preserves the same Issue and immutable Change
- AND it does not rewrite the Change to unset or infer that a replacement carrier already exists

#### Scenario: Withdrawal does not determine the semantic successor

- GIVEN an independently resolved withdrawal is an eligible close-only effect
- AND remaining candidate work truthfully requires research or a separate Human decision
- WHEN application completes the close and the current Action's formal result
- THEN it derives the successor solely from that truthful Action and Result
- AND it does not manufacture READY, a review handoff, terminal completion, or a replacement PR

## ADDED Requirements

### Requirement: Candidate withdrawal is independent of replacement readiness

Withdrawal of one existing unmerged candidate SHALL be a consequence distinct from preserving the parent requirement, researching or authoring another candidate, and accepting that later candidate. An already-resolved Human-authorized withdrawal MUST NOT require replacement proposal-readiness, implementation-readiness, a replacement PR, or a fresh artifact set. The coordination Issue SHALL remain open with the same immutable Change and still-applicable requirements, dependencies, accepted history, and recovery obligations.

Lead SHALL establish the exact resolved withdrawal decision and disposition all substantive newer Human input before requesting the close. A different unresolved question about the remaining candidate MAY be reported truthfully as human-decision-required or blocked; an unresolved decision about withdrawal itself MUST NOT be treated as permission to close. Connector identity, a generic authorization boolean, label presence, model output, or an accepted effect envelope alone SHALL NOT replace Human semantic authority. Repository application SHALL retain its existing fresh machine-source, effect, provenance, and postcondition qualifications; this contract does not invent a new approval field, approval state, or separate Human classifier.

The existing effect-contract owner SHALL define one finite candidate-withdrawal capability. New coverage SHALL be limited to derived Lead source Actions explore-change, propose-change, and resolve-question, an existing legal DEFAULT_BRANCH-evidence result, and an existing model-derived nonterminal successor within those candidate Actions. Existing resolve-question / ready retirement SHALL remain compatible. This capability SHALL NOT authorize a review-readiness, lifecycle-ready, terminal, Reviewer, Executor, finalize, or merge result to withdraw a candidate. Result truth remains independent of withdrawal eligibility, and successors SHALL always be derived by the existing next_action owner.

The semantic withdrawal effect SHALL name exactly one qualified same-repository, same-Issue, same-Change PR and its exact expected head, with operation pull-request-update and fields exactly equal to state closed. Application SHALL preserve unrelated PR, Issue, branch, and historical content. New Explore or Propose coverage MUST NOT grant ordinary PR title, body, base, reopen, mixed-field, content, ref, or replacement creation capability. Extra semantic effects, duplicate close obligations, multiple accepted owners, an already merged target, competing carriers, changed head, contradictory state, or incomplete qualification SHALL fail closed. Application-owned formal-result and routing projections are not additional worker-requested semantic effects.

One existing carrier qualification owner SHALL provide the source and target proof consumed by effect retention, cardinality validation, target qualification, reconciliation, and later supersession qualification. Before close, proof SHALL use the freshly authorized source, complete exact target evidence, and the immutable accepted close obligation without requiring a future formal result. Initial pre-ACCEPT withdrawal SHALL require a uniquely qualified open target; an already closed target SHALL not be claimed by a new acceptance. Only the exact durable accepted obligation may reconcile its already closed-unmerged postcondition. After close, a consumer of completed retirement SHALL bind that same original request and unique native ACCEPT, exact PR and head, observed closed-unmerged postcondition, and exact qualified formal consequence. Complete source event evidence SHALL establish ACCEPT no later than close and close no later than the attributed formal result; contradictory or unavailable ordering SHALL not be inferred from prose or identifiers.

The accepted obligation SHALL preserve the same raw or supported legacy original, body digest, provenance, supplied identity, result meaning, and complete retained nested effect semantics. Qualification SHALL reuse the shared accepted-original reader and preserve its legacy correlation and strict raw preflight policies. Historical accepted payloads SHALL not be rewritten, supplied with fabricated content, or treated as new unaccepted worker inputs. The existing accepted READY/FINDINGS and Lead READY retirement histories SHALL remain supported when their own exact evidence qualifies.

Repository application SHALL persist ACCEPT before consequential close, obtain the close through the existing exact carrier boundary, freshly observe closed-unmerged, and only then commit the truthful formal result and model-derived routing. If interrupted after ACCEPT, it SHALL resume only the same missing obligation. If close already succeeded, reconciliation SHALL observe it without another close write or semantic replay; a missing formal result or routing projection SHALL be completed through the same existing consequence owner. Completed descendants SHALL not be replayed or rewound.

Fresh formal-consequence completion SHALL recognize an accepted withdrawal obligation and consume the same exact carrier-owned closed-unmerged proof before any generic DEFAULT_BRANCH-evidence success. A valid default revision or an earlier formal record alone SHALL NOT qualify a currently reopened, changed-head, merged, competing, or otherwise contradictory withdrawn target. This narrow obligation check SHALL not impose a PR requirement on unrelated DEFAULT_BRANCH results or create another consequence owner.

A fresh process SHALL reconstruct the no-replacement research frontier from the accepted chain and current source objects, without invocation-local memory. Establishing that frontier SHALL not require readiness or existence of a future candidate. Later replacement creation remains a separate action-local capability with fresh-main construction, exact content ingress, unique carrier qualification, new validation, and independent semantic acceptance; withdrawal does not transfer old unmerged code, test design, completion markers, review, or CI.

#### Scenario: Exact withdrawal precedes replacement readiness

- GIVEN the Human has resolved withdrawal of one qualified exact unmerged candidate
- AND remaining work requires research and no replacement PR exists
- WHEN Lead returns the truthful eligible research result with one exact close-only effect
- THEN application may accept and execute that close without replacement readiness
- AND it observes closed-unmerged before the formal result and derived research route
- AND the original Issue and immutable Change remain open and preserved

#### Scenario: Separate remaining Human question does not undo resolved withdrawal

- GIVEN the withdrawal decision is already resolved and source-qualified
- AND a different decision about the future candidate still requires Human intent
- WHEN Lead truthfully returns an eligible human-decision-required result with the exact close-only obligation
- THEN withdrawal eligibility is evaluated independently of the remaining question
- AND the existing model derives the clarification successor after application completes the close
- AND the result does not claim that the remaining Human question is resolved

#### Scenario: Unresolved withdrawal grants no close authority

- GIVEN the Human has not resolved whether the existing candidate should be withdrawn
- WHEN the remaining question is presented for Human decision
- THEN Lead requests that decision without a candidate close effect
- AND label presence, generic authorization, or connector authorship does not substitute for the missing semantic decision

#### Scenario: Non-candidate or terminal result cannot borrow withdrawal capability

- GIVEN a worker submits a withdrawal under an ineligible source Action or result
- WHEN the shared effect contract qualifies the request
- THEN the request is rejected without a close
- AND review-readiness, lifecycle readiness, terminal completion, and mutation ownership are not inferred from the requested effect

#### Scenario: New candidate capability is close-only

- GIVEN an Explore or Propose worker has no ordinary PR-update permission
- WHEN it requests title, body, base, reopening, mixed close fields, ref changes, or replacement creation through withdrawal
- THEN the effect is rejected
- AND the new capability permits only the exact qualified state-closed obligation

#### Scenario: One semantic withdrawal cannot hide additional writes

- GIVEN a candidate result includes an exact close and another semantic effect or another close
- WHEN application constructs or requalifies its accepted intent
- THEN it rejects the ambiguous effect set
- AND it does not normalize away extra writes and falsely claim a close-only acceptance

#### Scenario: Current target mismatch fails before close

- GIVEN the requested PR head has changed or the PR is merged, competing, or not uniquely qualified
- WHEN application freshly evaluates the exact withdrawal target
- THEN it performs no close or replacement mutation
- AND it preserves the source obligation and precise failed boundary without rebinding the request to a new head

#### Scenario: Close does not depend on a future formal result

- GIVEN one immutable close obligation has been accepted for a fresh qualified open target
- AND its formal result has not yet been created
- WHEN the existing carrier is required to perform the close
- THEN pre-close qualification uses the accepted obligation and current exact target
- AND it does not require the later formal result as a prerequisite for its own effect

#### Scenario: Completed retirement requires causal source evidence

- GIVEN a consumer claims a closed candidate was withdrawn by an accepted result
- WHEN it qualifies the completed withdrawal
- THEN it verifies the exact original, unique ACCEPT, PR head, closed-unmerged state, formal consequence, and ACCEPT-before-close-before-formal ordering
- AND missing, duplicate, contradictory, or unrelated sources do not qualify through value equality or prose

#### Scenario: Interrupted accepted close resumes without replay

- GIVEN application accepted one exact withdrawal and execution stopped before the close completed
- WHEN a fresh process reconstructs that same accepted obligation
- THEN it performs only the still-missing qualified close through the existing carrier
- AND it does not run the semantic Action again or invent another accepted owner

#### Scenario: Lost close response does not close again

- GIVEN the exact accepted close is durable but formal result or routing is incomplete
- WHEN a fresh process observes the same closed-unmerged PR and accepted obligation
- THEN it performs no duplicate close write
- AND it completes only the missing qualified formal result or derived route

#### Scenario: No replacement frontier survives a process boundary

- GIVEN exact withdrawal, truthful research result, and derived routing are complete
- AND there is no replacement PR
- WHEN a fresh normal dispatch reconstructs current repository state
- THEN the same open Issue and immutable Change are eligible for their model-derived candidate Action
- AND missing replacement readiness does not make the accepted work invalid

#### Scenario: Raw and legacy accepted history preserves its protection

- GIVEN a qualified retirement originated from raw WORKER_RESULT or a supported legacy original
- WHEN the common proof reconstructs that accepted history
- THEN it preserves original bytes and digest, provenance, supplied identity, legacy correlation, and full retained effect equivalence
- AND it neither fabricates absent historical content nor transfers that history to another Issue, Change, PR, or head

#### Scenario: Historical accepted withdrawal lanes remain supported

- GIVEN an existing Lead READY retirement or accepted implementation READY and Reviewer FINDINGS retirement has complete qualifying evidence
- WHEN later same-Change carrier qualification consumes it
- THEN it remains supported under its applicable source and lifecycle proof
- AND the new candidate capability does not replay, rewrite, or retroactively reset that completed history

#### Scenario: Later candidate has its own acceptance boundary

- GIVEN an exact candidate withdrawal has completed
- WHEN later authoring seeks a same-Change replacement
- THEN the replacement must use its separately deployed authoring and materialization capability from fresh main
- AND it obtains new exact validation and independent semantic acceptance
- AND retired unmerged implementation, tests, markers, reviews, or CI do not satisfy those new gates

#### Scenario: Fresh acceptance cannot adopt an already closed candidate

- GIVEN an initial withdrawal request has no durable ACCEPT for its own exact close obligation
- AND its target is already closed-unmerged
- WHEN application evaluates initial acceptance
- THEN it rejects adoption of that completed close as a new withdrawal
- AND a local accepted-intent flag or matching current fields does not replace the missing causal accepted obligation

#### Scenario: Fresh formal completion observes the withdrawal postcondition

- GIVEN an exact withdrawal formal result is durable
- AND the target is now reopened, at another head, merged, competing, or otherwise contradictory
- WHEN a fresh process evaluates formal-consequence completion
- THEN it fails the same carrier-owned completed-withdrawal proof
- AND it does not return success merely because the current default revision is a valid SHA
