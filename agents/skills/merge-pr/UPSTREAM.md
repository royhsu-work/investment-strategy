# Upstream responsibility provenance

- Upstream repository: `Fission-AI/OpenSpec`
- Upstream Skill path: `skills/openspec-archive-change/`
- Upstream revision: `2826b8889e5223a9a8095d4428b60b56597e1020`
- Local Skill: `agents/skills/merge-pr/SKILL.md`
- Relationship: repository-specific decomposition of the upstream Archive completion responsibility into an Executor-owned merge mutation shared with implementation merges.

## Relationship

For the Archive path, this local Skill carries only the final accepted PR merge and predeclared safe cleanup portion of the broader upstream Archive responsibility. It also serves implementation merges, which is a repository-original operational composition rather than an upstream Archive behavior.

## Added responsibilities

- Exact-head Reviewer PASS/current-check/linkage reconstruction before any merge mutation.
- Shared implementation/Archive PR merge operation with target-specific preconditions.
- Crash-safe merge recovery, causal-descendant consumption guards, and reviewed pre-close temporary-branch cleanup.
- Consumption of the repository-owned substantive Human-input freshness/disposition invariant immediately before unsafe merge mutation.

Reason: repository merge mutation is isolated under Executor, must be safely reconstructable across interrupted scheduled runs, and must not consume an older accepted snapshot while newer material Human input changes the mutation assumptions.

Maintenance implication: preserve exact acceptance, recovery, and consequential-boundary safeguards when upstream Archive changes; implementation-merge composition remains repository-owned and must be assessed separately from upstream Archive semantics. The shared Human-input classifier remains owned by `agents/AGENTS.md`.

## Deleted or omitted responsibilities

- Archive artifact generation is omitted and owned by repository automation.
- Lifecycle preparation/final Archive PR creation and terminal finalization are omitted and owned by Lead.
- Independent Archive acceptance is omitted and owned by Reviewer.

Reason: merge mutation must not absorb specification/lifecycle judgment or independent review authority.

Maintenance implication: future upstream Archive behavior that combines mutation and judgment must stay decomposed unless repository governance explicitly changes the role boundary.

## Modified responsibilities

- Upstream archive completion is represented here only as merging an already prepared and independently accepted exact Archive PR revision.
- Completion after merge becomes a durable handoff/native-close reconstruction boundary rather than final lifecycle judgment by the merger.
- Merge preconditions additionally consume shared current coordination-Issue Human-input freshness/disposition evidence without defining a new approval or Human-authority token.

Reason: repository lifecycle uses PR review, native closing linkage, Lead terminal reconstruction, and fresh contradictory-evidence checks as separate safety boundaries.

Maintenance implication: compare future upstream completion semantics against all Archive owners (`lifecycle-finalize`, `archive-review`, `merge-pr`, automation), not this Skill alone.