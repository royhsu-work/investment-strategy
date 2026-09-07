---
name: openspec-review
description: Reviewer procedure for independent exact-revision OpenSpec semantic review and gate results.
---

# OpenSpec Review

Mapped Action: Reviewer / review-openspec.

When openspec/config.yaml declares schema: spec-driven, load
agents/skills/skill-creator/SKILL.md, agents/skills/skill-creator/references/repository-governance.md,
and agents/skills/openspec-semantic-adapter.md as procedural input. None of these resources is
runtime authority; Reviewer independence remains with default-branch governance.

Fresh-read the current default branch, Issue/Change/PR, exact proposed revision, canonical specs,
design, tasks, Human input, and exact-R validation. The semantic baseline B is the exact baseline, and the reviewed
target is R; a bookkeeping-only revision does not advance or invalidate B. Mechanical validation
alone does not create semantic acceptance, even when strict validation passes.

Before accepting the proposal, independently reconstruct the current decision boundary from current
Human-approved intent, applicable canonical specs, current default-branch governance/config, and
current repository evidence. Preserve decided outcomes, invariants, constraints, architecture
decisions, safety properties, and scope boundaries. Consume the existing project-wide proportionality
owner (`openspec/specs/repository-governance/spec.md`, referenced by `agents/proportionality.md`);
this reference is not a competing authority.

Apply remove -> reuse -> consolidate -> existing ownership layer before retaining or adding any mechanism.

Review reverse-first and forward traceability:
tasks -> design -> specs -> proposal
proposal -> specs -> design -> tasks
Both directions must be complete before PASS. Check scope, scenarios, safety invariants, design
trade-offs, task traceability, and Skill maintenance traceability. An undeclared material Skill,
differently classified material change, or Formatting drift is a finding. Review material semantic
changes in (B, R] and do not substitute a historical PASS.

If an exact same-Issue Explore result and supporting source/evidence are applicable, dereference and
preserve them before review; this is not a re-run of Explore. Missing, contradictory, stale, or
unqualified evidence is a finding or blocked result.

Reviewer symmetry is an independent predicate. A retained or additional mechanism without an exact
current requirement, concrete safety property, or demonstrated failure mode is an existing
`FINDINGS`. A removal, reuse, consolidation, or existing ownership layer that is sufficient while
a new mechanism remains is also an existing FINDINGS; the executable model routes that result
through `resolve-question`. No new Action, Result, routing state, or review-result type is needed.

Return one structured PASS, FINDINGS, HUMAN_DECISION_REQUIRED, NO_GO, or BLOCKED result with exact
revision and evidence. The executable model derives the next Action; Reviewer does not choose routing,
mutate the repository, or execute a successor.

## Conditional repository Skill composition

When this Action materially creates or modifies a repository Skill, conditionally compose:
`agents/skills/skill-creator/SKILL.md`
and `agents/skills/skill-creator/references/repository-governance.md`.
This repository Skill guidance is procedural input, not runtime authority.

Reviewers must preserve every still-applicable scenario/content when evaluating a MODIFIED requirement.
Successful mechanical OpenSpec validation is not semantic PASS evidence; semantic review remains
independent.

Reviewer semantic uncertainty must fail closed: a missing or contradictory review context cannot be
treated as acceptance.

## Conditional staged-delivery composition

When reviewing a staged OpenSpec plan, load
`agents/skills/openspec-delivery/SKILL.md` as procedural input. Independently check that the reviewed
revision accounts for completed work, current delivery, and mandatory follow-up while preserving this
Action's exact-revision semantic gate and non-mutation boundary.
