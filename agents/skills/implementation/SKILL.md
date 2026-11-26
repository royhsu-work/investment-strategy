---
name: implementation
description: Executor procedure for approved implement-change work using per-behavior Test First and verified slices.
---

# Implementation

Mapped Action: Executor / implement-change.

Reconstruct default-branch governance, the existing Issue/Change/PR, approved OpenSpec context,
independent review-openspec PASS, exact branch/head, Human freshness, and task state. A missing or
contradictory semantic input is a SPEC_BLOCKER routed through the executable model to Lead.

## Respond to implementation review findings

Before editing for a finding, independently check the reviewed revision, the approved requirement or
invariant, the current delivery stage, and the evidence. Fix confirmed defects within the approved
scope using the smallest sufficient change. Verify the expected behavior with the original
counterexample or equivalent evidence. When the evidence is insufficient or contradicted, record the
reason and available evidence for independent re-review. When the resolution requires a material
semantic or scope change, return the existing SPEC_BLOCKER to Lead.

Use the existing review evidence to record each disposition. Treat proposed fixes and advisory
comments as inputs to engineering judgment. A finding does not grant authority to expand the
approved scope, and Executor does not clear the review gate. Preserve required later-stage
acceptance at its applicable gate.

## Implement one bounded slice

For executable feature or defect-correction behavior, load `agents/skills/tdd/SKILL.md` and use its
one-behavior RED/GREEN loop. For material changes to Skill or procedural decisions without new
executable behavior, evaluate fixed discriminating inputs before and after, recording actual
decisions and consulted source revisions. Do not claim executable RED for such evaluation.
Ordinary wording-only documentation changes do not require semantic evaluation.

VERIFY the slice using focused evidence and the complete required gates:
   uv run pytest
   uv run ruff check .
   uv run ruff format --check .
   uv run mypy src tests

The semantic Executor does not assume a mutable checkout or shell. Use repository-supported CI
evidence from the exact relevant revisions for executable behavior. Submit complete candidate
source/tests as content-addressed blobs for existing repository-owned candidate verification.
Only after the required checks and fresh Issue/Change/routing/PR/head/main, review, and Human
reauthorization observations may application persist `APPLICATION_DECISION: ACCEPTED` and
materialize the already-verified blobs. A verifier failure before ACCEPT leaves zero authoritative
repository consequence; it is not repaired by pushing a broken candidate. If a required evidence
path is unavailable, use the existing governed blocker path.

Independent Implementation Review owns proactive refactoring assessment. Executor implements the
minimum sufficient correct behavior and repairs genuine regressions and substantiated findings.
For affected tests, preserve applicable coverage and record justified replacement or retirement
evidence under the existing config rules.

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

## Verified-slice checkpoint boundary

Every fresh `Executor / implement-change` invocation reconstructs current recovery truth from
`tasks.md`, the current implementation PR/head, and current code/tests/evidence. It identifies the
first incomplete slice and executes exactly one bounded slice using the applicable behavior or
semantic evaluation procedure followed by VERIFY.

After VERIFY succeeds, persist task markers first and then one bounded SLICE_CHECKPOINT containing
the exact Change, verified revision, completed task IDs, gate evidence, and remaining approved
boundary. The checkpoint obligation must be durable before READY or MORE_IMPLEMENTATION_REQUIRED is
emitted, before continuation or handoff, or before application derives a successor.

If interruption occurs before implementation, task, or checkpoint durability, the next fresh wake
reconstructs current truth and satisfies only the missing effect. It must never redo a verified slice,
does not create a cursor or progress state, and resumes the first incomplete slice. A verified slice
is not repeated merely to recreate missing evidence.

Historical #322 exception (not a new Executor invocation): for the already-accepted
`implement-change / READY` decision on request `6019133874`, a missing/unreadable old
`SLICE_CHECKPOINT` is not retroactively manufactured or replayed as a prerequisite to
*pre-formal-result recovery qualification*. The application must independently verify current
task/implementation/gate facts, and must isolate any potentially irreversible checkpoint
write before an operation that could repeat it. This exception does not certify that the
historical checkpoint happened, authorize a new slice, remove required task verification,
or relax this checkpoint obligation for any later fresh Executor invocation.

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


## Spec-driven semantic adapter

When openspec/config.yaml declares schema: spec-driven, load agents/skills/openspec-semantic-adapter.md.
The adapter is a closed Apply context, not runtime authority. Missing or contradictory context fails
closed. Do not choose which upstream/config semantics count.

When there is no material semantic OpenSpec change, implementation completion routes directly to
Reviewer / review-implementation. A material semantic OpenSpec change routes to Lead / resolve-question
and then Reviewer / review-openspec. The exact-current-head gate and semantic OpenSpec bookkeeping
exception do not weaken exact-head review.
## Conditional repository Skill composition

When this Action materially creates or modifies a repository Skill, conditionally compose:
`agents/skills/skill-creator/SKILL.md`
and `agents/skills/skill-creator/references/repository-governance.md`.
This repository Skill guidance is procedural input, not runtime authority.

The closed Apply context includes approved proposal, applicable delta specs, approved design, approved tasks, canonical specs needed to interpret modified behavior, and materially applicable default-branch `openspec/config.yaml` context/rules. Executor is not responsible for choosing which upstream/config semantics count; missing or contradictory context fails closed.

The closed Apply context does not grant Executor specification authority. Choosing which upstream/config semantics count remains a Lead semantic decision; uncertainty is routed to `Lead / resolve-question`.

Executor must fail closed when semantic context is incomplete.
