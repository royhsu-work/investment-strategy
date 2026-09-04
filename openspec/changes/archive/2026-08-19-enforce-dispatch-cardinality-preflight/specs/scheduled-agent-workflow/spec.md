## MODIFIED Requirements

### Requirement: Active-workflow cardinality and Issue-state coherence precede queue selection

Scheduled dispatch SHALL establish the complete cardinality of terminal-pending and formal active workflows before evaluating pre-activation queue order, blocker projection, priority, Project/Kanban state, or selecting/loading a mapped normal action.

The pre-dispatch reconstruction SHALL use repository-wide durable state sufficient to classify every candidate relevant to formal-active, terminal-pending, and bounded premature-close recovery semantics. The reconstruction MUST establish observable enumeration completeness for every query/read surface whose incompleteness could hide such a candidate. Pagination, bounded result limits, role-local searches, candidate-local reads, or first-page/search projections MUST NOT be treated as complete merely because they returned a plausible candidate or no candidate. If the available tool surface cannot establish complete repository-wide enumeration, cardinality is indeterminate.

From one complete current reconstruction, dispatch SHALL apply the following decision table before normal action execution:

| Formal active / terminal-pending cardinality | Legal dispatch result |
| --- | --- |
| `0` | Evaluate bounded recovery candidates, then the deterministic combined pre-activation queue when no recovery candidate blocks it. |
| `1` | Select only that formal/terminal workflow and derive role/action from its valid routing tuple. |
| `>1` | Fail closed before any normal mapped action executes. |
| indeterminate | Fail closed before any normal mapped action executes. |

A selected action SHALL consume that shared pre-dispatch classification as an execution precondition rather than starting from a candidate-local assumption. Before substantive `explore-change` work begins, the current reconstruction MUST still prove formal/terminal cardinality `0` and that the selected Issue is the deterministic combined pre-activation winner. Before a formal lifecycle/review/implementation action proceeds, the current reconstruction MUST prove that its selected coordination Issue is the sole formal/terminal workflow selected by the shared preflight. `propose-change` SHALL additionally retain its existing immediate pre-activation and post-write fresh-read checks, using the same complete-cardinality semantics. If routing, Issue state, Change identity, repository enumeration, or winner identity is stale or contradictory at action entry, the action MUST fail closed and reconstruct instead of proceeding from previously selected local context.

If active-workflow cardinality cannot be established as exactly zero or one, dispatch MUST fail closed and MUST NOT infer that queued work is eligible. Normal nonterminal routed workflow work MUST have an open coordination Issue. A closed Issue with nonterminal routing is contradictory durable state except for the existing narrow terminal-pending `Lead / finalize-archive` shape and MUST NOT execute its stale routed action while closed.

When repository-wide durable state already contains more than one formal active/terminal-pending workflow, Scheduled roles SHALL remain fail closed. They MUST NOT select a winner by age, role/action priority, issue number, model judgment, or presumed legitimacy; MUST NOT automatically clear or rewrite persisted Change identities; and MUST NOT mutate routing merely to force cardinality back to one. Human/maintainer administrative repair may correct the durable repository state outside normal Scheduled-Agent lifecycle execution. A later wake MUST reconstruct the repaired current repository state from scratch before any normal action resumes; prior PASS/readiness evidence does not override newly changed `main`, routing, or lifecycle evidence.

A closed nonterminal Issue MAY be recovered automatically only for the demonstrated premature-close class when durable reconstruction proves all of the following: the Issue has a persisted non-`unset` Change and exactly one otherwise legal nonterminal routing tuple; matching durable lifecycle evidence proves the Change is unfinished; no authorized final Archive/native-close completion or `LIFECYCLE_COMPLETE` exists; no qualifying provenance-bound Human decision requires termination/non-resumption; and repository-wide reconstruction finds no other normal formal/terminal-pending workflow or second premature-close recovery candidate. A bare Issue close event or actor identity MUST NOT by itself count as qualifying Human termination authority.

When exactly one such premature-close recovery candidate exists, it MUST block pre-activation intake and normal lifecycle execution. The governed recovery owner/action SHALL be `Lead / resolve-question`. Lead MAY reopen that same coordination Issue while preserving its immutable Change identity and pre-close nonterminal routing tuple. After reopening, Lead MUST fresh-read Issue state, routing, matching OpenSpec/PR lifecycle evidence, and repository-wide active cardinality. Recovery is complete only when the reopened Issue reconstructs as the single coherent formal active workflow and the preserved routing tuple remains legal. The recovery invocation MUST NOT execute the preserved normal lifecycle action; a later wake MUST dispatch from the freshly reconstructed normal tuple.

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
- WHEN `explore-change` consumes its action-entry precondition
- THEN it does not continue from the earlier candidate-local selection
- AND it fails closed and reconstructs current repository-wide state

#### Scenario: Two active workflows fail closed before a mapped action executes

- GIVEN repository-wide durable state contains two open valid-routing Issues with persisted non-`unset` Change identities
- WHEN any Scheduled Task wakes in `workflow-dynamic` mode
- THEN cardinality is greater than one
- AND no normal mapped action is selected or executed
- AND the Scheduled role does not choose a winner or rewrite either workflow to manufacture cardinality one

#### Scenario: Indeterminate enumeration cannot authorize work

- GIVEN the available repository read is capped, incomplete, or otherwise cannot prove that every formal/terminal candidate was enumerated
- WHEN dispatch derives active-workflow cardinality
- THEN cardinality is indeterminate
- AND neither formal action execution nor pre-activation intake is authorized from that incomplete evidence

#### Scenario: Human or maintainer repairs a multiple-active repository state

- GIVEN Scheduled dispatch previously failed closed because multiple formal workflows existed
- AND Human or maintainer later performs an administrative durable-state repair outside normal Scheduled-Agent lifecycle execution
- WHEN a later Scheduled Task wakes
- THEN it reconstructs repository-wide state from the repaired current repository
- AND it does not inherit a previously guessed winner or stale routing/readiness evidence
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
- AND the recovery invocation does not execute the preserved normal action

#### Scenario: Premature close cannot be recovered unambiguously

- GIVEN a closed nonterminal coordination Issue has missing or contradictory lifecycle evidence, a qualifying Human termination decision, another formal/terminal-pending workflow, or another premature-close recovery candidate
- WHEN recovery eligibility is evaluated
- THEN Scheduled roles remain fail closed
- AND Lead does not reopen the Issue by inference
- AND the repository uses existing diagnosis or Human-escalation semantics rather than creating a generic recovery state
