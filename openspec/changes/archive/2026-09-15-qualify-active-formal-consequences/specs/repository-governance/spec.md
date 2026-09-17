## MODIFIED Requirements

### Requirement: Governance rule categories have one authoritative surface

The repository SHALL assign each governance rule category to one authoritative surface and SHALL NOT require duplicated normative definitions across multiple surfaces to remain synchronized by convention.

The minimum ownership model SHALL be:

| Rule category | Authoritative surface | Other surfaces |
| --- | --- | --- |
| Repository overview / Human entry point | README.md | MAY link to authoritative governance; MUST NOT redefine runtime protocol |
| Shared Scheduled-Agent runtime protocol and safety invariants | agents/AGENTS.md | roles/skills MAY reference; MUST NOT duplicate the shared contract |
| Machine-decidable Action vocabulary, Action→Role mapping, finite transition/result rules, deterministic selection, effect authorization, carrier eligibility, explicit merged-carrier reconciliation, stale/replay/no-rewind guards, and postconditions | one default-branch executable workflow model | agents/workflow.md MAY be generated or mechanically verified Human-readable presentation; AGENTS/roles/skills/runtime/transport/carriers MUST NOT maintain a competing production DAG or parse prose as topology |
| Machine-decidable consequence qualification | the existing canonical executable owner of that consequence | consumers SHALL reuse the owner's structured decision and MUST NOT reconstruct a competing acceptance path |
| Semantic role authority | agents/roles/*.md | AGENTS/Skills MAY orient/reference; MUST NOT redefine machine Action→Role or successor selection |
| Action-specific semantic procedure and evidence meaning | agents/skills/* | roles/AGENTS MAY map/reference; MUST NOT duplicate machine topology/effect bodies |
| OpenSpec authoring and validation conventions | openspec/config.yaml | Change artifacts follow them; MUST NOT restate them as runtime rules |
| Approved capability requirements and acceptance scenarios | openspec/specs/* | runtime code implements/references them; they are not an alternative runtime instruction surface |
| Proposed intent/design/tasks before merge | active openspec/changes/* | review input only; MUST NOT govern its own current invocation |
| Historical change provenance | archived OpenSpec changes | evidence only; MUST NOT override current default-branch governance or become routing state |
| Scheduled Task cadence and transport wiring | external product configuration and a replaceable transport adapter | repository docs MAY describe deployment context; transport MUST NOT define Action/Role/WIP/successor state |
| Project-wide proportionality and simplicity | openspec/specs/repository-governance/spec.md | runtime/documentation surfaces MAY implement or reference it; MUST NOT maintain a competing workflow-only definition |

When a machine-decidable consequence depends on multiple authoritative observations, its existing executable owner SHALL consume the authoritative observation set through one executable decision surface and return one structured decision. All downstream consumers of that consequence SHALL consume the decision rather than independently reconstructing its predicates. This decision atomicity does not replace mutation atomicity: fresh application reauthorization, exact effects, and fresh postcondition observation remain required.

Before retaining a new check, guard, qualification, lifecycle rule, gate, carrier rule, or state, repository design SHALL identify the affected consequence and its existing owner and classify the proposed delta as `REUSE`, `CONSOLIDATE`, `NO-DELTA`, or `ADD`. `ADD` is eligible only when current requirements or safety properties cannot be satisfied by reuse, consolidation, or no delta under the project-wide proportionality rule.

The executable workflow model becomes authoritative for machine-decidable workflow semantics only after the approved implementation and delegating governance are merged to the current default branch. An active Change or feature branch containing a future model remains review input and MUST NOT govern its own invocation.

The Human-readable workflow surface MAY include rationale and semantic guidance that cannot be represented in the finite model. Any machine-decidable Action/Role/transition/effect/carrier rule represented there MUST be produced from or mechanically checked against the executable owner so divergence fails validation rather than being resolved by runtime prose parsing.

Repository application/kernel authorization and mutation-carrier identity SHALL remain separate. Application binds each effect to its exact target, preconditions, revision, and legal carrier class. A carrier is an actuator only and MUST NOT choose workflow meaning, target, effect, successor, retry, weaker preconditions, or success. Repository-owned fresh observation is required before a mutation can support a routing, gate, lifecycle, merge, or successor consequence.

For a carrier that is already closed and merged, application MAY authorize only the explicit read-only reconciliation contract: exact historical head, repositories/base/ref, merge metadata, current default-branch revision and ancestry, and the matching revision-bound independent PASS must all be fresh and coherent. The carrier performs no merge write; it only exposes the existing postcondition for application observation. Reopen, rewrite, force movement, substitution, duplicate merge writes, and duplicate PR creation are prohibited.

Deterministic application rejection SHALL include a machine-readable guard classification and relevant expected/observed identity or predicate evidence whenever that boundary knows the failed predicate. Aggregate diagnostic text MAY accompany it but MUST NOT be the only rejection evidence. Rejection evidence never authorizes retry, weaker preconditions, alternate targets, or a worker-selected successor.

#### Scenario: Project-wide design principle is needed by workflow and production design

- GIVEN proportionality applies to both Scheduled-Agent governance and ordinary project design
- WHEN the repository assigns normative ownership
- THEN the capability-level requirement is owned by repository-governance
- AND runtime/documentation surfaces may implement or reference it without maintaining a competing workflow-only normative definition

#### Scenario: Shared rule appears in a role or skill

- GIVEN a rule is owned by shared governance or the executable workflow model
- WHEN a role or skill needs that rule
- THEN it references the owner or states only its semantic specialization
- AND it does not define a second machine-control copy

#### Scenario: Active change contains future governance

- GIVEN an unmerged Change or feature branch defines a future executable model
- WHEN a Scheduled Agent wakes before that change is merged
- THEN the feature content is review input only
- AND current execution loads authority from the default branch

#### Scenario: Action derives role without a second owner

- GIVEN the current routed state contains one valid action:review-openspec
- WHEN machine dispatch selects work
- THEN it derives reviewer through role_for(action)
- AND no separately persisted normal role label is required for ownership

#### Scenario: Human-readable presentation drifts

- GIVEN agents/workflow.md differs from the default-branch executable Action model
- WHEN governance validation runs
- THEN validation fails
- AND runtime does not resolve the conflict by parsing or preferring Markdown

#### Scenario: Transport changes without changing workflow semantics

- GIVEN a supported transport invokes the same default-branch dispatch/application entry points
- WHEN the transport adapter changes
- THEN Action vocabulary, Role derivation, transitions, WIP/cardinality, effects, and success criteria remain unchanged
- AND transport is not a second workflow authority

#### Scenario: Mutation carrier cannot gain authority

- GIVEN application has authorized one exact mutation plan
- AND the Actions identity cannot legally execute it
- WHEN a legal connector/App carrier executes the plan
- THEN the carrier changes no Issue/Action/Role/effect/successor/retry meaning
- AND application accepts only the exact freshly observed postcondition

#### Scenario: One structured decision is reused by all consequence consumers

- GIVEN a machine-decidable consequence depends on an authoritative observation set and explicit predicates
- AND that consequence has an existing canonical executable owner
- WHEN the owner evaluates consequence eligibility
- THEN it emits one structured decision
- AND every downstream consumer consumes that decision without reconstructing another acceptance path
- AND later mutation still requires fresh application authorization and postcondition observation

#### Scenario: Architecture precedent is classified before adding control behavior

- GIVEN a change proposes a check, guard, qualification, lifecycle rule, gate, carrier rule, or state
- WHEN repository design evaluates the proposal
- THEN it identifies the affected consequence and its existing owner
- AND it classifies the delta as `REUSE`, `CONSOLIDATE`, `NO-DELTA`, or `ADD`
- AND `ADD` is retained only when the current requirement or safety property cannot be satisfied by the other dispositions
