## MODIFIED Requirements

### Requirement: Active-workflow cardinality and Issue-state coherence precede queue selection

Scheduled dispatch SHALL establish the complete cardinality of terminal-pending and formal active workflows before evaluating pre-activation queue order, blocker projection, priority, Project/Kanban state, or selecting/loading a mapped normal action.

The pre-dispatch reconstruction SHALL use repository-wide durable state sufficient to classify every candidate relevant to formal-active, terminal-pending, and bounded premature-close recovery semantics. The reconstruction MUST establish observable enumeration completeness for every query/read surface whose incompleteness could hide such a candidate. Pagination, bounded result limits, role-local searches, candidate-local reads, or first-page/search projections MUST NOT be treated as complete merely because they returned a plausible candidate or no candidate. If the available tool surface cannot establish complete repository-wide enumeration, cardinality is indeterminate.

Every field asserted as **current** for dispatch authorization—including Issue open/closed state, persisted `Change:` identity, routing labels/tuple, and enumeration/completeness metadata—MUST be derived from authoritative GitHub observations obtained during the same repository-runtime execution that consumes the decision. Conversation history, prior model/Scheduled-Agent output, model memory, cached observations, historical Issue body/comment routing, copied summaries, or an earlier execution's snapshot MUST NOT satisfy a current-state predicate. Historical durable evidence MAY be consumed only for audit/lifecycle semantics that are explicitly historical; it cannot override a contradictory or absent current GitHub routing/state observation. If authoritative current fields or their provenance/completeness cannot be established, authorization is indeterminate and MUST fail closed.

The repository SHALL provide one production executable dispatch-precondition implementation that consumes an explicit normalized repository Issue snapshot together with explicit enumeration-completeness and observation-provenance evidence and returns the deterministic cardinality/selection/action-authorization decision required by this requirement. Executable regression coverage, the repository-hosted pre-model runtime gate, and the durable-effect application gate MUST consume that same implementation rather than maintaining a parallel classifier or re-deriving candidate-local behavior from prose. The executable input contract MUST prevent historical/prior-run/cache/conversation-only state from being represented as provenance-qualified current authorization input.

Normal scheduled mapped work after runtime cutover MUST be authorized by repository-hosted executable dispatch **before the mapped model worker is invoked**. The model worker MUST NOT be responsible for deciding whether its own mapped action was allowed to begin. A legacy/direct ChatGPT Scheduled Task or other model invocation outside that machine-gated runtime is not sufficient authorization for a normal mapped action after cutover.

From one complete current reconstruction, dispatch SHALL apply the following decision table before normal mapped model invocation:

| Formal active / terminal-pending cardinality | Legal dispatch result |
| --- | --- |
| `0` | Evaluate bounded recovery candidates, then the deterministic combined pre-activation queue when no recovery candidate blocks it. |
| `1` | Select only that formal/terminal workflow and derive role/action from its valid routing tuple. |
| `>1` | Fail closed before any normal mapped model worker is invoked. |
| indeterminate | Fail closed before any normal mapped model worker is invoked. |

Before substantive `explore-change` work begins, the machine runtime MUST prove formal/terminal cardinality `0`, no blocking bounded recovery candidate, and that the selected Issue is the deterministic combined pre-activation winner. Before a formal lifecycle/review/implementation worker is invoked, the same execution MUST prove that its coordination Issue is the sole formal/terminal workflow selected by the shared preflight. A fixed scheduled role slot whose role does not equal the selected current role MUST exit without invoking a mapped model worker.

`propose-change` activation is a durable effect and therefore MUST NOT be written directly by the model worker. The application boundary SHALL perform the shared complete-cardinality check immediately before the activation write and again from a fresh repository-wide snapshot immediately after the write. If routing, Issue state, Change identity, repository enumeration, winner identity, observation provenance, or completeness is stale, unavailable, incomplete, or contradictory at application time, the effect MUST fail closed rather than proceed from the worker's earlier local context.

A Propose activation SHALL be accepted for legal successor execution only when the immediate post-write reconstruction proves complete enumeration, valid authoritative observation provenance, and exactly one formal active/terminal-pending workflow corresponding to the expected selected coordination Issue, Change identity, and routing. If competing durable state produces multiple/contradictory active workflows after the write, or current routing/state cannot be authoritatively observed, no activation in that state is accepted for normal continuation; the repository runtime fails closed and MUST NOT choose a winner or automatically rewrite another workflow.

Applicable canonical `ACTION_RESULT` evidence for `Lead / explore-change` and `Lead / propose-change` SHALL preserve the exact authoritative reconstruction evidence actually consumed by the machine runtime at their pre-model/apply boundaries rather than a separately invented Issue list. The action worker MAY contribute semantic result content, but an action result MUST NOT claim executable authorization that was not produced by the repository runtime. These fields are audit/diagnostic evidence only and MUST NOT replace current `Change + agent + action` workflow state or authorize a later execution without fresh reconstruction.

If active-workflow cardinality cannot be established as exactly zero or one, dispatch MUST fail closed and MUST NOT infer that queued work is eligible. Normal nonterminal routed workflow work MUST have an open coordination Issue. A closed Issue with nonterminal routing is contradictory durable state except for the existing narrow terminal-pending `Lead / finalize-archive` shape and MUST NOT execute its stale routed action while closed.

When repository-wide durable state already contains more than one formal active/terminal-pending workflow, normal runtime remains fail closed. It MUST NOT select a winner by age, role/action priority, Issue number, model judgment, or presumed legitimacy; MUST NOT automatically clear or rewrite persisted Change identities; and MUST NOT mutate routing merely to force cardinality back to one. Human/maintainer administrative repair may correct the durable repository state outside normal Scheduled-Agent lifecycle execution. A later runtime wake MUST reconstruct the repaired current repository state from scratch using authoritative current GitHub observations before any normal action resumes.

A closed nonterminal Issue MAY be recovered automatically only for the demonstrated premature-close class when durable reconstruction proves all of the following: the Issue has a persisted non-`unset` Change and exactly one otherwise legal nonterminal routing tuple; matching durable lifecycle evidence proves the Change is unfinished; no authorized final Archive/native-close completion or `LIFECYCLE_COMPLETE` exists; no qualifying provenance-bound Human decision requires termination/non-resumption; and repository-wide reconstruction finds no other normal formal/terminal-pending workflow or second premature-close recovery candidate. A bare Issue close event or actor identity MUST NOT by itself count as qualifying Human termination authority.

When exactly one such premature-close recovery candidate exists, it MUST block pre-activation intake and normal lifecycle execution. The governed recovery owner/action SHALL be `Lead / resolve-question`, but that recovery worker is still invoked only after the machine runtime selects it. Reopen/routing recovery effects MUST pass the same fresh application boundary and post-write reconstruction. Recovery MUST NOT execute the preserved pre-close normal lifecycle action inside the same stale authorization; a later fresh dispatch selects any resumed normal action.

If any recovery predicate is missing, contradictory, Human-reserved, or would create multiple-active ambiguity, the runtime MUST remain fail closed and MUST NOT reopen by inference. This bounded recovery MUST NOT create a generic fault state machine, hidden recovery registry, cancellation lifecycle, or authority to undo a qualifying Human decision.

#### Scenario: One active workflow is missed by a partial search

- GIVEN repository durable state contains one formal active workflow
- AND a partial query fails to enumerate it
- WHEN pre-activation work is also present
- THEN dispatch does not treat the partial query as proof of zero active workflows
- AND pre-activation work cannot be selected until repository-wide active cardinality is established
- AND no mapped model worker is invoked from the partial reconstruction

#### Scenario: Complete enumeration selects the sole active workflow

- GIVEN repository-wide enumeration is complete
- AND exactly one formal active workflow exists
- AND one or more routed pre-activation Issues also exist
- WHEN repository-hosted scheduled dispatch performs its preflight
- THEN only the formal active workflow is selected
- AND its routing tuple determines the selected role/action
- AND no queued Explore or Propose worker begins

#### Scenario: Pre-activation Explore revalidates zero formal WIP before substantive research

- GIVEN a fixed Lead runtime slot wakes while an open `Lead / explore-change + Change: unset` Issue is queued
- AND another formal workflow currently occupies WIP or complete current cardinality cannot be established
- WHEN the repository runtime performs pre-model dispatch
- THEN it does not invoke the queued Explore worker
- AND it fails closed or selects the actual formal workflow according to the production classifier

#### Scenario: Production classifier rejects the #100/#130 recurrence shape

- GIVEN complete provenance-qualified classifier input contains #100 as a formal active workflow
- AND #130 is an open routed `Lead / explore-change + Change: unset` pre-activation candidate
- WHEN the production classifier evaluates the repository state before model invocation
- THEN it selects the formal workflow rather than #130
- AND no model request for #130 Explore is emitted
- AND regression/runtime coverage calls the production implementation rather than a parallel test classifier

#### Scenario: Previously routed Issue with current routing removed is not active

- GIVEN historical durable Issue text or comments record that Issue #130 previously had a formal routing tuple
- AND authoritative current GitHub observations show that #130 currently lacks the required routing labels
- WHEN current repository state is normalized
- THEN historical routing text does not restore or synthesize current routing
- AND #130 is not classified as formal-active solely from that historical evidence

#### Scenario: Prior execution output cannot satisfy current-state predicates

- GIVEN a previous execution recorded a routing/state snapshot for an Issue
- AND the current runtime execution has not obtained authoritative GitHub observations sufficient to establish that Issue's current routing/state
- WHEN dispatch authorization is evaluated
- THEN the previous output, model memory, cache, and conversation context are non-authoritative for the current predicate
- AND authorization is indeterminate rather than inferred from the stale snapshot

#### Scenario: Current routing observation is unavailable

- GIVEN repository enumeration returns a candidate whose current routing labels are required for formal-workflow classification
- AND current authoritative GitHub evidence cannot establish those labels
- WHEN dispatch authorization is evaluated
- THEN observation provenance is incomplete
- AND authorization fails closed as indeterminate
- AND historical Issue prose/comments MUST NOT fill the missing current routing fields

#### Scenario: Executable regression and machine runtime share one classifier

- GIVEN the repository defines the production executable dispatch precondition
- WHEN regression coverage, pre-model runtime authorization, or durable-effect application evaluates cardinality, completeness, observation provenance, deterministic selection, or action authorization
- THEN it calls that production implementation
- AND it does not define a parallel behavioral classifier

#### Scenario: Scheduled-Agent environment lacks repository execution

- GIVEN the legacy ChatGPT Scheduled Task environment cannot demonstrate a repository-controlled executable pre-model hook
- WHEN the machine-gated GitHub Actions runtime has become authoritative for normal scheduled mapped work
- THEN the legacy environment is not used as an independent normal mapped-action scheduler
- AND a model invocation in that environment cannot substitute for repository-runtime dispatch authorization

#### Scenario: Explore action result preserves consumed current-state identities

- GIVEN `Lead / explore-change` was authorized by complete authoritative pre-model runtime reconstruction
- AND substantive Explore later reaches a canonical result
- WHEN the runtime applies the durable `ACTION_RESULT`
- THEN it records the applicable completeness/provenance and formal/recovery/pre-activation/selected Issue identities actually consumed by the runtime
- AND the durable comment remains audit evidence rather than authorization state for a later wake

#### Scenario: Propose post-write state must be accepted before continuation

- GIVEN the application-time pre-write reconstruction legally authorizes one `Lead / propose-change + Change: unset` Issue
- AND the authorized worker requests persistence of its expected non-`unset` Change identity
- WHEN the application boundary performs the write and immediately fresh-reconstructs repository state
- AND that reconstruction observes more than one formal active workflow, contradictory expected identity/routing, or provenance-incomplete current state
- THEN the activation is not accepted for normal successor execution
- AND the runtime fails closed without selecting a winner or automatically rewriting another workflow

#### Scenario: Two active workflows fail closed before a mapped action executes

- GIVEN repository-wide durable state contains two open valid-routing Issues with persisted non-`unset` Change identities
- WHEN any fixed Scheduled Agent runtime role wakes
- THEN cardinality is greater than one
- AND no normal mapped model action is invoked
- AND the runtime does not choose a winner or rewrite either workflow to manufacture cardinality one

#### Scenario: Indeterminate enumeration cannot authorize work

- GIVEN the available repository read is capped, incomplete, provenance-incomplete, or otherwise cannot prove that every formal/terminal candidate was enumerated from authoritative current GitHub state
- WHEN dispatch derives active-workflow cardinality
- THEN cardinality is indeterminate
- AND neither formal action execution nor pre-activation intake results in a mapped model invocation

#### Scenario: Human or maintainer repairs a multiple-active repository state

- GIVEN scheduled runtime previously failed closed because multiple formal workflows existed
- AND Human or maintainer later performs an administrative durable-state repair outside normal Scheduled-Agent lifecycle execution
- WHEN a later runtime wake occurs
- THEN it reconstructs repository-wide state from authoritative GitHub observations obtained during that later execution
- AND it does not inherit a previously guessed winner, stale routing/readiness evidence, or historical Issue prose as current routing
- AND normal execution resumes only if the new reconstruction independently satisfies the ordinary cardinality and routing contracts

#### Scenario: Nonterminal workflow Issue is closed prematurely and safely recoverable

- GIVEN a coordination Issue has a persisted non-`unset` Change and exactly one otherwise legal nonterminal routing tuple
- AND the Issue is closed outside the authorized terminal Archive boundary
- AND durable lifecycle evidence proves the Change remains unfinished
- AND no qualifying provenance-bound Human decision requires termination or non-resumption
- AND repository-wide reconstruction finds no other formal/terminal-pending workflow or premature-close recovery candidate
- WHEN machine dispatch reconstructs workflow state
- THEN the stale routed action is not executed while the Issue is closed
- AND pre-activation work is not selected
- AND `Lead / resolve-question` is the selected bounded recovery action
- AND any reopen/routing recovery effect is freshly authorized/applied by the runtime
- AND the preserved normal lifecycle action is not executed without a later fresh dispatch

#### Scenario: Premature close cannot be recovered unambiguously

- GIVEN a closed nonterminal coordination Issue has missing or contradictory lifecycle evidence, a qualifying Human termination decision, another formal/terminal-pending workflow, or another premature-close recovery candidate
- WHEN recovery eligibility is evaluated
- THEN runtime remains fail closed
- AND no recovery worker/effect reopens the Issue by inference
- AND the repository uses existing diagnosis or Human-escalation semantics rather than creating a generic recovery state

## ADDED Requirements

### Requirement: Machine-gated runtime authorizes mapped work before model invocation and reauthorizes durable effects

The repository SHALL provide a default-branch GitHub Actions Scheduled Agent runtime in which executable authorization precedes every normal mapped model invocation and durable model-requested effects are applied only after fresh executable reauthorization.

The runtime SHALL preserve fixed Lead, Reviewer, and Executor role slots. A schedule/manual trigger carries only its fixed role identity. Current coordination Issue, Change identity, routing/action, formal-active cardinality, recovery/pre-activation winner, completeness, and observation provenance MUST be acquired from authoritative GitHub state by the runtime and MUST NOT be supplied as authorization facts by cron text, model prompt, prior output, or user/comment prose.

Before invoking a mapped model worker, the runtime MUST execute the production dispatch classifier on a complete provenance-qualified current reconstruction. It may invoke a worker only when the classifier returns `AUTHORIZE` for exactly one Issue/current routing and the selected role equals the fixed invocation role. `FAIL_CLOSED`, `NO_WORK`, role mismatch, multiple-active, incomplete enumeration, contradictory state, or provenance failure MUST result in no mapped model invocation.

The authorized worker SHALL receive the exact selected Issue/role/action and the mapped default-branch role/Skill semantics. The worker runtime for this Change uses repository code integrating with the OpenAI Responses API and MUST NOT depend on Codex. Model/provider credentials and model selection are deployment configuration, not workflow authorization state.

The model-controlled worker MUST NOT possess durable write-capable GitHub credentials or persisted repository credentials that allow it to bypass the application boundary. It MAY read authoritative GitHub/repository evidence and modify a local workspace as required by its action. Any requested durable GitHub effect or local patch to be published SHALL be carried as invocation-local staged output to repository-owned application code.

Staged output is not workflow state and does not authorize application. Before applying a normal effect batch, the application boundary MUST fresh-reconstruct complete current GitHub state, execute the same production classifier, prove the exact source Issue/role/action is still authorized, and verify effect-specific current preconditions. Any requested routing successor MUST additionally be legal under the canonical `agents/workflow.md` topology. Stale or unprovable source state fails closed without applying the stale normal batch.

After an accepted effect batch, the runtime MUST fresh-observe the durable result. Any same-role continuation requires another complete production-classifier dispatch from that resulting current state. A cross-role successor ends the current fixed-role execution. No earlier classifier result or staged output can authorize the continuation.

Scheduled Agent runtime executions SHALL use one repository-wide serialization boundary and re-read current state when they actually execute. This execution serialization MUST NOT be represented as a repository lock, lease, heartbeat, claim, hidden queue, workflow owner, or second lifecycle state machine.

Before cutover, the runtime MUST demonstrate support for every current mapped normal action, including `Lead / explore-change` and `Lead / propose-change`. Legacy ChatGPT Scheduled Tasks MUST be disabled before/when the GitHub Actions runtime becomes authoritative and MUST NOT remain as an independent fallback normal scheduler. A partial/dual cutover does not satisfy this requirement.

PR-stage tests MUST verify the runtime with deterministic model/test doubles but MUST NOT be represented as live default-branch scheduled evidence. After merge to default branch, live verification MUST use ordinary current workflow state: a non-matching fixed-role slot proves pre-model STOP/no model invocation, and the matching slot proves production-classifier authorization before its real mapped model invocation. No synthetic second formal workflow or special routing state is required for this canary.

#### Scenario: Fixed role mismatch stops before model invocation

- GIVEN complete current reconstruction selects Issue #133 at a Lead action
- AND a Reviewer or Executor fixed runtime slot wakes
- WHEN the production classifier returns the selected Lead routing
- THEN the runtime exits without invoking any mapped model worker
- AND it does not mutate workflow state merely to make the slot eligible

#### Scenario: Exact authorized role and action invokes the mapped worker

- GIVEN complete provenance-qualified current reconstruction selects exactly Issue #133 at `Lead / resolve-question`
- AND the fixed Lead slot wakes
- WHEN the production classifier authorizes that exact current routing
- THEN the runtime invokes the Lead `resolve-question` worker with that exact Issue/role/action
- AND the worker is not asked to rediscover or override its own dispatch authorization

#### Scenario: Formal work prevents queued Explore model invocation

- GIVEN #100 is the sole formal active workflow
- AND #130 is a queued `Lead / explore-change + Change: unset` Issue
- WHEN the fixed Lead runtime slot wakes
- THEN the production classifier selects #100's current formal action
- AND no model request for #130 Explore is emitted

#### Scenario: Model worker cannot directly write durable GitHub state

- GIVEN an exact mapped worker has been machine-authorized
- WHEN model-controlled tools execute the action
- THEN they have no durable write-capable GitHub credential or persisted checkout credential
- AND requested Issue/PR/routing/ref/merge/close effects are staged for repository-owned application rather than directly committed by the model worker

#### Scenario: Stale worker result is rejected at application time

- GIVEN a mapped worker was authorized for one exact Issue/role/action
- AND current durable GitHub workflow state changes before its staged effects are applied
- WHEN the application boundary fresh-reconstructs state
- AND the production classifier no longer authorizes that exact source
- THEN the staged normal effect batch is not applied
- AND the runtime does not use the worker's earlier authorization as a stale write permit

#### Scenario: Routing successor is validated by canonical topology

- GIVEN a still-authorized source action requests a routing successor
- WHEN the application boundary evaluates the effect
- THEN it verifies the successor against the authoritative `agents/workflow.md` topology
- AND it does not maintain or consult a second normative lifecycle DAG
- AND an unsupported successor is rejected without routing mutation

#### Scenario: Same-role continuation performs a new machine dispatch

- GIVEN an authorized Lead action applies a legal durable successor that is also Lead-owned
- WHEN post-write state is freshly observed
- THEN the runtime executes the production classifier again from the new current state
- AND only a newly authorized matching Lead action may continue
- AND the prior action authorization is not reused

#### Scenario: Cross-role successor ends the current fixed-role execution

- GIVEN an authorized Lead action applies a legal successor routed to Reviewer
- WHEN post-write state is freshly observed
- THEN the current Lead runtime does not invoke the Reviewer worker
- AND Reviewer work waits for a Reviewer fixed slot that independently re-dispatches current state

#### Scenario: Full mapped-action coverage precedes cutover

- GIVEN the repository is preparing to make the GitHub Actions runtime authoritative
- WHEN cutover readiness is evaluated
- THEN all current mapped normal actions, including Explore and Propose, have executable runtime/worker/effect-path coverage
- AND no unsupported action requires an independent legacy ChatGPT Scheduled Task to remain live

#### Scenario: Legacy scheduler is not a fallback after cutover

- GIVEN the GitHub Actions runtime has become the authoritative normal scheduled execution path
- WHEN legacy ChatGPT Lead/Reviewer/Executor Scheduled Tasks are inspected
- THEN they are disabled for normal workflow execution
- AND an independently waking legacy model is not treated as an authorized mapped action merely because its prompt names the repository/role

#### Scenario: Live default-branch canary uses ordinary workflow state

- GIVEN the runtime implementation has been merged to the default branch
- AND #133 remains in an ordinary current lifecycle action
- WHEN a non-matching fixed role slot runs
- THEN Actions evidence proves it stopped before a model invocation
- WHEN the matching fixed role slot later runs
- THEN Actions evidence proves complete current acquisition and production-classifier authorization occurred before the real mapped model invocation
- AND any requested durable effects are freshly reauthorized before application
- AND no synthetic second formal workflow or special canary routing state is created
