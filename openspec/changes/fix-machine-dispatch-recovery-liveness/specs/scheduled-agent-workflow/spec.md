# scheduled-agent-workflow Delta Specification

## MODIFIED Requirements

### Requirement: The deployed no-API bridge carries the production dispatch decision without model-side selection

After the no-API bridge and production dispatch path are deployed on the repository default branch, the no-API bridge SHALL execute the same repository-owned production dispatch orchestration consumed by runtime regression coverage and SHALL return its exact decision to the requesting Scheduled Task without model-side Issue/Role/Action selection.

The machine decision MUST remain correlated solely by the exact GitHub request comment ID and MUST identify the exact default-branch revision used to execute dispatch. Its durable response SHALL have this shape:

```text
DISPATCH_DECISION
Request-Comment-ID: <exact GitHub request comment ID>
Default-Branch-Revision: <exact handler checkout revision>
Disposition: AUTHORIZE | NO_WORK | FAIL_CLOSED
Reason: <bounded machine-owned diagnostic>  # NO_WORK / FAIL_CLOSED only
Issue: <exact Issue number>                  # AUTHORIZE only
Role: <lead|reviewer|executor>               # AUTHORIZE only
Action: <mapped action>                      # AUTHORIZE only
```

`AUTHORIZE` MUST contain exactly one Issue/Role/Action tuple produced by the production executable decision and MUST NOT require the Scheduled Task to reinterpret a diagnostic reason before loading that exact tuple. `NO_WORK` and `FAIL_CLOSED` MUST NOT contain an Issue/Role/Action tuple and MUST contain one bounded machine-owned `Reason` that identifies the executable classifier disposition without exposing model-generated interpretation as authority. The Scheduled Task MUST NOT replace, reinterpret, or fill in a missing tuple or reason from conversation history, Issue prose, previous invocation output, model memory, or another uncorrelated result.

The diagnostic reason is observability only. It MUST NOT authorize routing, `Change:` mutation, review or merge acceptance, recovery mutation, consequential effects, or another durable GitHub mutation. The machine decision SHALL authorize only creation/loading of the mapped model invocation for the exact `AUTHORIZE` tuple; all durable effect boundaries retain their existing fresh action/effect-specific preconditions.

#### Scenario: Authorize decision fixes the mapped model identity

- GIVEN the deployed production dispatch orchestration returns `AUTHORIZE` for exact Issue N and routing `Reviewer / review-openspec`
- WHEN the requesting Scheduled Task receives the exactly correlated `DISPATCH_DECISION`
- THEN the response contains Issue N, Role `reviewer`, and Action `review-openspec`
- AND only that mapped model invocation may be loaded from the decision
- AND the model does not select a different Issue, Role, or Action from prose or prior context

#### Scenario: Fail-closed result creates no model authority

- GIVEN the deployed production dispatch orchestration returns `FAIL_CLOSED`
- WHEN the requesting Scheduled Task consumes the exactly correlated decision
- THEN the result contains no Issue/Role/Action tuple
- AND it contains one bounded machine-owned diagnostic reason for the fail-closed classification
- AND no mapped Role or Skill is loaded from model inference
- AND no consequential workflow mutation is authorized by the decision or diagnostic

#### Scenario: No-work result creates no synthetic work

- GIVEN the deployed production dispatch orchestration returns `NO_WORK`
- WHEN the requesting Scheduled Task consumes the exactly correlated decision
- THEN the result contains no Issue/Role/Action tuple
- AND it contains one bounded machine-owned diagnostic reason for the no-work classification
- AND the model does not manufacture an advisory, queued Issue, or mapped action merely to avoid an idle result

#### Scenario: Uncorrelated decision is rejected

- GIVEN request comment C has one exact GitHub comment ID
- AND a `DISPATCH_DECISION` exists for another request comment
- WHEN the Scheduled Task evaluates the result for C
- THEN it rejects the other decision as uncorrelated
- AND it does not use the other decision's tuple, reason, or disposition as current authorization

#### Scenario: Real no-API machine dispatch is required before completion

- GIVEN production dispatch and the decision-producing bridge are deployed on `main`
- WHEN the Change is evaluated for final implementation completion
- THEN one real ChatGPT Scheduled Task invocation obtains and consumes an exactly correlated production `DISPATCH_DECISION`
- AND the evidence identifies the exact default-branch revision and returned disposition/tuple when authorized
- AND mapped semantic work begins only from the machine-selected `AUTHORIZE` tuple
- AND `NO_WORK` or `FAIL_CLOSED` does not gain a tuple through model interpretation

#### Scenario: Real no-API machine dispatch remains the deployed authority

- GIVEN production dispatch is deployed on `main`
- WHEN a real ChatGPT Scheduled Task invocation obtains and consumes an exactly correlated production `DISPATCH_DECISION`
- THEN the evidence identifies the exact default-branch revision and returned disposition/tuple when authorized
- AND mapped semantic work begins only from the machine-selected `AUTHORIZE` tuple
- AND `NO_WORK` or `FAIL_CLOSED` does not gain a tuple through model interpretation

### Requirement: Actionable workflow routing is one logical role/action tuple

A coordination Issue SHALL be actionable by scheduled roles only when it is open and contains exactly one valid `agent:<role>` label and exactly one valid `action:<action>` label forming a legal routing tuple for that role.

A closed coordination Issue that still retains a workflow routing tuple SHALL NOT be normal actionable work and SHALL represent unresolved routing/recovery debt until bounded recovery, terminal-retirement cleanup, legacy normalization, or administrative repair resolves it. During rollout, pre-existing terminal Issues that still carry legacy routing remain visible as such debt rather than being silently treated as safe history.

Repository-owned terminal close effects SHALL close the Issue and retire all workflow `agent:*` and `action:*` routing labels as one logical Issue mutation after a fresh read, while preserving every unrelated label. This routing-retirement rule applies both to formal `LIFECYCLE_COMPLETE` closure and to legal pre-Change terminal research closure after `NO_CHANGE_REQUIRED` or `NO_GO`.

A closed coordination Issue with valid terminal completion and retired workflow routing is terminal history and MUST NOT participate in normal formal-workflow routing/cardinality or current unresolved-recovery enumeration. A closed Issue with retained routing MUST NOT be treated as terminal merely from age, prose, or prior model output.

Zero, multiple, contradictory, or illegal routing labels on an open actionable Issue MUST fail closed and MUST NOT be resolved by model inference. Unrelated Issue labels MUST be preserved during routing changes, terminal routing retirement, and legacy routing normalization.

#### Scenario: Open coordination Issue has valid routing

- GIVEN an open coordination Issue has exactly one `agent:reviewer` label
- AND exactly one `action:review-openspec` label
- WHEN Reviewer discovers eligible work
- THEN the Issue is eligible for the Reviewer `review-openspec` action

#### Scenario: Closed terminal-pending Issue has the one legal exception

- GIVEN a coordination Issue is closed
- AND it still retains a valid nonterminal workflow routing tuple
- AND valid terminal completion for final terminal conditions is absent
- WHEN scheduled work discovery evaluates current unresolved obligations
- THEN the Issue is not eligible as normal routed work
- AND only the bounded premature-close recovery or fail-closed contract may apply

#### Scenario: Closed completed Issue is terminal history

- GIVEN a coordination Issue has valid `LIFECYCLE_COMPLETE` evidence for its final reviewed and merged Archive revision
- AND repository-owned terminal closure succeeds
- WHEN the close postcondition is observed
- THEN the Issue is closed
- AND workflow `agent:*` and `action:*` routing labels are absent
- AND unrelated labels are preserved
- AND the Issue is terminal history that does not consume formal WIP or current unresolved-recovery capacity

#### Scenario: Terminal research closure retires routing

- GIVEN a pre-Change Explore has a legal terminal `NO_CHANGE_REQUIRED` or `NO_GO` result
- AND the coordination Issue still has `Change: unset`
- WHEN repository-owned application closes that research Issue
- THEN the same logical close effect retires workflow `agent:*` and `action:*` labels
- AND preserves unrelated labels
- AND later normal dispatch does not rediscover that completed research as unresolved recovery work

#### Scenario: Premature close retains an explicit recovery signal

- GIVEN a nonterminal coordination Issue is closed outside the repository-owned terminal close effect
- AND its valid workflow routing tuple remains attached
- WHEN production acquisition reconstructs current unresolved closed-routing state
- THEN that exact closed routed Issue is an unresolved recovery candidate
- AND normal dispatch does not infer terminal completion merely because the Issue is closed

#### Scenario: Coordination Issue has conflicting role labels

- GIVEN an open coordination Issue has both `agent:lead` and `agent:reviewer`
- WHEN a scheduled role evaluates eligibility
- THEN the routing is invalid
- AND no role proceeds by guessing which role owns the work

### Requirement: Active-workflow cardinality and Issue-state coherence precede queue selection

Workflow-dynamic Scheduled dispatch SHALL use repository-owned executable classification before loading any mapped Role or Skill. Steady-state production selection SHALL operate on two complete provenance-qualified current sets:

1. current open Issues needed for formal WIP and pre-activation selection; and
2. current closed Issues that still retain workflow routing labels and therefore represent unresolved recovery/routing debt.

The normal classifier SHALL consume only facts required to select current work: Issue number/state, persisted `Change:` identity, current routing tuple derived from labels, GitHub `created_at` ordering for pre-activation candidates, and enumeration/provenance completeness. Any additional admission fact required for a queued candidate MUST come from its existing canonical executable admission predicate rather than model interpretation of prose.

Completed closed workflow history, PR heads, CI state, OpenSpec artifacts, review evidence, lifecycle-specific PR evidence, and effect-specific mutation guards MUST NOT be prerequisites for global Issue selection. Completed terminal history SHALL NOT be re-enumerated or re-adjudicated merely to authorize unrelated current work. Action/effect-specific evidence SHALL be reconstructed only after an exact Issue/Role/Action or unresolved recovery candidate is selected by the boundary that owns those facts.

Dispatch read-reduction SHALL stop at that selection boundary. After `AUTHORIZE` selects an exact mapped Action, this Change MUST preserve that Action's existing default-branch evidence-reconstruction and evidence-consumption contract. It MUST NOT filter, truncate, replace, summarize away, impose a latest-comment shortcut on, or otherwise narrow action-required Issue comments, review findings, prior `ACTION_RESULT`/`HANDOFF`, Human-decision evidence, PR/review state, CI evidence, OpenSpec artifacts, or other durable inputs. If the governing Action currently requires complete Issue-comment reconstruction, that completeness requirement remains unchanged by this Change.

The rollout SHALL include one bounded repository-owned migration/reconciliation that completely enumerates the pre-existing closed routed workflow set and classifies each entry from authoritative evidence. Entries proven terminal/retired SHALL have only workflow routing labels removed while preserving unrelated labels and historical body/comments/state. Genuine unfinished obligations SHALL remain explicit current recovery work. Missing, contradictory, incomplete, or unqualified migration evidence MUST fail closed and leave the unresolved routing debt visible. The repository MUST NOT require a separate activation flag or hide legacy routed entries merely to permit dispatch. After successful normalization there SHALL be no recurring migration cursor, cutover watermark, terminal-history cache, or periodic full-history reconciliation requirement.

From the complete current open-Issue and unresolved closed-routing reconstruction, the executable classifier SHALL apply these rules before pre-activation selection:

| Current state | Required result |
| --- | --- |
| exactly `1` open formal workflow and `0` unresolved closed-routing candidates | AUTHORIZE only that formal workflow using its current valid routing tuple |
| `>1` open formal workflows | `FAIL_CLOSED` before any mapped action executes |
| open formal cardinality indeterminate | `FAIL_CLOSED` before any mapped action executes |
| exactly `1` open formal workflow and one or more unresolved closed-routing candidates | `FAIL_CLOSED`; current formal work MUST NOT coexist with unresolved closed routing debt |
| `0` open formal workflows and `0` unresolved closed-routing candidates | select the deterministic combined pre-activation winner, or return `NO_WORK` when none exists |
| `0` open formal workflows and exactly `1` unresolved closed-routing candidate | perform detailed exceptional recovery/retirement evaluation for that candidate before pre-activation or `NO_WORK` |
| `0` open formal workflows and `>1` unresolved closed-routing candidates | `FAIL_CLOSED` outside the bounded rollout migration path |
| unresolved closed-routing enumeration/provenance indeterminate | `FAIL_CLOSED` |

Production unresolved-recovery acquisition SHALL use complete paginated current GitHub observations constrained by `state=closed` and the existing workflow `agent:*` routing labels, deduplicate Issue identities, and validate the resulting current routing/Change shape. Because repository-owned terminal close and the one-time migration retire routing from terminal history, this acquisition SHALL scale with current unresolved routed closes rather than accumulated completed workflow history. It MUST NOT perform a repository-wide closed-history projection as a normal authorization prerequisite.

Detailed exceptional recovery SHALL obtain detailed terminal/recovery evidence only for the exact current unresolved closed-routing candidate selected by the current-state boundary. With formal cardinality zero, exactly one qualifying premature-close recovery candidate SHALL authorize that closed Issue as `Lead / resolve-question` and SHALL block pre-activation intake. A candidate that proves terminal/retired is not normal work and SHALL be eligible only for the bounded cleanup/retirement effect required to restore the closed+unrouted invariant before normal dispatch proceeds. Multiple candidates outside the one-time rollout migration, incomplete evidence, indeterminate required provenance, or genuine contradiction MUST produce `FAIL_CLOSED`.

Canonical terminal completion evidence used by migration or detailed recovery SHALL be classified by semantic consistency rather than raw comment cardinality. Multiple valid `LIFECYCLE_COMPLETE` journals that identify the same coordination Issue, immutable Change, `Lead / finalize-archive` action, terminal result, and non-conflicting terminal revision/Archive identity SHALL represent idempotent at-least-once replay of one terminal fact. If otherwise valid terminal journals disagree on immutable terminal identity or carry materially contradictory completion evidence, terminal evidence SHALL remain `INDETERMINATE`. Additional non-conflicting metadata or a later journal supplying previously omitted compatible metadata MUST NOT by itself turn one terminal fact into a contradiction.

Historical routing in Issue bodies/comments, prior model output, conversation history, cached observations, or normalized terminal history MUST NOT override the current authoritative open-Issue and unresolved closed-routing sets.

The combined pre-activation queue SHALL continue to contain every otherwise eligible open `Lead / explore-change + Change: unset` entry and every legally admitted open `Lead / propose-change + Change: unset` entry, ordered by earliest GitHub `created_at`, then lower Issue number. The model MUST NOT introduce another role/action priority or urgency score.

A selected action SHALL consume a fresh executable dispatch decision as an action-entry identity precondition rather than starting from a candidate-local assumption. Before a formal lifecycle/review/implementation action proceeds, current executable selection MUST still prove that its coordination Issue is the sole open formal workflow, its routing equals the selected Issue/Role/Action, and the current unresolved closed-routing set is empty. Before substantive `explore-change` or pre-activation `propose-change` work proceeds, executable selection MUST still prove open formal cardinality zero, no unresolved closed-routing candidate blocks intake, and the selected Issue remains the deterministic combined pre-activation winner. `propose-change` SHALL additionally preserve the immediate pre-write and fresh post-write activation checks. Stale, contradictory, incomplete, provenance-invalid, or execution-unavailable evidence MUST fail closed rather than being filled from model memory or prose.

When repository durable state contains more than one open formal workflow, Scheduled roles SHALL remain fail closed. They MUST NOT select a winner by age, role/action priority, Issue number, model judgment, presumed legitimacy, automatic Change clearing, or routing rewrite. Human/maintainer administrative repair MAY correct that illegal durable state outside normal Scheduled-Agent lifecycle execution. A later wake MUST reconstruct current repository state and obtain a new executable decision before normal work resumes.

A closed nonterminal Issue MAY be recovered automatically only for the demonstrated premature-close class when detailed exceptional recovery proves all existing predicates required for that recovery: persisted non-`unset` Change, one otherwise legal nonterminal routing tuple, unfinished lifecycle evidence, no valid terminal completion, no qualifying Human termination/non-resumption decision, no competing open formal workflow, and no second unresolved closed-routing candidate. Lead MAY reopen only that same Issue under `Lead / resolve-question`, preserve the immutable Change and pre-close routing identity, then fresh-reconstruct normal dispatch after reopening. The recovery invocation MUST NOT execute the preserved stale normal lifecycle action.

This separation MUST NOT create a generic fault state machine, hidden recovery registry, new lifecycle status, activation flag, lock, lease, heartbeat, retry counter, durable claim, cursor/watermark, cache-based authorization, or second workflow DAG. Deterministic normal-selection, unresolved-close, terminal-replay, migration, and exceptional-recovery mechanics SHALL be implemented and tested in production executable surfaces rather than duplicated as a second natural-language classifier for the model.

#### Scenario: One active workflow is missed by a partial search

- GIVEN repository durable state contains one open formal active workflow
- AND a partial query fails to enumerate it
- WHEN pre-activation work is also present
- THEN the partial query is not proof of zero formal WIP
- AND incomplete enumeration produces `FAIL_CLOSED`
- AND pre-activation work cannot be selected from that incomplete evidence

#### Scenario: Complete enumeration selects the sole active workflow

- GIVEN current open-Issue enumeration is provenance-qualified and complete
- AND current unresolved closed-routing enumeration is provenance-qualified and complete
- AND exactly one open formal active workflow exists
- AND no unresolved closed-routing candidate exists
- AND one or more routed pre-activation Issues also exist
- WHEN workflow-dynamic dispatch performs normal classification
- THEN only the formal active workflow is selected
- AND its current routing tuple determines the exact invocation Role/Action
- AND no queued Explore or Propose action begins

#### Scenario: Clear sole formal workflow does not require detailed closed-history forensics

- GIVEN current open-Issue and unresolved closed-routing enumeration are provenance-qualified and complete
- AND exactly one open formal active workflow exists
- AND no unresolved closed-routing candidate exists
- AND historical terminal workflows exist in the repository
- WHEN normal dispatch selects work
- THEN it authorizes the sole open formal workflow without enumerating or fetching historical terminal workflow evidence merely for that selection
- AND historical closed workflow state cannot override the current open formal winner by prose or stale context

#### Scenario: Sole formal workflow with a possible closed unfinished conflict does not fast-path authorization

- GIVEN current open-Issue and unresolved closed-routing enumeration are provenance-qualified and complete
- AND exactly one open formal active workflow A exists
- AND at least one different closed Issue still retains workflow routing and is therefore unresolved routing/recovery debt
- WHEN workflow-dynamic dispatch evaluates authorization
- THEN dispatch returns `FAIL_CLOSED`
- AND it does not execute A or reopen the closed Issue into a second formal workflow

#### Scenario: Formal zero with structural-clear history proceeds without detailed forensics

- GIVEN current open-Issue and unresolved closed-routing enumeration are provenance-qualified and complete
- AND open formal cardinality is zero
- AND no unresolved closed-routing candidate exists
- AND one or more eligible pre-activation candidates exist
- WHEN workflow-dynamic dispatch reaches pre-activation selection
- THEN it does not enumerate or fetch historical terminal workflow evidence merely to re-prove completion
- AND it selects the deterministic combined pre-activation winner
- AND the selected tuple remains subject to the normal fresh action-entry identity precondition

#### Scenario: Formal zero with no queued work and structural-clear history returns no work

- GIVEN current open-Issue and unresolved closed-routing enumeration are provenance-qualified and complete
- AND open formal cardinality is zero
- AND no unresolved closed-routing candidate exists
- AND no eligible pre-activation candidate exists
- WHEN workflow-dynamic dispatch evaluates repository work
- THEN it returns `NO_WORK` without historical terminal-workflow reconstruction
- AND the durable decision includes the bounded machine-owned no-work reason required by the no-API decision contract

#### Scenario: Possible closed unfinished conflict still enters detailed recovery

- GIVEN current unresolved closed-routing enumeration is provenance-qualified and complete
- AND exactly one closed Issue retains a coherent nonterminal workflow routing tuple
- AND open formal cardinality is zero
- WHEN workflow-dynamic dispatch evaluates authorization
- THEN it performs bounded detailed exceptional recovery for that exact Issue only
- AND qualifying or genuinely indeterminate recovery state preserves the existing recovery/fail-closed semantics

#### Scenario: Exceptional recovery runs before pre-activation selection

- GIVEN complete current open-Issue state contains zero formal workflows
- AND one or more open pre-activation candidates exist
- AND exactly one unresolved closed-routing candidate exists
- WHEN workflow-dynamic dispatch reaches the admission boundary
- THEN it executes detailed exceptional recovery for that candidate before authorizing the queue winner
- AND a qualifying or genuinely indeterminate recovery state blocks pre-activation
- AND the queue is evaluated only after the current unresolved candidate is cleared or retired

#### Scenario: No formal or queued work still checks recoverable closed workflow state

- GIVEN complete current open-Issue state contains zero formal workflows and no eligible pre-activation candidate
- AND exactly one unresolved closed-routing candidate exists
- WHEN workflow-dynamic dispatch evaluates whether the repository has no work
- THEN it executes detailed exceptional recovery for that candidate before returning `NO_WORK`
- AND a qualifying premature-close candidate is selected for `Lead / resolve-question` instead of being stranded
- AND genuinely indeterminate required recovery evidence produces `FAIL_CLOSED`

#### Scenario: Equivalent duplicate terminal journals are one terminal fact

- GIVEN migration or detailed recovery evaluates a closed workflow with two or more valid canonical `LIFECYCLE_COMPLETE` journals
- AND every journal identifies the same coordination Issue, immutable Change, `Lead / finalize-archive` action, and terminal result
- AND any recorded terminal revision/Archive identities are compatible and non-conflicting
- WHEN terminal evidence is classified
- THEN the journals are treated as idempotent at-least-once replay of one terminal fact
- AND terminal evidence is `terminal-history`
- AND duplicate journal count alone cannot block unrelated legal current work

#### Scenario: Contradictory terminal identities remain fail closed

- GIVEN migration or detailed recovery evaluates multiple otherwise valid terminal journals
- AND those journals disagree on an immutable terminal revision, Archive identity, or another required terminal fact
- WHEN terminal evidence is classified
- THEN terminal evidence is `INDETERMINATE`
- AND the affected migration or recovery boundary fails closed
- AND the model does not choose which terminal journal to trust

#### Scenario: Pre-activation Explore revalidates zero formal WIP before substantive research

- GIVEN normal classification identifies an open `Lead / explore-change + Change: unset` Issue as the deterministic combined-queue winner
- AND current unresolved closed-routing enumeration was complete and empty
- AND before substantive Explore begins another durable formal workflow or unresolved closed-routing candidate appears, or completeness can no longer be established
- WHEN `explore-change` consumes its fresh action-entry identity precondition
- THEN it does not continue from the earlier candidate-local selection
- AND it fails closed and reconstructs current executable dispatch

#### Scenario: Two active workflows fail closed before a mapped action executes

- GIVEN complete current open-Issue state contains two valid-routing Issues with persisted non-`unset` Change identities
- WHEN any Scheduled Task wakes in `workflow-dynamic` mode
- THEN open formal cardinality is greater than one
- AND production dispatch returns `FAIL_CLOSED`
- AND no normal mapped action is selected or executed
- AND the Scheduled role does not choose a winner or rewrite either workflow to manufacture cardinality one

#### Scenario: Indeterminate enumeration cannot authorize work

- GIVEN the available current open-Issue or unresolved closed-routing read is capped, incomplete, provenance-invalid, or otherwise cannot prove enumeration completeness
- WHEN normal dispatch derives current formal/recovery state
- THEN classification is fail-closed
- AND neither formal action execution nor pre-activation intake is authorized from that evidence

#### Scenario: Action-specific evidence is not a global selection prerequisite

- GIVEN production dispatch has selected one exact formal Issue routed to `Reviewer / review-openspec`
- AND that action later requires OpenSpec artifacts, exact validation evidence, review-specific provenance, and an older Issue comment under its existing reconstruction contract
- WHEN global Issue selection is performed and the mapped Reviewer action subsequently starts
- THEN those review-specific resources and the older comment are not required to identify the Issue/Role/Action
- AND after `AUTHORIZE`, Reviewer reconstructs every one of those required inputs under the unchanged mapped-action contract
- AND dispatch optimization does not filter, truncate, latest-only select, summarize away, or substitute for that older required comment or any other action-required durable evidence

#### Scenario: Human or maintainer repairs a multiple-active repository state

- GIVEN Scheduled dispatch previously returned `FAIL_CLOSED` because multiple open formal workflows existed
- AND Human or maintainer later performs an administrative durable-state repair outside normal Scheduled-Agent lifecycle execution
- WHEN a later Scheduled Task wakes
- THEN it reconstructs current repository state from authoritative GitHub observations
- AND executes production dispatch again
- AND it does not inherit a previously guessed winner or stale routing/readiness evidence

#### Scenario: Nonterminal workflow Issue is closed prematurely and safely recoverable

- GIVEN open formal cardinality is zero
- AND exactly one closed coordination Issue still retains a persisted non-`unset` Change and exactly one otherwise legal nonterminal routing tuple
- AND detailed exceptional recovery evidence proves the Change remains unfinished
- AND no valid terminal completion or qualifying Human termination/non-resumption decision exists
- AND no second unresolved closed-routing candidate exists
- WHEN the exceptional recovery boundary classifies current state
- THEN the stale routed action is not executed while the Issue is closed
- AND pre-activation work is not selected
- AND that Issue is selected for `Lead / resolve-question`
- AND Lead may reopen the same Issue without changing its immutable Change identity or preserved nonterminal routing tuple
- AND the recovery invocation does not execute the preserved normal action

#### Scenario: Premature close cannot be recovered unambiguously

- GIVEN a closed routed coordination Issue has missing or contradictory lifecycle evidence, a qualifying Human termination decision, another open formal workflow, another unresolved closed-routing candidate, or incomplete recovery provenance
- WHEN detailed exceptional recovery evaluates eligibility
- THEN Scheduled dispatch returns `FAIL_CLOSED`
- AND Lead does not reopen the Issue by inference
- AND the repository uses existing diagnosis or Human-escalation semantics rather than creating a generic recovery state

#### Scenario: Legacy routed terminal history is normalized once

- GIVEN rollout encounters pre-existing closed workflow Issues that still retain workflow routing labels
- WHEN the one-time migration/reconciliation runs
- THEN it completely enumerates that bounded pre-existing closed routed set
- AND removes only workflow routing labels from each entry proven terminal or retired while preserving unrelated labels and historical state/evidence
- AND leaves or restores genuine unfinished obligations as explicit recovery work
- AND any ambiguous or incomplete entry keeps the migration and normal authorization fail closed
- AND successful normalization leaves no activation flag, recurring migration cursor, watermark, or full-history scan
