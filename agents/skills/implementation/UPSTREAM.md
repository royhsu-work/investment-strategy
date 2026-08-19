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

Reason: repository quality policy and at-least-once scheduled execution require durable implementation checkpoints and strict role boundaries.

Maintenance implication: preserve these Executor-owned verification and recovery integrations when assessing upstream Apply updates; they are not incidental prose.

## Deleted or omitted responsibilities

- Requirement/specification interpretation beyond the approved context is omitted and owned by Lead.
- Independent implementation acceptance is omitted and owned by `Reviewer / review-implementation`.
- Normal deterministic archive mechanics are omitted and owned by repository automation.

Reason: separation of duties prevents Executor from authoring contract meaning or self-approving implementation/archive transitions.

Maintenance implication: upstream Apply behavior that combines these responsibilities must remain decomposed unless repository governance explicitly changes ownership.

## Modified responsibilities

- Upstream task application is restricted to a reconstructable closed Apply context and verified slice checkpoints.
- Completion is a revision-aware handoff to independent review rather than an implicit end of the workflow.

Reason: scheduled execution must resume safely after interruption and preserve exact-review boundaries.

Maintenance implication: future upstream task/progress semantics must be reconciled with verified-slice durability rather than copied as live progress state.