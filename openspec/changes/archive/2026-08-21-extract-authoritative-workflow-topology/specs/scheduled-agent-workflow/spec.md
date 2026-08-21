# scheduled-agent-workflow Delta Specification

## ADDED Requirements

### Requirement: Runtime workflow topology has one authoritative repository owner

The Scheduled-Agent runtime SHALL define end-to-end workflow topology and lifecycle relationships in exactly one authoritative repository surface, `agents/workflow.md`. That topology owner SHALL cover legal action progression, same-role and cross-role successor relationships, correction loops, pre-Change Explore terminal outcomes, and formal terminal completion.

`agents/AGENTS.md` SHALL remain authoritative for shared runtime execution invariants such as dispatch/cardinality, reconstruction, Human authority, work-conserving execution, Invocation Exit, evidence consumption, and concurrency safety, and SHALL reference rather than independently redefine global workflow topology. Role files SHALL remain authoritative for role mission/authority/ownership. Mapped Skills SHALL remain authoritative for action-local executable procedure and MAY name local predecessor/successor actions only as operational references consistent with `agents/workflow.md`, not as competing global topology definitions.

Canonical OpenSpec specifications remain the approved capability requirement and acceptance source; they do not become the runtime instruction-loading DAG. README remains Human/contributor orientation and SHALL reference the authoritative workflow topology instead of maintaining another normative workflow copy.

The ownership extraction MUST preserve the current observable Scheduled-Agent lifecycle, including the default-branch post-#115 terminal contract, and MUST NOT add a machine workflow engine, generated registry, hidden workflow state, or synchronization-by-convention mechanism.

#### Scenario: One runtime surface owns the end-to-end topology

- GIVEN the repository contains the Scheduled-Agent governance surfaces
- WHEN a Scheduled Agent needs the authoritative relationship among legal workflow actions
- THEN `agents/workflow.md` is the single runtime topology owner
- AND `agents/AGENTS.md`, role files, mapped Skills, and README do not maintain competing normative copies of the global topology

#### Scenario: Shared execution invariants remain owned by AGENTS

- GIVEN workflow topology has been extracted to `agents/workflow.md`
- WHEN dispatch, cardinality, Human authority, reconstruction, work-conserving execution, Invocation Exit, or concurrency rules are evaluated
- THEN `agents/AGENTS.md` remains authoritative for those shared runtime invariants
- AND moving topology does not transfer those responsibilities to `agents/workflow.md`

#### Scenario: Existing workflow behavior is preserved

- GIVEN the authoritative default-branch lifecycle before this Change
- WHEN topology ownership is extracted
- THEN legal action progression, correction loops, review and merge separation, pre-Change Explore outcomes, and same-role/cross-role boundaries remain behaviorally equivalent
- AND the formal terminal path remains Archive merge → open `Lead / finalize-archive` → durable `LIFECYCLE_COMPLETE` → coordination Issue close and closed re-observation

#### Scenario: OpenSpec and README keep distinct responsibilities

- GIVEN canonical OpenSpec requirements and README orientation both describe aspects of the Scheduled-Agent workflow
- WHEN runtime topology ownership is evaluated
- THEN canonical OpenSpec remains the approved capability requirement/acceptance source
- AND README remains Human/contributor orientation
- AND neither is treated as a second runtime workflow-topology owner