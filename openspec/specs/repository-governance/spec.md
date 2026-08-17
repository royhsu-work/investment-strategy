# repository-governance Specification

## Purpose

Define repository governance authority and ownership boundaries, single-source-of-truth reference rules, and current-versus-history boundaries so approved governance remains traceable without competing normative copies.
## Requirements
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

### Requirement: Non-authoritative orientation is distinguishable from normative authority

A non-authoritative surface MAY contain a brief orientation or link to help Human readers navigate the repository, but it MUST make the authoritative destination clear and MUST NOT restate detailed MUST/SHALL lifecycle semantics in a way that can conflict with the owning surface.

#### Scenario: README explains the development lifecycle

- GIVEN README needs to explain that the repository uses Scheduled Agents and OpenSpec
- WHEN it presents the development workflow
- THEN it may provide a concise overview and link to the authoritative governance
- AND detailed routing, role priority, Human escalation, retry, or terminal-state rules remain authoritative only in their owning governance surfaces

### Requirement: Reviewer and Executor use ownership boundaries during changes

Reviewer SHALL treat duplicate normative authority, stale copies, and ownership drift within the current change scope as reviewable governance defects. Executor SHALL modify the authoritative surface for a rule category and SHALL update dependent references only when needed, rather than maintaining parallel normative copies.

#### Scenario: Change modifies a shared runtime invariant

- GIVEN an approved change modifies a cross-role runtime invariant
- WHEN Executor implements it
- THEN the authoritative shared governance surface is modified
- AND role/skill files are changed only for references or true role/action-specific specialization
- AND Reviewer checks that no stale competing normative copy remains in the affected scope

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

### Requirement: Python static security extends the existing Ruff quality gate

The repository SHALL enforce Ruff's non-preview `S` security rule family through the existing Python Quality Ruff lint gate rather than requiring a parallel static-analysis lifecycle. The selected security family SHALL apply to repository Python code under the normal Ruff scope. Test files under `tests/**` MAY ignore `S101` so ordinary test assertions remain valid, but production/source code and repository Python scripts MUST NOT receive a blanket `S101` exemption. Any additional security-rule ignore MUST be narrowly scoped and justified by concrete repository context; the `S` family MUST NOT be globally disabled to avoid remediation. Bandit, Semgrep, or another static-security scanner MUST NOT be required by this contract unless a separately demonstrated capability gap shows the existing Ruff gate cannot satisfy a required security property.

#### Scenario: Stable security rule is applicable

- GIVEN repository Python code violates a non-preview rule selected by Ruff's `S` family
- WHEN the existing Python Quality Ruff lint step runs
- THEN the same Ruff gate reports the violation
- AND no second static-analysis lifecycle is required for that coverage

#### Scenario: Test assertion is linted

- GIVEN a Python file is under `tests/**`
- AND it uses an ordinary `assert` statement for test verification
- WHEN Ruff evaluates `S101`
- THEN the configured test-only exception permits that assertion
- AND the exception does not grant a blanket `S101` exemption to production/source code or repository Python scripts

#### Scenario: Preview security rule exists

- GIVEN Ruff exposes a security rule that is still preview-only
- WHEN the repository selects the `S` family under this contract
- THEN this change does not enable Ruff preview mode merely to activate that rule
- AND preview-rule adoption requires separate evidence before becoming part of the quality contract

#### Scenario: Additional security finding appears

- GIVEN enabling the `S` family exposes a stable security finding
- WHEN Executor implements the approved change
- THEN the finding is remediated where feasible
- AND any exception is narrowly scoped and justified by the concrete repository pattern
- AND the `S` family is not globally disabled to make the gate pass

#### Scenario: Security lint configuration regresses

- GIVEN the repository has adopted the Ruff security-family policy
- WHEN a later change removes `S` from the configured lint families or broadens the test-only `S101` exception into production scope
- THEN focused repository regression coverage fails
- AND the existing Python Quality workflow surfaces the regression without a second scanner job

#### Scenario: Another scanner is proposed

- GIVEN Bandit, Semgrep, or another static-security scanner is proposed in addition to Ruff
- WHEN no concrete required capability gap in Ruff has been demonstrated
- THEN the repository does not add the duplicate scanner lifecycle under this requirement
- AND a separately evidenced need is required before such an expansion is governed

