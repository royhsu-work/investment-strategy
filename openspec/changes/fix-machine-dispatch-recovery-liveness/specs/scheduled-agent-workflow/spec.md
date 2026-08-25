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

- GIVEN transport-only `BRIDGE_OK` has already been proved
- AND production dispatch and the decision-producing bridge are deployed on `main`
- WHEN the Change is evaluated for final implementation completion
- THEN one real ChatGPT Scheduled Task invocation obtains and consumes an exactly correlated production `DISPATCH_DECISION`
- AND the evidence identifies the exact default-branch revision and returned disposition/tuple when authorized
- AND mapped semantic work begins only from the machine-selected `AUTHORIZE` tuple
- AND `NO_WORK` or `FAIL_CLOSED` does not gain a tuple through model interpretation
- AND lifecycle completion is not claimed from transport-only evidence

#### Scenario: Real no-API machine dispatch remains the deployed authority

- GIVEN production dispatch is deployed on `main`
- WHEN a real ChatGPT Scheduled Task invocation obtains and consumes an exactly correlated production `DISPATCH_DECISION`
- THEN the evidence identifies the exact default-branch revision and returned disposition/tuple when authorized
- AND mapped semantic work begins only from the machine-selected `AUTHORIZE` tuple
- AND `NO_WORK` or `FAIL_CLOSED` does not gain a tuple through model interpretation

### Requirement: Actionable workflow routing is one logical role/action tuple

A coordination Issue SHALL be actionable as ordinary open workflow work only when it is open and contains exactly one valid `agent:<role>` label and exactly one valid `action:<action>` label forming a legal routing tuple for that role.

A closed coordination Issue retaining any repository-governed workflow `agent:*` or `action:*` label SHALL NOT be ordinary actionable work and SHALL represent current closed-routing debt until bounded recovery, terminal-retirement cleanup, or administrative repair resolves it. This includes a complete retained tuple and partial residue containing only an `agent:*` or only an `action:*` label. Pre-existing terminal Issues that still carry legacy routing remain visible as debt rather than being silently treated as safe history.

Repository-owned terminal closure SHALL make `closed + no workflow routing labels` the logical postcondition for both formal `LIFECYCLE_COMPLETE` closure and legal pre-Change terminal research closure after `NO_CHANGE_REQUIRED` or `NO_GO`. The effect MUST be idempotent and MUST preserve every unrelated label under concurrent changes. It MUST NOT compute a complete label set from a fresh read and replace all labels as if that fresh read were a mutex or CAS primitive. Repository-owned application SHALL close Issue state without replacing labels, fresh-observe the Issue, remove only exact currently observed workflow routing labels through narrow label-removal effects with fresh preconditions/postconditions, and finish only after a fresh observation proves the Issue is closed and contains no workflow routing label.

If that logical effect is interrupted after close or after removal of only part of the workflow routing tuple, any remaining `agent:*` or `action:*` residue SHALL remain current closed-routing debt and MUST stay discoverable by production acquisition until cleanup completes. An already-completed close or already-removed routing label MUST NOT be replayed merely to simulate atomicity.

A closed coordination Issue with valid terminal completion and no workflow routing labels is terminal history and MUST NOT participate in normal formal-workflow routing/cardinality or current closed-routing-debt enumeration. A closed Issue with workflow routing residue MUST NOT be treated as terminal merely from age, prose, or prior model output.

Zero, multiple, contradictory, or illegal routing labels on an open actionable Issue MUST fail closed and MUST NOT be resolved by model inference. Unrelated Issue labels MUST be preserved during ordinary routing changes and terminal routing retirement.

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
- THEN the Issue is not eligible as ordinary routed work
- AND it remains current closed-routing debt
- AND only the bounded `Lead / resolve-question` recovery or fail-closed contract may apply

#### Scenario: Closed completed Issue is terminal history

- GIVEN a coordination Issue has valid `LIFECYCLE_COMPLETE` evidence for its final reviewed and merged Archive revision
- AND repository-owned terminal closure completes
- WHEN the terminal postcondition is freshly observed
- THEN the Issue is closed
- AND workflow `agent:*` and `action:*` routing labels are absent
- AND unrelated labels are preserved
- AND the Issue is terminal history that does not consume formal WIP or current closed-routing-debt capacity

#### Scenario: Terminal research closure retires routing

- GIVEN a pre-Change Explore has a legal terminal `NO_CHANGE_REQUIRED` or `NO_GO` result
- AND the coordination Issue still has `Change: unset`
- WHEN repository-owned application performs the terminal close effect
- THEN it closes the Issue without replacing its label set
- AND it removes only workflow `agent:*` and `action:*` labels through narrow retirement effects
- AND preserves unrelated labels
- AND later normal dispatch does not rediscover that completed research after routing retirement finishes

#### Scenario: Concurrent unrelated label survives terminal routing retirement

- GIVEN a terminal close effect has been authorized for one exact Issue
- AND the Issue has workflow routing plus unrelated label `foo`
- AND another actor adds unrelated label `security-review` after a fresh read but before a routing-label removal
- WHEN repository-owned application completes routing retirement
- THEN it removes only the exact workflow routing labels
- AND both `foo` and `security-review` remain present
- AND no stale complete-label replacement can erase the concurrent unrelated label

#### Scenario: Partial routing retirement remains observable

- GIVEN a terminal Issue is closed
- AND an interrupted retirement removed its `agent:*` label but left `action:finalize-archive`
- WHEN production acquisition reconstructs current closed-routing debt
- THEN the Issue is discovered from the retained action label
- AND it is not classified as retired terminal history merely because the role label is already absent
- AND candidate-bound cleanup may remove only the remaining routing residue after fresh terminal proof

#### Scenario: Premature close retains an explicit recovery signal

- GIVEN a nonterminal coordination Issue is closed outside the repository-owned terminal close effect
- AND one or more workflow routing labels remain attached
- WHEN production acquisition reconstructs current closed-routing debt
- THEN that exact Issue remains a closed-routing candidate
- AND normal dispatch does not infer terminal completion merely because the Issue is closed

#### Scenario: Coordination Issue has conflicting role labels

- GIVEN an open coordination Issue has both `agent:lead` and `agent:reviewer`
- WHEN a scheduled role evaluates eligibility
- THEN the routing is invalid
- AND no role proceeds by guessing which role owns the work

### Requirement: Active-workflow cardinality and Issue-state coherence precede queue selection

Workflow-dynamic Scheduled dispatch SHALL use repository-owned executable classification before loading any mapped Role or Skill. Steady-state production selection SHALL operate on two complete provenance-qualified current sets:

1. current open Issues needed for formal WIP and pre-activation selection; and
2. current closed Issues carrying any repository-governed workflow `agent:*` or `action:*` routing-label residue and therefore representing current closed-routing debt.

The normal classifier SHALL consume only facts required to select current work: Issue number/state, persisted `Change:` identity, current routing labels/tuple, GitHub `created_at` ordering for pre-activation candidates, and enumeration/provenance completeness. Any additional admission fact required for a queued candidate MUST come from its existing canonical executable admission predicate rather than model interpretation of prose.

Completed closed workflow history, PR heads, CI state, OpenSpec artifacts, review evidence, lifecycle-specific PR evidence, and effect-specific mutation guards MUST NOT be prerequisites for global Issue selection. Completed terminal history whose routing debt is retired SHALL NOT be re-enumerated or re-adjudicated merely to authorize unrelated current work. Action/effect-specific evidence SHALL be reconstructed only after an exact Issue/Role/Action or exact current closed-routing candidate is selected by the boundary that owns those facts.

Dispatch read-reduction SHALL stop at that selection boundary. After `AUTHORIZE` selects an exact mapped Action, this Change MUST preserve that Action's existing default-branch evidence-reconstruction and evidence-consumption contract. It MUST NOT filter, truncate, replace, summarize away, impose a latest-comment shortcut on, or otherwise narrow action-required Issue comments, review findings, prior `ACTION_RESULT`/`HANDOFF`, Human-decision evidence, PR/review state, CI evidence, OpenSpec artifacts, or other durable inputs. If the governing Action currently requires complete Issue-comment reconstruction, that completeness requirement remains unchanged by this Change.

There SHALL be no standalone bulk legacy migration/reconciliation action. Pre-existing closed routed history SHALL enter the same complete current closed-routing-debt set as interrupted or prematurely closed work. Repository-owned executable classification MAY authorize `Lead / resolve-question` for at most one exact closed candidate at a time, with a machine-derived debt disposition sufficient to constrain the action to one of these outcomes:

- proven terminal/retired candidate → request only candidate-local narrow routing retirement while keeping the Issue closed;
- exactly one qualifying unfinished premature-close candidate with no competing open formal workflow and no other unresolved debt → preserve the existing bounded reopen semantics;
- ambiguous, incomplete, contradictory, stale, or competing unresolved debt → no cleanup/reopen mutation and fail closed.

When more than one closed-routing candidate exists, executable classification MAY inspect only the current debt candidates needed to establish their authoritative debt dispositions. If one or more candidates are deterministically proven terminal/retired and no required evidence is incomplete or contradictory, the classifier MAY choose at most one terminal/retired candidate for candidate-local cleanup, ordered by lower Issue number after terminal classification. This ordering is cleanup determinism only and MUST NOT become a general workflow priority system. An unfinished candidate MUST NOT be reopened while another closed-routing candidate remains or while an open formal workflow exists. Multiple unfinished candidates, any candidate whose unfinished/terminal disposition is indeterminate, or incomplete current debt enumeration MUST produce `FAIL_CLOSED`.

From the complete current open-Issue and closed-routing-debt reconstruction, the executable classifier SHALL apply these rules before ordinary pre-activation selection:

| Current state | Required result |
| --- | --- |
| exactly `1` open formal workflow and `0` closed-routing debt candidates | AUTHORIZE only that formal workflow using its current valid routing tuple |
| `>1` open formal workflows | `FAIL_CLOSED` before any mapped action executes |
| open formal cardinality indeterminate | `FAIL_CLOSED` before any mapped action executes |
| exactly `1` open formal workflow plus debt containing a deterministically proven terminal/retired candidate and no ambiguous debt | select at most one such terminal/retired candidate for `Lead / resolve-question` cleanup before ordinary formal execution resumes |
| exactly `1` open formal workflow plus any unfinished or indeterminate debt candidate | `FAIL_CLOSED`; the closed Issue MUST NOT be reopened into a second formal workflow |
| `0` open formal workflows and `0` closed-routing debt candidates | select the deterministic combined pre-activation winner, or return `NO_WORK` when none exists |
| `0` open formal workflows and exactly `1` closed-routing candidate | perform detailed exceptional classification; proven terminal/retired debt routes candidate-local cleanup, one qualifying unfinished candidate routes bounded recovery, indeterminate evidence fails closed |
| `0` open formal workflows and `>1` closed-routing candidates | select at most one deterministically proven terminal/retired candidate for cleanup only when all evidence required for that choice is complete/non-contradictory; otherwise `FAIL_CLOSED` |
| closed-routing enumeration/provenance indeterminate | `FAIL_CLOSED` |

Production closed-routing acquisition SHALL use complete paginated current GitHub observations constrained by `state=closed` and the complete finite repository-governed workflow routing-label vocabulary: every governed `agent:<role>` label and every governed `action:<action>` label. It SHALL union and deduplicate Issue identities, fresh-observe the candidate's current state/labels, and treat any remaining workflow routing label as debt even when the other half of the tuple is absent. Because repository-owned terminal retirement removes all workflow routing residue from completed history, this acquisition SHALL scale with current routing debt rather than accumulated completed workflow history. It MUST NOT perform a repository-wide closed-history projection as a normal authorization prerequisite.

Detailed exceptional classification SHALL obtain terminal/recovery evidence only for current closed-routing debt candidates required to determine a safe current disposition. A selected candidate is the only historical/closed Issue the resulting `Lead / resolve-question` invocation may mutate. Repository-owned application MUST fresh-reauthorize that exact source action, exact candidate, exact machine disposition, current Issue state, and effect-specific preconditions before each close/reopen/label-removal effect; changed or stale candidate state rejects the mutation and requires fresh classification.

A candidate that proves terminal/retired is not ordinary workflow work. `Lead / resolve-question` MAY request only the narrow missing routing-retirement effects needed to establish `closed + no workflow routing`, and MUST NOT reopen or rewrite its immutable historical meaning. A qualifying unfinished candidate MAY be reopened only under the existing premature-close predicates and only when it is the sole remaining closed-routing debt with formal cardinality zero. The recovery invocation MUST NOT execute the preserved stale normal lifecycle action.

Canonical terminal completion evidence used by detailed debt classification SHALL be classified by semantic consistency rather than raw comment cardinality. Multiple valid `LIFECYCLE_COMPLETE` journals that identify the same coordination Issue, immutable Change, `Lead / finalize-archive` action, terminal result, and non-conflicting terminal revision/Archive identity SHALL represent idempotent at-least-once replay of one terminal fact. If otherwise valid terminal journals disagree on immutable terminal identity or carry materially contradictory completion evidence, terminal evidence SHALL remain `INDETERMINATE`. Additional non-conflicting metadata or a later journal supplying previously omitted compatible metadata MUST NOT by itself turn one terminal fact into a contradiction.

Historical routing in Issue bodies/comments, prior model output, conversation history, cached observations, or already-retired terminal history MUST NOT override the current authoritative open-Issue and closed-routing-debt sets.

The combined pre-activation queue SHALL continue to contain every otherwise eligible open `Lead / explore-change + Change: unset` entry and every legally admitted open `Lead / propose-change + Change: unset` entry, ordered by earliest GitHub `created_at`, then lower Issue number. The model MUST NOT introduce another role/action priority or urgency score.

A selected ordinary open action SHALL consume a fresh executable dispatch decision as an action-entry identity precondition rather than starting from a candidate-local assumption. Before a formal lifecycle/review/implementation action proceeds, current executable selection MUST still prove that its coordination Issue is the sole open formal workflow, its routing equals the selected Issue/Role/Action, and no closed-routing debt requires cleanup/recovery first. Before substantive `explore-change` or pre-activation `propose-change` work proceeds, executable selection MUST still prove open formal cardinality zero, no closed-routing debt blocks intake, and the selected Issue remains the deterministic combined pre-activation winner. `propose-change` SHALL additionally preserve the immediate pre-write and fresh post-write activation checks. Stale, contradictory, incomplete, provenance-invalid, or execution-unavailable evidence MUST fail closed rather than being filled from model memory or prose.

When repository durable state contains more than one open formal workflow, Scheduled roles SHALL remain fail closed. They MUST NOT select a winner by age, role/action priority, Issue number, model judgment, presumed legitimacy, automatic Change clearing, or routing rewrite. Human/maintainer administrative repair MAY correct that illegal durable state outside normal Scheduled-Agent lifecycle execution. A later wake MUST reconstruct current repository state and obtain a new executable decision before normal work resumes.

A closed nonterminal Issue MAY be recovered automatically only for the demonstrated premature-close class when detailed exceptional classification proves all existing predicates required for that recovery: persisted non-`unset` Change, one otherwise legal nonterminal routing identity, unfinished lifecycle evidence, no valid terminal completion, no qualifying Human termination/non-resumption decision, no competing open formal workflow, and no second closed-routing debt candidate. Lead MAY reopen only that same Issue under `Lead / resolve-question`, preserve the immutable Change and pre-close routing identity, then fresh-reconstruct normal dispatch after reopening. The recovery invocation MUST NOT execute the preserved normal action.

This separation MUST NOT create a generic fault state machine, hidden recovery registry, new lifecycle status, bulk migration action, activation flag, lock, lease, heartbeat, retry counter, durable claim, cursor/watermark, cache-based authorization, or second workflow DAG. Deterministic normal-selection, closed-routing-debt, terminal-replay, candidate cleanup, and exceptional-recovery mechanics SHALL be implemented and tested in production executable surfaces rather than duplicated as a second natural-language classifier for the model.

#### Scenario: One active workflow is missed by a partial search

- GIVEN repository durable state contains one open formal active workflow
- AND a partial query fails to enumerate it
- WHEN pre-activation work is also present
- THEN the partial query is not proof of zero formal WIP
- AND incomplete enumeration produces `FAIL_CLOSED`
- AND pre-activation work cannot be selected from that incomplete evidence

#### Scenario: Complete enumeration selects the sole active workflow

- GIVEN current open-Issue enumeration is provenance-qualified and complete
- AND current closed-routing-debt enumeration is provenance-qualified and complete
- AND exactly one open formal active workflow exists
- AND no closed-routing debt candidate exists
- AND one or more routed pre-activation Issues also exist
- WHEN workflow-dynamic dispatch performs normal classification
- THEN only the formal active workflow is selected
- AND its current routing tuple determines the exact invocation Role/Action
- AND no queued Explore or Propose action begins

#### Scenario: Clear sole formal workflow does not require detailed closed-history forensics

- GIVEN current open-Issue and closed-routing-debt enumeration are provenance-qualified and complete
- AND exactly one open formal active workflow exists
- AND no closed-routing debt candidate exists
- AND historical terminal workflows exist in the repository
- WHEN normal dispatch selects work
- THEN it authorizes the sole open formal workflow without enumerating or fetching retired historical terminal workflow evidence merely for that selection
- AND historical closed workflow state cannot override the current open formal winner by prose or stale context

#### Scenario: Sole formal workflow with a possible closed unfinished conflict does not fast-path authorization

- GIVEN current open-Issue and closed-routing-debt enumeration are provenance-qualified and complete
- AND exactly one open formal active workflow A exists
- AND a different closed Issue is classified as unfinished closed-routing debt
- WHEN workflow-dynamic dispatch evaluates authorization
- THEN dispatch returns `FAIL_CLOSED`
- AND it does not execute A or reopen the closed Issue into a second formal workflow

#### Scenario: Sole formal workflow can be paused for proven terminal debt cleanup

- GIVEN exactly one open formal active workflow exists
- AND current debt classification proves a different closed routed Issue is already terminal/retired
- AND the evidence required for that terminal classification is complete and non-contradictory
- WHEN workflow-dynamic dispatch selects the next safe bounded action
- THEN it may authorize only that exact closed Issue as `Lead / resolve-question` for candidate-local routing retirement
- AND the open formal workflow is not executed concurrently by that authorization
- AND the closed Issue is not reopened
- AND a later fresh dispatch resumes ordinary formal work only after debt is freshly cleared

#### Scenario: Formal zero with clear history proceeds without detailed forensics

- GIVEN current open-Issue and closed-routing-debt enumeration are provenance-qualified and complete
- AND open formal cardinality is zero
- AND no closed-routing debt candidate exists
- AND one or more eligible pre-activation candidates exist
- WHEN workflow-dynamic dispatch reaches pre-activation selection
- THEN it does not enumerate or fetch retired historical terminal workflow evidence merely to re-prove completion
- AND it selects the deterministic combined pre-activation winner
- AND the selected tuple remains subject to the normal fresh action-entry identity precondition

#### Scenario: Formal zero with no queued work and no debt returns no work

- GIVEN current open-Issue and closed-routing-debt enumeration are provenance-qualified and complete
- AND open formal cardinality is zero
- AND no closed-routing debt candidate exists
- AND no eligible pre-activation candidate exists
- WHEN workflow-dynamic dispatch evaluates repository work
- THEN it returns `NO_WORK` without historical terminal-workflow reconstruction
- AND the durable decision includes the bounded machine-owned no-work reason required by the no-API decision contract

#### Scenario: Possible closed unfinished conflict still enters detailed recovery

- GIVEN current closed-routing-debt enumeration is provenance-qualified and complete
- AND exactly one closed Issue retains a coherent nonterminal workflow routing identity
- AND open formal cardinality is zero
- WHEN workflow-dynamic dispatch evaluates authorization
- THEN it performs bounded detailed exceptional recovery for that exact Issue only
- AND qualifying or genuinely indeterminate recovery state preserves the existing recovery/fail-closed semantics

#### Scenario: Exceptional recovery runs before pre-activation selection

- GIVEN complete current open-Issue state contains zero formal workflows
- AND one or more open pre-activation candidates exist
- AND at least one closed-routing debt candidate exists
- WHEN workflow-dynamic dispatch reaches the admission boundary
- THEN it resolves only a safely executable candidate-bound debt action before authorizing the queue winner
- AND unfinished or genuinely indeterminate debt blocks pre-activation
- AND the queue is evaluated only after current debt is cleared or safely reduced to the one qualifying recovery candidate

#### Scenario: No formal or queued work still checks recoverable closed workflow state

- GIVEN complete current open-Issue state contains zero formal workflows and no eligible pre-activation candidate
- AND exactly one closed-routing debt candidate exists
- WHEN workflow-dynamic dispatch evaluates whether the repository has no work
- THEN it executes detailed exceptional classification for that candidate before returning `NO_WORK`
- AND a qualifying premature-close candidate is selected for `Lead / resolve-question` instead of being stranded
- AND a proven terminal/retired candidate is selected only for candidate-local routing retirement
- AND genuinely indeterminate required evidence produces `FAIL_CLOSED`

#### Scenario: Equivalent duplicate terminal journals are one terminal fact

- GIVEN detailed debt classification evaluates a closed workflow with two or more valid canonical `LIFECYCLE_COMPLETE` journals
- AND every journal identifies the same coordination Issue, immutable Change, `Lead / finalize-archive` action, and terminal result
- AND any recorded terminal revision/Archive identities are compatible and non-conflicting
- WHEN terminal evidence is classified
- THEN the journals are treated as idempotent at-least-once replay of one terminal fact
- AND terminal evidence is `terminal-history`
- AND duplicate journal count alone cannot block unrelated legal current work after routing debt is retired

#### Scenario: Contradictory terminal identities remain fail closed

- GIVEN detailed debt classification evaluates multiple otherwise valid terminal journals
- AND those journals disagree on an immutable terminal revision, Archive identity, or another required terminal fact
- WHEN terminal evidence is classified
- THEN terminal evidence is `INDETERMINATE`
- AND the affected debt boundary fails closed
- AND the model does not choose which terminal journal to trust

#### Scenario: Pre-activation Explore revalidates zero formal WIP before substantive research

- GIVEN normal classification identifies an open `Lead / explore-change + Change: unset` Issue as the deterministic combined-queue winner
- AND current closed-routing-debt enumeration was complete and empty
- AND before substantive Explore begins another durable formal workflow or closed-routing debt candidate appears, or completeness can no longer be established
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

- GIVEN the available current open-Issue or closed-routing-debt read is capped, incomplete, provenance-invalid, or otherwise cannot prove enumeration completeness
- WHEN normal dispatch derives current formal/debt state
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
- AND exactly one closed coordination Issue remains as closed-routing debt with a persisted non-`unset` Change and an otherwise legal nonterminal routing identity
- AND detailed exceptional evidence proves the Change remains unfinished
- AND no valid terminal completion or qualifying Human termination/non-resumption decision exists
- AND no second closed-routing debt candidate exists
- WHEN the exceptional recovery boundary classifies current state
- THEN the stale routed action is not executed while the Issue is closed
- AND pre-activation work is not selected
- AND that Issue is selected for `Lead / resolve-question`
- AND Lead may reopen only the same Issue without changing its immutable Change identity or preserved nonterminal routing identity
- AND the recovery invocation does not execute the preserved normal action

#### Scenario: Premature close cannot be recovered unambiguously

- GIVEN a closed-routing candidate has missing or contradictory lifecycle evidence, a qualifying Human termination decision, another open formal workflow, another closed-routing debt candidate, or incomplete recovery provenance
- WHEN detailed exceptional recovery evaluates reopen eligibility
- THEN Lead does not reopen the Issue by inference
- AND unfinished or indeterminate debt remains fail closed
- AND the repository uses existing diagnosis or Human-escalation semantics rather than creating a generic recovery state

#### Scenario: Legacy routed terminal history drains through the existing owner

- GIVEN current acquisition finds multiple pre-existing closed Issues that still retain workflow routing labels
- AND detailed executable classification proves at least one candidate terminal/retired with complete non-contradictory evidence
- WHEN workflow-dynamic dispatch selects cleanup work
- THEN it authorizes at most one exact terminal/retired candidate as `Lead / resolve-question`
- AND Lead may request removal only of that candidate's remaining workflow routing labels
- AND repository-owned application fresh-reauthorizes each narrow removal against the same current candidate/disposition
- AND no other historical Issue is mutated by that invocation
- AND later invocations repeat from fresh current debt until terminal debt is drained or unresolved evidence requires fail-closed handling

#### Scenario: Multiple unfinished or ambiguous debt candidates fail closed

- GIVEN current closed-routing-debt enumeration finds more than one candidate
- AND at least two candidates are unfinished or one or more required candidate dispositions are indeterminate
- WHEN workflow-dynamic dispatch evaluates safe debt resolution
- THEN it returns `FAIL_CLOSED`
- AND it does not choose an unfinished candidate to reopen by Issue number or model judgment
- AND it does not perform a bulk cleanup mutation
