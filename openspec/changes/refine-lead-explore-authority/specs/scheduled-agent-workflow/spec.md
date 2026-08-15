# scheduled-agent-workflow Delta Specification

## MODIFIED Requirements

### Requirement: Workflow admission is explicitly authority-controlled

Scheduled agents MUST NOT autonomously admit arbitrary Issues, PRs, repository activity, discussions, discovered requirements, or Agent-authored recommendations into workflow work.

Human admission remains valid through the repository's Human-authority contract. In addition, Lead MAY autonomously materialize one bounded `Lead / explore-change` coordination Issue with `Change: unset` only from the idle-discovery boundary when the admission is independently justified by one of the following:

- an applicable default-branch canonical MUST/SHALL requirement with a concrete material gap;
- an approved required-deferred obligation with reconstructable source linkage;
- an explicitly governed README project-direction commitment that is prospective, scoped, affirmative, non-contradictory with canonical specs, and not merely descriptive/current-state/non-goal/example/deferred-uncommitted text; or
- concrete material behavior-preserving maintenance/friction evidence with a bounded ownership surface and no new Human-reserved product/scope/risk decision.

An autonomous admission MUST contain reconstructable evidence identifying the admission kind, exact observed default-branch revision where applicable, exact authority/evidence source, bounded problem statement, and why no Human-reserved decision is being made. Later reconstruction MUST validate that evidence and MUST fail closed when the cited source is absent, stale, contradictory, merely descriptive, insufficiently material, or otherwise does not authorize the bounded problem.

Agent-authored advisory text, Explore conclusions, and prior Agent-created tickets MUST NOT recursively serve as sufficient authority for another autonomous admission by themselves. Every autonomous admission SHALL trace to an independent default-branch authority source or current concrete repository/friction evidence.

Autonomous admission MUST NOT add, remove, restore, or manufacture `intake:approved`, MUST NOT persist a formal Change identity, and MUST NOT bypass Propose, Reviewer, implementation, merge, archive, or lifecycle gates.

A Human-admitted or valid repository-authorized `Lead / explore-change` Issue with `Change: unset` is queued pre-Change research. A Human-admitted `Lead / propose-change` Issue MAY remain queued with `Change: unset` as direct-to-Propose work. In workflow-dynamic mode, neither may bypass a formal active or terminal-pending workflow, and eligible pre-activation work continues to follow the deterministic queue contract.

Explore admission establishes a bounded authority envelope for the admitted problem. When Explore reaches `PROPOSAL_READY`, Lead MAY route the same Issue to `Lead / propose-change` without a second generic Human proceed decision only when the proposal-ready direction remains within that envelope and introduces no new Human-reserved decision. A new project/product direction, material externally observable behavior choice, material scope trade-off, explicit risk acceptance, materially different security/privacy/cost/operational commitment, contradictory authority evidence, or materially changed governing evidence SHALL require `HUMAN_DECISION_REQUIRED` before Propose.

Scheduled Lead, Reviewer, and Executor MUST NEVER manufacture Human-only `intake:approved`; they MAY only consume valid Human-authored evidence where that capability remains applicable.

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

### Requirement: Lead idle advisory and discovery mode is bounded and non-disruptive

Lead SHALL keep idle discovery/advisory behavior bounded and subordinate to existing workflow work.

Lead may enter idle discovery only when no formal active or terminal-pending workflow requires advancement, no already eligible pre-activation work should be selected first, and no unresolved orphan/governance evidence requires diagnosis. Reviewer and Executor remain silent when they have no eligible workflow work.

One idle invocation MAY either produce no material action, update/create the bounded advisory permitted by governance, or autonomously materialize at most one valid repository-authorized Formal Explore candidate under the admission requirement above. It MUST deduplicate against existing open/reconstructably unresolved Issues and required-deferred trackers before creating a candidate.

Idle discovery SHALL use materiality rather than style preference. Repeated materially similar responsibility/knowledge/workaround evidence MAY use Rule-of-Three as sufficient investigation evidence; a clear single-instance structural hazard such as dual authority, circular ownership, dead abstraction, or a known-always-failing normal workflow step MAY also satisfy the threshold when concrete cost/risk/friction and bounded ownership are demonstrated.

Idle discovery MUST NOT introduce a scan cursor, TTL coverage registry, lease, heartbeat, progress counter, global priority score, hidden backlog state, or requirement for exhaustive repository coverage merely to remember what was inspected previously.

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

### Requirement: Lead Explore is decision-complete before lifecycle disposition

Lead SHALL treat `explore-change` as bounded problem-before-solution research rather than proposal authoring.

Before exiting Explore, each material unresolved question that could change the selected disposition MUST be resolved by evidence, shown to be non-blocking, identified as a genuine Human intent/authority decision, or sufficient to establish a current no-change/no-go conclusion.

The legal Explore dispositions SHALL be:

- `PROPOSAL_READY`: evidence supports a concrete/buildable direction and formal proposal authoring would not require Lead to invent a material requirement or solution decision; when the direction remains within the valid admission authority envelope and no new Human-reserved decision exists, this disposition authorizes same-Issue routing to Propose without a second generic Human proceed decision;
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

#### Scenario: Explore requires genuinely new Human authority

- GIVEN a material unresolved decision falls outside the admitted authority envelope
- WHEN repository/technical evidence cannot resolve it
- THEN the result is `HUMAN_DECISION_REQUIRED`
- AND generic continuation is prohibited until valid Human authority is reconstructed
