## MODIFIED Requirements

### Requirement: Governance rule categories have one authoritative surface

The repository SHALL assign each governance rule category to one authoritative surface and SHALL NOT require duplicated normative definitions across multiple surfaces to remain synchronized by convention.

The minimum ownership model SHALL be:

| Rule category | Authoritative surface | Other surfaces |
| --- | --- | --- |
| Repository overview / Human entry point | `README.md` | MAY link to authoritative governance; MUST NOT redefine runtime protocol |
| Shared Scheduled-Agent execution protocol / cross-role invariants | `agents/AGENTS.md` | roles/skills MAY reference; MUST NOT duplicate shared normative contract |
| Machine-decidable Scheduled-Agent Action vocabulary, Action→Role mapping, finite result/transition topology, deterministic dispatch/cardinality, effect capabilities, mutation-carrier eligibility, fresh application authorization, deterministic rejection classification/evidence, stale/replay classification, and structural postconditions | repository executable workflow topology/kernel selected by current default-branch governance | `agents/workflow.md` SHALL be generated or mechanically verified Human-readable presentation; AGENTS/roles/skills/runtime/transport/carriers MUST NOT maintain a competing executable transition DAG or parse Human prose as the normal topology authority |
| GitHub mutation execution identity / carrier mechanics | replaceable carrier selected only from repository-authorized carrier eligibility | Actions `GITHUB_TOKEN`, Scheduled-Agent connector, or GitHub App MAY execute an exact already-authorized mutation plan; a carrier MUST NOT select Issue/Action/effect, weaken preconditions, infer retry, or make API success authoritative |
| Role mission / semantic authority / ownership / role-specific invariant | `agents/roles/*.md` | AGENTS/skills MAY orient/reference; MUST NOT create a competing authority definition or redefine executable Action→Role/transition tables |
| Action-specific semantic procedure / action-local evidence and result meaning | `agents/skills/*` | role/AGENTS MAY map/reference; MUST NOT duplicate machine-decidable topology/effect bodies owned by the executable kernel |
| OpenSpec authoring/validation conventions | `openspec/config.yaml` | change artifacts follow them; MUST NOT restate them as independent runtime rules |
| Approved capability requirements / acceptance scenarios | `openspec/specs/*` | runtime governance/executable code implement/reference them; they are not an alternative instruction-loading surface for Scheduled Agents |
| Proposed change intent/design/tasks before merge | active `openspec/changes/*` | review target only; MUST NOT govern its own current runtime execution |
| Historical change provenance | archived OpenSpec changes | history/traceability only; MUST NOT override current default-branch runtime governance or become current routing state |
| External Scheduled Task cadence/configuration and transport wiring | external product configuration / replaceable transport adapter as applicable | repository docs MAY describe migration/current setup informationally; transport MUST NOT define workflow topology or durable routing state |
| Project-wide proportionality / simplicity contract | `openspec/specs/repository-governance/spec.md` | runtime/documentation surfaces MAY implement or reference it; MUST NOT maintain a competing workflow-only normative definition |

The executable workflow topology/kernel becomes authoritative for machine-decidable workflow semantics and effect/carrier eligibility only after the approved implementation and governance that delegate that ownership are merged to the current default branch. An active Change or feature branch containing a future kernel remains review input and MUST NOT govern its own invocation.

A Human-readable workflow surface MAY include explanatory lifecycle rationale and semantic guidance that cannot be generated from a finite topology. Any machine-decidable Action/Role/transition/effect/carrier rule represented there MUST be produced from or mechanically checked against the executable owner so a divergence fails repository validation instead of depending on manual synchronization.

Effect authority and mutation identity SHALL remain separate. Repository application/kernel authorization binds an exact effect to its exact target, preconditions, revision, and legal carrier class. A selected carrier is an actuator only; replacing the carrier MUST NOT change workflow semantics, effect eligibility, or success criteria. Repository-owned fresh observation of the resulting object/head/state is required before any routing, review, lifecycle, merge, or successor consequence can consume the mutation as successful.

When deterministic repository authorization/application rejects an effect plan, the executable owner SHALL emit machine-readable rejection classification/evidence identifying the exact failed guard class and the relevant expected/observed identity or predicate evidence available at that boundary. An aggregate human-readable reason MAY accompany it but MUST NOT be the sole rejection evidence when the executable boundary already knows which deterministic predicate failed. This rejection evidence MUST NOT grant a carrier or semantic worker authority to retry, weaken preconditions, choose a successor, or reinterpret workflow state.

#### Scenario: Shared rule appears in a role or skill

- GIVEN a rule is owned by shared Scheduled-Agent governance or the executable workflow topology/kernel
- WHEN a role or skill needs that rule
- THEN it references the owning contract or states only its role/action-specific semantic specialization
- AND it does not redefine a second normative machine-control copy that must be manually synchronized

#### Scenario: Active change contains future governance

- GIVEN an unmerged OpenSpec change or feature branch defines new governance behavior or an executable topology/kernel
- WHEN a Scheduled Agent wakes before that change is merged to the default branch
- THEN the feature-branch/change content is review input only
- AND the Scheduled Agent still loads current runtime governance and executable authority from the current default branch

#### Scenario: Project-wide design principle is needed by workflow and production design

- GIVEN proportionality applies to both Scheduled-Agent governance and ordinary project design
- WHEN the repository assigns normative ownership
- THEN the capability-level requirement is owned by `repository-governance`
- AND runtime/documentation surfaces may implement or reference it without maintaining a competing workflow-only normative definition

#### Scenario: Human-readable topology drifts from executable topology

- GIVEN current default-branch governance delegates machine-decidable workflow topology to the repository executable kernel
- AND `agents/workflow.md` presents an Action/Role/transition/effect/carrier rule that differs from that executable topology
- WHEN repository governance validation runs
- THEN validation fails
- AND production dispatch/application continue to consume the executable topology rather than resolving the conflict by parsing or preferring Markdown prose

#### Scenario: Transport changes without changing workflow semantics

- GIVEN the current Scheduled Task transport uses Issue comments to trigger deterministic GitHub Actions
- AND a future supported transport can invoke the same deterministic dispatch/application entry points directly
- WHEN the adapter changes
- THEN Action vocabulary, Action→Role derivation, typed result/transition semantics, WIP/cardinality, effect authorization, and carrier eligibility remain unchanged
- AND transport messages do not become a second workflow-semantics authority

#### Scenario: Mutation carrier changes without gaining workflow authority

- GIVEN repository application has fresh-authorized one exact GitHub effect with exact target, preconditions, revision, and legal carrier class
- AND the current Actions `GITHUB_TOKEN` identity cannot legally execute that effect or preserve required event semantics
- WHEN an eligible Scheduled-Agent connector or GitHub App carrier executes the exact authorized plan
- THEN the carrier does not select or reinterpret workflow state, Action, successor, effect, retry, or success
- AND repository application accepts completion only after fresh observation proves the exact governed postcondition
- AND replacing the carrier does not change the workflow contract

#### Scenario: Deterministic rejection remains repository-owned evidence

- GIVEN repository application rejects one authorized effect plan because a deterministic guard fails
- WHEN the result is returned to the semantic worker
- THEN the result identifies the exact failed guard class and relevant expected/observed evidence machine-readably
- AND the semantic worker is not required to reverse-engineer the failed deterministic predicate from routing, SHA, branch payload, or application source code
- AND the rejection does not itself authorize retry, weaker preconditions, a different target, or a successor
