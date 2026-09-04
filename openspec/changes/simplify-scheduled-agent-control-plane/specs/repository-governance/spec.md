## MODIFIED Requirements

### Requirement: Governance rule categories have one authoritative surface

The repository SHALL assign each governance rule category to one authoritative surface and SHALL NOT require duplicated normative definitions across multiple surfaces to remain synchronized by convention.

The minimum ownership model SHALL be:

| Rule category | Authoritative surface | Other surfaces |
| --- | --- | --- |
| Repository overview / Human entry point | README.md | MAY link to authoritative governance; MUST NOT redefine runtime protocol |
| Shared Scheduled-Agent runtime protocol and safety invariants | agents/AGENTS.md | roles/skills MAY reference; MUST NOT duplicate the shared contract |
| Machine-decidable Action vocabulary, Action→Role mapping, finite transition/result rules, deterministic selection, effect authorization, carrier eligibility, stale/replay/no-rewind guards, and postconditions | one default-branch executable workflow model | agents/workflow.md MAY be generated or mechanically verified Human-readable presentation; AGENTS/roles/skills/runtime/transport/carriers MUST NOT maintain a competing production DAG or parse prose as topology |
| Semantic role authority | agents/roles/*.md | AGENTS/Skills MAY orient/reference; MUST NOT redefine machine Action→Role or successor selection |
| Action-specific semantic procedure and evidence meaning | agents/skills/* | roles/AGENTS MAY map/reference; MUST NOT duplicate machine topology/effect bodies |
| OpenSpec authoring and validation conventions | openspec/config.yaml | Change artifacts follow them; MUST NOT restate them as runtime rules |
| Approved capability requirements and acceptance scenarios | openspec/specs/* | runtime code implements/references them; they are not an alternative runtime instruction surface |
| Proposed intent/design/tasks before merge | active openspec/changes/* | review input only; MUST NOT govern its own current invocation |
| Historical change provenance | archived OpenSpec changes | evidence only; MUST NOT override current default-branch governance or become routing state |
| Scheduled Task cadence and transport wiring | external product configuration and a replaceable transport adapter | repository docs MAY describe deployment context; transport MUST NOT define Action/Role/WIP/successor state |
| Project-wide proportionality and simplicity | openspec/specs/repository-governance/spec.md | runtime/documentation surfaces MAY implement or reference it; MUST NOT maintain a competing workflow-only definition |

The executable workflow model becomes authoritative for machine-decidable workflow semantics only after the approved implementation and delegating governance are merged to the current default branch. An active Change or feature branch containing a future model remains review input and MUST NOT govern its own invocation.

The Human-readable workflow surface MAY include rationale and semantic guidance that cannot be represented in the finite model. Any machine-decidable Action/Role/transition/effect/carrier rule represented there MUST be produced from or mechanically checked against the executable owner so divergence fails validation rather than being resolved by runtime prose parsing.

Repository application/kernel authorization and mutation-carrier identity SHALL remain separate. Application binds each effect to its exact target, preconditions, revision, and legal carrier class. A carrier is an actuator only and MUST NOT choose workflow meaning, target, effect, successor, retry, weaker preconditions, or success. Repository-owned fresh observation is required before a mutation can support a routing, gate, lifecycle, merge, or successor consequence.

Deterministic application rejection SHALL include a machine-readable guard classification and relevant expected/observed identity or predicate evidence whenever that boundary knows the failed predicate. Aggregate diagnostic text MAY accompany it but MUST NOT be the only rejection evidence. Rejection evidence never authorizes retry, weaker preconditions, alternate targets, or a worker-selected successor.

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
