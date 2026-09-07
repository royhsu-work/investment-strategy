# Tasks: Restore verified-slice checkpoints for interruption recovery

## Delivery stage 1 — One independently reviewable enforcement correction

Parent-outcome coverage: the complete Human-approved Issue #221 outcome,
including interruption recovery, one-slice boundaries, durable task/checkpoint
ordering, monotonic bookkeeping, lifecycle-gate separation, and workaround
retirement criteria.

N-1 prerequisites: current default-branch Action/result/application boundary,
content-addressed materialization, existing task-only exception, canonical
workflow/message contracts, and the current test/CI harness.

Stage exit criteria: every implementation slice below is verified; exact
OpenSpec/implementation review gates are satisfied; required quality and
validation checks are green; the implementation and archive lifecycle complete
without reducing the approved outcome.

## Slice 1 — Block incomplete implement-change completion effects

Trace: canonical verified-slice/checkpoint contract -> application completion
predicate -> existing typed successor derivation.

- [ ] 1.1 RED: add production-boundary regressions proving an
  `implement-change` `READY` or `MORE_IMPLEMENTATION_REQUIRED` result with no
  complete task/checkpoint effect set cannot derive or persist its successor,
  while incomplete/blocker dispositions retain their existing bounded behavior.
- [ ] 1.2 GREEN: add the smallest completion-boundary predicate to the existing
  effect application path; preserve the current Action/Result vocabulary,
  effect ordering, fresh guards, postconditions, and derived successor model.
- [ ] 1.3 REFACTOR: keep the predicate local to existing application/effect
  ownership and reject duplicate/ambiguous checkpoint effects without adding a
  new state machine or protocol.
- [ ] 1.4 VERIFY: run focused result/effect tests, full pytest, Ruff check,
  Ruff format check, and mypy.

## Slice 2 — Enforce monotonic current-Change task checkpoints

Trace: canonical task-completion boundary -> existing Executor task-only
materialization -> content/postcondition guards.

- [ ] 2.1 RED: add materialization regressions for wording changes,
  add/remove/reorder, `[x] -> [ ]`, stale expected SHA, and a valid
  unchecked-to-checked update.
- [ ] 2.2 GREEN: strengthen the existing task-only materialization guard and
  postcondition to accept only the exact monotonic checkbox-only current-Change
  task update for Executor / `implement-change`.
- [ ] 2.3 REFACTOR: reuse existing content-addressed blobs, PR/ref/head
  identity, idempotent replay, and fail-closed behavior; keep post-merge
  reconciliation separate until its retirement precondition is proven.
- [ ] 2.4 VERIFY: run focused materialization tests and all current quality
  checks against the changed application boundary.

## Slice 3 — Persist the bounded SLICE_CHECKPOINT before continuation

Trace: canonical shared message/checkpoint presentation -> implementation
procedure -> ordered task/checkpoint effects -> typed successor.

- [ ] 3.1 RED: add regressions for missing/ambiguous checkpoint fields, missing
  checkpoint after durable task markers, checkpoint-before-task interruption,
  and replay of an already durable checkpoint.
- [ ] 3.2 GREEN: bind the existing bounded checkpoint comment effect to the exact
  current Change, verified revision, task IDs, VERIFY/gate evidence, and
  remaining approved boundary; require it together with task-only materialization
  before `READY` or `MORE_IMPLEMENTATION_REQUIRED` continuation.
- [ ] 3.3 GREEN: update the existing implementation Skill with the exact
  reconstruct -> first incomplete slice -> RED -> GREEN -> REFACTOR -> VERIFY ->
  task/checkpoint -> result boundary, including recovery after each interruption
  point. Do not add a cursor or progress state.
- [ ] 3.4 VERIFY: run focused application/message/Skill tests, full quality
  checks, and exact current OpenSpec validation required by the changed surface.

## Slice 4 — Keep lifecycle gates out of Executor task semantics

Trace: current OpenSpec authoring owner -> implementation task boundary ->
existing review/merge/archive gates.

- [ ] 4.1 RED: add a focused authoring/regression assertion for task markers that
  depend on Reviewer PASS, merge, archive, or a later lifecycle transition.
- [ ] 4.2 GREEN: add the minimum current-owner task-authoring rule and correct the
  directly applicable approved task representation without changing the
  downstream lifecycle gate.
- [ ] 4.3 REFACTOR: preserve canonical workflow/message ownership and remove only
  the duplicate Executor checkbox representation; do not create a lifecycle
  marker or alternate completion state.
- [ ] 4.4 VERIFY: confirm Proposal/Design/Tasks traceability, strict OpenSpec
  validation, and focused task-authoring/application regressions.

## Slice 5 — Retire the compensating post-merge path after fresh proof

Trace: normal verified-slice enforcement + green regressions + fresh consumer
inventory -> workaround deletion decision.

- [ ] 5.1 RED: add or extend an existing regression proving the normal path does
  not require a post-merge task-marker repair and that no active/legacy consumer
  is silently relied upon by the production application.
- [ ] 5.2 GREEN: after the fresh deletion preconditions are satisfied, remove the
  post-merge task reconciliation branch and its obsolete special-case tests;
  otherwise retain it and record the exact consumer/reason in the bounded result.
- [ ] 5.3 REFACTOR: ensure normal implementation cannot route through a
  post-merge repair path and preserves all existing stale/replay/no-rewind
  safety.
- [ ] 5.4 VERIFY: run the focused regression, full pytest, Ruff check, Ruff
  format check, mypy, and strict OpenSpec validation on the exact head.

## Slice 6 — Final implementation readiness

Trace: all approved vertical slices -> exact current evidence -> existing
implementation handoff.

- [ ] 6.1 VERIFY: fresh-reconstruct every approved slice from tasks.md, current
  PR/head, code/tests/evidence, and bounded checkpoint comments; prove recovery
  resumes at the first incomplete slice and never repeats a verified slice.
- [ ] 6.2 VERIFY: prove no new Action, Result kind, state, cursor, registry,
  carrier, lock, lease, second DAG, validator framework, or #218/#207 scope was
  introduced; confirm downstream lifecycle gates remain independent.
- [ ] 6.3 VERIFY: complete all required exact-head quality/validation checks and
  prepare the existing `READY` result only after every verified slice has its
  durable task/checkpoint boundary.
