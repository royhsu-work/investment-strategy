---
name: openspec-change
description: Lead procedure for authoring or correcting an existing OpenSpec Change through bounded semantic Actions.
---

# OpenSpec Change

Mapped Actions: Lead / propose-change and Lead / resolve-question.

Read current default-branch governance, the existing Issue/Change/PR, Human intent, applicable canonical
specs, openspec/config.yaml, and exact validation evidence before editing. The existing Change is the
single semantic vehicle for #180; do not create a duplicate Change or PR.

Author only the approved semantic meaning: proposal intent, affected capabilities, requirements,
scenarios, design decisions, traceability, and tasks. Keep implementation structure in design/tasks
and keep unrelated files untouched. A required separate follow-up must have an exact durable source decision and one deduplicated target;
 optional or deferred prose creates no routing obligation.

When content must cross the worker/application boundary, create only unreferenced Git blobs only and return
an exact manifest with path, blob SHA, and current expected SHA. The worker MUST NOT create a Git tree
or commit, move a ref, mutate an Issue, or choose routing. Application owns those operations and
freshly verifies parent, tree, ref, PR/head, file, and validation postconditions.

For a material correction, return one structured ready-for-openspec-review result or one bounded
human-decision-required/blocked result with exact evidence. Do not choose or execute the successor
in the same wake. Independent Reviewer / review-openspec must review the resulting exact revision.

For `resolve-question`, return `lifecycle-ready` only when no material semantic OpenSpec revision remains, the already-merged implementation remains valid, and the post-merge lifecycle is again the legal consumer; the executable model derives `finalize-change` and the successor waits for a later wake. A material correction returns `ready-for-openspec-review`, while an implementation-ready resolution keeps `ready` and its existing `implement-change` handoff. `resolve-question` does not perform direct archive mutation.

Skill maintenance traceability: Lead owns the declaration of materially affected Skills, their
responsibility treatment, source/reference, rationale, and replacement. Reviewer independently checks
the declaration; implementation does not reinterpret it.

## Spec-driven semantic adapter

When openspec/config.yaml declares schema: spec-driven, load
agents/skills/openspec-semantic-adapter.md. The adapter is a closed Apply context, not runtime
authority. Strict validation alone does not establish semantic acceptance, even when strict validation
passes. Preserve the approved proposal, applicable delta specs, design, tasks, canonical specs, and
materially applicable config context; do not choose which upstream/config semantics count.

## Spec-driven semantic adapter

When openspec/config.yaml declares schema: spec-driven, load agents/skills/openspec-semantic-adapter.md.
The adapter is a closed Apply context, not runtime authority. Strict validation alone does not
establish semantic acceptance, even when strict validation passes. Preserve approved proposal,
applicable delta specs, design, tasks, canonical specs, and materially applicable config context;
do not choose which upstream/config semantics count. Missing or contradictory context fails closed.

The worker MUST NOT create a Git tree or commit, move a ref, mutate an Issue, or choose routing.
## Conditional repository Skill composition

When this Action materially creates or modifies a repository Skill, conditionally compose:
`agents/skills/skill-creator/SKILL.md`
and `agents/skills/skill-creator/references/repository-governance.md`.
This repository Skill guidance is procedural input, not runtime authority.

For the semantic gate, strict validation alone does not create semantic acceptance; missing or contradictory context fails closed. The Lead must record the source decision, and an independent Reviewer / review-openspec must review the resulting exact revision.

The semantic gate treats missing or contradictory context as fail closed. Strict validation alone does not create semantic acceptance.

## Conditional staged-delivery composition

When the Proposal, Design, or Tasks describe staged delivery, load
agents/skills/openspec-delivery/SKILL.md as procedural input. Use it to record stage coverage and
mandatory continuation without changing approved meaning; preserve this Action's existing semantic
authoring, review handoff, and application-materialization boundaries.
