## MODIFIED Requirements

### Requirement: Actionable workflow routing is one logical role/action tuple

An open coordination Issue SHALL be actionable as ordinary workflow work only when it contains exactly one valid `action:<action>` label whose Action exists in the current default-branch executable workflow topology. The logical Role/Action tuple SHALL be formed by deriving Role deterministically from that Action; Role SHALL NOT be stored as an independent canonical routing dimension after cutover.

`agent:*` labels SHALL NOT participate in normal post-cutover dispatch, ownership, cardinality, transition, or terminal-state classification. A legacy `agent:*` label observed after cutover is migration/debt evidence to be retired through the bounded migration/recovery procedure; it MUST NOT override or supplement the Action-derived Role.

Zero, multiple, or unknown `action:*` labels on an open coordination Issue that otherwise appears routed SHALL fail closed. The model MUST NOT infer the intended Action or Role from Issue prose, historical comments, prior routing, PR state, or conversation memory.

Repository-owned terminal closure SHALL make `closed + no action:*` the workflow-routing postcondition while preserving every unrelated label. A closed Issue retaining any `action:*` label SHALL remain current closed-routing debt until bounded terminal-retirement/recovery proves and completes the legal disposition.

#### Scenario: Open coordination Issue has valid routing

- GIVEN an open coordination Issue contains exactly one valid `action:review-openspec`
- WHEN production dispatch reconstructs current routing
- THEN the Issue has one valid logical routing state
- AND Role `Reviewer` is derived from the executable topology
- AND no persistent `agent:reviewer` label is required

#### Scenario: Closed terminal-pending Issue has the one legal exception

- GIVEN a coordination Issue is closed
- AND it still contains one workflow Action label because terminal retirement is incomplete
- WHEN production acquisition reconstructs unresolved state
- THEN the Issue remains bounded closed-routing debt
- AND queued work MUST NOT bypass that debt

#### Scenario: Closed completed Issue is terminal history

- GIVEN a coordination Issue is closed
- AND it contains no `action:*` label
- WHEN dispatch reconstructs current workflow state
- THEN the Issue is terminal history
- AND its historical comments or old `agent:*` labels do not make it current work

#### Scenario: Terminal research closure retires routing

- GIVEN an Explore result legally terminates without activating a formal Change
- WHEN repository-owned terminal application completes
- THEN the Issue is closed
- AND its workflow Action label is removed
- AND unrelated labels are preserved

#### Scenario: Concurrent unrelated label survives terminal routing retirement

- GIVEN an unrelated label is added before terminal retirement
- WHEN repository application removes workflow Action routing
- THEN the unrelated label remains present
- AND the terminal postcondition is still `closed + no action:*`

#### Scenario: Partial routing retirement remains observable

- GIVEN terminal retirement was interrupted before the Action label was removed
- WHEN a later wake reconstructs the closed Issue
- THEN the retained Action label remains an explicit recovery signal
- AND the workflow does not infer completion from prose

#### Scenario: Premature close retains an explicit recovery signal

- GIVEN an Issue is closed before its current workflow Action is legally finalized
- WHEN production state is reconstructed
- THEN the retained Action label exposes the premature close as routing debt
- AND recovery fails closed or completes only the governed terminal path

#### Scenario: Coordination Issue has conflicting role labels

- GIVEN post-cutover current routing has one valid Action
- AND stale legacy `agent:*` labels conflict with one another or with the Action-derived Role
- WHEN production dispatch evaluates the Issue
- THEN the Action remains the only canonical routing dimension
- AND the legacy Role labels are migration/debt evidence rather than alternate routing authority

#### Scenario: Multiple Actions fail closed

- GIVEN an open coordination Issue contains more than one `action:*` label
- WHEN dispatch evaluates routing
- THEN it fails closed
- AND it does not infer the intended Action from Role labels, history, or prose

### Requirement: Review and finalize actions have Lead-owned minimum gate contracts

The repository SHALL preserve the existing minimum semantic and revision-aware checks for `review-openspec`, `review-implementation`, `review-archive`, `finalize-change`, and `finalize-archive`. Procedural Skills MAY operationalize these checks but MUST NOT invent, weaken, or bypass them.

`review-openspec` SHALL require independent source/evidence → Explore → Proposal/Specs/Design/Tasks traceability, reverse-first then forward inspection, semantic contract/scope coherence, Human-intent preservation, and an exact semantic review target.

`review-implementation` SHALL require exact-current-head implementation coverage and an unambiguous PASS or actionable findings against the approved OpenSpec contract. A PASS SHALL transition to explicit Action `merge-implementation-pr`.

`review-archive` SHALL require exact-current-head Archive coverage, canonical archive correctness, lifecycle preparation, cleanup/retention obligations, and an unambiguous PASS or actionable findings. A PASS SHALL transition to explicit Action `merge-archive-pr`.

`finalize-change` and `finalize-archive` SHALL preserve lifecycle reconstruction, archive-automation ownership, Human-input freshness, immutable Change identity, terminal evidence, and Issue-close requirements. The executable topology SHALL derive finite successors/effects; semantic lifecycle judgment remains with the mapped Role.

#### Scenario: Reviewer performs OpenSpec review

- GIVEN Lead has produced Proposal, Specs, Design, and Tasks at exact revision R
- WHEN Reviewer performs `review-openspec`
- THEN Reviewer independently checks reverse and forward traceability against source evidence and Human intent
- AND PASS or findings are recorded against R without Reviewer rewriting the artifacts

#### Scenario: Lead evaluates implementation merge authorization

- GIVEN implementation review has independently passed exact head R
- WHEN lifecycle readiness is evaluated
- THEN no second Lead merge-authorization token is required
- AND the executable topology routes exact PASS to `merge-implementation-pr`
- AND merge-time preconditions remain Executor responsibilities

#### Scenario: Archive preparation completes before independent review

- GIVEN implementation merge is complete
- WHEN Lead performs the governed archive-preparation lifecycle work
- THEN deterministic archive preparation and required lifecycle evidence complete before `review-archive`
- AND Reviewer receives an independently reviewable exact Archive revision

#### Scenario: Archive review PASS routes directly to merge

- GIVEN Reviewer passes exact Archive revision R
- WHEN repository application consumes that PASS while source Action remains current
- THEN the executable topology derives `merge-archive-pr`
- AND no generic merge phase is inferred from history

#### Scenario: Human asks material question before implementation review PASS

- GIVEN direct Human input materially changes or questions the current review basis before PASS
- WHEN Reviewer evaluates freshness
- THEN the question is dispositioned under the existing Human-input contract
- AND PASS is not emitted from stale semantic evidence

#### Scenario: Finalize archive closes only after durable completion

- GIVEN Archive merge and required post-merge lifecycle work are durably complete
- WHEN Lead performs `finalize-archive`
- THEN terminal evidence is persisted before closure
- AND the Issue closes only after routing retirement and required postconditions are observed

#### Scenario: Implementation review PASS selects explicit implementation merge Action

- GIVEN Reviewer passes exact implementation revision R
- WHEN repository application validates the PASS
- THEN it derives `merge-implementation-pr`
- AND Executor Role is derived from that Action

### Requirement: Scheduled execution is at-least-once and state reconstructable

Every Scheduled-Agent action SHALL reconstruct relevant durable repository, Issue, Action, Change, PR, OpenSpec, GitHub Actions, Human-input, and specifically awaited external-resource state before deciding what remains to be done. Execution MUST NOT require memory of a previous Scheduled Task wake or assume that a previous run exited cleanly.

A worker result is staged input until repository-owned application fresh-observes and reauthorizes the exact source Issue + Action + immutable Change/revision predicates required by that effect. If the source Action already moved to the expected legal postcondition, application SHALL reconstruct completion idempotently and MUST NOT rewind routing. If current state moved incompatibly or became contradictory, application SHALL fail closed.

Before a consequential result/application boundary, the semantic action SHALL retain the existing direct-Human input freshness/disposition contract. Human-reserved decisions continue to require their separately governed provenance-bound authority predicate.

Once one mapped semantic Action reaches its legal result and repository-owned application durably applies/observes the resulting transition or terminal effect, that Scheduled Task wake SHALL end. A successor Action, including a same-Role successor, SHALL execute only on a later Scheduled Task wake after fresh neutral dispatch.

#### Scenario: Run stops after durable work but before handoff

- GIVEN action result evidence and target Action were durably persisted
- AND the wake stops before optional cross-role HANDOFF evidence is written
- WHEN a later wake reconstructs state
- THEN the target Action remains canonical current routing
- AND missing audit evidence may be completed without replaying the source Action

#### Scenario: Normal evidence write itself is unavailable

- GIVEN required durable result evidence cannot be written
- WHEN the action reaches its application boundary
- THEN it does not perform ownership-changing workflow mutation that depends on that missing evidence
- AND it exits only through the governed hard/external failure boundary

#### Scenario: Same-role action becomes immediately actionable

- GIVEN Action A completes and its legal successor B derives to the same Role
- WHEN application durably observes B
- THEN the current wake ends
- AND B waits for a later fresh dispatch despite being immediately actionable

#### Scenario: Cross-role routing ends the invocation

- GIVEN Action A completes and its successor derives to another Role
- WHEN application observes the successor
- THEN the current wake ends
- AND no same-wake model chaining occurs

#### Scenario: Just-triggered exact validation completes quickly

- GIVEN the selected Action just triggered exact validation resource R
- AND R reaches terminal state during bounded re-observation
- WHEN that terminal state is actionable inside the selected Action
- THEN the same wake consumes R before deciding the Action result

#### Scenario: Later wake resumes a real asynchronous wait

- GIVEN an earlier wake legally ended because an exact external resource remained genuinely unconsumable after required bounded re-observation
- WHEN a later Scheduled Task wakes
- THEN it fresh-reconstructs current Action and exact resource state
- AND continues only if repository dispatch still authorizes that Action

#### Scenario: Earlier merge transition already has causal descendants

- GIVEN a duplicate/stale result refers to an earlier merge Action
- AND current durable state already contains legal causal descendants of that merge
- WHEN application reconstructs state
- THEN it does not rewind to the merge Action
- AND it treats already-applied effects idempotently or fails closed on contradiction

#### Scenario: Consumption evidence is contradictory

- GIVEN durable evidence about whether a result/effect was consumed is contradictory
- WHEN a wake reconstructs state
- THEN it fails closed
- AND it does not infer a transition from prose or ordering guesses

#### Scenario: Human input arrives while Executor is preparing READY

- GIVEN direct Human input arrives while Executor is preparing an action result
- WHEN Executor reaches the consequential result boundary
- THEN the Human input is fresh-read and dispositioned before READY-equivalent control output is finalized

#### Scenario: Clearly non-substantive Human comment does not create lifecycle waiting state

- GIVEN a fresh direct-Human comment is clearly non-substantive to the current gate
- WHEN the owning Role applies the governed freshness rule
- THEN it may record/disposition the comment without inventing a new durable waiting state
- AND current routing remains governed by Action state

#### Scenario: Human-reserved decision remains provenance-bound

- GIVEN a decision would change a Human-reserved requirement, scope, risk acceptance, or architecture commitment
- WHEN the workflow evaluates authority
- THEN ordinary Human-input freshness is insufficient by itself
- AND the separately governed provenance-bound Human authority predicate remains mandatory

#### Scenario: Question belongs to another role authority

- GIVEN a fresh question requires semantic authority owned by another Role
- WHEN the current Role classifies the boundary
- THEN it does not answer outside its authority
- AND it uses the governed exception/question path rather than inventing a transition

#### Scenario: Repeated wake recognizes prior exact-comment disposition

- GIVEN a direct-Human comment was already durably dispositioned by exact comment identity
- WHEN a later wake reconstructs Human-input state
- THEN it recognizes that exact disposition
- AND does not repeatedly block on the same comment

#### Scenario: Connector-authored workflow message is not reclassified as direct-Human input

- GIVEN a workflow message was authored by the connector/automation surface
- WHEN Human-input freshness is evaluated
- THEN that message is not treated as direct Human authority merely because it appears on the Issue

#### Scenario: Already-applied result is not replayed backward

- GIVEN result X legally moved Issue I from Action A to Action B
- AND a duplicate application request for X arrives
- WHEN application observes B as the legal postcondition
- THEN it treats X as already applied
- AND it does not restore A or execute B in the same wake

### Requirement: Routing handoff persists evidence before ownership transfer

A Scheduled-Agent action SHALL persist required action/review result and revision-aware evidence before repository-owned application changes current Action routing. Before mutation, application SHALL fresh-read the exact source Issue/Action/Change and reject stale or contradictory state.

The executable topology SHALL derive target Action from source Action plus bounded typed result/effect. Repository application SHALL mutate only required workflow Action routing, preserve unrelated labels, and fresh-observe the target postcondition. Target Role SHALL be derived from resulting Action; no Role label mutation is required for normal routing.

When source and target Actions derive to different Roles, canonical `HANDOFF` MAY remain required as durable cross-role audit evidence after target Action is observed. Same-role transitions require no synthetic HANDOFF. In both cases the current wake ends after the selected Action is applied.

#### Scenario: Result is durable before ownership transfer

- GIVEN source Action result is ready
- WHEN repository application prepares a target Action transition
- THEN required result/revision evidence is durable first
- AND the source Action is fresh-reauthorized before mutation

#### Scenario: Another run has already changed routing

- GIVEN another run changed current Action before this result is applied
- WHEN application fresh-reads the Issue
- THEN it does not overwrite the newer Action
- AND it emits no false handoff for the stale result

#### Scenario: Routing changed but handoff write was interrupted

- GIVEN a cross-role target Action was durably observed
- AND writing the HANDOFF audit record was interrupted
- WHEN recovery runs
- THEN current Action remains authoritative
- AND recovery may complete missing handoff evidence without replaying source semantic work

#### Scenario: Same-role transition does not create synthetic handoff

- GIVEN source and target Actions derive to the same Role
- WHEN application observes the target Action
- THEN no HANDOFF is required solely for Role continuity
- AND the wake still ends after this Action

#### Scenario: Cross-role transfer still requires handoff

- GIVEN current governance requires a cross-role HANDOFF audit record
- AND target Action derives to a different Role
- WHEN application observes the target Action
- THEN HANDOFF is written from the observed transition evidence
- AND HANDOFF does not become routing authority

#### Scenario: Cross-role transition derives ownership from target Action

- GIVEN Lead Action A transitions to `review-openspec`
- WHEN target routing is observed
- THEN Reviewer ownership is derived from the target Action
- AND no `agent:reviewer` state mutation is necessary

### Requirement: Fresh-read plus label update is not treated as mutual exclusion

The workflow MUST NOT claim that `fresh-read Action → update Action label` provides a mutex, compare-and-swap primitive, or guaranteed single-flight execution.

Overlapping wakes SHALL remain safe through authoritative reconstruction, bounded typed results, fresh source-Action/Change/revision reauthorization, narrow idempotent effects, SHA/revision guards where available, first-valid-write-wins behavior where applicable, and fresh postcondition observation. The workflow MUST NOT add lock, claim, lease, heartbeat, retry counter, hidden sequence, or another durable ownership state solely to serialize model wakes.

#### Scenario: Two same-role runs observe the same tuple

- GIVEN two overlapping wakes observe the same source Action and therefore derive the same Role
- WHEN one result changes current Action first
- THEN the other result must fresh-reauthorize the source Action
- AND stale execution cannot overwrite the winner merely because both initial reads were valid

#### Scenario: Two workers receive the same Action

- GIVEN two workers were validly authorized for the same Action before either application completed
- WHEN one legal application wins
- THEN the second application proceeds only if its effect is already satisfied idempotently or remains independently legal
- AND otherwise fails closed

### Requirement: Executor merges only an explicitly authorized unchanged revision

Executor SHALL execute implementation merge only under Action `merge-implementation-pr` and Archive merge only under Action `merge-archive-pr`.

For `merge-implementation-pr`, durable evidence SHALL establish an unambiguous independent implementation Reviewer PASS for exact revision R, current PR head R, current required checks, applicable Human-input freshness/disposition, and absence of Issue-closing linkage to the persistent coordination Issue.

For `merge-archive-pr`, durable evidence SHALL establish an unambiguous independent archive Reviewer PASS for exact revision R, current Archive PR head R, current required checks, approved non-closing coordination-Issue reference, absence of closing linkage, applicable pre-review lifecycle preparation, and required cleanup/retention disposition.

No second Lead merge-authorization token is required. Exact-head Reviewer PASS remains acceptance authority, while fresh merge-time preconditions remain mandatory. Phase, head, review evidence, checks, linkage, Human-input state, lifecycle preparation, and cleanup evidence MUST all be current.

#### Scenario: Authorized implementation revision remains current without closing linkage

- GIVEN current Action is `merge-implementation-pr`
- AND exact implementation PASS exists for current head R
- AND required checks pass and the PR does not close the coordination Issue
- WHEN Executor fresh-verifies all merge gates
- THEN R may be merged

#### Scenario: Implementation PR would close the coordination Issue

- GIVEN an implementation PR contains closing linkage to the persistent coordination Issue
- WHEN Executor evaluates `merge-implementation-pr`
- THEN merge is not authorized
- AND the linkage must be corrected without closing the coordination Issue

#### Scenario: Archive PR has the approved closing linkage

- GIVEN an Archive PR uses closing linkage to the persistent coordination Issue
- WHEN Executor evaluates `merge-archive-pr`
- THEN merge is not authorized under the approved non-closing lifecycle contract
- AND the linkage must be corrected before merge

#### Scenario: Archive PR has the approved non-closing linkage

- GIVEN an Archive PR references the coordination Issue without closing it
- AND exact archive PASS and all lifecycle/cleanup gates are current
- WHEN Executor evaluates `merge-archive-pr`
- THEN the linkage gate is satisfied

#### Scenario: PR head changes after authorization

- GIVEN Reviewer PASS is bound to revision R
- AND the PR head changes to R2
- WHEN Executor fresh-reads the PR
- THEN the old PASS does not authorize merge of R2
- AND new exact-head review is required

#### Scenario: Human input arrives after Reviewer PASS but before merge

- GIVEN direct Human input arrives after exact-head PASS but before merge
- WHEN Executor performs merge-time freshness checks
- THEN the input is dispositioned under the existing Human-input contract
- AND merge does not proceed from stale authorization if the input is material

#### Scenario: Implementation merge Action cannot infer Archive phase

- GIVEN current Action is `merge-implementation-pr`
- AND the discovered target is an Archive PR
- WHEN Executor evaluates the merge
- THEN it does not infer a generic merge phase
- AND it fails closed

### Requirement: Merge recovery is idempotent and reconstructable

If either explicit merge Action succeeds but the wake stops before all result/application evidence is complete, a later invocation SHALL reconstruct exact PR/head/merge state and SHALL NOT attempt a duplicate merge. Recovery SHALL distinguish `merge-implementation-pr` from `merge-archive-pr` from current Action and durable PR identity rather than infer phase from historical prose.

#### Scenario: Merge succeeded before interruption

- GIVEN an explicitly authorized merge succeeded at exact revision R
- AND the wake stopped before the legal successor Action/evidence was fully observed
- WHEN recovery fresh-reconstructs PR and Issue state
- THEN it recognizes the completed merge
- AND does not attempt a duplicate merge
- AND completes only still-authorized result/transition work

#### Scenario: Archive merge recovery cannot reuse implementation PASS

- GIVEN recovery target is an Archive PR
- AND only implementation-review PASS exists
- WHEN `merge-archive-pr` is evaluated
- THEN implementation PASS is not accepted as archive authority
- AND recovery fails closed until archive evidence exists

### Requirement: Each scheduled run processes at most one actionable work item using a fixed stable order

A normal Scheduled-Agent invocation SHALL process at most one eligible coordination Issue and exactly one mapped semantic Action per wake.

Normal production selection SHALL use workflow-dynamic dispatch from the current default-branch executable topology/kernel. An open formal active workflow SHALL be selected before pre-activation intake. Current closed-routing debt SHALL be classified/recovered before queued pre-activation work. If neither exists, coherently routed pre-activation `explore-change` and `propose-change` Issues with `Change: unset` SHALL share one FIFO ordered by earliest GitHub `created_at`, then lower Issue number.

Selection SHALL use current structural Issue/Action/Change facts plus authoritative completeness/provenance and other machine-decidable kernel predicates. It MUST NOT parse historical result prose, transport comments, Issue narrative, or old Role labels to reconstruct normal current queue eligibility.

Legacy fixed-role Scheduled Task identity MUST NOT override workflow-dynamic selection in the normal post-cutover path. Any bounded migration/test compatibility surface for fixed-role execution MUST NOT become a second normal production selector.

#### Scenario: Dynamic mode follows the formal active workflow

- GIVEN exactly one formal active workflow exists
- WHEN a normal Scheduled Task wakes
- THEN dispatch selects that workflow's current Action
- AND Role is derived from Action
- AND queued pre-activation work is untouched

#### Scenario: Dynamic mode selects earliest pre-activation entry across Explore and Propose

- GIVEN no active formal workflow and no closed-routing debt exists
- AND valid Explore/Propose pre-activation Issues exist
- WHEN dispatch selects intake
- THEN it selects earliest creation time across both Action types
- AND lower Issue number breaks an exact timestamp tie

#### Scenario: Irrelevant result prose cannot alter pre-activation selection

- GIVEN a pre-activation Issue contains historical routing-looking/result prose
- WHEN current structural queue eligibility is evaluated
- THEN that prose does not change FIFO eligibility
- AND only current Action/Change state and executable predicates control selection

#### Scenario: Fixed-role Lead uses the same combined pre-activation winner

- GIVEN bounded migration/test compatibility invokes a fixed-role Lead selector
- WHEN it is still temporarily supported before cutover completion
- THEN it MUST NOT define a different pre-activation FIFO from the executable kernel
- AND it MUST be removed/disabled as a normal selector at cutover

#### Scenario: Open Explore remains selected without an in-progress marker

- GIVEN the oldest eligible pre-activation Issue remains open at `explore-change`
- AND no hidden claim/status marker exists
- WHEN a later wake reconstructs state
- THEN the same Issue remains selected until its Action changes or terminates

#### Scenario: Dynamic mode selects terminal reconstruction before queued work

- GIVEN closed-routing debt exists and queued intake also exists
- WHEN dispatch runs
- THEN it selects the bounded terminal/debt recovery path first
- AND queued intake cannot bypass unresolved routing debt

#### Scenario: One selected Action cannot chain into a second Action

- GIVEN dispatch authorizes Issue I Action A
- AND A completes and application derives successor B
- WHEN the applied result boundary is reached
- THEN the invocation ends
- AND B is not executed in the same wake

### Requirement: Repository agent artifacts expose the governance contract

Implementation SHALL provide `agents/AGENTS.md` as current-default-branch bootstrap/shared execution protocol; one executable workflow topology/kernel as machine-decidable owner of Action vocabulary, Action→Role derivation, finite result/transition topology, dispatch/cardinality, effect capabilities, fresh source authorization, stale/replay handling, and structural postconditions; `agents/workflow.md` as generated or mechanically verified Human-readable projection of that topology; role definitions for semantic mission/authority; mapped Skills for action-specific semantic procedure/evidence without duplicated transition tables; and message/documentation surfaces that do not redefine routing authority.

Scheduled Task prompts SHALL remain thin bootstrap/delegation surfaces. They MUST NOT duplicate the DAG, Action→Role mapping, successor rules, continuation policy, historical eligibility parser, or transport-mailbox semantics. ChatGPT Scheduled Tasks remain the only normal model wake. GitHub Actions MAY run deterministic repository control-plane code but MUST NOT host or invoke a model worker.

#### Scenario: Dynamic Scheduled Task bootstraps from repository governance

- GIVEN a normal Scheduled Task wakes
- WHEN execution begins
- THEN it loads current default-branch governance
- AND uses neutral executable dispatch rather than task-name/history inference
- AND executes only the one authorized mapped Action

#### Scenario: Human workflow documentation drifts

- GIVEN `agents/workflow.md` presents a machine-decidable transition that differs from executable topology
- WHEN repository validation runs
- THEN validation fails
- AND production runtime does not parse Markdown as an alternate DAG

### Requirement: Default-branch governance declares the scheduled dispatch mode

The repository SHALL declare exactly one authoritative `Scheduled-Dispatch-Mode` marker in current default-branch governance. The normal post-cutover Scheduled-Agent path SHALL use `workflow-dynamic` dispatch and SHALL NOT infer Role/Action from legacy task names, conversation memory, old Role labels, or feature-branch governance.

A fixed-role mode MAY exist only as an explicitly bounded migration/test/recovery compatibility mechanism and MUST NOT remain another normal Scheduled Task selector after cutover.

#### Scenario: Workflow-dynamic mode is declared

- GIVEN current default-branch governance declares `Scheduled-Dispatch-Mode: workflow-dynamic`
- WHEN a normal Scheduled Task wakes
- THEN repository-owned neutral dispatch is the only normal Issue/Action selector
- AND Role is derived from selected Action

#### Scenario: Fixed-role mode is declared

- GIVEN a fixed-role marker/path is encountered during the bounded migration compatibility window
- WHEN normal production execution is evaluated after cutover acceptance
- THEN that path is not a permitted normal Scheduled Task selector
- AND completion of this Change requires its normal production dependence to be removed or disabled

#### Scenario: Legacy task name does not select Role

- GIVEN a Scheduled Task has a historical Lead-like name
- AND executable dispatch selects `review-openspec`
- WHEN the task wakes
- THEN Reviewer is derived from Action
- AND the legacy name does not override dispatch

### Requirement: Workflow-dynamic dispatch derives one fixed invocation role from durable workflow state

In workflow-dynamic mode, a normal Scheduled Task wake SHALL use repository-owned executable dispatch to select one exact coordination Issue and Action from current authoritative state. Role SHALL be derived deterministically from that Action and SHALL govern only the semantic authority of that one mapped Action invocation.

After repository-owned application persists and observes that Action's legal successor or terminal effect, the current wake SHALL end. The successor MAY derive to the same Role or another Role, but no successor semantic Action SHALL execute until a later Scheduled Task wake fresh-loads current default-branch governance and performs neutral executable dispatch.

Repository code owns dispatch, typed transition, effects, and postconditions but SHALL NOT require an OpenAI API, Responses API, GitHub Actions-hosted model worker, direct model wake chaining, wake-role attestation, lease, heartbeat, or durable continuation cursor.

#### Scenario: Active workflow routes to Reviewer

- GIVEN the active workflow's current Action is `review-openspec`
- WHEN neutral dispatch authorizes that Action
- THEN invocation Role is Reviewer
- AND no stored Role label or task-name inference is required

#### Scenario: Handoff changes the next owner

- GIVEN source Action completion derives a target Action owned by another Role
- WHEN target Action is observed
- THEN the next wake's owner will be derived from that target Action
- AND HANDOFF evidence itself does not select the owner

#### Scenario: Same-role successor remains work-conserving

- GIVEN selected Action A is work-conserving internally
- AND its legal successor B derives to the same Role
- WHEN A's result is applied
- THEN all still-actionable work belonging to A must already have been consumed
- AND B nevertheless waits for a later wake because one-action-per-wake is the normal contract

#### Scenario: Cross-role barrier does not create durable wake state

- GIVEN selected Action A derives a target Action owned by another Role
- WHEN A completes
- THEN the wake ends without creating a wake-role token, lease, cursor, or barrier state
- AND the target Action itself is sufficient current state for later dispatch

#### Scenario: Prompt-level boundary does not claim a mechanical host guarantee

- GIVEN the external ChatGPT Scheduled Task host cannot be proven by repository code to enforce physical single-step model execution
- WHEN governance defines the normal execution contract
- THEN it requires the model invocation to stop after one mapped Action
- AND repository correctness does not depend on an unverifiable host-side mutex or model API

#### Scenario: Same-role successor waits for fresh wake

- GIVEN Lead Action A derives Lead Action B
- WHEN A is durably applied
- THEN current wake ends
- AND B requires later fresh neutral dispatch

### Requirement: Selected Scheduled Agent actions are work-conserving within an invocation

A selected mapped Action SHALL remain work-conserving internally until it reaches one action-defined result/application boundary or a genuine Human-reserved, external-asynchronous, stale/precondition, contradictory-state, or hard execution boundary.

Immediately actionable work that remains part of the selected Action MUST NOT be deferred merely because a RED/checkpoint/commit exists or validation first failed. Examples include RED→GREEN→REFACTOR/VERIFY within an approved implementation slice, correction of actionable validation failure inside current authority, completion of required Proposal/Spec/Design/Tasks authoring, and bounded re-observation/consumption of an exact just-triggered CI/validation resource.

Successful completion and deterministic application of the selected Action itself SHALL be a normal Invocation Exit. An immediately actionable successor Action, including a same-Role successor, MUST NOT extend the wake into a second mapped Action.

For an exact external resource just created/triggered by the selected Action, the existing bounded re-observation rule remains: a first absent/queued/in-progress observation alone is not sufficient ordinary asynchronous-wait Exit evidence while current Action/revision/authority still permits bounded consumption. At least one subsequent fresh observation of that same exact resource is required. Actionable terminal success/failure SHALL be consumed immediately.

Catchable execution exceptions SHALL retain shared raw-evidence capture and action-defined recovery/disposition requirements. An exception is not voluntary Exit while legal same-Action recovery remains immediately actionable.

#### Scenario: Failed validation is locally actionable

- GIVEN required validation fails for a correction within the selected Action's authority
- WHEN current source Action/revision/preconditions remain valid
- THEN the correction and validation rerun occur in the same wake
- AND the failure is not an Invocation Exit

#### Scenario: Verified implementation checkpoint has more approved work

- GIVEN an implementation checkpoint verifies successfully
- AND the same selected `implement-change` Action has additional approved immediately actionable work in its current slice
- WHEN Executor evaluates Exit
- THEN it continues that same Action
- AND does not exit merely because a checkpoint exists

#### Scenario: External asynchronous evidence is genuinely pending

- GIVEN required external evidence cannot yet be consumed after the governed bounded re-observation of the exact resource
- WHEN no same-Action correction/consumption is immediately legal
- THEN the wake may exit for genuine asynchronous wait
- AND a later wake must fresh-reconstruct state

#### Scenario: Competing durable state invalidates the execution base

- GIVEN current Action/revision/preconditions changed while work was underway
- WHEN the selected Action fresh-observes that conflict
- THEN stale/precondition loss permits fail-closed Exit
- AND local work is not rebased speculatively

#### Scenario: RED with immediately actionable GREEN cannot exit

- GIVEN a RED test has been produced for approved work
- AND GREEN implementation is immediately actionable within the selected Action
- WHEN Exit is evaluated
- THEN the wake must continue to GREEN rather than defer approved same-Action work

#### Scenario: Failed but actionable validation cannot exit

- GIVEN validation fails
- AND the correction is immediately actionable within current Action authority
- WHEN Exit is evaluated
- THEN the correction must be attempted in the same wake

#### Scenario: First nonterminal exact-resource observation cannot exit

- GIVEN selected Action just triggered exact resource R
- AND first fresh observation is queued/in-progress
- WHEN R remains consumable by the selected Action
- THEN ordinary asynchronous Exit is not yet justified
- AND another fresh observation of R is required

#### Scenario: Genuine unconsumable external wait may exit

- GIVEN an external prerequisite is genuinely outside current Action control
- AND no bounded local observation/correction can make progress
- WHEN required evidence demonstrates the wait
- THEN the wake may exit for asynchronous boundary

#### Scenario: First nonterminal exact-resource observation requires re-observation

- GIVEN exact resource R was just triggered and first observation is nonterminal
- WHEN selected Action still owns consumption of R
- THEN at least one subsequent fresh observation of R is mandatory before ordinary async Exit

#### Scenario: Subsequent terminal success is consumed

- GIVEN the subsequent fresh observation of exact resource R is terminal success
- WHEN selected Action can consume that success
- THEN it consumes the result in the same wake and continues to its Action result boundary

#### Scenario: Subsequent terminal actionable failure is consumed

- GIVEN the subsequent fresh observation of exact resource R is terminal failure
- AND correction is inside selected Action authority
- WHEN current preconditions remain valid
- THEN the same wake performs the correction and reruns required validation

#### Scenario: Genuine unconsumable external wait may exit after bounded re-observation

- GIVEN required bounded re-observation of exact R still shows nonterminal external work
- AND the selected Action cannot legally advance R further
- WHEN Exit is evaluated
- THEN ordinary asynchronous wait is a legal Exit class

#### Scenario: Async wait without required re-observation is rejected

- GIVEN only the first nonterminal observation of a just-triggered exact resource exists
- WHEN the action claims asynchronous wait
- THEN the Exit claim is rejected
- AND bounded re-observation remains required

#### Scenario: Stale state during re-observation permits fail-closed exit

- GIVEN source Action/revision becomes stale while re-observing exact resource R
- WHEN current state is fresh-read
- THEN stale/precondition loss permits fail-closed Exit
- AND no further effect is applied from stale authority

#### Scenario: Same-role successor continues

- GIVEN selected Action A completes and successor B derives to the same Role
- WHEN the one-action-per-wake contract is applied
- THEN same-role continuation means only that work inside A was fully work-conserving before completion
- AND B does NOT execute in the same wake
- AND B waits for a later fresh dispatch

#### Scenario: Completed cross-role handoff may exit

- GIVEN selected Action A has durably transitioned to a target Action owned by another Role
- AND any required handoff evidence is complete
- WHEN Exit is evaluated
- THEN completion of A is a normal one-action wake boundary

#### Scenario: Stale precondition permits fail-closed exit

- GIVEN a required source Action/revision/precondition no longer holds
- WHEN same-Action work would otherwise continue
- THEN the invocation may exit fail-closed without speculative mutation

#### Scenario: Hard execution boundary may exit only after legal local recovery is unavailable

- GIVEN connector/tool/runtime failure occurs
- WHEN legal same-Action recovery or alternate read surface remains available
- THEN recovery must be attempted
- AND hard-boundary Exit is allowed only when governed local recovery is unavailable

#### Scenario: No proven Exit class rejects return

- GIVEN selected Action has not completed
- AND no Human, external wait, stale/precondition, contradictory-state, or hard execution boundary is proven
- WHEN the invocation attempts to return
- THEN return is rejected by governance
- AND immediately actionable same-Action work must continue

#### Scenario: Completed Action is a normal wake boundary

- GIVEN selected Action A has reached its result and application observed legal successor B
- WHEN Exit is evaluated
- THEN A completion is sufficient normal Exit
- AND B is not executed in the current wake

### Requirement: Persisted Change identity defines the single active workflow boundary

An open coordination Issue with exactly one valid current Action and a persisted non-`unset` `Change:` identity SHALL be an active formal workflow. Role is derived from Action. The repository MUST allow at most one such open active formal workflow at a time.

Pre-activation `explore-change` and `propose-change` MAY remain `Change: unset` under existing semantic evidence contracts. Once Propose persists a non-`unset` Change, that identity remains immutable through implementation, review, merges, archive, and terminal finalization.

Normal queued work MUST NOT bypass the one active formal workflow. Historical routing prose, old `agent:*` labels, transport comments, prior worker output, or archived Change artifacts MUST NOT create a second active-workflow classification.

#### Scenario: Queued pre-activation work exists while another workflow is active

- GIVEN one open formal workflow has non-`unset` Change and valid current Action
- AND queued pre-activation Issues exist
- WHEN dispatch runs
- THEN the active formal workflow wins
- AND queued work remains untouched

#### Scenario: Closed terminal handoff still blocks new activation

- GIVEN a closed Issue retains workflow Action routing from incomplete terminal retirement
- AND queued pre-activation work exists
- WHEN dispatch reconstructs state
- THEN the closed routing debt is handled before new formal activation

#### Scenario: Older Explore prevents later direct-Propose activation

- GIVEN older eligible `explore-change + Change: unset` and newer eligible `propose-change + Change: unset` Issues exist
- WHEN no active workflow/debt exists
- THEN combined FIFO selects the older Explore
- AND later Propose cannot bypass it

#### Scenario: Proposal-ready Explore keeps its queue position when Human authorizes Propose

- GIVEN an Explore reached governed proposal-ready evidence while remaining the oldest pre-activation work item
- WHEN its legal Action changes to `propose-change` under current semantics
- THEN its original Issue creation time continues to define FIFO position
- AND it is not re-enqueued as newly created work

#### Scenario: Oldest eligible Propose activates after older Explore terminates

- GIVEN an older Explore legally terminates
- AND the next-oldest eligible pre-activation Issue is Propose
- WHEN dispatch next runs without active workflow/debt
- THEN that Propose is selected
- AND activation still requires its semantic baseline contract

#### Scenario: Selected Propose evidence failure preserves Issue ownership without freezing the action

- GIVEN FIFO selects a `propose-change + Change: unset` Issue
- AND required semantic baseline evidence is absent or invalid
- WHEN Lead evaluates Propose
- THEN it does not activate a formal Change from invented evidence
- AND the Issue remains the selected work item for governed correction/disposition rather than silently bypassing to newer work

#### Scenario: Out-of-band coherent Propose routing is operational but not semantic authority

- GIVEN current structural routing coherently says `propose-change`
- AND out-of-band history/prose claims proposal readiness
- WHEN semantic Propose preconditions are evaluated
- THEN structural routing establishes operational ownership only
- AND semantic activation still requires the governed exact baseline evidence

#### Scenario: Action-only formal workflow consumes WIP

- GIVEN an open Issue has one valid Action and non-`unset` Change
- WHEN WIP is reconstructed
- THEN it consumes the single formal workflow slot
- AND Role is derived from Action

### Requirement: Dynamic dispatch tolerates overlapping wakes without hidden ownership state

Workflow-dynamic dispatch SHALL remain at-least-once and MUST NOT rely on Scheduled Tasks to provide mutual exclusion. Overlapping wakes MAY receive the same source Action before either application wins.

Safety SHALL come from complete authoritative reconstruction, executable Action/cardinality classification, fresh source reauthorization, revision/precondition-aware mutations, idempotent result/effect handling, and stale-run termination. The workflow MUST NOT introduce locks, claims, leases, heartbeats, retry counters, hidden sequences, or `status:in-progress` state solely to serialize model wakes.

#### Scenario: Two wakes observe the same active tuple

- GIVEN two wakes observe the same current Action and derive the same Role before either result is applied
- WHEN one wake changes current Action first
- THEN the other must fresh-reauthorize the old source Action before consequence
- AND stale execution stops or reconstructs idempotent completion
- AND no durable wake-owner state is required

#### Scenario: Overlapping wakes share source Action

- GIVEN overlapping wakes are both authorized for the same source Action
- WHEN one result wins first
- THEN the other cannot overwrite newer state from its stale initial authorization
