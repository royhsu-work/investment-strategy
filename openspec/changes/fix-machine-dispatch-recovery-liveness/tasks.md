# Tasks: Fix machine dispatch recovery liveness

## Slice 1 — Formal-zero structural-clear dispatch

- [ ] 1.1 RED — Add production-path regression coverage for formal cardinality zero with a complete structural closed-workflow projection of `CLEAR`, covering both an eligible queued `Lead / explore-change` winner and the no-queued-work `NO_WORK` case. Prove the current implementation fails because it enters detailed exceptional history unconditionally.
- [ ] 1.2 RED — Add a regression that instruments detailed closed-workflow comment/history acquisition and proves it must not be invoked for unrelated historical terminal Issues when formal-zero structural state is `CLEAR`.
- [ ] 1.3 GREEN — Change production acquisition/orchestration so formal-zero consumes the complete structural closed-conflict disposition first and proceeds directly to deterministic pre-activation selection/`NO_WORK` on `CLEAR`.
- [ ] 1.4 GREEN — Preserve `POSSIBLE_CONFLICT` / `INDETERMINATE` routing into detailed exceptional recovery and preserve current recovery/fail-closed results.
- [ ] 1.5 REFACTOR — Consolidate formal-one and formal-zero use of the structural conflict boundary without duplicating a second classifier or introducing durable state/cache/registry.
- [ ] 1.6 VERIFY — Run focused dispatch/runtime tests, then the full regression suite, mypy, ruff, and strict OpenSpec validation for the exact implementation revision.

## Slice 2 — Idempotent terminal replay classification

- [ ] 2.1 RED — Add the exact #91 regression shape with two valid canonical `LIFECYCLE_COMPLETE` journals that identify the same workflow/change/action/result and compatible terminal identity; prove the current terminal classifier returns `indeterminate` only because valid comment count is greater than one.
- [ ] 2.2 RED — Add contrast coverage where otherwise valid terminal journals disagree on an immutable terminal revision/Archive identity and must remain `indeterminate` / `FAIL_CLOSED`.
- [ ] 2.3 RED — Cover monotonic compatible replay where a later journal contains additional non-conflicting terminal metadata that an earlier valid journal omitted.
- [ ] 2.4 GREEN — Introduce the minimum semantic terminal-evidence representation/comparison needed to classify compatible repetitions as one terminal fact while preserving the existing validity/provenance checks for each journal.
- [ ] 2.5 GREEN — Make detailed recovery consume semantic terminal consistency rather than raw valid-comment cardinality.
- [ ] 2.6 REFACTOR — Keep parsing/comparison bounded to terminal identity required by the contract; do not compare raw bodies or create a generic event-sourcing/history framework.
- [ ] 2.7 VERIFY — Run focused terminal/recovery tests, the exact #91 regression, then the full regression suite, mypy, ruff, and strict OpenSpec validation for the exact implementation revision.

## Slice 3 — Bounded machine diagnostic for non-authorizing decisions

- [ ] 3.1 RED — Add bridge parser/render tests proving `NO_WORK` and `FAIL_CLOSED` carry exactly one bounded machine-owned `Reason` while containing no Issue/Role/Action tuple.
- [ ] 3.2 RED — Prove the diagnostic cannot be parsed or consumed as workflow routing/effect authority and that correlated-request identity remains mandatory.
- [ ] 3.3 GREEN — Extend the durable `DISPATCH_DECISION` render/parse contract to publish the existing production `DispatchDecision.reason` for `NO_WORK` / `FAIL_CLOSED` only.
- [ ] 3.4 GREEN — Keep `AUTHORIZE` tuple semantics unchanged and reject malformed decisions that mix a non-authorizing disposition with an Issue/Role/Action tuple.
- [ ] 3.5 REFACTOR — Bound diagnostic values to stable repository-owned classifier output; do not emit exception traces, arbitrary GitHub payloads, or model prose.
- [ ] 3.6 VERIFY — Run focused bridge tests, full regression suite, mypy, ruff, and strict OpenSpec validation for the exact implementation revision.

## Slice 4 — Governance alignment and end-to-end regression

- [ ] 4.1 RED — Update/add governance regression coverage showing current shared governance must no longer require unconditional detailed exceptional recovery for every formal-zero wake while still requiring complete current structural conflict proof and fail-closed escalation on non-clear state.
- [ ] 4.2 GREEN — Make the minimum `agents/AGENTS.md` wording change required to align with the approved canonical behavior; do not duplicate executable classifier mechanics into prose.
- [ ] 4.3 GREEN — Add an end-to-end production regression combining: closed #91-compatible duplicate terminal replay + formal cardinality zero + one legal queued Explore candidate, and require an `AUTHORIZE` result for the deterministic candidate rather than repository-wide `FAIL_CLOSED`.
- [ ] 4.4 GREEN — Add a companion end-to-end case with genuinely contradictory terminal identity and require `FAIL_CLOSED`.
- [ ] 4.5 REFACTOR — Remove obsolete test assumptions that equate formal-zero with unconditional detailed history; preserve tests for real premature-close recovery, multiple active workflows, incomplete observations, and stale current-state rejection.
- [ ] 4.6 VERIFY — Run all focused workflow/governance tests, complete pytest suite, mypy, ruff, and `openspec validate --all --strict --json --no-interactive` against the exact final implementation revision.

## Completion evidence

- [ ] 5.1 Record the exact implementation PR head used for final verification and preserve test/quality/OpenSpec evidence for that revision.
- [ ] 5.2 Demonstrate from production-path regression evidence that compatible duplicate terminal journals no longer strand unrelated pre-activation work and that real contradictory/recovery state still fails closed.
- [ ] 5.3 Confirm no lightweight-runtime/`uv`/packaging change, lock/lease/cache/registry, second DAG, or unrelated #138 scope entered this Change.
