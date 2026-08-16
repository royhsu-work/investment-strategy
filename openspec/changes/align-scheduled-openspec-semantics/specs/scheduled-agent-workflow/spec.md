# scheduled-agent-workflow Delta Specification

## ADDED Requirements

### Requirement: Scheduled roles preserve material OpenSpec semantics when CLI instructions are unavailable

When a Scheduled role performs an OpenSpec action in an execution environment that cannot obtain material schema/artifact/action semantics from the OpenSpec CLI, the repository SHALL provide one accessible shared semantic adapter for the currently configured OpenSpec schema rather than allowing each role to infer or independently duplicate those semantics.

For the current `schema: spec-driven` configuration, the adapter MUST represent the material semantics needed by Scheduled actions for artifact dependency/readiness, applicable project context and artifact rules, delta-authoring completeness, canonicalization-readiness information knowable before Archive, approved Apply context, and the semantic-baseline provenance needed for later reassessment.

The adapter MUST be consumed together with current default-branch `openspec/config.yaml`, applicable canonical specs, current Change artifacts, and applicable durable source decisions. It MUST NOT become a second workflow DAG, a replacement for canonical capability specs, a generic OpenSpec schema engine, or authority for role/routing decisions.

If the repository's configured schema or a material required semantic input cannot be represented by the current adapter, the affected Scheduled action MUST fail closed until the semantic contract is deliberately updated. Deterministic CLI mechanics and exact-revision strict validation MAY remain owned by repository automation and MUST NOT be copied into hidden Agent state.

#### Scenario: Scheduled Propose consumes the configured semantic adapter

- GIVEN the repository is configured with `schema: spec-driven`
- AND Lead cannot execute the OpenSpec CLI instruction/status commands in the Scheduled environment
- WHEN Lead performs `propose-change`
- THEN Lead consumes the shared spec-driven semantic adapter together with current `openspec/config.yaml`, applicable canonical specs, current durable source decisions, and the Change artifacts being authored
- AND material artifact/context semantics are not omitted merely because their upstream delivery surface is unavailable

#### Scenario: Unsupported semantic contract fails closed

- GIVEN the configured OpenSpec schema or a material semantic input required by the current action is not represented by the shared adapter
- WHEN a Scheduled role attempts an affected OpenSpec action
- THEN the role does not infer the missing semantics from familiar artifact names or prior memory
- AND the action fails closed until the adapter/configuration contract is deliberately reconciled

#### Scenario: Semantic adapter does not become a second authority source

- GIVEN the shared adapter describes procedural OpenSpec semantics for Scheduled roles
- WHEN runtime routing or approved capability behavior is reconstructed
- THEN `agents/AGENTS.md` remains authoritative for Scheduled runtime protocol
- AND canonical `openspec/specs/*` remain authoritative for approved capability requirements
- AND the adapter does not override either authority surface

### Requirement: OpenSpec authoring and independent review prevent knowable canonicalization omissions

Before a newly authored or materially revised OpenSpec Change is handed to implementation, Lead and independent Reviewer SHALL each consume the applicable shared OpenSpec semantic adapter and SHALL prevent material semantic information already knowable for later Sync/Archive/canonicalization from escaping the Propose/OpenSpec-review boundary.

Lead SHALL author the required artifact information and applicable project/artifact-rule content before review handoff. Reviewer SHALL independently verify the same applicable semantic completeness/coherence in addition to the existing reverse-first plus forward traceability and exact-revision validation gates.

For a NEW capability, the reviewed artifact set MUST contain the semantic information required to form a valid canonical capability, including exactly one non-empty `## Purpose`, before `review-openspec` may PASS. A successful strict OpenSpec validation result alone MUST NOT substitute for this semantic check when the validator does not prove the required semantic invariant.

Archive automation MAY retain deterministic fail-closed verification as defense-in-depth, but a semantic invariant knowable during Propose MUST NOT intentionally rely on Archive as its first detector.

#### Scenario: Missing NEW-capability Purpose is rejected before implementation

- GIVEN a Change introduces a NEW capability
- AND the capability delta lacks one non-empty `## Purpose`
- AND strict OpenSpec validation otherwise succeeds
- WHEN Lead evaluates readiness or Reviewer performs `review-openspec`
- THEN the Change does not pass the Propose/OpenSpec-review boundary
- AND Reviewer returns an actionable specification finding to Lead rather than allowing implementation to proceed
- AND Archive remains defense-in-depth rather than the first intended detector

#### Scenario: Traceability success does not hide semantic incompleteness

- GIVEN proposal, specs, design, and tasks have mechanically consistent forward and reverse trace declarations
- AND exact-head strict OpenSpec validation succeeds
- BUT a material spec-driven semantic requirement needed by later canonicalization is missing
- WHEN Reviewer evaluates `review-openspec`
- THEN Reviewer records `FINDINGS`
- AND neither traceability nor strict validation is treated as sufficient proof of semantic completeness

### Requirement: Executor consumes complete approved OpenSpec apply context

`Executor / implement-change` SHALL consume the approved Change artifacts and all materially applicable project/config semantics represented by the shared OpenSpec semantic adapter before implementing or marking tasks complete.

The apply context SHALL include the approved proposal, applicable delta specs, design, tasks, and applicable `openspec/config.yaml` context/rules required by the configured schema. Executor MUST NOT silently omit required context merely because upstream would normally supply it through an unavailable CLI instruction surface.

If required approved context is missing, contradictory, or materially ambiguous such that implementation would require inventing specification meaning, Executor MUST fail closed and return the blocker through the existing Lead specification-question path. This requirement MUST NOT grant Executor authority to redefine requirements, scope, or task meaning.

#### Scenario: Missing apply context returns to Lead

- GIVEN Executor is routed to `implement-change`
- AND a material approved context/rule required by the configured OpenSpec semantic adapter is unavailable or contradictory
- AND continuing would require Executor to choose specification meaning
- WHEN Executor reconstructs the implementation context
- THEN Executor does not silently omit or invent the missing meaning
- AND the blocker is returned to Lead through the existing specification-question lifecycle

#### Scenario: Complete apply context preserves existing Executor authority boundary

- GIVEN the approved proposal, specs, design, tasks, and applicable config context/rules are available
- WHEN Executor implements the Change
- THEN Executor consumes that complete approved context
- AND existing RED → GREEN → REFACTOR → VERIFY and verified-slice checkpoint semantics remain applicable
- AND Executor gains no authority to redefine the approved contract
