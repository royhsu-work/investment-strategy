## MODIFIED Requirements

### Requirement: Active-workflow cardinality and Issue-state coherence precede queue selection

Scheduled dispatch SHALL establish the complete cardinality of terminal-pending and formal active workflows before evaluating pre-activation queue order, blocker projection, priority, Project/Kanban state, or selecting/loading a mapped normal action.

The pre-dispatch reconstruction SHALL use repository-wide durable state sufficient to classify every candidate relevant to formal-active, terminal-pending, and bounded premature-close recovery semantics. The reconstruction MUST establish observable enumeration completeness for every query/read surface whose incompleteness could hide such a candidate. Pagination, bounded result limits, role-local searches, candidate-local reads, or first-page/search projections MUST NOT be treated as complete merely because they returned a plausible candidate or no candidate. If the available tool surface cannot establish complete repository-wide enumeration, cardinality is indeterminate.

Every field asserted as **current** for dispatch authorization—including Issue open/closed state, persisted `Change:` identity, routing labels/tuple, and enumeration/completeness metadata—MUST be derived from authoritative GitHub observations obtained during the same execution that consumes the decision. Conversation history, prior Scheduled-Agent output, model memory, cached observations, historical Issue body/comment routing, copied summaries, or an earlier execution's snapshot MUST NOT satisfy a current-state predicate. Historical durable evidence MAY be consumed only for audit/lifecycle semantics that are explicitly historical; it cannot override a contradictory or absent current GitHub routing/state observation. If authoritative current fields or their provenance/completeness cannot be established, authorization is indeterminate and MUST fail closed.

The repository SHALL provide one production executable dispatch-precondition implementation that consumes an explicit normalized repository Issue snapshot together with explicit enumeration-completeness and observation-provenance evidence and returns the deterministic cardinality/selection/action-authorization decision required by this requirement. Executable regression coverage and any repository-hosted machine authorization Gate MUST consume that same implementation rather than maintaining a parallel classifier or re-deriving candidate-local behavior from prose. The executable input contract MUST prevent historical/prior-run/cache/conversation-only state from being represented as provenance-qualified current authorization input.

This requirement does not assume that the Scheduled-Agent container itself can execute repository Python. Outside a repository-hosted machine Gate, Scheduled roles still MUST perform the shared fresh complete-cardinality/current-state reconstruction required by default-branch governance and MUST fail closed on stale, incomplete, contradictory, or provenance-unqualified current evidence. They MUST NOT claim that an executable helper was consumed unless the execution environment actually ran that helper.

From one complete current reconstruction, dispatch SHALL apply the following decision table before normal action execution:

| Formal active / terminal-pending cardinality | Legal dispatch result |
| --- | --- |
| `0` | Evaluate bounded recovery candidates, then the deterministic combined pre-activation queue when no recovery candidate blocks it. |
| `1` | Select only that formal/terminal workflow and derive role/action from its valid routing tuple. |
| `>1` | Fail closed before any normal mapped action executes. |
| indeterminate | Fail closed before any normal mapped action executes. |

Before substantive `explore-change` work begins, a fresh current reconstruction MUST still prove formal/terminal cardinality `0`, no blocking bounded recovery candidate, and that the selected Issue is the deterministic combined pre-activation winner. Before a formal lifecycle/review/implementation action proceeds, a fresh current reconstruction MUST still prove that its coordination Issue is the sole formal/terminal workflow selected by the shared preflight. `propose-change` SHALL additionally perform the shared complete-cardinality check immediately before the activation write and again from a fresh repository-wide snapshot immediately after the write. If routing, Issue state, Change identity, repository enumeration, winner identity, observation provenance, or completeness is stale, unavailable, incomplete, or contradictory at action entry, the action MUST fail closed and reconstruct instead of proceeding from previously selected local context.

A Propose activation SHALL be accepted for legal successor execution only when the immediate post-write reconstruction proves complete enumeration, valid authoritative observation provenance, and exactly one formal active/terminal-pending workflow corresponding to the expected selected coordination Issue, Change identity, and routing. If competing durable state produces multiple/contradictory active workflows after the write, or current routing/state cannot be authoritatively observed, no activation in that state is accepted for normal continuation; Scheduled roles fail closed and MUST NOT choose a winner or automatically rewrite another workflow.

Applicable canonical `ACTION_RESULT` evidence for `Lead / explore-change` and `Lead / propose-change` SHALL preserve the exact authoritative reconstruction evidence actually consumed at their pre-activation boundaries rather than a separately invented Issue list. When a repository-hosted executable Gate produced the applicable decision, the result MAY additionally preserve that Gate's exact classifier output. These fields are audit/diagnostic evidence only and MUST NOT replace current `Change + agent + action` workflow state or authorize a later execution without fresh reconstruction.

If active-workflow cardinality cannot be established as exactly zero or one, dispatch MUST fail closed and MUST NOT infer that queued work is eligible. Normal nonterminal routed workflow work MUST have an open coordination Issue. A closed Issue with nonterminal routing is contradictory durable state except for the existing narrow terminal-pending `Lead / finalize-archive` shape and MUST NOT execute its stale routed action while closed.

When repository-wide durable state already contains more than one formal active/terminal-pending workflow, Scheduled roles SHALL remain fail closed. They MUST NOT select a winner by age, role/action priority, issue number, model judgment, or presumed legitimacy; MUST NOT automatically clear or rewrite persisted Change identities; and MUST NOT mutate routing merely to force cardinality back to one. Human/maintainer administrative repair may correct the durable repository state outside normal Scheduled-Agent lifecycle execution. A later wake MUST reconstruct the repaired current repository state from scratch using authoritative current GitHub observations before any normal action resumes.

A closed nonterminal Issue MAY be recovered automatically only for the demonstrated premature-close class when durable reconstruction proves all of the following: the Issue has a persisted non-`unset` Change and exactly one otherwise legal nonterminal routing tuple; matching durable lifecycle evidence proves the Change is unfinished; no authorized final Archive/native-close completion or `LIFECYCLE_COMPLETE` exists; no qualifying provenance-bound Human decision requires termination/non-resumption; and repository-wide reconstruction finds no other normal formal/terminal-pending workflow or second premature-close recovery candidate. A bare Issue close event or actor identity MUST NOT by itself count as qualifying Human termination authority.

When exactly one such premature-close recovery candidate exists, it MUST block pre-activation intake and normal lifecycle execution. The governed recovery owner/action SHALL be `Lead / resolve-question`. Lead MAY reopen that same coordination Issue while preserving its immutable Change identity and pre-close nonterminal routing tuple. After reopening, Lead MUST fresh-read Issue state, routing, matching OpenSpec/PR lifecycle evidence, and repository-wide active cardinality. Recovery is complete only when the reopened Issue reconstructs as the single coherent formal active workflow and the preserved routing tuple remains legal. The recovery execution MUST NOT execute the preserved normal lifecycle action; a later wake MUST dispatch from the freshly reconstructed normal tuple.

If any recovery predicate is missing, contradictory, Human-reserved, or would create multiple-active ambiguity, Scheduled roles MUST remain fail closed and MUST NOT reopen by inference. This bounded recovery MUST NOT create a generic fault state machine, hidden recovery registry, cancellation lifecycle, or authority to undo a qualifying Human decision.

#### Scenario: One active workflow is missed by a partial search

- GIVEN repository durable state contains one formal active workflow
- AND a partial query fails to enumerate it
- WHEN pre-activation work is also present
- THEN dispatch does not treat the partial query as proof of zero active workflows
- AND pre-activation work cannot be selected until repository-wide active cardinality is established

#### Scenario: Complete enumeration selects the sole active workflow

- GIVEN repository-wide enumeration is complete
- AND exactly one formal active workflow exists
- AND one or more routed pre-activation Issues also exist
- WHEN workflow-dynamic dispatch performs its preflight
- THEN only the formal active workflow is selected
- AND its routing tuple determines the invocation role/action
- AND no queued Explore or Propose action begins

#### Scenario: Pre-activation Explore revalidates zero formal WIP before substantive research

- GIVEN repository-wide preflight initially selects an open `Lead / explore-change + Change: unset` Issue as the deterministic combined-queue winner
- AND before substantive Explore begins another durable formal workflow has appeared or completeness can no longer be established
- WHEN `explore-change` revalidates its action-entry precondition
- THEN it does not continue from the earlier candidate-local selection
- AND it fails closed and reconstructs current repository-wide state

#### Scenario: Production classifier rejects the #100/#130 recurrence shape

- GIVEN complete provenance-qualified classifier input contains #100 as a formal active workflow
- AND #130 is an open routed `Lead / explore-change + Change: unset` pre-activation candidate
- WHEN the production classifier evaluates the repository state
- THEN it selects the formal workflow rather than #130
- AND #130 Explore is not authorized by that decision
- AND regression coverage calls the production implementation rather than a parallel test classifier

#### Scenario: Previously routed Issue with current routing removed is not active

- GIVEN historical durable Issue text or comments record that Issue #130 previously had a formal routing tuple
- AND authoritative current GitHub observations show that #130 currently lacks the required routing labels
- WHEN current repository state is normalized
- THEN historical routing text does not restore or synthesize current routing
- AND #130 is not classified as formal-active solely from that historical evidence

#### Scenario: Prior execution output cannot satisfy current-state predicates

- GIVEN a previous execution recorded a routing/state snapshot for an Issue
- AND the current execution has not obtained authoritative GitHub observations sufficient to establish that Issue's current routing/state
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

#### Scenario: Executable regression and machine Gate share one classifier

- GIVEN the repository defines the production executable dispatch precondition
- WHEN regression coverage or a repository-hosted machine authorization Gate evaluates cardinality, completeness, observation provenance, deterministic selection, or action authorization
- THEN it calls that production implementation
- AND it does not define a parallel behavioral classifier

#### Scenario: Scheduled-Agent environment lacks repository execution

- GIVEN current Scheduled/manual execution can reconstruct GitHub state but cannot execute repository Python
- WHEN a non-Gate action-entry boundary is evaluated
- THEN the Agent does not claim executable-helper consumption
- AND it still applies the default-branch fresh complete-cardinality/current-state governance and fails closed when that evidence is incomplete or contradictory

#### Scenario: Explore action result preserves consumed current-state identities

- GIVEN `Lead / explore-change` was authorized by complete authoritative current-state reconstruction
- AND substantive Explore later reaches a durable action result
- WHEN Lead persists the canonical `ACTION_RESULT`
- THEN it records the applicable completeness/provenance and formal/recovery/pre-activation/selected Issue identities actually consumed
- AND the durable comment remains audit evidence rather than authorization state for a later wake

#### Scenario: Propose post-write state must be accepted before continuation

- GIVEN the immediate pre-write reconstruction legally authorizes one `Lead / propose-change + Change: unset` Issue
- AND Lead persists its expected non-`unset` Change identity
- WHEN the immediate fresh post-write reconstruction observes more than one formal active workflow, contradictory expected identity/routing, or provenance-incomplete current state
- THEN the activation is not accepted for normal successor execution
- AND Scheduled execution fails closed without selecting a winner or automatically rewriting another workflow

#### Scenario: Two active workflows fail closed before a mapped action executes

- GIVEN repository-wide durable state contains two open valid-routing Issues with persisted non-`unset` Change identities
- WHEN any Scheduled Task wakes in `workflow-dynamic` mode
- THEN cardinality is greater than one
- AND no normal mapped action is selected or executed
- AND the Scheduled role does not choose a winner or rewrite either workflow to manufacture cardinality one

#### Scenario: Indeterminate enumeration cannot authorize work

- GIVEN the available repository read is capped, incomplete, provenance-incomplete, or otherwise cannot prove that every formal/terminal candidate was enumerated from authoritative current GitHub state
- WHEN dispatch derives active-workflow cardinality
- THEN cardinality is indeterminate
- AND neither formal action execution nor pre-activation intake is authorized from that incomplete evidence

#### Scenario: Human or maintainer repairs a multiple-active repository state

- GIVEN Scheduled dispatch previously failed closed because multiple formal workflows existed
- AND Human or maintainer later performs an administrative durable-state repair outside normal Scheduled-Agent lifecycle execution
- WHEN a later Scheduled Task wakes
- THEN it reconstructs repository-wide state from authoritative GitHub observations obtained during that later execution
- AND it does not inherit a previously guessed winner, stale routing/readiness evidence, or historical Issue prose as current routing
- AND normal execution resumes only if the new reconstruction independently satisfies the ordinary cardinality and routing contracts

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
- AND the recovery execution does not execute the preserved normal action

#### Scenario: Premature close cannot be recovered unambiguously

- GIVEN a closed nonterminal coordination Issue has missing or contradictory lifecycle evidence, a qualifying Human termination decision, another formal/terminal-pending workflow, or another premature-close recovery candidate
- WHEN recovery eligibility is evaluated
- THEN Scheduled roles remain fail closed
- AND Lead does not reopen the Issue by inference
- AND the repository uses existing diagnosis or Human-escalation semantics rather than creating a generic recovery state

## ADDED Requirements

### Requirement: Issue-comment Transition Gate executes live formal-routing authorization

The repository SHALL provide a default-branch GitHub Actions Transition Gate that receives a newly created Issue-comment transition intent and executes repository-owned live authorization before performing an MVP routing mutation.

For this MVP, a transition request MUST be an Issue comment on an already-formal coordination Issue and MUST request only one of the two supported targets from current `Lead / resolve-question`: `Reviewer / review-openspec` or `Executor / implement-change`. The comment is intent only. The Gate MUST derive the Issue identity from the triggering GitHub event and MUST independently acquire current Change identity, current routing, repository-wide active-workflow state, enumeration completeness, and observation provenance from GitHub. Request prose MUST NOT satisfy those current-state predicates.

The Gate MUST execute the production dispatch classifier against its own complete provenance-qualified current reconstruction. It may accept a request only when that decision selects the same Issue at current `Lead / resolve-question`, the Issue remains formal/open with coherent Change identity, and the requested target is inside the bounded MVP successor set. The Gate MUST NOT create a second lifecycle topology owner; `agents/workflow.md` remains authoritative for the legal successor meaning.

Gate executions SHALL use one repository-wide concurrency boundary and SHALL reconstruct current GitHub state when each run actually executes. A request that became stale while waiting MUST be rejected from the newer current state rather than replaying comment-time assumptions.

The Gate SHALL return exactly one of `ACCEPTED`, `REJECTED`, or `INDETERMINATE`. Only `ACCEPTED` may mutate routing. Before mutation, the Gate MUST fresh-read the source Issue and require the accepted source precondition still holds. After mutation, it MUST fresh-read the Issue again and require the expected target routing is durably observable. `REJECTED` and `INDETERMINATE` MUST leave routing unchanged.

Gate result evidence SHALL identify the triggering request, requested target, completeness/provenance disposition, formal-active Issue identities, selected Issue/current routing, outcome/reason, and post-write routing when accepted. That evidence is audit-only and does not authorize a later execution.

The MVP does NOT claim that the current ChatGPT GitHub connector is physically unable to mutate routing labels directly. Direct connector routing-label writes remain a known capability limitation outside the Gate's acceptance guarantee. Routing-event provenance hardening, connector action restriction, Explore admission, Propose activation, and migration of other lifecycle transitions are outside this MVP.

Because an `issue_comment` workflow added by this Change is not a live default-branch trigger until merged, PR-stage adapter tests are necessary but insufficient live evidence. Before lifecycle completion, the repository MUST obtain post-merge canary evidence for one valid request that reaches the real default-branch event path and is accepted with the expected routing mutation, and one invalid/stale request that reaches the same event path and leaves routing unchanged.

#### Scenario: Valid resolve-question transition is accepted by the live Gate

- GIVEN exactly one formal active workflow exists on Issue #133
- AND its current routing is `Lead / resolve-question`
- AND the default-branch Gate receives `/transition reviewer review-openspec` on that Issue
- WHEN the Gate reconstructs complete provenance-qualified current GitHub state and the production classifier selects #133 at that source routing
- THEN the Gate returns `ACCEPTED`
- AND only then changes routing to `Reviewer / review-openspec`
- AND freshly verifies the target routing after the write

#### Scenario: Request on a non-selected Issue is rejected

- GIVEN the production classifier selects formal Issue #133
- AND another Issue receives an otherwise syntactically valid transition request
- WHEN the Gate evaluates that request
- THEN it returns `REJECTED`
- AND it performs no routing mutation on the requesting Issue

#### Scenario: Multiple-active or incomplete state is indeterminate

- GIVEN the Gate cannot establish complete repository enumeration or observes more than one formal active workflow
- WHEN it evaluates a transition request
- THEN it returns `INDETERMINATE`
- AND it performs no routing mutation

#### Scenario: Stale queued request does not replay comment-time routing

- GIVEN a request is created while an Issue is routed `Lead / resolve-question`
- AND the current routing changes before that Gate run executes
- WHEN the serialized Gate run reconstructs current state
- THEN it rejects the stale request
- AND it does not restore or overwrite the newer routing from the comment-time assumption

#### Scenario: Concurrent requests are serialized and the second re-evaluates current state

- GIVEN request A and request B target the same current `Lead / resolve-question` Issue
- AND request A executes first and is accepted
- WHEN request B later begins under the same Gate concurrency group
- THEN request B observes the routing produced by A
- AND request B is rejected as stale instead of being accepted from its earlier request context

#### Scenario: Direct connector label write is not represented as Gate acceptance

- GIVEN the current connector can still write Issue routing labels directly
- WHEN such a mutation occurs outside the Transition Gate
- THEN the repository MUST NOT describe that mutation as `ACCEPTED` Gate authorization
- AND this MVP makes no claim that the direct write was physically prevented

#### Scenario: Post-merge live canary distinguishes live event execution from fixtures

- GIVEN the Gate workflow has been merged to the default branch
- WHEN one controlled valid request and one controlled invalid/stale request are submitted through real Issue comments
- THEN durable Actions/request/result evidence proves both traversed the live default-branch `issue_comment` path
- AND the valid request mutates routing only after `ACCEPTED`
- AND the invalid/stale request leaves routing unchanged
