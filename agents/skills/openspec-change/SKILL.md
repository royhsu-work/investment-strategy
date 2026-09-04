---
name: openspec-change
description: Lead procedure for authoring or correcting an existing OpenSpec Change through bounded semantic Actions.
---

# OpenSpec Change

Mapped Actions: Lead / propose-change and Lead / resolve-question.

Read current default-branch governance, the existing Issue/Change/PR, Human intent, applicable canonical
specs, openspec/config.yaml, and exact validation evidence before editing. The existing Change is the
single semantic vehicle for #138; do not create a duplicate Change or PR.

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

Skill maintenance traceability: Lead owns the declaration of materially affected Skills, their
responsibility treatment, source/reference, rationale, and replacement. Reviewer independently checks
the declaration; implementation does not reinterpret it.

## Spec-driven semantic adapter

When openspec/config.yaml declares schema: spec-driven, load
agents/skills/openspec-semantic-adapter.md. The adapter is a closed Apply context, not runtime
authority. Strict validation alone does not establish semantic acceptance, even when strict validation
passes. Preserve the approved proposal, applicable delta specs, design, tasks, canonical specs, and
materially applicable config context; do not choose which upstream/config semantics count.
