# repository-governance

## ADDED Requirements

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
