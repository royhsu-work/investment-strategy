# scheduled-agent-workflow Delta Specification

## ADDED Requirements

### Requirement: Default-branch governance declares the scheduled dispatch mode

The repository SHALL declare exactly one authoritative `Scheduled-Dispatch-Mode` marker in default-branch `agents/AGENTS.md`, with value `fixed-role` or `workflow-dynamic`.

A Scheduled Task MUST determine dispatch mode from that marker after loading default-branch governance and MUST NOT infer the mode from task names, conversation memory, Issues, PRs, or feature branches.

#### Scenario: Workflow-dynamic mode is declared

- GIVEN default-branch `agents/AGENTS.md` declares `Scheduled-Dispatch-Mode: workflow-dynamic`
- WHEN any Scheduled Task wakes
- THEN it uses workflow-dynamic dispatch
- AND its legacy externally assigned role does not override the repository-selected role

#### Scenario: Fixed-role mode is declared

- GIVEN default-branch `agents/AGENTS.md` declares `Scheduled-Dispatch-Mode: fixed-role`
- WHEN a legacy role Scheduled Task wakes
- THEN it uses its externally assigned legacy role
- AND follows the existing role-local deterministic discovery contract

### Requirement: Workflow-dynamic dispatch derives one fixed invocation role from durable workflow state

In `workflow-dynamic` mode, a wake SHALL reconstruct current durable workflow state before selecting a role. If exactly one active workflow exists, its valid routing tuple SHALL determine the invocation role/action and mapped skill.

Once selected, the invocation role MUST remain fixed for the remainder of that run. A routing handoff MAY persist a different next role/action, but the current invocation MUST end rather than redispatch to the new role.

The dispatcher MUST NOT introduce model-derived global urgency, cross-role priority scoring, or a second workflow DAG.

#### Scenario: Active workflow routes to Reviewer

- GIVEN dispatch mode is `workflow-dynamic`
- AND the single active workflow has valid routing `agent:reviewer + action:review-openspec`
- WHEN a Scheduled Task dispatches the run
- THEN Reviewer is selected for that invocation
- AND the `review-openspec` skill is loaded
- AND any legacy external Lead/Reviewer/Executor assignment is ignored for role selection

#### Scenario: Handoff changes the next owner

- GIVEN the current invocation was dispatched as Lead
- AND Lead durably completes its action and legally hands off to Reviewer
- WHEN the routing tuple is changed to Reviewer
- THEN the current invocation ends as Lead
- AND it does not execute Reviewer work in the same invocation

### Requirement: Persisted Change identity defines the single active workflow boundary

An open coordination Issue with a valid routing tuple and a persisted non-`unset` `Change:` identity SHALL be an active workflow. The repository MUST allow at most one such active workflow at a time.

An open Human-admitted `Lead / propose-change` coordination Issue with `Change: unset` SHALL be queued pre-activation work and MUST NOT count as an active workflow until Lead persists its immutable Change identity.

Lead MUST NOT activate a queued proposal while another active workflow exists. If no active workflow exists, deterministic admission among queued `propose-change` candidates SHALL use earliest GitHub `created_at`, then lower Issue number.

#### Scenario: Queued proposal exists while another workflow is active

- GIVEN Change A is an active workflow
- AND Change B is an open `Lead / propose-change` Issue with `Change: unset`
- WHEN workflow-dynamic dispatch reconstructs work
- THEN Change A remains the only active workflow
- AND Change B is not activated or globally arbitrated against Change A

#### Scenario: Oldest queued proposal activates when idle

- GIVEN no active workflow exists
- AND two valid Human-admitted `Lead / propose-change` Issues have `Change: unset`
- WHEN Lead selects pre-activation work
- THEN the earlier `created_at` Issue is selected
- AND lower Issue number breaks an equal-time tie
- AND persisting its Change identity activates that workflow

### Requirement: Dynamic dispatch tolerates overlapping wakes without hidden ownership state

Workflow-dynamic dispatch SHALL remain at-least-once and MUST NOT rely on Scheduled Tasks to provide mutual exclusion.

Overlapping wakes SHALL remain safe through durable reconstruction, idempotency where practical, revision/precondition-aware unsafe mutations, first-valid-write-wins where applicable, and stale-run termination. The workflow MUST NOT add lock, claim, lease, heartbeat, retry counter, hidden sequence, or `status:in-progress` state solely to serialize dispatcher runs.

#### Scenario: Two wakes observe the same active tuple

- GIVEN two wakes reconstruct the same active workflow and routing tuple concurrently
- WHEN both dispatch the same role/action
- THEN neither assumes single-flight execution
- AND each action re-evaluates durable preconditions before unsafe mutation
- AND a run that becomes stale stops rather than overwriting newer durable state

### Requirement: Unexplained durable workflow evidence fails closed to Lead diagnosis

If dispatch finds no active workflow but durable repository evidence indicates an unresolved workflow-related state that cannot be safely classified under the normal lifecycle, it MUST NOT activate queued proposal work merely by ignoring that evidence.

The repository SHALL use bounded Lead diagnosis and, when Human input is required, a decision-ready escalation rather than a repository-wide fault classifier or persistent fault state machine.

#### Scenario: Orphan evidence blocks new activation

- GIVEN no active coordination Issue with a persisted Change is found
- AND durable PR/OpenSpec evidence appears to belong to unresolved workflow work
- WHEN dispatch evaluates whether to activate a queued proposal
- THEN activation fails closed
- AND Lead diagnoses the evidence or escalates a bounded decision to Human
- AND the dispatcher does not invent a global fault status taxonomy

### Requirement: Human-required authority is bound to the repository Human actor

For workflow decisions that governance reserves to Human, only durable GitHub activity attributable to actor `royhsu-work` SHALL satisfy the Human authority condition.

Activity from other actors MAY be used as evidence but MUST NOT satisfy Human-required admission, answers, authorization, or resume conditions.

`human:notified`, when present, SHALL be analytics-only metadata and MUST NOT grant authority, route work, create waiting semantics, or prove that Human answered.

#### Scenario: Non-Human actor answers a Human-required question

- GIVEN workflow progress requires a Human decision
- AND an actor other than `royhsu-work` posts an apparent answer
- WHEN Lead reconstructs authorization evidence
- THEN the answer may be considered evidence
- BUT it does not satisfy the Human-required decision condition

#### Scenario: Notification metadata exists

- GIVEN `human:notified` metadata is present
- WHEN any role evaluates routing or authorization
- THEN that metadata does not change workflow ownership or authority
- AND it is not treated as proof of a Human response

### Requirement: Lead Human-facing escalation is bounded and decision-ready

When Lead requires Human input, it SHALL present at most three actionable proposals and SHALL include the material impact, risk/trade-off, and Lead recommendation needed to make the decision.

Lead MUST NOT repeat materially equivalent unanswered notifications while the durable question and available evidence remain unchanged.

#### Scenario: Lead needs a Human decision

- GIVEN Lead cannot legally continue without Human input
- WHEN Lead records the escalation
- THEN it presents no more than three actionable options
- AND states material impact and trade-offs
- AND identifies a recommended option

#### Scenario: Human has not answered

- GIVEN Lead already recorded a decision-ready escalation
- AND no authoritative Human answer or material evidence change exists
- WHEN a later wake reconstructs the same blocked state
- THEN Lead does not post a duplicate unanswered notification

### Requirement: Idle exploration considers recent relevant Issue activity

Lead idle advisory SHALL remain available only when no active workflow requires work and no unresolved advisory already prevents duplicate advisory creation.

When forming bounded idle recommendations, Lead SHALL consider relevant repository Issues created or materially active during the preceding seven days in addition to current default-branch repository state.

#### Scenario: Recent Issue changes recommendation context

- GIVEN workflow execution is idle
- AND a relevant Issue was created or materially active within the preceding seven days
- WHEN Lead forms an idle advisory
- THEN that Issue is considered as current exploration evidence
- AND the advisory remains bounded to at most three recommendations

### Requirement: Workflow governance applies a simplicity and proportionality constraint

Repository workflow design SHALL add complexity only when justified by current approved requirements or demonstrated failure modes. Hypothetical future generality MUST NOT by itself justify a central workflow engine, multi-active arbitration platform, generic fault classifier, or hidden runtime ownership state.

#### Scenario: A generalized dispatcher framework is proposed without current need

- GIVEN current workflow requirements are satisfied by the thin workflow-first dispatcher
- AND no demonstrated failure requires a generalized orchestration subsystem
- WHEN an implementation or later proposal considers such machinery
- THEN the additional machinery is out of scope
- AND a new approved OpenSpec change with concrete evidence is required before adding it

## MODIFIED Requirements

### Requirement: Each scheduled run processes at most one actionable work item using a fixed stable order

A scheduled invocation SHALL process at most one eligible actionable coordination Issue per run.

In `fixed-role` mode, selection SHALL retain the existing role-local action priority:

- Lead: `resolve-question` > `finalize-archive` > `finalize-change` > `propose-change`;
- Reviewer: `review-archive` > `review-implementation` > `review-openspec`;
- Executor: `merge-pr` > `implement-change`.

Within the same fixed-role role/action priority, selection SHALL choose earliest GitHub `created_at`, then lower Issue number.

In `workflow-dynamic` mode, the single active workflow SHALL be selected before role/action selection; its valid routing tuple determines the role/action. If no active workflow exists, only valid queued `Lead / propose-change` admission or bounded Lead idle/orphan diagnosis may proceed according to the requirements above.

The model MUST NOT substitute its own urgency or preference for either mode's deterministic selection rules.

#### Scenario: Fixed-role mode retains role-local priority

- GIVEN dispatch mode is `fixed-role`
- AND Lead has one eligible `propose-change` Issue and one eligible `resolve-question` Issue
- WHEN Lead selects work for the run
- THEN Lead selects `resolve-question`
- AND processes at most that one Issue

#### Scenario: Dynamic mode follows the active workflow

- GIVEN dispatch mode is `workflow-dynamic`
- AND exactly one active workflow routes to `Executor / implement-change`
- AND a queued `Lead / propose-change` Issue also exists
- WHEN a Scheduled Task selects work
- THEN the active workflow is selected
- AND Executor is the fixed invocation role
- AND the queued proposal remains pre-activation

### Requirement: Workflow admission is explicitly Human-controlled

Scheduled agents MUST NOT autonomously admit arbitrary Issues, PRs, repository activity, discussions, or discovered requirements into workflow work.

An initial coordination Issue is Human-admitted only through explicit routing established by actor `royhsu-work`; other actors cannot satisfy this Human-required admission condition.

A Human-admitted `Lead / propose-change` Issue MAY remain queued with `Change: unset`; in workflow-dynamic mode it becomes active only when no other active workflow exists and Lead durably persists its immutable Change identity.

Lead idle advisory admission additionally requires both an unambiguous selected direction from actor `royhsu-work` and the reserved Human capability marker `intake:approved` applied by that Human actor.

Scheduled Lead, Reviewer, and Executor MUST NEVER add, remove, restore, or otherwise manufacture `intake:approved`; they MAY only consume valid Human-authored evidence.

#### Scenario: Human directly admits a queued proposal

- GIVEN actor `royhsu-work` creates or explicitly routes a coordination Issue to `Lead / propose-change`
- AND `Change:` is unset
- WHEN scheduled workflow reconstructs admission
- THEN the Issue is valid queued pre-activation work
- AND it does not become active while another persisted Change workflow exists

#### Scenario: Non-Human routing is insufficient

- GIVEN an actor other than `royhsu-work` applies apparently valid initial routing
- WHEN scheduled workflow evaluates Human admission
- THEN that routing does not satisfy Human-required admission
- AND scheduled roles fail closed rather than treating it as authorized workflow entry

### Requirement: Lead idle advisory mode is bounded and non-routing

Lead SHALL keep idle advisory mode bounded and non-routing.

When no active workflow requires work, no queued Human-admitted proposal is eligible for activation, and no unresolved orphan evidence requires diagnosis, Lead MAY create an idle advisory Issue containing at most three current recommendations only if no other open `advisory:idle` Issue exists.

An advisory Issue MUST NOT contain `agent:*` or `action:*` routing labels and is not itself a coordination workflow instance.

If an open advisory remains without valid Human admission, later Lead runs SHALL no-op rather than create duplicate advisory noise. Recommendation formation SHALL consider relevant Issues created or materially active during the preceding seven days.

#### Scenario: Existing idle advisory has no Human decision

- GIVEN one open `advisory:idle` Issue exists
- AND no valid Human admission has occurred
- WHEN Lead runs while workflow is otherwise idle
- THEN Lead does not create another advisory Issue
- AND does not repeat the same recommendations as new workflow noise

### Requirement: Repository agent artifacts expose the governance contract

Implementation SHALL provide:

- `agents/AGENTS.md` for shared execution protocol and the single authoritative `Scheduled-Dispatch-Mode` marker;
- role definitions for Lead, Reviewer, and Executor under `agents/roles/`;
- a reduced reusable set of procedural skills under `agents/skills/` covering the nine action contracts without one skill per trivial action;
- repository documentation describing fixed-role compatibility, workflow-dynamic dispatch, the single-active activation boundary, and the relationship to existing OpenSpec/archive automation.

Scheduled Task prompts SHALL remain bootstrap-only: they may require loading default-branch governance and selecting dispatch mode, but MUST NOT duplicate repository execution, concurrency, handoff, stale-state, Human-escalation, or idle semantics.

Associated Scheduled Task conversation/result surfacing SHALL be treated as an external product boundary and MUST NOT become repository workflow state.

#### Scenario: Dynamic Scheduled Task bootstraps from repository governance

- GIVEN a Scheduled Task wakes
- WHEN it loads default-branch shared governance
- THEN it determines dispatch mode from `Scheduled-Dispatch-Mode`
- AND in workflow-dynamic mode reconstructs the active workflow to derive role/action and mapped skill
- AND repository governance remains sufficient without embedding a duplicate workflow protocol in the Scheduled Task prompt
