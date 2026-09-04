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
design, tasks, Human input, and exact-R validation. The exact semantic baseline is B and the reviewed
target is R; a bookkeeping-only revision does not advance or invalidate B. Mechanical validation
alone does not create semantic acceptance, even when strict validation passes.

Review reverse-first and forward traceability:
tasks -> design -> specs -> proposal
proposal -> specs -> design -> tasks
tasks → design → specs → proposal
proposal → specs → design → tasks
Both directions must be complete before PASS. Check scope, scenarios, safety invariants, design
trade-offs, task traceability, and Skill maintenance traceability. An undeclared material Skill,
differently classified material change, or Formatting drift is a finding. Review material semantic
changes in (B, R] and do not substitute a historical PASS.

If an exact same-Issue Explore result and supporting source/evidence are applicable, dereference and
preserve them before review; this is not a re-run of Explore. Missing, contradictory, stale, or
unqualified evidence is a finding or blocked result.

Return one structured PASS, FINDINGS, HUMAN_DECISION_REQUIRED, NO_GO, or BLOCKED result with exact
revision and evidence. The executable model derives the next Action; Reviewer does not choose routing,
mutate the repository, or execute a successor.
The semantic baseline B is the last independently accepted meaning; review target R includes all material semantic changes in (B, R]. Mechanical validation alone does not create semantic acceptance, even when strict validation passes.

## Conditional repository Skill composition

When this Action materially creates or modifies a repository Skill, conditionally compose:
`agents/skills/skill-creator/SKILL.md`
and `agents/skills/skill-creator/references/repository-governance.md`.
This repository Skill guidance is procedural input, not runtime authority.

Reviewers must preserve every still-applicable scenario/content when evaluating a MODIFIED requirement. Successful mechanical OpenSpec validation is not semantic PASS evidence; semantic review remains independent.

Reviewer semantic uncertainty fails closed; a missing or contradictory review context cannot be treated as acceptance.

Reviewer must fail closed when semantic context is incomplete.
