## ADDED Requirements

### Requirement: Repository design applies project-wide proportionality and simplicity

Repository design SHALL prefer the smallest sufficient design that preserves required capabilities and safety properties across production code, architecture, persisted state, APIs, configuration, dependencies, tests/tooling, GitHub Actions, OpenSpec design, and Agent/workflow governance.

Before adding a concept or mechanism, the change SHALL identify a current approved requirement, concrete safety property, or demonstrated failure mode that requires the added complexity. When an existing concept is within the current change scope, the design SHALL prefer removal, consolidation, or an existing ownership layer when required capabilities and safety properties still hold without that concept.

This evaluation MUST remain bounded to the current change's relevant scope and MUST NOT turn ordinary change work into an unrelated repository-wide simplification audit.

#### Scenario: New abstraction has no demonstrated need

- GIVEN a proposed change introduces a new abstraction or persistent mechanism
- AND no current requirement, safety property, or demonstrated failure mode requires that mechanism
- WHEN Lead and Reviewer evaluate the design
- THEN the proposal does not retain the mechanism for hypothetical future generality alone
- AND the design prefers removal, consolidation, or an existing ownership layer

#### Scenario: Existing complexity is necessary

- GIVEN a concept within the current change scope appears removable
- WHEN removing it would violate a required capability or safety property
- THEN the design may retain the concept
- AND the requirement or safety property that justifies it is identifiable from current evidence

### Requirement: Skill maintenance uses bounded progressive disclosure and existing authority layers

Repository Skill authoring and maintenance SHALL keep each `SKILL.md` focused on the executable procedure for its mapped action. Conditionally needed detail MAY be moved to clearly referenced bundled/shared resources when that improves progressive disclosure, and guidance reused by multiple Skills SHOULD be extracted to one reusable source when genuine cross-Skill reuse exists.

Skill resources MUST NOT become a competing owner for shared Scheduled-Agent runtime invariants or role authority. Shared runtime invariants remain owned by `agents/AGENTS.md`; role mission/authority remains owned by `agents/roles/*`; action-specific procedure remains owned by the mapped Skill.

External mutable Skill-authoring references MAY inform a governed change, but scheduled runtime MUST NOT depend on fetching or obeying those external sources as authority. Adopted behavior SHALL be represented in current default-branch repository governance/artifacts before it can govern execution.

#### Scenario: Skill grows with conditionally needed detail

- GIVEN a mapped Skill contains detail needed only for a specific execution condition
- WHEN keeping that detail inline would make the main procedure unnecessarily large or obscure the common path
- THEN the Skill may reference a bundled or shared resource loaded only for that condition
- AND the main `SKILL.md` retains the action's compact executable flow

#### Scenario: Guidance is shared by multiple Skills

- GIVEN materially identical procedural guidance is needed by multiple Skills
- WHEN maintaining copies would create synchronization-by-convention
- THEN the repository prefers one explicit reusable guidance source with clear loading conditions
- AND does not move shared runtime invariants or role authority into that Skill resource

#### Scenario: External skill guidance changes upstream

- GIVEN an external Skill-authoring reference changes after repository approval
- WHEN a Scheduled Agent executes repository work
- THEN the external change does not alter runtime behavior
- AND any adopted update must enter the repository's governed change lifecycle before becoming authoritative

## MODIFIED Requirements

### Requirement: Governance rule categories have one authoritative surface

The repository SHALL assign each governance rule category to one authoritative surface and SHALL NOT require duplicated normative definitions across multiple surfaces to remain synchronized by convention.

The minimum ownership model SHALL be:

| Rule category | Authoritative surface | Other surfaces |
| --- | --- | --- |
| Repository overview / Human entry point | `README.md` | MAY link to authoritative governance; MUST NOT redefine runtime protocol |
| Shared Scheduled-Agent runtime protocol / cross-role invariants | `agents/AGENTS.md` | roles/skills MAY reference; MUST NOT duplicate shared normative contract |
| Role mission / authority / ownership / role-specific invariant | `agents/roles/*.md` | AGENTS/skills MAY orient/reference; MUST NOT create a competing authority definition |
| Action-specific executable procedure / local result and handoff behavior | `agents/skills/*` | role/AGENTS MAY map/reference; MUST NOT duplicate procedure bodies |
| OpenSpec authoring/validation conventions | `openspec/config.yaml` | change artifacts follow them; MUST NOT restate them as independent runtime rules |
| Approved capability requirements / acceptance scenarios | `openspec/specs/*` | runtime governance MAY implement/reference them; they are not an alternative instruction-loading surface for Scheduled Agents |
| Proposed change intent/design/tasks before merge | active `openspec/changes/*` | review target only; MUST NOT govern its own current runtime execution |
| Historical change provenance | archived OpenSpec changes | history/traceability only; MUST NOT override current default-branch runtime governance |
| External Scheduled Task topology/cadence/configuration | external product configuration | repository docs MAY describe migration/current setup informationally; MUST NOT model it as durable workflow state |
| Project-wide proportionality / simplicity contract | `openspec/specs/repository-governance/spec.md` | runtime/documentation surfaces MAY implement or reference it; MUST NOT maintain a competing workflow-only normative definition |

#### Scenario: Shared rule appears in a role or skill

- GIVEN a rule is owned by shared Scheduled-Agent governance
- WHEN a role or skill needs that rule
- THEN it references the shared contract or states only its role/action-specific specialization
- AND it does not redefine a second normative copy that must be manually synchronized

#### Scenario: Active change contains future governance

- GIVEN an unmerged OpenSpec change or feature branch defines new governance behavior
- WHEN a Scheduled Agent wakes before that change is merged to the default branch
- THEN the feature-branch/change content is review input only
- AND the Scheduled Agent still loads current runtime governance from the default branch

#### Scenario: Project-wide design principle is needed by workflow and production design

- GIVEN proportionality applies to both Scheduled-Agent governance and ordinary project design
- WHEN the repository assigns normative ownership
- THEN the capability-level requirement is owned by `repository-governance`
- AND runtime/documentation surfaces may implement or reference it without maintaining a competing workflow-only normative definition
