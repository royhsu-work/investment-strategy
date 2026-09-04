## MODIFIED Requirements

### Requirement: Actionable workflow routing is one logical role/action tuple

An open coordination Issue SHALL be actionable as ordinary workflow work only when it contains exactly one valid `action:<action>` label whose Action exists in the current default-branch executable workflow topology. The logical Role/Action tuple SHALL be formed by deriving Role deterministically from that Action; Role SHALL NOT be stored as an independent canonical routing dimension after cutover.

`agent:*` labels SHALL NOT participate in normal post-cutover dispatch, ownership, cardinality, transition, or terminal-state classification. A legacy `agent:*` label observed after cutover is migration/debt evidence to be retired through the bounded migration/recovery procedure; it MUST NOT override or supplement the Action-derived Role.

Zero, multiple, or unknown `action:*` labels on an open coordination Issue that otherwise appears routed SHALL fail closed. The model MUST NOT infer the intended Action or Role from Issue prose, historical comments, prior routing, PR state, or conversation memory.

Repository-owned terminal closure SHALL make `closed + no action:*` the workflow-routing postcondition while preserving every unrelated label. A closed Issue retaining any `action:*` label SHALL remain current closed-routing debt until bounded terminal-retirement/recovery proves and completes the legal disposition. An already retired `agent:*` label is not required for debt discovery.

#### Scenario: Action derives Reviewer ownership

- GIVEN an open coordination Issue contains exactly `action:review-openspec` as its workflow Action label
- WHEN executable dispatch reconstructs current routing
- THEN the Issue has one logical routing state
- AND the executable topology derives Role `Reviewer`
- AND no persistent `agent:reviewer` label is required for ownership

#### Scenario: Multiple Actions fail closed

- GIVEN an open coordination Issue contains both `action:review-openspec` and `action:implement-change`
- WHEN executable dispatch reconstructs routing
- THEN routing is invalid
- AND neither Role nor Action is guessed from surrounding evidence

#### Scenario: Legacy Role label is not a second routing authority

- GIVEN post-cutover current routing contains one valid `action:implement-change`
- AND a stale legacy `agent:lead` label is also present
- WHEN production dispatch evaluates the Issue
- THEN Executor ownership is derived from `implement-change`
- AND `agent:lead` does not create an alternate routing tuple
- AND the legacy Role label is handled only by bounded migration/debt cleanup

#### Scenario: Closed Action residue remains routing debt

- GIVEN a coordination Issue is closed
- AND it retains `action:finalize-archive`
- WHEN production acquisition reconstructs unresolved workflow state
- THEN that exact Issue remains discoverable as closed-routing debt
- AND terminal history is not inferred from age, prose, or absence of an `agent:*` label

#### Scenario: Terminal retirement preserves unrelated labels

- GIVEN repository-owned terminal completion is authorized
- AND the Issue contains one workflow Action label plus unrelated labels
- WHEN terminal retirement completes
- THEN the Issue is closed
- AND no `action:*` label remains
- AND unrelated labels are preserved

### Requirement: Review and finalize actions have Lead-owned minimum gate contracts

The repository SHALL keep the existing minimum semantic and revision-aware checks for `review-openspec`, `review-implementation`, `review-archive`, `finalize-change`, and `finalize-archive`. Procedural Skills MAY operationalize these checks but MUST NOT invent, weaken, or bypass them.

`review-openspec` SHALL continue to require independent source/evidence → Explore → Proposal/Specs/Design/Tasks traceability, reverse-first then forward inspection, semantic contract/scope coherence, Human-intent preservation, and an exact semantic review target.

`review-implementation` SHALL continue to require exact-current-head implementation coverage and an unambiguous PASS or actionable findings against the approved OpenSpec contract. A PASS SHALL transition to the explicit Action `merge-implementation-pr`; findings SHALL transition only through the legal correction owner/path.

`review-archive` SHALL continue to require exact-current-head Archive coverage, canonical archive correctness, lifecycle preparation, cleanup/retention obligations, and an unambiguous PASS or actionable findings. A PASS SHALL transition to the explicit Action `merge-archive-pr`.

`finalize-change` and `finalize-archive` SHALL preserve their existing lifecycle reconstruction, archive-automation ownership, Human-input freshness, immutable Change identity, terminal evidence, and Issue-close requirements. The executable topology SHALL derive their legal finite successors/effects; the model SHALL retain semantic lifecycle judgment where meaning is required.

#### Scenario: Implementation review PASS selects explicit implementation merge Action

- GIVEN Reviewer has independently passed exact implementation revision R
- WHEN repository application consumes the bounded review PASS while the source Action remains current
- THEN the executable topology derives `merge-implementation-pr`
- AND Executor is derived as that Action's Role
- AND no generic merge phase must be inferred from surrounding history

#### Scenario: Archive review PASS selects explicit archive merge Action

- GIVEN Reviewer has independently passed exact Archive revision R
- WHEN repository application consumes the bounded review PASS while the source Action remains current
- THEN the executable topology derives `merge-archive-pr`
- AND Executor is derived as that Action's Role
- AND archive-specific linkage and lifecycle-preparation gates remain required

#### Scenario: OpenSpec semantic finding remains Reviewer-owned evidence

- GIVEN `review-openspec` identifies a material semantic defect
- WHEN Reviewer records the finding
- THEN Reviewer does not change the proposal/spec/design/tasks to make the gate pass
- AND the executable transition routes only to the legal Lead correction Action
- AND deterministic code does not reinterpret the semantic finding itself

### Requirement: Scheduled execution is at-least-once and state reconstructable

Every Scheduled-Agent action SHALL reconstruct relevant durable repository, Issue, Action, Change, PR, OpenSpec, GitHub Actions, Human-input, and specifically awaited external-resource state before deciding what remains to be done. Execution MUST NOT require memory of a previous Scheduled Task wake or assume that a previous run exited cleanly.

A worker result is staged input until repository-owned application fresh-observes and reauthorizes the exact source Issue + Action + immutable Change/revision predicates required by that effect. If the source Action has already moved to the expected legal postcondition, application SHALL reconstruct that completion idempotently and MUST NOT rewind routing. If current state moved incompatibly, became stale, or is contradictory, application SHALL fail closed rather than replay the old result.

Before a consequential result/application boundary, the owning semantic action SHALL retain the existing direct-Human input freshness/disposition contract. Human-reserved decisions SHALL continue to require their separately governed provenance-bound authority predicate; this freshness rule alone does not grant Human authority.

Once one mapped semantic Action has reached its legal result and repository-owned application has durably applied/observed the resulting transition or terminal effect, that Scheduled Task wake SHALL end. The successor Action, even when it derives to the same Role, SHALL be executed only by a later Scheduled Task wake after fresh neutral dispatch. No same-wake Action chaining is required for correctness or liveness.

#### Scenario: Interrupted application is reconstructed

- GIVEN a worker result was durably transported
- AND repository application completed only part of its authorized narrow effects before interruption
- WHEN a later wake or deterministic application attempt reconstructs the same source/result boundary
- THEN it distinguishes effects already observed from effects still required
- AND it completes only legal missing work
- AND it does not require previous model context

#### Scenario: Already-applied result is not replayed backward

- GIVEN result X legally moved Issue I from Action A to Action B
- AND a duplicate application request for X later arrives
- WHEN application fresh-observes I already at the legal postcondition B
- THEN it treats X as already applied
- AND does not restore A or execute B as part of replay recovery

#### Scenario: Successor waits for a later wake even when Role is unchanged

- GIVEN Lead Action A completes and application legally persists successor Action B
- AND B also derives to Lead
- WHEN the current Scheduled Task wake reaches the applied result boundary
- THEN the wake ends
- AND B is not executed in the same wake
- AND a later wake must perform fresh repository-owned dispatch before B may execute

### Requirement: Routing handoff persists evidence before ownership transfer

A Scheduled-Agent action SHALL persist its required action/review result and revision-aware evidence before repository-owned application changes current Action routing. Before the routing mutation, application SHALL fresh-read the exact source Issue/Action/Change and reject stale or contradictory source state.

The executable topology SHALL derive the target Action from the source Action plus bounded typed result/effect. Repository application SHALL mutate only the required workflow Action label(s), preserve unrelated labels, and fresh-observe the target Action postcondition. Target Role SHALL be derived from the resulting Action; no Role label mutation is required for normal routing.

When the source and target Actions derive to different Roles, the canonical `HANDOFF` record MAY remain required as durable cross-role audit/journal evidence after the target Action has been observed. When they derive to the same Role, no synthetic HANDOFF is required. In either case the current wake ends after the one selected Action has been applied; HANDOFF no longer decides whether another Action may execute in the same wake.

#### Scenario: Cross-role transition derives ownership from target Action

- GIVEN Lead Action A has durable result evidence
- AND the executable topology derives Reviewer Action B
- WHEN application fresh-reauthorizes A and applies the transition
- THEN the Action routing becomes B
- AND Reviewer ownership is derived from B
- AND any required HANDOFF is written only after B is observed
- AND the current Lead wake ends

#### Scenario: Same-role transition also ends the wake

- GIVEN Lead Action A has durable result evidence
- AND the executable topology derives Lead Action B
- WHEN application observes B as the legal target
- THEN no HANDOFF is required solely for the same-role transition
- AND the current wake still ends
- AND B waits for fresh dispatch in a later wake

#### Scenario: Competing transition wins first

- GIVEN a worker completed A from snapshot R
- AND another run changed the current Action before application of the first worker result
- WHEN the first application fresh-reads the Issue
- THEN it does not overwrite the newer Action
- AND it does not emit false HANDOFF evidence
- AND stale/precondition loss is recorded or returned through the legal existing disposition boundary

### Requirement: Fresh-read plus label update is not treated as mutual exclusion

The workflow MUST NOT claim that `fresh-read Action → update Action label` provides a mutex, compare-and-swap primitive, or guaranteed single-flight execution.

Overlapping wakes SHALL remain safe through authoritative reconstruction, bounded typed results, fresh source-Action/Change/revision reauthorization, narrow idempotent effects, SHA/revision guards where available, first-valid-write-wins behavior where applicable, and fresh postcondition observation. Stale or contradictory runs SHALL stop rather than rebasing or speculatively overwriting newer state.

The workflow MUST NOT add lock, claim, lease, heartbeat, retry counter, hidden sequence, `status:in-progress`, or another durable ownership state solely to serialize model wakes.

#### Scenario: Two workers receive the same Action

- GIVEN two overlapping wakes both received valid authorization for the same source Action before either result was applied
- WHEN one result legally changes current Action first
- THEN the second application must fresh-reauthorize its source Action
- AND it may proceed only if its effect is still idempotently satisfied or otherwise legally applicable
- AND it MUST NOT overwrite the winner merely because both initial reads were valid

### Requirement: Executor merges only an explicitly authorized unchanged revision

Executor SHALL execute implementation merge only under Action `merge-implementation-pr` and Archive merge only under Action `merge-archive-pr`.

For `merge-implementation-pr`, durable evidence SHALL establish an unambiguous independent implementation Reviewer PASS for exact revision R, current PR head R, current required checks, applicable Human-input freshness/disposition, and absence of Issue-closing linkage to the persistent coordination Issue. The Action MUST NOT be used for an Archive PR.

For `merge-archive-pr`, durable evidence SHALL establish an unambiguous independent archive Reviewer PASS for exact revision R, current Archive PR head R, current required checks, approved non-closing coordination-Issue reference, absence of closing linkage, applicable pre-review lifecycle preparation, and required cleanup/retention disposition. The Action MUST NOT be used for an implementation PR.

No second Lead merge-authorization token is required. The exact-head Reviewer PASS remains acceptance authority, while fresh merge-time preconditions remain mandatory. Repository-owned application or merge procedure SHALL fail closed if phase, head, review evidence, checks, linkage, Human-input state, lifecycle preparation, or cleanup evidence is stale or contradictory.

#### Scenario: Implementation merge Action cannot infer Archive phase

- GIVEN current Action is `merge-implementation-pr`
- AND the discovered target is a final Archive PR
- WHEN Executor evaluates the merge
- THEN it does not infer that generic merge work is close enough
- AND it does not merge
- AND the state is routed through the legal diagnosis/correction boundary

#### Scenario: Archive merge uses explicit archive gates

- GIVEN current Action is `merge-archive-pr`
- AND archive PASS exists for exact head R
- AND linkage, lifecycle preparation, cleanup/retention, checks, and Human-input predicates are current
- WHEN Executor fresh-verifies all merge preconditions
- THEN the Archive PR may be merged
- AND the coordination Issue remains open for `finalize-archive`

### Requirement: Merge recovery is idempotent and reconstructable

If either explicit merge Action succeeds but the wake stops before all result/application evidence is complete, a later invocation SHALL reconstruct the exact PR/head/merge state and SHALL NOT attempt a duplicate merge.

Recovery SHALL distinguish `merge-implementation-pr` from `merge-archive-pr` from current Action and durable PR identity rather than infer a generic merge phase from historical prose. If merge already succeeded, only missing legal evidence/transition/postcondition work may be completed.

#### Scenario: Implementation merge succeeded before interruption

- GIVEN `merge-implementation-pr` successfully merged exact authorized revision R
- AND the run ended before the next Action was durably observed
- WHEN recovery fresh-reconstructs the PR and coordination Issue
- THEN it recognizes the completed merge
- AND does not attempt a duplicate merge
- AND completes only the still-authorized result/transition evidence

#### Scenario: Archive merge recovery cannot reuse implementation PASS

- GIVEN the current recovery target is an Archive PR
- AND only implementation-review PASS exists for another lifecycle revision
- WHEN recovery evaluates `merge-archive-pr`
- THEN that implementation PASS is not accepted as archive merge authority
- AND recovery fails closed until the required archive evidence exists

### Requirement: Each scheduled run processes at most one actionable work item using a fixed stable order

A normal Scheduled-Agent invocation SHALL process at most one eligible coordination Issue and exactly one mapped semantic Action per wake.

Normal production Scheduled-Agent selection SHALL use workflow-dynamic dispatch from the current default-branch executable topology/kernel. An open formal active workflow SHALL be selected before pre-activation intake. Current closed-routing debt SHALL be classified/recovered before queued pre-activation work. If no formal active workflow and no closed-routing debt exists, coherently routed pre-activation `explore-change` and `propose-change` Issues with `Change: unset` SHALL share one FIFO ordered by earliest GitHub `created_at`, then lower Issue number.

Selection SHALL use current structural Issue/Action/Change facts plus authoritative completeness/provenance and other machine-decidable predicates owned by the executable kernel. It MUST NOT parse historical result prose, transport comments, Issue narrative, or old Role labels to reconstruct normal current queue eligibility.

Legacy fixed-role Scheduled Task identity MUST NOT override workflow-dynamic selection in the normal post-cutover path. Any explicit bounded recovery/testing compatibility surface for fixed-role execution MUST NOT become a second production selector or Scheduled Task workflow.

#### Scenario: Formal workflow wins over queued intake

- GIVEN exactly one open formal workflow is current
- AND queued pre-activation Issues also exist
- WHEN a normal Scheduled Task wakes
- THEN executable dispatch selects the formal workflow's current Action
- AND derives its Role from that Action
- AND queued intake remains untouched

#### Scenario: Pre-activation FIFO is Action-based

- GIVEN no formal active workflow exists
- AND current closed-routing debt is empty
- AND an older `propose-change + Change: unset` Issue and newer `explore-change + Change: unset` Issue are both structurally valid
- WHEN dispatch selects intake
- THEN the older Issue wins by creation order
- AND dispatch does not parse prior ACTION_RESULT or Human-admission prose to decide queue membership

#### Scenario: One selected Action cannot chain into a second Action

- GIVEN dispatch authorizes Issue I Action A
- AND A completes and application derives successor B
- WHEN the wake reaches the applied Action result boundary
- THEN the invocation has processed its one mapped Action
- AND it ends without executing B
- AND it does not select another Issue

### Requirement: Repository agent artifacts expose the governance contract

Implementation SHALL provide:

- `agents/AGENTS.md` as current default-branch bootstrap/shared execution protocol, including authoritative-input, Human-authority, exception/finalization, one-action-per-wake, semantic-versus-deterministic ownership, and application/postcondition boundaries;
- one current default-branch executable workflow topology/kernel as the machine-decidable owner of Action vocabulary, Action→Role derivation, finite typed result/transition topology, deterministic dispatch/cardinality, effect capabilities, source reauthorization, stale/replay handling, and structural postconditions;
- `agents/workflow.md` as generated or mechanically verified Human-readable presentation of that executable topology plus non-machine semantic explanation, without serving as a production-parsed DAG;
- role definitions under `agents/roles/` for Lead, Reviewer, and Executor semantic mission/authority;
- a reduced mapped Skill set under `agents/skills/` that owns action procedure and semantic evidence/judgment without duplicating executable Action→Role/successor/continuation tables;
- `agents/templates/messages.md` as durable presentation/evidence shape only, not routing or transition authority;
- documentation describing Action-only canonical routing, WIP=1, the executable kernel, typed result/application boundaries, one-action-per-wake, no-model-API deployment, replaceable transport, migration/cutover, and historical evidence versus current state.

Scheduled Task prompts SHALL remain bootstrap/delegation surfaces. They MUST NOT duplicate the workflow DAG, Action→Role mapping, successor rules, same/cross-role continuation policy, historical eligibility parser, or transport mailbox semantics. ChatGPT Scheduled Tasks remain the only normal model wake mechanism. GitHub Actions MAY run deterministic acquisition/dispatch/application/validation code but MUST NOT host or invoke a model worker.

#### Scenario: Human workflow documentation drifts

- GIVEN `agents/workflow.md` presents a machine-decidable transition not present in the executable topology
- WHEN repository validation runs
- THEN validation fails
- AND production runtime does not resolve the discrepancy by parsing the Markdown as an alternate DAG

#### Scenario: Scheduled Task remains a thin wake surface

- GIVEN a normal Scheduled Task wakes
- WHEN it begins execution
- THEN it loads current default-branch governance
- AND requests neutral executable dispatch
- AND executes only the one authorized mapped Action
- AND its prompt does not contain a private copy of the repository lifecycle topology

### Requirement: Default-branch governance declares the scheduled dispatch mode

The repository SHALL declare exactly one authoritative `Scheduled-Dispatch-Mode` marker in current default-branch governance. The normal post-cutover Scheduled-Agent path SHALL use `workflow-dynamic` dispatch and SHALL NOT infer Role/Action from legacy task names, conversation memory, old Role labels, or feature-branch governance.

A fixed-role mode MAY exist only as an explicitly bounded compatibility/test/recovery mechanism while required by migration, and MUST NOT be another normal Scheduled Task selector after cutover. Completion of this Change requires deleting or disabling normal production dependence on the old fixed-role selection path.

#### Scenario: Legacy task name does not select Role

- GIVEN a Scheduled Task historically has a Lead-like name
- AND current workflow-dynamic dispatch selects `review-openspec`
- WHEN the task wakes
- THEN Reviewer is derived from the selected Action
- AND the legacy task name does not override repository dispatch

### Requirement: Workflow-dynamic dispatch derives one fixed invocation role from durable workflow state

In workflow-dynamic mode, a normal Scheduled Task wake SHALL use repository-owned executable dispatch to select one exact coordination Issue and Action from current authoritative state. Role SHALL be derived deterministically from that Action and SHALL govern only the semantic authority of that one mapped Action invocation.

After repository-owned application persists and observes that Action's legal successor or terminal effect, the current wake SHALL end. The successor MAY derive to the same Role or another Role, but no successor semantic Action SHALL execute until a later Scheduled Task wake fresh-reconstructs current default-branch governance and performs neutral executable dispatch again.

The one-action wake boundary is an external execution contract enforced by current default-branch governance and Scheduled Task behavior. Repository code owns dispatch, typed transition, effects, and postconditions but SHALL NOT require an OpenAI API, Responses API, GitHub Actions-hosted model worker, direct model wake chaining, wake-role attestation, lease, heartbeat, or durable continuation cursor to enforce correctness.

#### Scenario: Same-role successor waits for fresh wake

- GIVEN current wake executes Lead `explore-change`
- AND its applied result derives `propose-change`, also owned by Lead
- WHEN the transition is durably observed
- THEN the current wake ends
- AND `propose-change` is not executed immediately
- AND a later wake must fresh-dispatch before Propose may run

#### Scenario: Cross-role successor uses the same boundary

- GIVEN current wake executes Lead `propose-change`
- AND its applied result derives Reviewer `review-openspec`
- WHEN the target Action is durably observed
- THEN the current wake ends
- AND no separate cross-role wake-barrier state or special chaining mechanism is required

#### Scenario: No model API is required for the successor

- GIVEN Action A has produced current successor B
- WHEN A's Scheduled Task wake ends
- THEN repository code does not invoke a model API to execute B
- AND the next ordinary ChatGPT Scheduled Task wake consumes B through fresh dispatch

### Requirement: Selected Scheduled Agent actions are work-conserving within an invocation

A selected mapped Action SHALL remain work-conserving internally until it reaches one action-defined result/application boundary or a genuine Human-reserved, external-asynchronous, stale/precondition, contradictory-state, or hard execution boundary.

Immediately actionable work that is still part of the selected Action MUST NOT be deferred merely because a RED/checkpoint/commit exists or a validation first failed. Examples include RED→GREEN→REFACTOR/VERIFY within an approved implementation slice, correcting an actionable validation failure inside current authority, completing required Proposal/Spec/Design/Tasks authoring, and bounded re-observation/consumption of an exact just-triggered CI or validation resource.

However, successful completion and deterministic application of the selected Action itself SHALL be a normal Invocation Exit. The existence of an immediately actionable successor Action, including a same-Role successor on the same Issue, MUST NOT extend the wake into that second Action.

For an exact external resource just created or triggered by the selected Action, the current minimum bounded re-observation rule remains: a first absent/queued/in-progress observation alone is not sufficient asynchronous-wait Exit evidence while current Action/revision/authority still permits bounded consumption. At least one subsequent fresh observation of the same exact resource is required before ordinary asynchronous wait may be classified. Terminal success/failure that is actionable within the selected Action SHALL be consumed immediately.

Catchable execution exceptions SHALL retain the existing shared raw-evidence capture and action-defined recovery/disposition requirements. An exception is not a voluntary exit while legal same-Action recovery remains immediately actionable.

#### Scenario: Failed validation remains inside the selected Action

- GIVEN one selected Action owns a required validation step
- AND validation fails for a clear correction within that Action's approved authority
- WHEN current source Action/revision/preconditions remain valid
- THEN the failure is not an Invocation Exit
- AND the correction and required validation rerun occur in the same wake

#### Scenario: Completed Action is a normal wake boundary

- GIVEN selected Action A has completed its semantic work
- AND repository application has durably observed A's legal successor B
- WHEN the invocation evaluates Exit
- THEN completion of A is sufficient normal Exit for this one-action wake
- AND B is not executed in the current invocation even if it is immediately actionable

#### Scenario: First nonterminal CI observation still requires re-observation

- GIVEN selected Action A just triggered exact CI resource R
- AND the first fresh observation of R is queued
- AND A remains current and can still consume R
- WHEN the invocation evaluates asynchronous wait
- THEN it must make at least one subsequent fresh observation of R before ending for ordinary async wait

#### Scenario: Subsequent actionable terminal failure is consumed

- GIVEN the subsequent fresh observation of exact resource R is terminal failure
- AND the correction remains within selected Action A's authority
- WHEN A evaluates its next step
- THEN A performs that correction in the same wake
- AND the failure does not defer approved same-Action work to a later Action or wake

### Requirement: Persisted Change identity defines the single active workflow boundary

An open coordination Issue with exactly one valid current Action and a persisted non-`unset` `Change:` identity SHALL be an active formal workflow. Role is derived from Action. The repository MUST allow at most one such open active formal workflow at a time.

Pre-activation `explore-change` and `propose-change` MAY remain `Change: unset` under their existing semantic evidence contracts. Once Propose persists a non-`unset` Change, that identity remains immutable through implementation, review, merges, archive, and terminal finalization.

Normal queued work MUST NOT bypass the one active formal workflow. Historical routing prose, old `agent:*` labels, transport comments, prior worker output, or archived Change artifacts MUST NOT create a second active workflow classification.

#### Scenario: Action-only formal workflow consumes WIP

- GIVEN Issue I is open
- AND has one valid Action `implement-change`
- AND has `Change: example-change`
- WHEN dispatch reconstructs formal workflow cardinality
- THEN I is one active workflow
- AND Executor ownership is derived from the Action
- AND another pre-activation Issue remains queued

### Requirement: Dynamic dispatch tolerates overlapping wakes without hidden ownership state

Workflow-dynamic dispatch SHALL remain at-least-once and MUST NOT rely on Scheduled Tasks to provide mutual exclusion. Overlapping wakes MAY receive the same source Action before either application wins.

Safety SHALL come from complete authoritative reconstruction, executable Action/cardinality classification, fresh source reauthorization, revision/precondition-aware unsafe mutations, idempotent result/effect handling, and stale-run termination. The workflow MUST NOT introduce locks, claims, leases, heartbeats, retry counters, hidden sequences, or `status:in-progress` state solely to serialize model wakes.

#### Scenario: Overlapping wakes share source Action

- GIVEN two wakes are authorized for the same Issue/Action from the same then-current state
- WHEN one wake's result is applied first and changes the Action
- THEN the other wake must revalidate the exact source Action before consequence
- AND stale application stops or reconstructs already-applied idempotency
- AND no durable wake-owner field is required