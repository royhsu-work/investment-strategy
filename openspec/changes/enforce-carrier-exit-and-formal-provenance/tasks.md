# Tasks: Enforce carrier invocation exit and formal transition provenance

## Delivery stage 1 — One independently reviewable corrective implementation

Parent-outcome coverage: the complete unchanged #221 outcome and the exact
Human-approved minimal repair direction in
`issuecomment-5575078000` and `issuecomment-5578787305`. This includes
repository-owned formal correctness, the carrier hard-exit boundary, fresh
post-carrier reconstruction, no replay of verified slices, first-incomplete
slice recovery, narrow active-state provenance, bounded connector ingress,
and preservation of all existing checkpoint and lifecycle gates.

N-1 prerequisites: current default-branch executable Action/Role/transition
model; current application authorization and postcondition machinery; existing
`EFFECT_REQUEST`, `CarrierPlan`, and carrier actuator; current checkpoint
cardinality and first-incomplete-slice enforcement; canonical governance and
workflow specs; and the current quality/strict OpenSpec validation harness.

Stage exit criteria: every implementation slice below is verified against the
approved Change; exact OpenSpec and implementation review gates can be
independently satisfied; exact-head quality/validation checks are green; no
prohibited mechanism or unrelated Issue scope is present; and the
repository-owned lifecycle can proceed without weakening #221's outcome.
Task markers in this file describe only Executor-implementable and
Executor-verifiable work. Reviewer PASS, merge, archive, and terminal
transitions remain lifecycle gates, not implementation tasks.

## Slice 1 — Make CarrierRequired a hard invocation exit

Trace: Human repair direction -> shared repository-governance carrier contract
-> existing application/effect and workflow bridge boundary.

- [x] 1.1 RED: add production-boundary regressions proving that when an exact,
  freshly authorized `CarrierPlan` is required, the current invocation stops
  before any later `SLICE_CHECKPOINT`, `ACTION_RESULT`, `action:*`,
  terminal/close, or successor effect, while the exact plan remains available
  for the carrier.
- [x] 1.2 GREEN: propagate the existing `CarrierRequired` boundary through
  the current application/effect bridge so it is not converted into an
  ordinary successful `ApplyResult`; expose only the exact plan and boundary
  outcome; preserve existing Action/Result/carrier primitives.
- [x] 1.3 GREEN: guard the existing workflow continuation/validation steps so
  the carrier-required invocation exits after plan persistence and does not
  execute formal effects in the same wake. Keep the carrier limited to the
  plan's exact operation, target, and expected values.
- [x] 1.4 REFACTOR: remove only duplicate or unreachable continuation handling
  introduced by the repair; do not add a carrier-result protocol, retry state,
  mailbox, successor path, or second workflow graph.
- [x] 1.5 VERIFY: run focused carrier/application/bridge regressions, the full
  Python suite, Ruff check, Ruff format check, mypy, and strict OpenSpec
  validation on the exact implementation revision.

## Slice 2 — Resume through later fresh reconstruction

Trace: Human fresh-reconstruction direction -> existing postcondition,
stale/replay/no-rewind, and historical exact-head reconciliation machinery.

- [ ] 2.1 RED: add a non-merge carrier interruption regression proving a later
  fresh repository-owned wake observes the already-current postcondition and
  applies only still-missing authorized effects, without replaying a verified
  slice or accepting carrier-asserted success.
- [ ] 2.2 GREEN: reuse the current application reauthorization and idempotent
  postcondition observation so non-merge carrier completion resumes only from
  fresh current truth. Preserve existing checkpoint cardinality and exact
  first-incomplete-slice matching.
- [ ] 2.3 RED: add a merge-carrier regression proving that a changed
  `main` makes the old authorization stale and that continuation cannot
  replay the stale `EFFECT_REQUEST`.
- [ ] 2.4 GREEN: route merge completion through the existing historical
  exact-head read-only reconciliation, then obtain fresh current-main
  authorization before any continuation or successor effect. Do not add a
  mailbox, registry, continuation token, retry state, or recovery graph.
- [ ] 2.5 VERIFY: run focused non-merge/merge, stale, replay, no-rewind,
  exact-head, and postcondition regressions plus all current quality checks.

## Slice 3 — Qualify active formal transitions by provenance

Trace: Human active-state guard -> scheduled-agent-workflow canonical owner
-> current runtime observation and application effect guard.

- [ ] 3.1 RED: add regressions showing that with `Change != unset`, a
  connector-authored or out-of-band direct `action:*` route is classified
  `INDETERMINATE` and fails closed even when its Issue/label shape is
  syntactically valid.
- [ ] 3.2 RED: add a regression showing that a connector-authored premature
  terminal/close mutation is also `INDETERMINATE` and cannot be accepted,
  rewound, or laundered by idempotent reconciliation.
- [ ] 3.3 GREEN: add the smallest current-formal-state provenance guard at the
  existing runtime/application observation boundary. Require fresh
  repository-owned Actions/application transition evidence for active routing
  and terminal/close; keep connector ingress as bounded untrusted
  `EFFECT_REQUEST` transport.
- [ ] 3.4 GREEN: prove a qualified repository-owned Actions/application formal
  transition remains accepted, while `Change: unset` pre-activation
  Explore/Propose behavior remains compatible.
- [ ] 3.5 VERIFY: run focused provenance, pre-activation, routing, terminal,
  and fail-closed regressions and all strict exact-head quality/validation
  checks.

## Slice 4 — Preserve the approved recovery and governance boundary

Trace: unchanged #221 checkpoint contract -> existing Action/Result and
lifecycle gates -> subtraction/reuse/consolidation decision.

- [ ] 4.1 RED: extend existing regressions to prove exact checkpoint cardinality,
  `newly checked task IDs == SLICE_CHECKPOINT Completed-Tasks == first
  incomplete slice task set`, monotonic task bookkeeping, and no replay of
  already verified slices remain enforced after carrier interruption.
- [ ] 4.2 GREEN: retain current one `implement-change` Action per bounded
  first-incomplete slice, task-before-checkpoint ordering, exact-head review/
  merge gates, independent Reviewer, and Human authority. Do not redesign
  checkpoint mechanics.
- [ ] 4.3 REFACTOR: reconcile the existing PR #226 work product with the
  approved OpenSpec meaning by reusing only necessary changes, removing
  duplicate normative representations and unrelated edits, and keeping
  `agents/AGENTS.md`, `agents/workflow.md`, Roles, and Skills from becoming
  competing owners.
- [ ] 4.4 VERIFY: inspect the complete changed-path inventory and current
  executable dispatch; prove no new Action, Result kind, state, registry,
  cursor, lease, heartbeat, retry counter, mailbox, carrier type,
  carrier-result protocol, generic provenance/recovery framework, token/App
  architecture, ruleset redesign, #218, #207, or #180 scope was introduced.

## Slice 5 — Final implementation evidence

Trace: all approved corrective slices -> exact current repository evidence ->
existing implementation readiness boundary.

- [ ] 5.1 VERIFY: fresh-reconstruct each approved implementation slice from
  current `main`, the active Change, implementation PR/head, tests, and
  durable evidence; prove a later wake resumes the first incomplete slice and
  never replays a previously verified slice.
- [ ] 5.2 VERIFY: fresh-check the exact carrier plans, postconditions,
  provenance evidence, checkpoint cardinality, stale/replay/no-rewind
  behavior, exact-head review/merge gates, Reviewer independence, Human
  authority, #221 historical boundary, and #218 blocked/unrouted state.
- [ ] 5.3 VERIFY: run the repository's complete Python quality suite and
  strict OpenSpec validation from the exact implementation head, record the
  evidence needed by the current executable result model, and prepare the
  existing `READY` result only after every required regression is green.
