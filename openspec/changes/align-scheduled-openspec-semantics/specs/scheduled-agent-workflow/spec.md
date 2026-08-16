# scheduled-agent-workflow Delta Specification

## ADDED Requirements

### Requirement: Scheduled roles preserve material OpenSpec semantics when CLI instructions are unavailable

When a Scheduled role performs an OpenSpec action in an execution environment that cannot obtain material schema/artifact/action semantics from the OpenSpec CLI, the repository SHALL provide one accessible shared semantic adapter for the currently configured OpenSpec schema rather than allowing each role to infer or independently duplicate those semantics.

For the current `schema: spec-driven` configuration, the adapter MUST represent the exact material semantics below, derived from the declared immutable upstream baseline `Fission-AI/OpenSpec@2826b8889e5223a9a8095d4428b60b56597e1020` `schemas/spec-driven/schema.yaml` and adapted by repository policy:

1. **Artifact dependency/readiness contract**
   - `proposal` has no artifact prerequisite.
   - `specs` requires `proposal`.
   - `design` requires `proposal`.
   - `tasks` requires both `specs` and `design`.
   - Apply requires `tasks` and tracks `tasks.md`.
   - Proposal capability declarations define which delta specs must exist; zero-delta changes are legal only when the Change explicitly opts out with `skip_specs: true` because no spec-level behavior changes.
   - Scheduled roles MUST treat these dependencies as authoring/consumption prerequisites, not as a second runtime routing DAG.

2. **Artifact and config-rule consumption contract**
   - Proposal authoring consumes current repository context plus applicable proposal rules from default-branch `openspec/config.yaml` and must research existing canonical specs before declaring new/modified capabilities.
   - Specs consume the proposal capability declaration, applicable canonical `openspec/specs/*`, and applicable spec rules from `openspec/config.yaml`.
   - Design consumes the proposal plus applicable specs and design rules; material questions that would change specs, approach, or task breakdown are not deferrable implementation choices.
   - Tasks consume specs plus design and applicable task rules; tasks are checkbox work items whose meaning comes from approved specs/design, not from Executor inference.
   - When a material applicable `openspec/config.yaml` context/rule cannot be determined or represented by the adapter, the affected action MUST fail closed rather than omit it.

3. **Delta-authoring contract**
   - `ADDED Requirements` contains only new requirement blocks, each complete and scenario-bearing; an ADDED header MUST NOT collide with an existing canonical requirement header.
   - `MODIFIED Requirements` uses the exact existing canonical requirement header after whitespace normalization and case-sensitive comparison, and MUST contain the complete future requirement block: requirement text plus every existing scenario/content that still survives the change, plus any intended additions or edits. Partial MODIFIED blocks that silently drop surviving canonical scenarios/content are invalid.
   - `REMOVED Requirements` identifies an existing canonical requirement and MUST record the removal rationale and migration/transition treatment required by the configured schema; removed content is not re-expressed as a partial MODIFIED block.
   - `RENAMED Requirements` is used only for identifier/name changes and MUST declare exact `FROM` and `TO` headers. If behavior/content also changes, the rename is declared and the complete modified requirement is authored under the NEW header.
   - Requirement headers are identifiers for matching; duplicate or ambiguous identifiers fail closed.
   - Every requirement MUST have at least one `#### Scenario:` block using the configured scenario format and normative SHALL/MUST behavior.

4. **Canonicalization-readiness contract**
   - A delta for a NEW capability MUST contain exactly one non-empty `## Purpose` that is sufficient to seed the canonical spec; a missing/blank/generated-placeholder Purpose MUST fail before implementation handoff even if strict validation otherwise passes.
   - A delta for an EXISTING capability MUST NOT invent a second Purpose as part of ordinary requirement modification; current canonical Purpose remains authoritative unless the Change explicitly and lawfully modifies that canonical content under repository rules.
   - Lead and Reviewer MUST verify that every MODIFIED/REMOVED/RENAMED target exists in the applicable canonical spec and every ADDED target is genuinely new, so later Sync/Archive does not become the first semantic matcher.
   - Canonicalization applies rename, removal, modification, and addition semantics without discarding untouched canonical requirements/scenarios/content. Archive remains deterministic defense-in-depth, not the intended first detector for knowable authoring omissions.

5. **Apply context contract**
   - Executor MUST consume the approved proposal, applicable delta specs, design, tasks, current canonical specs needed to interpret modified behavior, and materially applicable default-branch `openspec/config.yaml` context/rules.
   - Executor works only pending approved tasks, preserves completed task meaning, and MUST stop/return to Lead when required context is missing, contradictory, or materially ambiguous.
   - Executor MUST NOT choose which upstream/config semantics are important, invent omitted requirements, resolve material design/spec ambiguity, or reinterpret task meaning to keep implementation moving.

6. **Semantic-baseline provenance contract**
   - The adapter MUST record the immutable upstream source commit/path used for each represented semantic family and the repository executable baseline observed when adopted.
   - A later schema change or material upstream semantic change MUST trigger deliberate adapter reassessment; absence of representable semantics fails closed rather than falling back to model memory or current upstream `main`.

The adapter MUST be consumed together with current default-branch `openspec/config.yaml`, applicable canonical specs, current Change artifacts, and applicable durable source decisions. It MUST NOT become a second workflow DAG, a replacement for canonical capability specs, a generic OpenSpec schema engine, or authority for role/routing decisions.

If the repository's configured schema or a material required semantic input cannot be represented by the current adapter, the affected Scheduled action MUST fail closed until the semantic contract is deliberately updated. Deterministic CLI mechanics and exact-revision strict validation MAY remain owned by repository automation and MUST NOT be copied into hidden Agent state.

#### Scenario: Scheduled Propose consumes the configured semantic adapter

- GIVEN the repository is configured with `schema: spec-driven`
- AND Lead cannot execute the OpenSpec CLI instruction/status commands in the Scheduled environment
- WHEN Lead performs `propose-change`
- THEN Lead consumes the shared spec-driven semantic adapter together with current `openspec/config.yaml`, applicable canonical specs, current durable source decisions, and the Change artifacts being authored
- AND Lead applies the exact artifact dependency, config-rule, delta-authoring, and canonicalization-readiness contract above
- AND material semantics are not selected by Executor or inferred from memory

#### Scenario: Unsupported semantic contract fails closed

- GIVEN the configured OpenSpec schema or a material semantic input required by the current action is not represented by the shared adapter
- WHEN a Scheduled role attempts an affected OpenSpec action
- THEN the role does not infer the missing semantics from familiar artifact names, current upstream `main`, or prior memory
- AND the action fails closed until the adapter/configuration contract is deliberately reconciled

#### Scenario: Semantic adapter does not become a second authority source

- GIVEN the shared adapter describes procedural OpenSpec semantics for Scheduled roles
- WHEN runtime routing or approved capability behavior is reconstructed
- THEN `agents/AGENTS.md` remains authoritative for Scheduled runtime protocol
- AND canonical `openspec/specs/*` remain authoritative for approved capability requirements
- AND the adapter does not override either authority surface

#### Scenario: Artifact dependency contract is deterministic

- GIVEN a `spec-driven` Change has proposal/specs/design/tasks artifacts
- WHEN a Scheduled role evaluates readiness for the next OpenSpec responsibility
- THEN it uses proposal → specs and proposal → design, then specs + design → tasks, and tasks → Apply as the represented dependency contract
- AND it does not invent a different dependency graph from artifact names or local convenience

#### Scenario: Complete MODIFIED requirement preserves surviving scenarios

- GIVEN canonical requirement R contains scenarios S1 and S2
- AND a Change modifies R while S1 remains applicable and S2 is intentionally changed
- WHEN Lead authors the MODIFIED block
- THEN the block contains the complete future R including surviving S1 and the intended future form of S2
- AND omission of a still-applicable canonical scenario is a semantic authoring defect before implementation

#### Scenario: Rename plus behavior change is explicit

- GIVEN canonical requirement `Old Name` must become `New Name`
- AND its behavior also changes
- WHEN Lead authors the delta
- THEN `RENAMED Requirements` declares `FROM: Old Name` and `TO: New Name`
- AND `MODIFIED Requirements` contains the complete future requirement under `New Name`
- AND Executor is not asked to infer whether a renamed block also changes behavior

### Requirement: OpenSpec authoring and independent review prevent knowable canonicalization omissions

Before a newly authored or materially revised OpenSpec Change is handed to implementation, Lead and independent Reviewer SHALL each consume the applicable shared OpenSpec semantic adapter and SHALL prevent material semantic information already knowable for later Sync/Archive/canonicalization from escaping the Propose/OpenSpec-review boundary.

Lead SHALL author the required artifact information and applicable project/artifact-rule content before review handoff. Reviewer SHALL independently verify the same applicable semantic completeness/coherence in addition to the existing reverse-first plus forward traceability and exact-revision validation gates.

Reviewer PASS requires independently checking the adapter's artifact dependency/readiness contract, applicable config/rule consumption, complete delta operation semantics, canonicalization-readiness, and fail-closed boundaries against the reviewed artifacts. Reviewer MUST return `FINDINGS` when any of those semantics would otherwise be left for Executor or Archive to invent/discover.

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

#### Scenario: Reviewer rejects partial MODIFIED content

- GIVEN a canonical requirement contains still-applicable scenarios/content
- AND the Change's MODIFIED block omits some of that surviving content
- WHEN Reviewer independently evaluates semantic completeness
- THEN Reviewer records `FINDINGS` before implementation
- AND the omission is not deferred to Executor or Archive interpretation

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
- AND existing RED → GREEN → REFACTOR → VERIFY and verified-slice checkpoint semantics remain applicable
- AND Executor gains no authority to redefine the approved contract
