# Upstream responsibility provenance

- Upstream repository: `Fission-AI/OpenSpec`
- Upstream Skill path: `skills/openspec-apply-change/`
- Upstream revision: `2826b8889e5223a9a8095d4428b60b56597e1020`
- Local Skill: `agents/skills/implementation/SKILL.md`
- Relationship: semantic adaptation of upstream Apply into the repository Executor implementation action.

## Relationship

The local Skill preserves the upstream Apply responsibility of implementing approved tasks from the OpenSpec artifact set. It narrows that responsibility to Executor-owned mutations under an independently approved, closed Apply context.

## Added responsibilities

- RED→GREEN→REFACTOR→VERIFY vertical-slice execution and verified task/checkpoint persistence.
- Exact CI/OpenSpec evidence handling, constrained branch-integration recovery, and Draft-to-Ready ownership.
- Explicit routing to Lead when implementation would require new specification meaning.
- Consumption of the repository-owned substantive Human-input freshness/disposition invariant immediately before implementation `READY` and review handoff.

Reason: repository quality policy and at-least-once scheduled execution require durable implementation checkpoints, strict role boundaries, and prevention of READY/handoff from silently skipping newer material Human input.

Maintenance implication: preserve these Executor-owned verification, recovery, and consequential-boundary integrations when assessing upstream Apply updates; they are not incidental prose. The Human-input classifier itself remains owned by shared repository governance rather than this Skill.

## Deleted or omitted responsibilities

- Requirement/specification interpretation beyond the approved context is omitted and owned by Lead.
- Independent implementation acceptance is omitted and owned by `Reviewer / review-implementation`.
- Normal deterministic archive mechanics are omitted and owned by repository automation.

Reason: separation of duties prevents Executor from authoring contract meaning or self-approving implementation/archive transitions.

Maintenance implication: upstream Apply behavior that combines these responsibilities must remain decomposed unless repository governance explicitly changes ownership.

## Modified responsibilities

- Upstream task application is restricted to a reconstructable closed Apply context and verified slice checkpoints.
- Completion is a revision-aware handoff to independent review rather than an implicit end of the workflow.
- Completion now consumes shared current coordination-Issue Human-input freshness/disposition evidence before `READY`; the Skill does not independently define provenance classification or Human authority.

Reason: scheduled execution must resume safely after interruption, preserve exact-review boundaries, and avoid consuming stale completion assumptions after newer material Human input.

Maintenance implication: future upstream task/progress semantics must be reconciled with verified-slice durability and the repository-owned consequential-boundary invariant rather than copied as live progress or duplicated classifier state.