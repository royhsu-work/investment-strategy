## MODIFIED Requirements

### Requirement: Explicit required deferred follow-up becomes durable before lifecycle completion

An approved decision explicitly classifying bounded work as necessary separate follow-up SHALL persist its exact source Issue/Change, decision reference, scope and affected dependents under existing authority. The Application SHALL derive tracker and dependency completeness from that source independently of worker-requested effects. Optional, out-of-scope or unregistered prose MUST NOT grant admission. Independent Reviewer SHALL find a missing necessary tracker or dependency at review; lifecycle finalization MUST verify the same postcondition or an exact authoritative supersession.

#### Scenario: Ordinary scope exclusion creates no tracker obligation

- GIVEN only optional ideas or exclusions
- WHEN Application reconstructs the decision
- THEN no Issue or dependency is inferred

#### Scenario: Required deferred work must have a durable tracker

- GIVEN a qualified decision explicitly defers required work
- WHEN the worker omits all requested effects
- THEN the existing Application still materializes the source-linked Issue and verifies its applicable edges

#### Scenario: OpenSpec review catches a missing required tracker

- GIVEN a required decision lacks verified tracker or dependencies
- WHEN the worker reports readiness or PASS
- THEN Reviewer identifies the gap and readiness cannot complete

#### Scenario: Lifecycle completion fails safe on missing required tracker

- GIVEN required evidence remains missing
- WHEN terminal archive qualification runs
- THEN advance only after positive completion or qualified supersession


### Requirement: Operational execution eligibility remains orthogonal to lifecycle state

A Scheduled-Agent work item SHALL derive whether its next legal action is currently executable from the durable preconditions and evidence owned by that action without introducing a parallel lifecycle state for ordinary waits or blockers.

A formal workflow with a qualified unsatisfied Issue prerequisite or declared external prerequisite SHALL remain the same formal workflow, but SHALL be suspended and consume no execution slot. Other runnable work MAY progress under the existing admission, independent review, merge and mutation boundaries. WIP is not a count of unfinished Changes. A generic BLOCKED result or a transient/unknown observation alone is not proof of a persistent prerequisite; existing action-specific result, wait, exception, escalation and recovery evidence remains authoritative and MUST NOT be bypassed. An external declaration is operational and reversible by a qualified Lead/maintainer after fresh evidence that the actual condition clears; no universal external-condition evaluator, new lifecycle label, or Human approval per dependency is introduced.

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

Dispatch and Application SHALL hold only affected work while required materialization or dependency effects remain outstanding. Only the exact accepted producer suffix MAY finish its own pending effect without ordinary reselection; independently established prerequisites and structural cycle/target checks remain mandatory.

#### Scenario: Missing target and producer self-dependency

- GIVEN a required source is durable before any tracker exists
- WHEN the subsequent producer work depends on that tracker
- THEN ordinary dependent work is held and the exact authorized Application suffix can create and attach the tracker without running another semantic Action
- AND independent blockers, including an independently declared edge to that same target, remain binding


### Requirement: Required separate follow-up is directly queueable for fresh Explore revalidation

An explicitly approved required separate follow-up SHALL authorize source-bound creation, reuse or repair as action-only preactivation work. Each admitted carrier participates in the existing formal-first WIP=1 queue subject to its own applicable prerequisites. A paused workflow consumes no WIP. No carrier SHALL acquire exclusive execution rights by age or existence.

#### Scenario: Required follow-up is created at the defer boundary

- GIVEN explicit required work and no qualified existing tracker
- WHEN the defer decision becomes durable
- THEN Application observes a queueable Issue with exact source, Change: unset and action:explore-change, or qualifies its valid advanced state

#### Scenario: Optional future work is mentioned

- GIVEN an optional idea appears in a document
- WHEN eligibility is reconstructed
- THEN no Issue gains admission from that text

#### Scenario: A suspended duplicate does not reserve execution

- GIVEN two authorized carriers cover the same work and one is suspended
- WHEN the dispatcher selects work
- THEN the other remains eligible only when its own prerequisites and ordinary gates permit


### Requirement: Required separate follow-up work is materialized as one routing-complete postcondition

Required follow-up materialization SHALL complete only after qualified read-back of at least one source-linked routing-complete tracker or lawful descendant and all still-required dependency effects. Before any write, Application SHALL reobserve complete authoritative tracker evidence, exact scope, current authority and source. It SHALL reuse a qualified existing match or repair authorized missing fields before creating. Physical duplicates are permitted after uncertain writes. Multiple verified matches SHALL NOT by themselves block progress or grant authority to choose an arbitrary dependency target. Contradictory provenance and insufficient observations MUST NOT authorize mutation.

#### Scenario: Required follow-up is created and routed as one logical result

- GIVEN an explicit qualified decision with no reusable tracker after complete fresh observation
- WHEN the Application performs a necessary creation
- THEN the source linkage, routing-complete Issue and applicable dependency effects must be observed before advancing the affected boundary

#### Scenario: Ambiguous matching trackers fail closed

- GIVEN observed trackers have contradictory or unverifiable source, scope or authority
- WHEN the Application cannot establish the eligibility of a proposed mutation
- THEN withhold that mutation and seek qualified evidence or an authorized correction
- AND several individually verified legitimate trackers alone do not constitute this ambiguity or prevent their independently eligible work

#### Scenario: Optional or ordinary deferred work creates no required tracker

- GIVEN a source mentions optional or uncommitted work without an approved required decision
- WHEN Application evaluates materialization
- THEN no new tracker or dependency is authorized

#### Scenario: Lifecycle preparation repairs one uniquely incomplete required tracker

- GIVEN an exact existing tracker is missing only an authorized routing field
- WHEN lifecycle preparation observes the pending approved decision
- THEN the owning Application repairs the missing field, preserves unrelated content, and verifies tracking and dependency completeness before handoff

#### Scenario: Interrupted create-before-route is repaired idempotently

- GIVEN an existing exact tracker lacks only authorized routing
- WHEN Application fresh-reads it
- THEN repair only missing state and preserve unrelated labels and content

#### Scenario: Accepted operation before any POST or failure artifact

- GIVEN original accepted source and pending required effect can be qualified
- WHEN a new legal wake reaches existing continuation ingress
- THEN exact operation can reenter, reobserve and issue a necessary create without proof that the prior POST never ran

#### Scenario: Delayed POST and lost response

- GIVEN a previous write may yet commit
- WHEN complete fresh evidence finds no reusable tracker and authority remains valid
- THEN a necessary create is permitted and any resulting duplicates retain all applicable admission and dependency gates

#### Scenario: Incomplete enumeration

- GIVEN a page, field or required provenance is unavailable
- WHEN recovery examines the target
- THEN perform no guessed write and reobserve on a lawful opportunity

#### Scenario: Already advanced tracker

- GIVEN positive source-bound descendant evidence exists
- WHEN reconstruction resumes
- THEN adopt qualified current evidence without rewinding the carrier

#### Scenario: Tracker prose does not create routing authority

- GIVEN an unrelated or copied body resembles the work
- WHEN admission or dispatch is evaluated
- THEN no authoritative match is inferred from wording

#### Scenario: Retirement is not delivery

- GIVEN a former tracker is closed without qualified delivery and the necessary decision still applies
- WHEN the exact authorized retirement and absence of a reusable carrier are verified
- THEN complete remaining tracking through ordinary reconciliation without crediting the closure as successful delivery


### Requirement: Explore-originated required follow-up decisions are materialized before Propose and preserved through formalization

The exact durable Explore result SHALL preserve its explicit required defer decisions before their effects. The owning Application SHALL observe tracking and dependency completeness before completing the source successor. Propose SHALL dereference that exact result and preserve every still-applicable decision through formalization. Recovery SHALL reconstruct the accepted intent, retain historical uncertainty, skip completed effects and reauthorize only the missing suffix.

#### Scenario: Explore materializes a newly required separate follow-up before successor routing

- GIVEN a qualified Explore result explicitly defers necessary work
- WHEN the source result is persisted
- THEN the successor waits for observed tracker and dependency effects

#### Scenario: Interrupted Explore materialization resumes from the same durable decision

- GIVEN one or more independent writes have committed
- WHEN reentry reconstructs the same accepted source
- THEN finish only remaining authorized effects with read-back

#### Scenario: Ordinary deferred wording creates no tracker obligation

- GIVEN Explore mentions speculative later work
- WHEN Propose reads the result
- THEN no necessary work is inferred from prose

#### Scenario: Propose preserves a required follow-up while keeping it outside current implementation scope

- GIVEN required work falls outside current implementation scope
- WHEN Lead prepares the proposal
- THEN preserve source linkage and dependency disposition and verify the postcondition before readiness


#### Scenario: Propose repairs only a unique incomplete required tracker

- GIVEN the exact Explore source identifies a tracker whose missing fields are independently authorized
- WHEN Propose observes incomplete materialization
- THEN repair only the precisely qualified target and reobserve the postcondition before readiness
- AND do not infer target-specific repair authority from similarity or require physical uniqueness across independently qualified trackers

### Requirement: Persisted Change identity defines the single active workflow boundary

An open coordination Issue with a valid routing tuple and persisted non-`unset` `Change:` SHALL be a formal workflow. The title is retained as the canonical requirement identity; formal workflow cardinality no longer defines execution capacity. WIP=1 SHALL bound selection to one runnable Action per wake, not the number of open formal workflows. A qualified unsatisfied prerequisite MUST suspend the affected workflow without changing its Issue state, immutable Change, current Action, accepted effects, or recovery obligations.

Lead or the repository maintainer MAY declare or correct already admitted necessary prerequisites within approved scope based on actual blocking evidence. For a legacy declaration stream the latest qualified standalone comment `Blocked by: #<issue-number>, #<issue-number>` (one or more targets) on an open routed Issue SHALL define its complete prerequisite set; an independently observed external prerequisite not represented by an admitted Issue MAY be denoted by `external` in the same list. No additional Human-reserved decision, native Issue dependency, new work admission or routing mutation is implied. Qualification MUST require repository-owner authorship, OWNER association and explicit direct or approved chatgpt-codex-connector provenance; arbitrary commenters, other apps and ordinary prose MUST NOT grant selection authority. GitHub creation time and comment ID determine the current qualifying command. Correction MUST append a new command, not edit or delete one; `Blocked by: none` withdraws a set only when no prerequisite remains applicable. External resumption MUST use a fresh qualified correction based on the actual cleared condition, not a generic retry or automatic interpretation of a BLOCKED result.

A managed complete-set correction SHALL cite the observed effective native declaration comment ID, or an explicit initial empty basis. Its first adoption SHALL preserve the qualified legacy prefix. Once managed, only a correction against the current effective basis may replace or clear that Issue’s set. Complete history in native creation time/ID order determines applicability. Stale/unbased writes SHALL NOT erase accepted independent edges. A native Application correction SHALL additionally prove the exact accepted decision, dependent, authorized edit, baseline, complete graph and read-back; ordinary bot comments cannot qualify. Maintainers can correct an affected downstream on current evidence while its old prerequisite is suspended. Conflicting same-edge decisions require explicit disposition. No dependency satisfaction by semantic equivalence is implied.

Selection and Application reauthorization SHALL consume the same executable dependency graph and current observations. Multiple prerequisites, shared prerequisites and nested prerequisites SHALL be represented by the same graph, without fixed incident identities or pair exceptions. A referenced Issue satisfies a prerequisite only with qualified terminal formal `finalize-archive` / `lifecycle-complete` evidence and closed/no-routing retirement, not bare closure or NO_GO. All unsatisfied prerequisites exclude their source from runnable selection; a completed prerequisite releases only its own edge. Cycles, unknown or unrouted targets, malformed/edited current qualified commands, incomplete enumeration and provenance-invalid selection evidence MUST NOT authorize work. A valid but unsatisfied prerequisite is not an invalid repository. Suspended work SHALL NOT consume an execution slot, require full action-local formal qualification before another eligible workflow runs, or be rewound; structural current identity remains mandatory and formal frontier qualification resumes before that work is selected.

Normal formal lifecycle work SHALL remain open through final Archive merge and `Lead / finalize-archive`. It remains active while open with a valid routing tuple and non-`unset` Change identity until terminal conditions are satisfied, `LIFECYCLE_COMPLETE` is durably persisted, and repository-owned terminal retirement completes the `closed + no workflow routing` postcondition.

A closed coordination Issue retaining any repository-governed workflow routing label SHALL be current closed-routing debt rather than active workflow work. Its disposition MUST come only from bounded current debt classification: a qualifying unfinished premature closure MAY recover only under the existing recovery predicates, while proven terminal/retired routing residue MAY receive only narrow routing-retirement cleanup. Ambiguous, competing, contradictory, or incomplete debt MUST fail closed. A closed Issue with valid terminal completion and no workflow routing labels is terminal history and MUST NOT block later workflow admission.

Open coherently routed `Lead / explore-change + Change: unset` and `Lead / propose-change + Change: unset` coordination Issues SHALL be queued pre-activation work based on current structural routing. Neither form counts as an active workflow before Propose persists an immutable Change identity. Dispatcher selection MUST NOT distinguish an unset Propose by origin, Human admission, comment provenance, or reconstructed semantic readiness.

Lead MUST NOT activate a queued proposal unless fresh executable selection authorizes that exact current runnable Propose and current closed-routing debt is resolved. Every original same-Issue Explore-result, Application, review and merge precondition still applies. The existence of other suspended or queued formal Changes is not an activation veto. Deterministic selection SHALL prefer runnable formal workflows, then runnable pre-activation prerequisites (including transitive prerequisites) of formal workflows, then the ordinary runnable combined Explore/Propose queue. Each group uses earliest GitHub `created_at`, then lower Issue number. A `propose-change` runner MUST re-check that its Issue still matches current executable selection immediately before persisting a non-`unset` Change identity, and independently verify the post-write selection/identity.

A proposal-ready Explore remains pre-activation until repository-owned application legally routes that same Issue to `Lead / propose-change`. The transition SHALL NOT require a generic Human proceed confirmation when the proposal-ready direction remains inside the bounded researched/canonical evidence and introduces no Human-reserved decision. After routing, the same Issue retains its original queue position. Propose SHALL reconstruct the exact durable same-Issue `PROPOSAL_READY` semantic baseline and independently validate its material source/evidence and feasibility basis before activation. An absent/invalid/incomplete but researchable basis routes the same Issue back to Explore without changing queue identity; it does not change dispatcher eligibility or authorize later work. If formalization would introduce a new Human-reserved product/project direction, material externally observable behavior or scope trade-off, explicit risk acceptance, or materially different security/privacy/cost/operational commitment, Lead MUST use the existing `HUMAN_DECISION_REQUIRED` boundary instead of treating routing or Explore execution as Human authority.

#### Scenario: Queued pre-activation work exists while another workflow is active

- GIVEN Change A is an active workflow
- AND Issue B is an open routed `Lead / explore-change` or `Lead / propose-change` Issue with `Change: unset`
- WHEN workflow-dynamic dispatch reconstructs work
- THEN if A is runnable, A is selected before pre-activation B
- AND if A is suspended, it consumes no selection slot and B may be selected according to the runnable policy and existing Action/Result gates

#### Scenario: Closed terminal handoff still blocks new activation

- GIVEN Change A's coordination Issue is closed
- AND it retains at least one repository-governed workflow routing label
- AND queued Explore or Propose work exists with `Change: unset`
- WHEN workflow-dynamic dispatch reconstructs work
- THEN Change A is treated as current closed-routing debt rather than active workflow work
- AND only bounded recovery/terminal-retirement handling may act on that debt
- AND the queued pre-activation work is not activated until the debt is legally resolved or retired

#### Scenario: Older Explore prevents later direct-Propose activation

- GIVEN no open active workflow exists
- AND current closed-routing debt is empty
- AND an older coherently routed `Lead / explore-change + Change: unset` Issue exists
- AND a newer coherently routed `Lead / propose-change + Change: unset` Issue exists
- WHEN dispatch selects pre-activation work after direct-Propose admission has been removed
- THEN the older Explore remains the deterministic combined-queue winner by creation order
- AND the newer Propose remains queued because current routing participates in the same FIFO, not because a direct-Propose Human-admission predicate exists

#### Scenario: Proposal-ready Explore keeps its queue position when Human authorizes Propose

- GIVEN an Explore Issue is the deterministic combined-queue winner
- AND Lead returns evidence-backed structured `PROPOSAL_READY` within the bounded current context
- AND no new Human-reserved decision is introduced
- WHEN repository-owned application routes the same Issue to `Lead / propose-change`
- THEN no Human authorization is required for that normal transition under the new contract; the legacy scenario title is retained only as the canonical scenario identity
- AND the same Issue retains its original GitHub `created_at` and queue position
- AND Propose may persist the immutable Change identity only after re-checking queue ownership and independently validating its action-local source/evidence and feasibility basis

#### Scenario: Oldest eligible Propose activates after older Explore terminates

- GIVEN no open active workflow exists
- AND current closed-routing debt is empty
- AND an older Explore has legally reached terminal `NO_CHANGE_REQUIRED` or `NO_GO` and left pre-activation routing
- AND at least one coherently routed `Lead / propose-change + Change: unset` Issue remains
- WHEN dispatch selects pre-activation work
- THEN the earliest remaining coherent candidate is selected by `created_at`, then Issue number
- AND Propose may activate only after its action-local source/evidence, feasibility, and activation preconditions pass
- AND no Human direct-Propose admission predicate is evaluated

#### Scenario: Selected Propose evidence failure preserves Issue ownership without freezing the action

- GIVEN the FIFO-selected pre-activation candidate is current `Lead / propose-change + Change: unset`
- BUT the mapped Propose action cannot establish a sufficient material source/evidence/feasibility basis
- WHEN Propose evaluates activation
- THEN no Change identity is persisted
- AND the current Issue remains the workflow/queue owner
- AND, when the gap is researchable within the same bounded problem, the legal action changes to same-Issue `Lead / explore-change`
- AND a later candidate is not silently authorized as fallback

#### Scenario: Out-of-band coherent Propose routing is operational but not semantic authority

- GIVEN an administrator or connector writes a structurally coherent `Lead / propose-change + Change: unset` tuple
- WHEN dispatch reconstructs current pre-activation state
- THEN the Issue participates in deterministic selection from current routing without label-writer provenance reconstruction
- AND that routing does not manufacture a sufficient evidence-backed same-Issue Explore basis
- AND consequential Propose activation still fails closed unless its action-local semantic preconditions are satisfied
- AND a researchable pre-activation evidence gap may route the same Issue to Explore rather than disappearing from the queue

#### Scenario: Two independent complete-set updates race

- GIVEN two qualified writers read the same set and propose different necessary additions
- WHEN the first update is read back and a stale update arrives later
- THEN retain the effective set and reapply only the still-authorized disjoint edit against the new basis
- AND a stale clear cannot remove either edge

#### Scenario: Downstream replacement before old prerequisite resumes

- GIVEN an authorized correction replaces one prerequisite while others remain
- WHEN the exact downstream declaration is updated
- THEN preserve every unrelated edge and qualify the replacement's delivery independently
- AND bare closure or NO_GO of either Issue does not count as successful dependency completion

## ADDED Requirements

### Requirement: Revalidate remaining scope before non-delivery retirement

At existing Explore or material resume/correction boundaries the responsible Role SHALL verify approved scope against current main and actual evidence. Fully satisfied work MAY terminate through preactivation NO_CHANGE_REQUIRED or justified formal Lead resolve-question/NO_GO. Terminal Application MUST preserve the original Change identity, settle independent accepted effects and cleanup obligations, and verify applicable PR disposition before recording terminal close/unroute. PR retirement MUST have exact type-specific authority, fresh repository/head/unmerged proof and read-back. Independent review and all delivery gates remain binding on outstanding work.

#### Scenario: Fully satisfied formal Change has an unmerged PR

- GIVEN deployed main meets every original acceptance condition, an unmerged PR exists and its retirement is authorized
- WHEN Lead terminates obsolete work
- THEN Application completes or adopts exact-head closed-unmerged retirement, verifies all required effects and branch dispositions, then verifies closed Issue and retired routing
- AND interruption resumes the missing suffix without a forced replacement, merge, archive or LIFECYCLE_COMPLETE

#### Scenario: Only partial or unmerged work exists

- GIVEN main meets some or none of the acceptance conditions
- WHEN another unmerged branch meets more of them
- THEN retain the necessary remaining scope and existing review obligations; the branch cannot qualify delivery

#### Scenario: Independent effects or cleanup remain

- GIVEN deployed main satisfies the original feature but an accepted follow-up or branch disposition remains outstanding
- WHEN non-delivery retirement is considered
- THEN complete or authoritatively supersede those obligations before terminal close; incomplete authority holds the affected operation
