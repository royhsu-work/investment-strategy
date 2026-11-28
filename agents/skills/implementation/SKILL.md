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

For each behavior, request the existing implement-change MORE_IMPLEMENTATION_REQUIRED envelope
with one application-materialize effect and no formal, readiness, routing or completion effects.
Keep code/test saves separate from task markers and normative OpenSpec. Application derives the
physical-only save and fresh authority from the typed ingress, current Issue/Change/routing/PR/head/main,
review and Human evidence. Read back the exact authorized saved revision W. A pending or failed
candidate is durable work, not formal completion. Never bypass an uncertain/competing write or
assume the physical effect from a CI result.

The semantic Executor does not assume a mutable checkout or shell. Use the existing native quality
resource with exact producer, repository, revision, checkout, run/attempt/job/step evidence. Its
full static-first order is:
   uv run ruff check .
   uv run ruff format --check .
   uv run mypy src tests
   uv run pytest

For Test First, qualify the intended behavioral RED on the saved test-only W after static PASS
before implementing minimum GREEN. Static/setup/unrelated failure is not intended RED. Continue
after a qualified ordinary failure with a lawful same-scope correction; do not overwrite or replay
historical effects, or use a later T PASS as W's verdict. If evidence is pending, perform remaining
lawful work and observe it; at a genuine authority/transport boundary preserve the unfinished work.
Do not create another validation request or semantic result merely to poll.

Independent Implementation Review owns proactive refactoring assessment. Executor implements the
minimum sufficient correct behavior and repairs genuine regressions and substantiated findings.
For affected tests, preserve applicable coverage and record justified replacement or retirement
evidence under the existing config rules.

After VERIFY, request the separate marker-only save when criteria are satisfied, then qualify
the actual marker-bearing head's own gates. Publish a bounded formal result only after the
current authorized task scope, markers and exact applicable gates are qualified. Results identify
the exact Action, revision, task/occurrence and gate/marker evidence; they do not carry routing
authority. A later wake fresh-dispatches any successor, including a same-Role successor.

Use content-addressed ingress for semantic file changes: unreferenced blobs plus exact path/blob/current
SHA manifest. The application constructs and verifies the commit/ref. Do not use a write as a probe,
force a ref, bypass Human freshness, or pass file content through Issue comments.

Before READY, make the current implementation PR non-Draft through the repository-supported mutation,
fresh-read the same exact head, and require current independent review readiness. If implementation
discovers a material semantic correction, stop semantic implementation and return SPEC_BLOCKER to Lead
for correction and fresh independent review.

Skill maintenance traceability: implementation consumes approved declarations; it does not claim
semantic review. Executor does not perform semantic bidirectional OpenSpec review.

## Save, verify, deliver, and resume

1. Reconstruct the approved task plan, current PR/head, code/tests, marker bytes and qualified formal
   occurrences. Select the first not formally delivered scope, or the exact authorized current
   finding/correction scope, even if its marker is checked. Do not select merely by checkbox
   position, a historical checkpoint or an old gate.
2. Save partial work and observe the authorized physical effect using the existing Application/Carrier.
   For each required predecessor verdict, qualify its own exact revision and causal authorization
   before progressing; reuse still-valid work and requalify changed inputs. The original saved W
   remains historical evidence after lawful same-path edits. An unknown or partial effect retains
   original ownership and must be reconciled, not replayed.
3. On full applicable native VERIFY PASS at H and satisfied scope criteria, request a separate
   monotonic marker-only save if markers need updating. No mixed manifest or formal publication.
   Qualify exact gates at actual H'. A qualified ordinary FAIL at H' permits correction of the
   same scope without resetting markers or repeating the settled write. Evidence-only correction
   at the same head needs no no-op commit; content correction uses a new head.
4. On current valid marker bytes, satisfied criteria, exact applicable gates and fresh authority,
   request publication-only READY or MORE_IMPLEMENTATION_REQUIRED with no materialization or
   checkpoint effect. Application derives the exact scope, formal result, necessary effects and
   successor. An unknown/partial publication retains the original accepted obligation; only the
   existing qualified terminal zero-effect invalidation can permit a fresh correction. Do not
   manufacture a formal result or duplicate a historical comment.
5. Checkpoint means saving, not passing or exiting. Continue legitimate same-Action work while
   authority and opportunity remain. Preserve the actual unfinished boundary when a new accepted
   operation requires fresh dispatch or an existing qualified asynchronous/CarrierRequired
   boundary is reached. Never execute a successor in the same wake.

Historical accepted checkpoint/completion effects retain their source-specific authorization and
reconciliation. For the already-accepted #322 implement-change / READY request 6019133874,
absence/unavailability of its old SLICE_CHECKPOINT is not itself a mandatory pre-formal-result
recovery predicate. Independently verify current task/implementation/gate facts and isolate any
potentially irreversible comment write. Do not infer absence, invent the old message, or replay
an unknown effect. This exception does not authorize a new slice or remove formal verification.

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
