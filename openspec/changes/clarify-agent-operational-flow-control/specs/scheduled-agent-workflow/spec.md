## ADDED Requirements

### Requirement: Operational execution eligibility remains orthogonal to lifecycle state

A Scheduled-Agent work item SHALL derive whether its next legal action is currently executable from the durable preconditions and evidence owned by that action without introducing a parallel lifecycle state for ordinary waits or blockers.

A formal active workflow that cannot currently proceed because required Human authority, exact CI/gate evidence, environment capability, dependency/conflict resolution, or other action-owned precondition is absent MUST remain the same formal active workflow and MUST continue to consume the repository's single formal WIP slot.

The repository MUST NOT introduce a universal `blocked` result, waiting-state taxonomy, or capacity-release rule merely to represent those conditions. Existing action-specific result, wait, exception, escalation, and routing evidence remains authoritative for why the next legal action cannot complete.

#### Scenario: Active workflow waits for an exact external gate

- GIVEN one formal active workflow is routed to its legal action
- AND the action requires exact external gate evidence that is not yet terminal
- WHEN the scheduler evaluates other queued work
- THEN the active workflow remains formal WIP
- AND no queued work activates merely because the active workflow is waiting
- AND the wait does not create a new lifecycle state

#### Scenario: Human authority is genuinely required

- GIVEN the next legal action cannot continue without a Human-reserved decision
- WHEN Lead persists the governed Human escalation
- THEN the workflow remains the same active workflow
- AND the Human boundary is represented by the existing provenance-bound escalation/resume contract
- AND optional advice that is not legally required does not create equivalent blocking semantics

### Requirement: Active-workflow cardinality and Issue-state coherence precede queue selection

Scheduled dispatch SHALL establish the complete cardinality of terminal-pending and formal active workflows before evaluating pre-activation queue order, blocker projection, priority, or Project/Kanban state.

If active-workflow cardinality cannot be established as exactly zero or one, dispatch MUST fail closed and MUST NOT infer that queued work is eligible. Normal nonterminal routed workflow work MUST have an open coordination Issue. A closed Issue with nonterminal routing is contradictory durable state except for the existing narrow terminal-pending `Lead / finalize-archive` shape and MUST NOT execute its stale routed action while closed.

A closed nonterminal Issue MAY be recovered automatically only for the demonstrated premature-close class when durable reconstruction proves all of the following: the Issue has a persisted non-`unset` Change and exactly one otherwise legal nonterminal routing tuple; matching durable lifecycle evidence proves the Change is unfinished; no authorized final Archive/native-close completion or `LIFECYCLE_COMPLETE` exists; no qualifying provenance-bound Human decision requires termination/non-resumption; and repository-wide reconstruction finds no other normal formal/terminal-pending workflow or second premature-close recovery candidate. A bare Issue close event or actor identity MUST NOT by itself count as qualifying Human termination authority.

When exactly one such premature-close recovery candidate exists, it MUST block pre-activation intake and normal lifecycle execution. The governed recovery owner/action SHALL be `Lead / resolve-question`. Lead MAY reopen that same coordination Issue while preserving its immutable Change identity and pre-close nonterminal routing tuple. After reopening, Lead MUST fresh-read Issue state, routing, matching OpenSpec/PR lifecycle evidence, and repository-wide active cardinality. Recovery is complete only when the reopened Issue reconstructs as the single coherent formal active workflow and the preserved routing tuple remains legal. The recovery invocation MUST NOT execute the preserved normal lifecycle action; a later wake MUST dispatch from the freshly reconstructed normal tuple.

If any recovery predicate is missing, contradictory, Human-reserved, or would create multiple-active ambiguity, Scheduled roles MUST remain fail closed and MUST NOT reopen by inference. This bounded recovery MUST NOT create a generic fault state machine, hidden recovery registry, cancellation lifecycle, or authority to undo a qualifying Human decision.

#### Scenario: One active workflow is missed by a partial search

- GIVEN repository durable state contains one formal active workflow
- AND a partial query fails to enumerate it
- WHEN pre-activation work is also present
- THEN dispatch does not treat the partial query as proof of zero active workflows
- AND pre-activation work cannot be selected until repository-wide active cardinality is established

#### Scenario: Nonterminal workflow Issue is closed prematurely and safely recoverable

- GIVEN a coordination Issue has a persisted non-`unset` Change and exactly one otherwise legal nonterminal routing tuple
- AND the Issue is closed outside the authorized terminal Archive boundary
- AND durable lifecycle evidence proves the Change remains unfinished
- AND no qualifying provenance-bound Human decision requires termination or non-resumption
- AND repository-wide reconstruction finds no other formal/terminal-pending workflow or premature-close recovery candidate
- WHEN scheduled dispatch reconstructs workflow state
- THEN the stale routed action is not executed while the Issue is closed
- AND pre-activation work is not selected
- AND `Lead / resolve-question` owns the bounded recovery
- AND Lead may reopen the same Issue without changing its immutable Change identity or preserved nonterminal routing tuple
- AND Lead fresh-reconstructs repository-wide cardinality and routing after reopening before any normal lifecycle action may resume
- AND the recovery invocation does not execute the preserved normal action

#### Scenario: Premature close cannot be recovered unambiguously

- GIVEN a closed nonterminal coordination Issue has missing or contradictory lifecycle evidence, a qualifying Human termination decision, another formal/terminal-pending workflow, or another premature-close recovery candidate
- WHEN recovery eligibility is evaluated
- THEN Scheduled roles remain fail closed
- AND Lead does not reopen the Issue by inference
- AND the repository uses existing diagnosis or Human-escalation semantics rather than creating a generic recovery state

### Requirement: Required separate follow-up is directly queueable for fresh Explore revalidation

When an approved Explore, specification, or lifecycle decision explicitly classifies work as a still-applicable required separate follow-up, that exact durable defer decision SHALL be sufficient repository authority to create or reuse one corresponding tracker as `Change: unset + Lead / explore-change` pre-activation work.

The tracker MUST retain reconstructable linkage to the source coordination Issue/Change and exact defer decision/reference. Ordinary out-of-scope work, non-goals, optional ideas, speculative cleanup, and merely deferred/uncommitted prose MUST NOT gain admission from this requirement.

Materialization MUST be idempotent and MUST participate in the existing combined pre-activation queue; it MUST NOT create a parallel backlog/status vocabulary.

#### Scenario: Required follow-up is created at the defer boundary

- GIVEN an approved decision states that bounded work is required to be handled separately
- AND no equivalent unresolved tracker exists
- WHEN Lead persists the defer obligation
- THEN Lead creates one tracker with reconstructable source linkage
- AND routes it as `Change: unset + Lead / explore-change`
- AND later Explore fresh-reads whether the obligation remains warranted before any formal Change activation

#### Scenario: Optional future work is mentioned

- GIVEN a proposal or discussion identifies optional future work or a non-goal
- WHEN the current Change records that scope boundary
- THEN no pre-activation workflow admission is created solely from that mention

### Requirement: Pre-activation Propose may conservatively fall back to Explore

A valid admitted `Lead / propose-change` work item with `Change: unset` MAY route to `Lead / explore-change` when Lead cannot author a decision-complete proposal from current evidence without inventing material requirements or approach meaning.

The fallback MUST remain on the same coordination Issue and inside the existing admission authority envelope, MUST keep `Change: unset`, and MUST use the existing same-role durable result/routing/fresh-read continuation contract without a synthetic cross-role handoff or second generic Human admission. Explore MAY return to Propose only after `PROPOSAL_READY` under the existing in-envelope continuation rule.

Once a non-`unset` Change identity exists, specification ambiguity MUST use the formal `Lead / resolve-question` path rather than returning to pre-Propose Explore.

#### Scenario: Direct-Propose intake is not proposal-ready

- GIVEN a valid admitted coordination Issue is routed to `Lead / propose-change`
- AND `Change: unset`
- AND current evidence is insufficient for a bounded decision-complete proposal
- WHEN Lead can investigate within the already admitted problem envelope
- THEN Lead records the pre-activation readiness disposition
- AND routes the same Issue to `Lead / explore-change`
- AND no second generic Human admission is required solely because Lead selected the safer pre-activation action

#### Scenario: Formal Change already exists

- GIVEN a coordination Issue has a persisted non-`unset` Change identity
- AND a material specification ambiguity appears
- WHEN Lead determines clarification is required
- THEN the workflow uses the formal specification-question path
- AND does not route backward to pre-Propose Explore

### Requirement: Flow visualization is derived and non-authoritative

GitHub Project/Kanban fields, blocker views, age metrics, and other flow presentation MAY project repository durable workflow evidence for Human observability, but they MUST NOT override or substitute for default-branch governance, coordination Issue routing/identity, PR/OpenSpec state, or exact gate evidence used for scheduled execution.

#### Scenario: Project status disagrees with repository routing

- GIVEN a GitHub Project field displays a status that conflicts with authoritative repository workflow evidence
- WHEN a Scheduled Agent reconstructs the next legal action
- THEN the Project field is treated as presentation only
- AND the repository-governed durable state determines execution
