---
name: merge-pr
description: Executor procedure shared by exact-head merge-implementation-pr and merge-archive-pr Actions.
---

# Merge PR

Mapped Actions: Executor / merge-implementation-pr and Executor / merge-archive-pr.

This Skill is a shared mechanics package; the explicit Action selects the lifecycle meaning.
Fresh-read the current Issue/Change, exact PR identity, current head, base, non-closing linkage,
independent Reviewer PASS, required checks, Human freshness, and contradictory evidence immediately
before the merge boundary. An open non-Draft PR requires its current exact head. A closed+merged carrier
requires its immutable historical head, merge metadata, exact repositories/base/ref, current
default-branch revision and ancestry, and the matching revision-bound PASS; this is a read-only
idempotent reconciliation path.

For merge-implementation-pr, require review-implementation PASS for exact head and implementation
completion. For merge-archive-pr, additionally require review-archive PASS, archive preparation,
terminal evidence, and known safe cleanup. Never infer the phase from a generic merge label or prose.

Apply only the repository-authorized merge plan through the mutation carrier. For an open PR, require
exact head unchanged immediately before and after the merge write, preserve unrelated labels/content,
and observe the PR merged postcondition. For a closed+merged carrier, send no merge write and instead
freshly observe the exact merged postcondition and metadata. A stale, changed, missing, contradictory,
or ambiguous precondition fails closed. Do not use a write as a probe, reopen or rewrite a carrier,
force a ref, merge a closing linkage, or bypass Human freshness.

Return one structured MERGED, LIFECYCLE_VIOLATION, or BLOCKED result. The executable model derives
finalize-change, finalize-archive, resolve-question, or the bounded same-Action successor; it is
persisted and executed only by a later fresh wake.

The explicit merge Actions use the same persistent coordination Issue and repository-approved
non-closing linkage. A generic merge label never supplies lifecycle meaning.
