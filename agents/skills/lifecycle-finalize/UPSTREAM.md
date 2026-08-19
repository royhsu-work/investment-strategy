# Upstream responsibility provenance

- Upstream repository: `Fission-AI/OpenSpec`
- Upstream Skill path: `skills/openspec-archive-change/`
- Upstream revision: `2826b8889e5223a9a8095d4428b60b56597e1020`
- Local Skill: `agents/skills/lifecycle-finalize/SKILL.md`
- Relationship: decomposition of upstream Archive lifecycle responsibility into Lead lifecycle judgment around repository automation, Reviewer review, and Executor merge.

## Relationship

The local Skill carries the Lead-owned lifecycle decisions surrounding Archive. Deterministic archive mutation is delegated to repository automation; independent Archive verification and merge remain separate owners.

## Added responsibilities

- Post-implementation-merge reconstruction and `MORE_IMPLEMENTATION_REQUIRED` / archive-wait decisions.
- Final Archive PR creation/presentation after validated archive-branch readiness.
- Pre-review follow-up/temporary-recovery preparation and terminal `LIFECYCLE_COMPLETE` reconstruction.

Reason: the repository separates lifecycle judgment from deterministic automation, independent review, and merge mutation.

Maintenance implication: future upstream Archive responsibilities must be mapped to the existing owner boundary before adoption; Lead-only lifecycle preparation remains intentional local behavior.

## Deleted or omitted responsibilities

- Deterministic OpenSpec archive mutation is omitted here and owned by repository GitHub Actions automation.
- Independent Archive acceptance is omitted and owned by `Reviewer / review-archive`.
- Archive PR merge is omitted and owned by `Executor / merge-pr`.

Reason: repository policy deliberately decomposes upstream Archive into automation plus Lead/Reviewer/Executor stages.

Maintenance implication: do not reintroduce a monolithic archive action when refreshing upstream; any changed upstream responsibility must be assigned to its current local owner or explicitly redesigned through governance.

## Modified responsibilities

- Upstream archive completion becomes a multi-stage durable lifecycle with validated branch readiness, final PR review, native close, and terminal reconstruction.
- Lead consumes automation output instead of directly performing archive mechanics.

Reason: scheduled execution needs revision-bound independent gates and reconstructable native-close semantics.

Maintenance implication: compare future upstream archive semantics against the complete decomposed lifecycle, not only this Lead Skill in isolation.