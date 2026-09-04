---
name: implementation
description: Executor procedure for approved implement-change work using bounded RED-GREEN-REFACTOR-VERIFY slices.
---

# Implementation

Mapped Action: Executor / implement-change.

Reconstruct default-branch governance, the existing Issue/Change/PR, approved OpenSpec context,
independent review-openspec PASS, exact branch/head, Human freshness, and task state. A missing or
contradictory semantic input is a SPEC_BLOCKER routed through the executable model to Lead.

For one bounded slice:

1. RED: add a focused behavioral test and confirm the failure is the intended gap.
2. GREEN: implement the minimum approved behavior.
3. REFACTOR: remove duplication without changing meaning.
4. VERIFY: run focused validation and the complete required gates:
   uv run pytest
   uv run ruff check .
   uv run ruff format --check .
   uv run mypy src tests

Persist task markers and one bounded SLICE_CHECKPOINT/result only after VERIFY succeeds. Results identify
the exact Action, revision, tests, and remaining approved work; they do not carry routing authority.
A later wake fresh-dispatches any successor, including a same-Role successor.

Use content-addressed ingress for semantic file changes: unreferenced blobs plus exact path/blob/current
SHA manifest. The application constructs and verifies the commit/ref. Do not use a write as a probe,
force a ref, bypass Human freshness, or pass file content through Issue comments.

Before READY, make the current implementation PR non-Draft through the repository-supported mutation,
fresh-read the same exact head, and require current independent review readiness. If implementation
discovers a material semantic correction, stop semantic implementation and return SPEC_BLOCKER to Lead
for correction and fresh independent review.

Skill maintenance traceability: implementation consumes approved declarations; it does not claim
semantic review. Executor does not perform semantic bidirectional OpenSpec review.

## Spec-driven semantic adapter

When openspec/config.yaml declares schema: spec-driven, load
agents/skills/openspec-semantic-adapter.md. The adapter is a closed Apply context, not runtime
authority. Strict validation alone does not establish semantic acceptance, even when strict validation
passes. Preserve the approved proposal, applicable delta specs, design, tasks, canonical specs, and
materially applicable config context; do not choose which upstream/config semantics count.

## Completion boundary

When there is no material semantic OpenSpec change, implementation completion routes directly to
Reviewer / review-implementation. A material semantic OpenSpec change routes to Lead / resolve-question
and then Reviewer / review-openspec. The exact-current-head gate and semantic OpenSpec bookkeeping
exception do not weaken exact-head review.

