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

### Requirement: Active-workflow cardinality and Issue-state coherence precede queue selection

Workflow-dynamic Scheduled dispatch SHALL use repository-owned executable classification before loading any mapped Role or Skill. The production normal-selection classifier SHALL operate on a complete provenance-qualified snapshot of current open Issues and SHALL consume only the current facts required to select work: Issue number, open state, persisted `Change:` identity, current routing tuple derived from labels, GitHub `created_at` ordering, and enumeration/provenance completeness. Any additional admission fact required for a queued candidate MUST come from its existing canonical executable admission predicate rather than model interpretation of prose.

PR heads, CI state, OpenSpec artifacts, review evidence, lifecycle-specific PR evidence, and effect-specific mutation guards MUST NOT be prerequisites for global Issue selection. They SHALL be reconstructed only after an exact Issue/Role/Action is selected by the mapped action or effect boundary that owns those facts.

From the complete current open-Issue reconstruction, the executable normal classifier SHALL apply these formal-WIP rules before pre-activation selection:

| Open formal cardinality | Required result |
| --- | --- |
| `1` | Require complete provenance-qualified structural closed-workflow conflict clearance before authorization. `CLEAR` MAY authorize only that formal workflow and derive exact Role/Action from its current valid routing tuple; `POSSIBLE_CONFLICT` or `INDETERMINATE` MUST enter detailed exceptional recovery/consistency evaluation before any authorization. |
| `>1` | `FAIL_CLOSED` before any normal mapped action executes. |
| indeterminate | `FAIL_CLOSED` before any normal mapped action executes. |
| `0` | Require the same complete provenance-qualified structural closed-workflow conflict projection before pre-activation selection or `NO_WORK`. `CLEAR` MAY proceed directly to the deterministic combined pre-activation queue/`NO_WORK`; `POSSIBLE_CONFLICT` or `INDETERMINATE` MUST enter detailed exceptional recovery/consistency evaluation first. |

Repository-owned acquisition SHALL establish a bounded, complete structural projection of current closed workflow-looking Issues whenever closed state could affect formal or pre-activation authorization. The projection SHALL use only current authoritative structural facts needed for the conflict screen, such as Issue identity, closed state, persisted non-`unset` `Change:` identity, current recoverable nonterminal routing shape, and already-available lifecycle/status facts that can exclude definitely non-conflicting history without per-candidate detailed forensic reconstruction. If the structural facts cannot safely exclude a candidate, the projection MUST classify it as a possible conflict rather than infer terminal history.

The structural projection SHALL produce only `CLEAR`, `POSSIBLE_CONFLICT`, or `INDETERMINATE`. `CLEAR` MAY authorize the sole open formal workflow, or with formal cardinality zero MAY proceed to deterministic pre-activation selection/`NO_WORK`, without fetching terminal comments, Human-retirement comments, legacy archive details, or closed-Issue terminal re-observation merely to re-prove unrelated historical completion. `POSSIBLE_CONFLICT` or `INDETERMINATE` MUST NOT authorize from the open-Issue snapshot alone and SHALL trigger detailed exceptional recovery/consistency evaluation. The structural projection MUST remain ephemeral executable classification input and MUST NOT become a durable recovery registry, hidden workflow state, cache-based authority, or second workflow DAG.

Detailed exceptional recovery/consistency evaluation SHALL run only when the structural projection cannot prove `CLEAR` for the applicable authorization boundary. That boundary SHALL establish observable completeness for the relevant current closed candidate set and SHALL obtain detailed terminal/recovery evidence only for candidates whose closed state can affect recovery or conflict classification. Applicable terminal `LIFECYCLE_COMPLETE`, direct-Human administrative retirement, legacy archive, unfinished-Change, and current re-observation predicates SHALL remain fail-closed evidence inside that detailed exceptional boundary rather than unconditional inputs to every formal-zero or sole-formal wake.

Canonical terminal completion evidence SHALL be classified by semantic consistency, not by raw comment cardinality. Multiple valid `LIFECYCLE_COMPLETE` journals that identify the same coordination Issue, immutable Change, `Lead / finalize-archive` action, terminal result, and non-conflicting terminal revision/Archive identity SHALL represent idempotent at-least-once replay of one terminal fact and SHALL be treated as terminal history. If otherwise valid terminal journals disagree on an immutable terminal identity or carry materially contradictory completion evidence, terminal evidence SHALL remain `INDETERMINATE` and dispatch MUST fail closed wherever that candidate affects authorization. Additional non-conflicting metadata or a later journal that supplies previously omitted compatible metadata MUST NOT by itself turn one terminal fact into a contradiction.

The detailed exceptional decision SHALL preserve the existing safety contract:

- with open formal cardinality `0`, exactly one qualifying premature-close recovery candidate SHALL authorize that closed Issue as `Lead / resolve-question` and SHALL block pre-activation intake;
- with open formal cardinality `1`, a qualifying unfinished premature-close candidate or unresolved contradiction SHALL conflict with the already-open formal workflow and MUST produce `FAIL_CLOSED`; the closed Issue MUST NOT be reopened automatically into a second formal workflow;
- multiple qualifying/conflicting candidates, incomplete candidate enumeration, or indeterminate required provenance/evidence MUST produce `FAIL_CLOSED` in either context;
- when detailed evidence proves all structurally possible closed candidates terminal, retired, or otherwise non-conflicting, dispatch MAY authorize the sole open formal workflow for cardinality `1`, or MAY select the deterministic combined pre-activation winner/return `NO_WORK` for cardinality `0`.

Historical routing in Issue bodies/comments, prior model output, conversation history, or cached observations MUST NOT override the current authoritative open-Issue snapshot, structural conflict projection, or detailed exceptional evidence.

The combined pre-activation queue SHALL continue to contain every otherwise eligible open `Lead / explore-change + Change: unset` entry and every legally admitted open `Lead / propose-change + Change: unset` entry, ordered by earliest GitHub `created_at`, then lower Issue number. The model MUST NOT introduce another role/action priority or urgency score.

A selected action SHALL consume a fresh executable dispatch decision as an action-entry identity precondition rather than starting from a candidate-local assumption. Before a formal lifecycle/review/implementation action proceeds, current executable selection MUST still prove that its coordination Issue is the sole open formal workflow, that its routing equals the selected Issue/Role/Action, and that the structural closed-workflow conflict boundary is `CLEAR` or has been cleared by the required detailed exceptional evaluation. Before substantive `explore-change` or pre-activation `propose-change` work proceeds, executable selection MUST still prove open formal cardinality zero, that the applicable structural/detailed recovery boundary proves no blocking closed recovery candidate exists, and that the selected Issue remains the deterministic combined pre-activation winner. `propose-change` SHALL additionally preserve the immediate pre-write and fresh post-write activation checks. Stale, contradictory, incomplete, provenance-invalid, or execution-unavailable evidence MUST fail closed rather than being filled from model memory or prose.

When repository durable state contains more than one open formal workflow, Scheduled roles SHALL remain fail closed. They MUST NOT select a winner by age, role/action priority, Issue number, model judgment, presumed legitimacy, automatic Change clearing, or routing rewrite. Human/maintainer administrative repair MAY correct that illegal durable state outside normal Scheduled-Agent lifecycle execution. A later wake MUST reconstruct current repository state and obtain a new executable decision before normal work resumes.

A closed nonterminal Issue MAY be recovered automatically only for the demonstrated premature-close class when detailed exceptional recovery proves all existing predicates required for that recovery: persisted non-`unset` Change, one otherwise legal nonterminal routing tuple, unfinished lifecycle evidence, no valid terminal completion, no qualifying Human termination/non-resumption decision, no competing open formal workflow, and no second recovery candidate. Lead MAY reopen only that same Issue under `Lead / resolve-question`, preserve the immutable Change and pre-close routing identity, then fresh-reconstruct normal dispatch after reopening. The recovery invocation MUST NOT execute the preserved stale normal lifecycle action.

This separation MUST NOT create a generic fault state machine, hidden recovery registry, lock, lease, heartbeat, retry counter, durable claim, cache-based authorization, or second workflow DAG. Deterministic normal-selection, structural-conflict, terminal-replay, and exceptional-recovery mechanics SHALL be implemented and tested in production executable surfaces rather than duplicated as a second natural-language classifier for the model.

#### Scenario: One active workflow is missed by a partial search

- GIVEN repository durable state contains one open formal active workflow
- AND a partial query fails to enumerate it
- WHEN pre-activation work is also present
- THEN the partial query is not proof of zero formal WIP
- AND incomplete enumeration produces `FAIL_CLOSED`
- AND pre-activation work cannot be selected from that incomplete evidence

#### Scenario: Complete enumeration selects the sole active workflow

- GIVEN current open-Issue enumeration is provenance-qualified and complete
- AND exactly one open formal active workflow exists
- AND one or more routed pre-activation Issues also exist
- AND the complete structural closed-workflow conflict projection returns `CLEAR`
- WHEN workflow-dynamic dispatch performs normal classification
- THEN only the formal active workflow is selected
- AND its current routing tuple determines the exact invocation Role/Action
- AND no queued Explore or Propose action begins

#### Scenario: Clear sole formal workflow does not require detailed closed-history forensics

- GIVEN current open-Issue enumeration is provenance-qualified and complete
- AND exactly one open formal active workflow exists
- AND historical closed workflow Issues also exist in the repository
- AND the complete structural closed-workflow conflict projection proves none can still be a conflicting unfinished/premature-close candidate
- WHEN normal dispatch selects work
- THEN the structural conflict disposition is `CLEAR`
- AND it authorizes the sole open formal workflow without fetching detailed historical terminal/recovery evidence merely for that selection
- AND historical closed workflow state cannot override the current open formal winner by prose or stale context

#### Scenario: Sole formal workflow with a possible closed unfinished conflict does not fast-path authorization

- GIVEN current open-Issue enumeration is provenance-qualified and complete
- AND exactly one open formal active workflow A exists
- AND a different closed workflow-looking Issue B cannot be safely excluded by the structural projection as an unfinished/premature-close conflict candidate
- WHEN workflow-dynamic dispatch evaluates sole-formal authorization
- THEN the structural disposition is `POSSIBLE_CONFLICT` or `INDETERMINATE`
- AND dispatch does not authorize A from the open-Issue snapshot alone
- AND it performs bounded detailed exceptional recovery/consistency evaluation for B
- AND qualifying or genuinely indeterminate recovery state preserves the existing fail-closed/recovery semantics

#### Scenario: Formal zero with structural-clear history proceeds without detailed forensics

- GIVEN current open-Issue enumeration is provenance-qualified and complete
- AND open formal cardinality is zero
- AND one or more eligible pre-activation candidates exist
- AND the complete structural closed-workflow conflict projection returns `CLEAR`
- WHEN workflow-dynamic dispatch reaches pre-activation selection
- THEN it does not fetch detailed terminal/recovery evidence for unrelated historical closed workflows merely to re-prove their completion
- AND it selects the deterministic combined pre-activation winner
- AND the selected tuple remains subject to the normal fresh action-entry identity precondition

#### Scenario: Formal zero with no queued work and structural-clear history returns no work

- GIVEN current open-Issue enumeration is provenance-qualified and complete
- AND open formal cardinality is zero
- AND no eligible pre-activation candidate exists
- AND the complete structural closed-workflow conflict projection returns `CLEAR`
- WHEN workflow-dynamic dispatch evaluates repository work
- THEN it returns `NO_WORK` without detailed forensic reconstruction of unrelated terminal history
- AND the durable decision includes the bounded machine-owned no-work reason required by the no-API decision contract

#### Scenario: Possible closed unfinished conflict still enters detailed recovery

- GIVEN current open-Issue enumeration is provenance-qualified and complete
- AND the structural projection identifies a closed workflow-looking Issue that cannot be safely excluded as an unfinished/premature-close conflict candidate
- WHEN workflow-dynamic dispatch evaluates authorization
- THEN the structural disposition is `POSSIBLE_CONFLICT` or `INDETERMINATE`
- AND dispatch does not authorize a formal or pre-activation action from the open-Issue snapshot alone
- AND it performs bounded detailed exceptional recovery/consistency evaluation for the relevant candidate
- AND qualifying or genuinely indeterminate recovery state preserves the existing fail-closed/recovery semantics

#### Scenario: Exceptional recovery runs before pre-activation selection

- GIVEN complete current open-Issue state contains zero formal workflows
- AND one or more open pre-activation candidates exist
- AND the complete structural closed-workflow conflict projection is `POSSIBLE_CONFLICT` or `INDETERMINATE`
- WHEN workflow-dynamic dispatch reaches the admission boundary
- THEN it executes detailed exceptional closed-recovery evaluation before authorizing the queue winner
- AND a qualifying or genuinely indeterminate recovery state blocks pre-activation
- AND the queue is evaluated only after the exceptional candidate set is cleared

#### Scenario: No formal or queued work still checks recoverable closed workflow state

- GIVEN complete current open-Issue state contains zero formal workflows and no eligible pre-activation candidate
- AND the complete structural closed-workflow conflict projection is `POSSIBLE_CONFLICT` or `INDETERMINATE`
- WHEN workflow-dynamic dispatch evaluates whether the repository has no work
- THEN it executes detailed exceptional recovery before returning `NO_WORK`
- AND a qualifying premature-close candidate is selected for `Lead / resolve-question` instead of being stranded as history
- AND genuinely indeterminate required recovery evidence produces `FAIL_CLOSED`

#### Scenario: Equivalent duplicate terminal journals are one terminal fact

- GIVEN a closed workflow has two or more valid canonical `LIFECYCLE_COMPLETE` journals
- AND every journal identifies the same coordination Issue, immutable Change, `Lead / finalize-archive` action, and terminal result
- AND any recorded terminal revision/Archive identities are compatible and non-conflicting
- WHEN detailed terminal evidence is classified
- THEN the journals are treated as idempotent at-least-once replay of one terminal fact
- AND terminal evidence is `terminal-history`
- AND duplicate journal count alone cannot block unrelated legal current work

#### Scenario: Contradictory terminal identities remain fail closed

- GIVEN a closed workflow has multiple otherwise valid terminal journals
- AND those journals disagree on an immutable terminal revision, Archive identity, or another required terminal fact
- WHEN detailed terminal evidence is classified
- THEN terminal evidence is `INDETERMINATE`
- AND any authorization boundary affected by that candidate returns `FAIL_CLOSED`
- AND the model does not choose which terminal journal to trust

#### Scenario: Pre-activation Explore revalidates zero formal WIP before substantive research

- GIVEN normal classification identifies an open `Lead / explore-change + Change: unset` Issue as the deterministic combined-queue winner
- AND the applicable structural/detailed closed-recovery boundary found no blocking recovery candidate
- AND before substantive Explore begins another durable formal workflow appears or completeness can no longer be established
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

- GIVEN the available current open-Issue read is capped, incomplete, provenance-invalid, or otherwise cannot prove enumeration completeness
- WHEN normal dispatch derives formal cardinality
- THEN classification is fail-closed
- AND neither formal action execution nor pre-activation intake is authorized from that evidence

#### Scenario: Action-specific evidence is not a global selection prerequisite

- GIVEN production dispatch has selected one exact formal Issue routed to `Reviewer / review-openspec`
- AND that action later requires OpenSpec artifacts, exact validation evidence, and review-specific provenance
- WHEN global Issue selection is performed
- THEN those review-specific resources are not required to identify the Issue/Role/Action
- AND Reviewer reconstructs them only after machine selection under the mapped action contract

#### Scenario: Human or maintainer repairs a multiple-active repository state

- GIVEN Scheduled dispatch previously returned `FAIL_CLOSED` because multiple open formal workflows existed
- AND Human or maintainer later performs an administrative durable-state repair outside normal Scheduled-Agent lifecycle execution
- WHEN a later Scheduled Task wakes
- THEN it reconstructs current repository state from authoritative GitHub observations
- AND executes production dispatch again
- AND it does not inherit a previously guessed winner or stale routing/readiness evidence

#### Scenario: Nonterminal workflow Issue is closed prematurely and safely recoverable

- GIVEN open formal cardinality is zero
- AND a closed coordination Issue has a persisted non-`unset` Change and exactly one otherwise legal nonterminal routing tuple
- AND detailed exceptional recovery evidence proves the Change remains unfinished
- AND no valid terminal completion or qualifying Human termination/non-resumption decision exists
- AND no competing formal or second recovery candidate exists
- WHEN the exceptional recovery boundary classifies current state
- THEN the stale routed action is not executed while the Issue is closed
- AND pre-activation work is not selected
- AND that Issue is selected for `Lead / resolve-question`
- AND Lead may reopen the same Issue without changing its immutable Change identity or preserved nonterminal routing tuple
- AND the recovery invocation does not execute the preserved normal action

#### Scenario: Premature close cannot be recovered unambiguously

- GIVEN a closed nonterminal coordination Issue has missing or contradictory lifecycle evidence, a qualifying Human termination decision, another open formal workflow, another premature-close recovery candidate, or incomplete recovery provenance
- WHEN detailed exceptional recovery evaluates eligibility
- THEN Scheduled dispatch returns `FAIL_CLOSED`
- AND Lead does not reopen the Issue by inference
- AND the repository uses existing diagnosis or Human-escalation semantics rather than creating a generic recovery state
