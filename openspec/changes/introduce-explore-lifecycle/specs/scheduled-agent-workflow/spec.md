# scheduled-agent-workflow Specification Delta

## MODIFIED Requirements

### Requirement: One persistent coordination Issue represents the normal OpenSpec workflow lifecycle

The workflow SHALL use one persistent coordination Issue for one Human-admitted work item through any optional pre-Propose Explore and, when a formal Change is authorized, through proposal, review, implementation, merge, archive review, archive merge, and final closure.

Before the change id exists, `explore-change` and `propose-change` MAY operate with `Change: unset`. `explore-change` MUST keep `Change: unset` and MUST NOT create a formal OpenSpec change solely to represent research. Once Lead persists a change id during `propose-change`, that identity MUST remain immutable for that Issue.

Normal clarification and review-correction transitions SHALL remain in the same coordination Issue unless a later repository contract explicitly introduces child workflow items.

A terminal Explore result that concludes `NO_CHANGE_REQUIRED` or `NO_GO` MAY complete and close the coordination/research Issue without creating or archiving a fake OpenSpec Change.

#### Scenario: Explore remains pre-Change

- GIVEN a Human-admitted coordination Issue is routed to `Lead / explore-change`
- AND `Change:` is unset
- WHEN Lead investigates the problem
- THEN the Issue remains `Change: unset`
- AND no `openspec/changes/<id>/` artifact set is created by Explore

#### Scenario: Lead selects a change id only after Propose entry

- GIVEN a coordination Issue has reached Human-authorized `Lead / propose-change`
- AND `Change:` is not yet set
- WHEN Lead creates or selects the OpenSpec change id
- THEN Lead persists that change id on the coordination Issue
- AND later scheduled runs treat the persisted change id as immutable workflow identity

#### Scenario: Explore concludes without a repository change

- GIVEN Lead has reached a decision-complete `NO_CHANGE_REQUIRED` or `NO_GO` Explore conclusion
- AND no formal Change identity was created
- WHEN Lead persists the bounded terminal research evidence
- THEN Lead may close the coordination/research Issue as completed
- AND the workflow does not create a fake OpenSpec Change only to obtain archive semantics

### Requirement: The MVP exposes exactly ten normal scheduled actions

The normal scheduled workflow SHALL support these action contracts:

- Lead: `explore-change`, `propose-change`, `resolve-question`, `finalize-change`, `finalize-archive`;
- Reviewer: `review-openspec`, `review-implementation`, `review-archive`;
- Executor: `implement-change`, `merge-pr`.

Procedural skills SHOULD be reusable across materially similar actions and MUST NOT create a second artifact DAG that duplicates OpenSpec's proposal/specs/design/tasks lifecycle. `explore-change` MUST remain a pre-artifact investigation action rather than an alternative OpenSpec artifact lifecycle.

#### Scenario: Explore and Propose are distinct Lead actions

- GIVEN Human-admitted work has a fuzzy problem or unresolved feasibility/scope
- WHEN it is routed to `Lead / explore-change`
- THEN Lead may investigate without creating formal OpenSpec artifacts
- AND formal artifact authoring remains owned by `Lead / propose-change`

#### Scenario: Merge target is an implementation PR or archive PR

- GIVEN Executor is routed to `merge-pr`
- AND Lead authorization identifies the target PR and authorized revision
- WHEN Executor evaluates the merge
- THEN the same merge action contract applies regardless of whether the target is an implementation PR or archive PR
- AND lifecycle-specific next routing is reconstructed from durable state after merge

### Requirement: Workflow admission is explicitly Human-controlled

Scheduled agents MUST NOT autonomously admit arbitrary Issues, PRs, repository activity, discussions, or discovered requirements into workflow work.

An initial coordination Issue is Human-admitted only through explicit routing established by actor `royhsu-work`; other actors cannot satisfy this Human-required admission condition.

A Human-admitted `Lead / explore-change` Issue with `Change: unset` is queued pre-Change research. A Human-admitted `Lead / propose-change` Issue MAY remain queued with `Change: unset` as direct-to-Propose work. In workflow-dynamic mode, neither may bypass a formal active or terminal-pending workflow, and both participate in the deterministic pre-activation queue defined below.

Explore admission is no-stakes research authority and MUST NOT by itself authorize formal Change creation. When Explore reaches `PROPOSAL_READY`, Lead MUST obtain valid Human intent to proceed before routing the same Issue to `Lead / propose-change`; after that routing, existing Propose activation persists the immutable Change identity.

Lead idle advisory admission additionally requires both an unambiguous selected direction from actor `royhsu-work` and the reserved Human capability marker `intake:approved` applied by that Human actor.

Scheduled Lead, Reviewer, and Executor MUST NEVER add, remove, restore, or otherwise manufacture `intake:approved`; they MAY only consume valid Human-authored evidence.

#### Scenario: Human directly admits fuzzy work to Explore

- GIVEN actor `royhsu-work` creates or explicitly routes a coordination Issue to `Lead / explore-change`
- AND `Change:` is unset
- WHEN scheduled workflow reconstructs admission
- THEN the Issue is valid queued pre-Change research
- AND Explore does not create a formal Change until later Human intent authorizes Propose

#### Scenario: Human directly admits concrete work to Propose

- GIVEN actor `royhsu-work` creates or explicitly routes a coordination Issue to `Lead / propose-change`
- AND `Change:` is unset
- WHEN scheduled workflow reconstructs admission
- THEN the Issue is valid queued pre-activation work
- AND Explore is not mandatory for that Issue

#### Scenario: Proposal-ready Explore still requires Human intent

- GIVEN Lead has a decision-complete Explore conclusion that is `PROPOSAL_READY`
- AND the Issue was admitted only to `Lead / explore-change`
- WHEN no valid Human decision to proceed has yet been reconstructed
- THEN Lead does not persist a Change id
- AND does not route to `propose-change`
- AND uses the existing Human-decision contract for the bounded proceed-or-stop decision

#### Scenario: Non-Human routing is insufficient

- GIVEN an actor other than `royhsu-work` applies apparently valid initial routing
- WHEN scheduled workflow evaluates Human admission
- THEN that routing does not satisfy Human-required admission
- AND scheduled roles fail closed rather than treating it as authorized workflow entry

### Requirement: Each scheduled run processes at most one actionable work item using a fixed stable order

A scheduled invocation SHALL process at most one eligible actionable coordination Issue per run.

In `fixed-role` mode, selection SHALL retain deterministic role-local priority with the new Lead action:

- Lead: `resolve-question` > `finalize-archive` > `finalize-change` > `explore-change` > `propose-change`;
- Reviewer: `review-archive` > `review-implementation` > `review-openspec`;
- Executor: `merge-pr` > `implement-change`.

Within the same fixed-role role/action priority, selection SHALL choose earliest GitHub `created_at`, then lower Issue number.

In `workflow-dynamic` mode, a formal active workflow or terminal-pending workflow SHALL be selected before pre-activation work; its valid routing tuple determines the role/action. The only closed-Issue active exception remains a terminal-pending `closed + agent:lead + action:finalize-archive` workflow with matching authorized merged Archive PR/native close and no valid Lead `LIFECYCLE_COMPLETE` evidence.

If no formal active or terminal-pending workflow exists, valid Human-admitted open `Lead / explore-change + Change: unset` and `Lead / propose-change + Change: unset` entries SHALL form one deterministic pre-activation queue ordered by earliest GitHub `created_at`, then lower Issue number. Only that winner may proceed. An open Explore winner remains the deterministic winner across later wakes until it reaches a terminal Explore result or valid Human intent authorizes its transition to Propose.

The model MUST NOT substitute its own urgency or preference for either mode's deterministic selection rules.

#### Scenario: Dynamic mode follows the formal active workflow

- GIVEN dispatch mode is `workflow-dynamic`
- AND exactly one formal active workflow routes to `Executor / implement-change`
- AND queued Explore and direct-Propose Issues also exist
- WHEN a Scheduled Task selects work
- THEN the formal active workflow is selected
- AND Executor is the fixed invocation role
- AND the queued pre-activation work remains queued

#### Scenario: Dynamic mode selects earliest pre-activation entry across Explore and Propose

- GIVEN dispatch mode is `workflow-dynamic`
- AND no formal active or terminal-pending workflow exists
- AND one Human-admitted Explore Issue is older than one Human-admitted direct-Propose Issue
- WHEN Scheduled workflow selects pre-activation work
- THEN the Explore Issue is selected
- AND the newer direct-Propose Issue remains queued

#### Scenario: Open Explore remains selected without an in-progress marker

- GIVEN the oldest valid pre-activation entry is an open `Lead / explore-change` Issue
- AND it has not reached a terminal result or transitioned to Propose
- WHEN a later wake reconstructs the same queue
- THEN that same Issue remains the deterministic winner by stable creation order
- AND no `status:exploring`, lease, heartbeat, or hidden ownership state is required

#### Scenario: Dynamic mode selects terminal reconstruction before queued work

- GIVEN dispatch mode is `workflow-dynamic`
- AND a closed coordination Issue is terminal-pending under `Lead / finalize-archive`
- AND queued Explore or Propose work exists
- WHEN a Scheduled Task selects work
- THEN the closed terminal-pending workflow is selected
- AND Lead is the fixed invocation role
- AND queued pre-activation work remains queued

## ADDED Requirements

### Requirement: Optional pre-Propose Explore preserves upstream investigation semantics

`Lead / explore-change` SHALL be an optional pre-Propose investigation action for Human-admitted work whose problem, feasibility, scope, or approach is not yet concrete enough for formal Change authoring.

Explore SHALL preserve problem-before-solution semantics: Lead MUST distinguish the underlying problem/requirement/evidence from a proposed mechanism, and existing implementation patterns, familiar solutions, industry conventions, or solution-shaped wording MUST NOT become requirements merely because they are available.

Explore MAY read/search the repository and relevant external evidence, compare meaningful options and trade-offs, inspect current behavior/root cause, perform Lead's existing bounded blast-radius analysis, and use simple diagrams when useful. Explore MUST NOT create an OpenSpec change folder, write proposal/spec/design/tasks artifacts, modify implementation code, or act as an alternative artifact generator.

Explore MUST remain optional. Human-admitted concrete/buildable work MAY enter `Lead / propose-change` directly.

#### Scenario: Fuzzy problem is investigated without artifact creation

- GIVEN Human admits a problem whose material scope or feasible direction is still unclear
- WHEN Lead executes `explore-change`
- THEN Lead may inspect repository/external evidence and compare approaches
- AND no formal OpenSpec Change artifacts or implementation code are created

#### Scenario: Concrete work skips Explore

- GIVEN Human has already supplied a concrete/buildable direction sufficient for bounded formal proposal authoring
- WHEN Human admits the Issue directly to `Lead / propose-change`
- THEN the workflow does not require an Explore pass merely for process uniformity

#### Scenario: Solution-shaped input does not become a requirement automatically

- GIVEN an Explore Issue or inspected source suggests a particular implementation mechanism
- AND current Human-approved requirements do not require that mechanism
- WHEN Lead investigates the problem
- THEN Lead treats the mechanism as evidence or an option
- AND first determines the actual requirement, constraint, and trade-off before recommending a direction

### Requirement: Explore exits on decision-complete dispositions

Lead SHALL treat Explore as complete when continued investigation is no longer required to choose the next legal disposition, rather than requiring exhaustive knowledge or a fixed research checklist.

Before exiting Explore, each material unresolved question that could change the selected disposition MUST be resolved by evidence, shown to be non-blocking, identified as a genuine Human intent/authority decision, or sufficient to establish a current no-change/no-go conclusion.

The legal Explore dispositions SHALL be:

- `PROPOSAL_READY`: evidence supports a concrete/buildable direction and formal proposal authoring would not require Lead to invent a material requirement or solution decision; this disposition requires Human intent before routing to Propose;
- `NO_CHANGE_REQUIRED`: evidence shows no repository change is required;
- `NO_GO`: evidence shows the contemplated change is currently infeasible or unjustified;
- `HUMAN_DECISION_REQUIRED`: a material remaining decision belongs to Human intent/authority and cannot be resolved from repository/technical evidence.

`SPECIFICATION_BLOCKED` MUST NOT be used as a terminal substitute for a decision-complete no-change/no-go Explore conclusion.

#### Scenario: Explore is proposal-ready

- GIVEN Lead has resolved all material questions that would alter the proposed direction
- AND a bounded proposal can be authored without inventing material requirements or solution choices
- WHEN Lead evaluates the Explore disposition
- THEN the result is `PROPOSAL_READY`
- AND Lead waits for valid Human intent before routing the same Issue to `propose-change`

#### Scenario: Explore finds no change is required

- GIVEN repository evidence already satisfies the problem or shows it is informational only
- WHEN no material question remains that could require a repository change
- THEN Lead records `NO_CHANGE_REQUIRED`
- AND may close the research Issue without creating a fake Change

#### Scenario: Explore reaches a current no-go

- GIVEN evidence shows the contemplated direction is currently infeasible or unjustified
- WHEN that evidence is sufficient to choose the disposition
- THEN Lead records `NO_GO`
- AND records a material reconsideration condition when one is identifiable
- AND may close the research Issue without creating a fake Change

#### Scenario: Remaining decision belongs to Human intent

- GIVEN technical/repository investigation has narrowed the problem and options
- AND the remaining material choice cannot be resolved without Human intent or authority
- WHEN Lead exits the current investigation step
- THEN Lead uses `HUMAN_DECISION_REQUIRED`
- AND the Issue remains routed to Explore for resumption after authoritative Human input

### Requirement: Explore persists bounded reconstructable evidence without a research state machine

Scheduled Explore SHALL persist only the durable evidence needed for a later wake or Human decision to reconstruct the current conclusion and continue correctly.

The bounded evidence SHALL identify, when applicable, the problem/question investigated, relevant evidence inspected, material constraints or meaningful alternatives needed for the conclusion, the selected disposition and rationale, the next Human/action boundary, and a material reconsideration condition for `NO_GO` when one is known.

The workflow MUST NOT require live research progress logging, a fixed option count, completeness score, research database, hidden cross-run context, separate artifact DAG, claim, lease, heartbeat, retry counter, or new independent `review-explore` gate.

#### Scenario: Explore resumes after a later wake

- GIVEN an Explore invocation persisted a bounded nonterminal Human-decision result
- AND the scheduled invocation ended
- WHEN a later Lead wake reconstructs the same Issue
- THEN Lead reads the durable conclusion/evidence and current Human response state
- AND does not require prior conversation memory to resume correctly

#### Scenario: Explore does not persist every intermediate thought

- GIVEN Lead performs multiple repository searches and compares alternatives during Explore
- WHEN the current investigation reaches a disposition boundary
- THEN durable evidence records only the bounded facts and rationale needed to reconstruct that disposition
- AND the workflow does not require a transcript, hidden memory, or research-progress state machine

### Requirement: Explore becomes authoritative only after default-branch activation

The #38 bootstrap Change SHALL continue to execute under the pre-Explore default-branch governance until the approved Explore implementation is merged to the repository default branch.

Feature-branch `explore-change` actions, role text, skills, and specs are review input only and MUST NOT govern #38 itself before merge.

After activation, existing non-`unset` active Changes SHALL continue their current lifecycle and MUST NOT be retroactively returned to Explore. Existing Human-admitted `Lead / propose-change + Change: unset` Issues SHALL remain valid direct-to-Propose entries. Deferred research Issues MAY enter the new Explore action only through valid Human admission/routing under the then-authoritative governance.

#### Scenario: Bootstrap Change cannot self-activate Explore

- GIVEN #38 is implementing `explore-change`
- AND the implementation branch contains the future Explore governance
- WHEN Scheduled execution processes #38 before that branch is merged
- THEN current default-branch `Lead / propose-change` governance remains authoritative
- AND the feature-branch Explore action is not used to reinterpret #38's own current routing

#### Scenario: Existing active Change is not pulled backward after activation

- GIVEN the Explore governance becomes authoritative on `main`
- AND another coordination Issue already has a persisted non-`unset` Change identity
- WHEN scheduled workflow reconstructs that active Change
- THEN it continues from its current legal routing
- AND Explore is not inserted retroactively into the active lifecycle
