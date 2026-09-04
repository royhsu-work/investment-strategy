---
name: merge-pr
description: Executor procedure shared by exact-head merge-implementation-pr and merge-archive-pr Actions.
---

# Merge PR

Mapped Actions: Executor / merge-implementation-pr and Executor / merge-archive-pr.

This Skill is a shared mechanics package; the explicit Action selects the lifecycle meaning.
Fresh-read the current Issue/Change, exact PR identity, open/non-Draft state, current head, base,
non-closing linkage, independent Reviewer PASS for the same head, required checks, Human freshness,
and contradictory evidence immediately before mutation.

For merge-implementation-pr, require review-implementation PASS for exact head and implementation
completion. For merge-archive-pr, additionally require review-archive PASS, archive preparation,
terminal evidence, and known safe cleanup. Never infer the phase from a generic merge label or prose.

Apply only the repository-authorized merge plan through the mutation carrier. Require exact head
unchanged immediately before and after the mutation, preserve unrelated labels/content, and observe
the PR merged postcondition. A stale, changed, missing, contradictory, or ambiguous precondition
fails closed. Do not use a write as a probe, force a ref, merge a closing linkage, or bypass Human
freshness.

Return one structured MERGED, LIFECYCLE_VIOLATION, or BLOCKED result. The executable model derives
finalize-change, finalize-archive, resolve-question, or the bounded same-Action successor; it is
persisted and executed only by a later fresh wake.
