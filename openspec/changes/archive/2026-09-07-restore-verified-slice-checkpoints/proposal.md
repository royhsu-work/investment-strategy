# Change: Restore verified-slice checkpoints for interruption recovery

## Why

Issue #221 identifies a current consumption/enforcement defect, not a missing
checkpoint requirement. The canonical `scheduled-agent-workflow` contract already
defines the verified slice as the interruption-recovery boundary:

```text
verified slice
-> durable task/checkpoint evidence
-> interruption
-> reconstruct current truth
-> resume the first incomplete slice
```

The current default branch preserves the right ownership split. `tasks.md`, the
implementation PR/head, and current code/tests/evidence are the durable recovery
truth. `SLICE_CHECKPOINT` is bounded completion-boundary audit evidence. Issue
lifecycle, immutable Change, `action:*`, review PASS, merge, and archive remain on
their existing surfaces.

The defect is that the existing application boundary accepts a typed
`implement-change` result and derives its successor without requiring the result's
verified-slice checkpoint obligation to be present and durably observed. The
existing post-merge task reconciliation then compensates for that divergence.

## What Changes

- Add the smallest application-level completion predicate at the existing
  `requested effect -> guard -> mutation -> durable postcondition -> derived
  successor` boundary. Existing `MORE_IMPLEMENTATION_REQUIRED` and `READY`
  results from `implement-change` may derive a successor only after one exact
  task-marker checkpoint materialization and one bounded `SLICE_CHECKPOINT`
  evidence effect have both passed their existing postcondition checks.
- Reuse Candidate A: materialize one implementation slice on the existing PR,
  verify its exact implementation head, then use the existing task-only
  `tasks.md` materialization capability plus one bounded checkpoint comment.
  Do not widen the capability to a mixed implementation/task carrier unless
  fresh implementation evidence proves this existing path insufficient.
- Strengthen the existing Executor task-only materialization guard so its
  content is monotonic, checkbox-only, current-Change-bound, and semantic-neutral.
  Reject wording changes, task additions/removals/reordering, unchecking,
  stale/ambiguous expected content, and unrelated OpenSpec mutation.
- Keep `SLICE_CHECKPOINT` as audit/observability evidence, not routing state, a
  recovery cursor, or a comment progress database. Reuse current effect,
  materialization, typed-result, idempotent replay, and exact-postcondition
  machinery.
- Add the minimum task-authoring rule at the current OpenSpec authoring owner so
  Executor task markers contain only work Executor can implement and VERIFY.
  Reviewer PASS, merge, archive, and lifecycle transitions remain on their
  existing lifecycle surfaces and are not implementation task markers.
- Retain the current post-merge task reconciliation only as a compensating
  migration/recovery path during this Change. Delete it, with obsolete special
  cases and tests, only after the normal checkpoint path is active on `main`,
  focused regressions are green, and fresh evidence shows no active or legacy
  consumer still requires it.

## Capabilities and ownership

### Modified capabilities

- `scheduled-agent-workflow`: no new canonical requirement is proposed; the
  current verified-slice and bounded checkpoint contract is consumed and enforced.
- Existing repository application/materialization and implementation procedure:
  enforce the already-canonical completion boundary.

`openspec/specs/scheduled-agent-workflow/spec.md` remains the canonical workflow
owner. `agents/templates/messages.md` remains the canonical message presentation
owner. The executable Action model, existing Result vocabulary, routing topology,
and application-owned successor derivation remain unchanged.

## Candidate comparison

### Candidate A — existing task-only checkpoint (selected)

```text
implementation materialization
-> exact-head VERIFY
-> current-Change tasks.md checkbox checkpoint
-> bounded SLICE_CHECKPOINT comment
-> durable postconditions
-> existing typed successor
```

This reuses the existing task-only Executor exception, content-addressed manifest,
PR/head guards, and postcondition machinery. If the task-only materialization or
comment is interrupted, a later fresh `implement-change` wake re-observes current
PR/tasks/evidence and completes only the missing effect. No later slice or handoff
is authorized until both effects are durable.

### Candidate B — combined implementation and task checkpoint

This would widen one materialization manifest to mix implementation paths with
`tasks.md`, while adding rules that distinguish implementation changes from
monotonic task bookkeeping in the same commit. Under current exact-head and
OpenSpec validation semantics it adds a new mixed-manifest classification and a
larger stale/replay surface. Current evidence does not establish that widening the
existing path is necessary, so it is not selected.

## Recovery and scope boundary

- Before implementation materialization: reconstruct the first incomplete slice
  and execute only that bounded slice.
- After implementation materialization but before VERIFY: re-read the exact PR
  head and verification evidence; do not mark tasks or claim a completed slice.
- After VERIFY but before task/checkpoint persistence: keep the same
  `implement-change` source and satisfy only the missing checkpoint obligation;
  do not redo verified implementation.
- After checkpoint persistence but before typed-result/successor persistence:
  replay only still-missing idempotent effects and let the application derive the
  existing successor after fresh postcondition observation.

This Change adds no Action, Result kind, routing state, cursor, registry,
checkpoint carrier, lock, lease, heartbeat, second DAG, orchestration layer, or
validator framework. It does not absorb #207's decision-boundary scope, #218's
Role/Workflow SSOT scope, or #180's staged-delivery scope.

## Evidence

- Current main at `b4fe2d00156ad3ec358b35dc15948380cec7930e`.
- Canonical checkpoint requirements in
  `openspec/specs/scheduled-agent-workflow/spec.md`, especially the verified
  vertical-slice and bounded coordination-Issue checkpoint requirements.
- Current application source in
  `scheduled_agent_effects.py`,
  `scheduled_agent_application_materialization.py`, and
  `scheduled_agent_validation_resource.py`.
- #25 comment `issuecomment-5275043326` (2026-08-13) records the Human-approved
  verified-slice checkpoint contract.
- #138 comment `issuecomment-5470121673` (2026-08-30) records the historical
  separation between executable semantics and the deployed application path.
- #169 comments `issuecomment-5553133600` and `issuecomment-5553177372`
  (2026-09-05) record the Executor task-bookkeeping capability collision and
  later repair.
- #180 comments `issuecomment-5562036607` and `issuecomment-5562297534`
  (2026-09-06) record post-merge task reconciliation.
- #207 comments `issuecomment-5565142337`, `issuecomment-5565198285`,
  `issuecomment-5565721662`, `issuecomment-5565975253`, and
  `issuecomment-5566106566` (2026-09-07) record the exact READY/review/merge
  divergence, partial then bulk task-marker repair, and eventual all-18-checked
  end state.

## Acceptance boundary

The Change is complete only when fresh exact-head evidence proves:

1. A completed `implement-change` result lacking the required task/checkpoint
   effects cannot persist its derived successor.
2. The chosen task-only path accepts only monotonic, current-Change,
   checkbox-only updates and observes the exact postcondition.
3. One bounded slice reaches exact VERIFY before its checkpoint; a later wake
   reconstructs the first incomplete slice without a second recovery state.
4. A durable `SLICE_CHECKPOINT` identifies the completed task IDs, verified
   revision, VERIFY/gate evidence, and remaining approved boundary without
   becoming workflow state.
5. Reviewer PASS, merge, archive, and lifecycle completion remain independent
   lifecycle evidence and are not Executor task markers.
6. The post-merge reconciliation is removed only after its fresh deletion
   preconditions are satisfied, or is explicitly retained with evidence of an
   active legacy consumer.
7. Focused application/materialization/result regressions and all required
   quality gates are green; no new Action, Result, state, carrier, or framework
   exists.
