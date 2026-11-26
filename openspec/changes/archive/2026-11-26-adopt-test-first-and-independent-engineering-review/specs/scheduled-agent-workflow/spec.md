## MODIFIED Requirements

### Requirement: Executor consumes complete approved OpenSpec apply context

`Executor / implement-change` SHALL consume the approved Change artifacts and all materially applicable project/config semantics represented by the shared OpenSpec semantic adapter before implementing or marking tasks complete.

The apply context SHALL include the approved proposal, applicable delta specs, design, tasks, applicable canonical specs required to interpret modified behavior, and applicable `openspec/config.yaml` context/rules required by the configured schema. Executor MUST NOT silently omit required context merely because upstream would normally supply it through an unavailable CLI instruction surface.

If required approved context is missing, contradictory, or materially ambiguous such that implementation would require inventing specification meaning, Executor MUST fail closed and return the blocker through the existing Lead specification-question path. This requirement MUST NOT grant Executor authority to redefine requirements, scope, design decisions, or task meaning.

#### Scenario: Missing apply context returns to Lead

- GIVEN Executor is routed to `implement-change`
- AND a material approved artifact/context/rule required by the configured OpenSpec semantic adapter is unavailable or contradictory
- AND continuing would require Executor to choose specification meaning
- WHEN Executor reconstructs the implementation context
- THEN Executor does not silently omit or invent the missing meaning
- AND the blocker is returned to Lead through the existing specification-question lifecycle

#### Scenario: Complete apply context preserves existing Executor authority boundary

- GIVEN the approved proposal, specs, design, tasks, applicable canonical specs, and applicable config context/rules are available
- WHEN Executor implements the Change
- THEN Executor consumes that complete approved context
- AND the applicable repository-governance test-first procedure, independent refactoring-assessment boundary and existing VERIFY and verified-slice checkpoint semantics remain applicable
- AND Executor gains no authority to redefine the approved contract
