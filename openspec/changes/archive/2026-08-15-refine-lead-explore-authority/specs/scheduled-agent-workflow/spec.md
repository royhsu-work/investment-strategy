# scheduled-agent-workflow Delta Specification

## RENAMED Requirements

- FROM: `### Requirement: Workflow admission is explicitly Human-controlled`
- TO: `### Requirement: Workflow admission is explicitly authority-controlled`
- FROM: `### Requirement: Lead idle advisory mode is bounded and non-routing`
- TO: `### Requirement: Lead idle advisory and discovery mode is bounded and non-disruptive`

## MODIFIED Requirements

### Requirement: Workflow admission is explicitly authority-controlled

Scheduled agents MUST NOT autonomously admit arbitrary Issues, PRs, repository activity, discussions, discovered requirements, or Agent-authored recommendations into workflow work.

Human admission remains valid through the repository's Human-authority contract. An initial Human-admitted coordination Issue is established only through explicit routing attributable to actor `royhsu-work`; other actors cannot satisfy that Human-required admission condition merely by applying routing.

In addition, Lead MAY autonomously materialize one bounded `Lead / explore-change` coordination Issue with `Change: unset` only from the idle-discovery boundary when the admission is independently justified by one of the following:

- an applicable default-branch canonical MUST/SHALL requirement with a concrete material gap;
- an approved required-deferred obligation with reconstructable source linkage;
- an explicitly governed README project-direction commitment that is prospective, scoped, affirmative, non-contradictory with canonical specs, and not merely descriptive/current-state/non-goal/example/deferred-uncommitted text; or
- concrete material behavior-preserving maintenance/friction evidence with a bounded ownership surface and no new Human-reserved product/scope/risk decision.

An autonomous admission MUST contain reconstructable evidence identifying the admission kind, exact observed default-branch revision where applicable, exact authority/evidence source, bounded problem statement, and why no Human-reserved decision is being made. Later reconstruction MUST validate that evidence and MUST fail closed when the cited source is absent, stale, contradictory, merely descriptive, insufficiently material, or otherwise does not authorize the bounded problem.

Agent-authored advisory text, Explore conclusions, and prior Agent-created tickets MUST NOT recursively serve as sufficient authority for another autonomous admission by themselves. Every autonomous admission SHALL trace to an independent default-branch authority source or current concrete repository/friction evidence.

Autonomous admission MUST NOT add, remove, restore, or manufacture `intake:approved`, MUST NOT persist a formal Change identity, and MUST NOT bypass Propose, Reviewer, implementation, merge, archive, or lifecycle gates.

A Human-admitted or valid repository-authorized `Lead / explore-change` Issue with `Change: unset` is queued pre-Change research. A Human-admitted `Lead / propose-change` Issue MAY remain queued with `Change: unset` as direct-to-Propose work. In workflow-dynamic mode, neither may bypass a formal active or terminal-pending workflow, and both participate in the deterministic pre-activation queue defined by the capability.

Explore admission establishes a bounded authority envelope for the admitted problem. When Explore reaches `PROPOSAL_READY`, Lead MAY route the same Issue to `Lead / propose-change` without a second generic Human proceed decision only when the proposal-ready direction remains within that envelope and introduces no new Human-reserved decision. A new project/product direction, material externally observable behavior choice, material scope trade-off, explicit risk acceptance, materially different security/privacy/cost/operational commitment, contradictory authority evidence, or materially changed governing evidence SHALL require `HUMAN_DECISION_REQUIRED` before Propose.

Lead idle advisory admission, where still used, continues to require both an unambiguous selected direction from actor `royhsu-work` and the reserved Human capability marker `intake:approved` applied by that Human actor. Scheduled Lead, Reviewer, and Executor MUST NEVER add, remove, restore, or otherwise manufacture Human-only `intake:approved`; they MAY only consume valid Human-authored evidence where that capability remains applicable.

#### Scenario: Human directly admits fuzzy work to Explore

- GIVEN actor `royhsu-work` creates or explicitly routes a coordination Issue to `Lead / explore-change`
- AND `Change:` is unset
- WHEN scheduled workflow reconstructs admission
- THEN the Issue is valid queued pre-Change research
- AND Explore does not create a formal Change until an applicable `PROPOSAL_READY` result is authorized within its admitted authority envelope

#### Scenario: Human directly admits concrete work to Propose

- GIVEN actor `royhsu-work` creates or explicitly routes a coordination Issue to `Lead / propose-change`
- AND `Change:` is unset
- WHEN scheduled workflow reconstructs admission
- THEN the Issue is valid queued pre-activation work
- AND Explore is not mandatory for that Issue

#### Scenario: Canonical requirement authorizes bounded Explore

- GIVEN no active/terminal-pending workflow or already eligible pre-activation work should be advanced first
- AND default-branch canonical requirement R contains an applicable MUST/SHALL obligation
- AND Lead observes a concrete material gap against R that introduces no new Human-reserved decision
- WHEN Lead performs bounded idle discovery
- THEN Lead may materialize at most one `Change: unset + Lead / explore-change` Issue
- AND the Issue records reconstructable admission evidence that cites R and the observed default-branch revision
- AND no `intake:approved` or formal Change identity is created

#### Scenario: Arbitrary README prose cannot authorize admission

- GIVEN README contains descriptive/current-state text, an example, a non-goal, or work marked merely deferred/uncommitted
- WHEN Lead evaluates autonomous Explore admission
- THEN that text alone is insufficient admission authority
- AND Lead does not infer roadmap permission from arbitrary prose

#### Scenario: Explicit README commitment can authorize bounded Explore

- GIVEN README contains an explicitly governed prospective project-direction commitment
- AND the commitment is scoped, affirmative, non-contradictory with canonical specs, and not merely deferred/uncommitted
- AND a concrete material gap remains within that direction without introducing a Human-reserved decision
- WHEN Lead evaluates bounded idle discovery
- THEN that commitment may serve as admission authority for one bounded Explore candidate
- AND runtime routing semantics remain governed by `agents/AGENTS.md` rather than README prose

#### Scenario: Recurring material workflow friction authorizes bounded maintenance Explore

- GIVEN current repository evidence demonstrates a behavior-preserving recurring workflow failure or equivalent material structural friction
- AND the problem has a bounded ownership surface
- AND resolving the problem does not choose new product scope or require Human risk acceptance
- WHEN Lead reaches the idle-discovery boundary
- THEN Lead may autonomously materialize one bounded Formal Explore candidate
- AND style preference or speculative cleanup alone would not satisfy the same threshold

#### Scenario: Agent-created ticket cannot self-feed another admission

- GIVEN an earlier Agent-created advisory or Explore Issue recommends additional work
- AND no independent default-branch authority source or current concrete material friction evidence supports that additional work
- WHEN Lead evaluates another autonomous admission
- THEN the earlier Agent-authored artifact alone is insufficient authority
- AND no recursive workflow ticket is materialized

#### Scenario: Proposal-ready Explore proceeds inside admitted authority

- GIVEN a Human-admitted or valid repository-authorized Explore has a decision-complete `PROPOSAL_READY`
- AND the proposed direction remains inside the admitted authority envelope
- AND no new Human-reserved decision is required
- WHEN Lead completes Explore
- THEN Lead may route the same Issue to `Lead / propose-change` without a second generic Human proceed decision
- AND same-role continuation follows the existing reconstruction contract

#### Scenario: Proposal-ready Explore exposes a new Human decision

- GIVEN Explore discovers a material new product direction, scope/behavior trade-off, risk acceptance, or materially different security/privacy/cost/operational commitment
- WHEN Lead evaluates the next disposition
- THEN Lead records `HUMAN_DECISION_REQUIRED`
- AND does not route to Propose until valid Human authority is reconstructed

#### Scenario: Non-Human routing is insufficient

- GIVEN an actor other than `royhsu-work` applies apparently valid initial routing
- AND no independently valid repository-authorized admission evidence satisfies the bounded autonomous Explore contract
- WHEN scheduled workflow evaluates admission
- THEN that routing does not satisfy Human-required admission
- AND scheduled roles fail closed rather than treating actor-applied routing alone as authorized workflow entry

### Requirement: Lead idle advisory and discovery mode is bounded and non-disruptive

Lead SHALL keep idle discovery/advisory behavior bounded and subordinate to existing workflow work.

Lead may enter idle discovery only when no formal active or terminal-pending workflow requires advancement, no already eligible pre-activation work should be selected first, and no unresolved orphan/governance evidence requires diagnosis. Reviewer and Executor remain silent when they have no eligible workflow work.

When the idle boundary is reached, Lead MAY create an idle advisory Issue containing at most three current recommendations only if no other open `advisory:idle` Issue exists. An advisory Issue MUST NOT contain `agent:*` or `action:*` routing labels and is not itself a coordination workflow instance. If an open advisory remains without valid Human admission, later Lead runs SHALL no-op rather than create duplicate advisory noise.

When forming bounded advisory recommendations, Lead SHALL consider relevant Issues created or materially active during the preceding seven days and recent durable workflow evidence for Skill-maintenance opportunities such as repeated Agent mistakes or recoverable failures, missing or obsolete action guidance, unnecessary Skill complexity, and materially duplicated Skill guidance. A Skill-maintenance recommendation remains diagnostic/advisory only: it MUST NOT directly mutate governed Skill behavior, bypass Human admission, or create a second maintenance workflow.

One idle invocation MAY instead autonomously materialize at most one valid repository-authorized Formal Explore candidate under the admission requirement above. Before creating that candidate, Lead MUST deduplicate against existing open or reconstructably unresolved Issues and required-deferred trackers.

Idle discovery SHALL use materiality rather than style preference. Repeated materially similar responsibility/knowledge/workaround evidence MAY use Rule-of-Three as sufficient investigation evidence; a clear single-instance structural hazard such as dual authority, circular ownership, dead abstraction, or a known-always-failing normal workflow step MAY also satisfy the threshold when concrete cost/risk/friction and bounded ownership are demonstrated.

Idle discovery MUST NOT introduce a scan cursor, TTL coverage registry, lease, heartbeat, progress counter, global priority score, hidden backlog state, or requirement for exhaustive repository coverage merely to remember what was inspected previously.

#### Scenario: Existing idle advisory has no Human decision

- GIVEN one open `advisory:idle` Issue exists
- AND no valid Human admission has occurred
- WHEN Lead runs while workflow is otherwise idle
- THEN Lead does not create another advisory Issue
- AND does not repeat the same recommendations as new workflow noise

#### Scenario: Recent workflow evidence suggests a Skill improvement

- GIVEN workflow execution is otherwise idle
- AND recent durable evidence shows a repeated action mistake or missing/obsolete Skill guidance
- WHEN Lead forms an eligible bounded idle advisory
- THEN Lead may recommend the narrowest Skill-maintenance change supported by that evidence
- AND the recommendation does not itself modify the Skill or create a parallel maintenance workflow
- AND any governed behavior change still requires normal Human-admitted/OpenSpec lifecycle

#### Scenario: Existing pre-activation work prevents autonomous materialization

- GIVEN no formal active workflow exists
- AND an eligible queued pre-activation Issue already exists
- WHEN Lead wakes
- THEN Lead advances the deterministic pre-activation winner before idle discovery
- AND does not create a new autonomous Explore candidate first

#### Scenario: One idle invocation creates at most one candidate

- GIVEN Lead reaches the idle-discovery boundary
- AND multiple material candidate problems are observed
- WHEN Lead chooses to materialize repository-authorized Formal Explore work
- THEN at most one new candidate Issue is created in that invocation
- AND no global priority/scoring framework is introduced to rank the remaining observations

#### Scenario: No material finding is a valid idle result

- GIVEN Lead performs bounded idle discovery
- AND no candidate meets repository-authority/materiality requirements
- WHEN the invocation completes
- THEN no workflow mutation is required
- AND the run does not create repository noise merely to report that nothing material was found

### Requirement: Explore exits on decision-complete dispositions

Lead SHALL treat Explore as complete when continued investigation is no longer required to choose the next legal disposition, rather than requiring exhaustive knowledge or a fixed research checklist.

Before exiting Explore, each material unresolved question that could change the selected disposition MUST be resolved by evidence, shown to be non-blocking, identified as a genuine Human intent/authority decision, or sufficient to establish a current no-change/no-go conclusion.

The legal Explore dispositions SHALL be:

- `PROPOSAL_READY`: evidence supports a concrete/buildable direction and formal proposal authoring would not require Lead to invent a material requirement or solution decision; when the direction remains within a valid Human- or repository-authorized admission authority envelope and no new Human-reserved decision exists, this disposition authorizes same-Issue routing to Propose without a second generic Human proceed decision;
- `NO_CHANGE_REQUIRED`: evidence shows no repository change is required;
- `NO_GO`: evidence shows the contemplated change is currently infeasible or unjustified;
- `HUMAN_DECISION_REQUIRED`: a material remaining decision belongs to Human intent/authority and cannot be resolved from repository/technical evidence.

`SPECIFICATION_BLOCKED` MUST NOT be used as a terminal substitute for a decision-complete no-change/no-go Explore conclusion.

#### Scenario: Explore is proposal-ready inside authority envelope

- GIVEN Lead has resolved all material questions that would alter the proposed direction
- AND a bounded proposal can be authored without inventing material requirements or solution choices
- AND the result remains inside valid Human- or repository-authorized admission authority
- WHEN Lead evaluates the Explore disposition
- THEN the result is `PROPOSAL_READY`
- AND Lead may transition the same Issue to Propose under the shared same-role continuation contract

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
