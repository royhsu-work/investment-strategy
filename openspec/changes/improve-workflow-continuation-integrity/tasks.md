# Tasks: Improve workflow continuation integrity

## Slice 1 — Required deferred follow-up integrity

- [ ] **RED** Add focused regression tests proving ordinary out-of-scope/non-goal text creates no tracking obligation, while an explicit approved required-defer decision without reconstructable tracker linkage is rejected by OpenSpec review and terminal lifecycle completion.
- [ ] **GREEN** Update canonical workflow governance and Lead/Reviewer/finalize procedures so Lead creates or reuses a tracker at the defer-decision boundary, the tracker is not auto-admitted/routed, Reviewer verifies required tracker linkage, and finalization blocks missing still-applicable trackers.
- [ ] **REFACTOR** Consolidate shared required-defer semantics into the authoritative shared ownership layer and leave role/skill files with only their action-specific specialization.
- [ ] **VERIFY** Run focused tests, full pytest suite, mypy, Ruff, and strict OpenSpec validation for the exact branch revision.

Trace: proposal `What Changes` item 1; delta requirement `Explicit required deferred follow-up becomes durable before lifecycle completion`; design Decision 1.

## Slice 2 — Same-role action continuation and HANDOFF boundary

- [ ] **RED** Add regression tests proving continuation stays on the same coordination Issue and fixed invocation role, reconstructs the target action before mutation, stops at cross-role/Human/async/stale/unsafe boundaries, and does not require synthetic `HANDOFF` for same-role transitions.
- [ ] **GREEN** Update shared governance, message presentation, and affected Lead procedures so immediately actionable same-role target actions may continue in the same invocation while cross-role transitions still persist `HANDOFF` and terminate the invocation.
- [ ] **REFACTOR** Remove duplicated action-boundary wording that conflicts with the shared continuation contract; do not introduce an action-transition message, dispatcher, counter, lease, heartbeat, or second workflow state.
- [ ] **VERIFY** Run focused tests, full pytest suite, mypy, Ruff, and strict OpenSpec validation for the exact branch revision.

Trace: proposal `What Changes` items 2–3; modified requirements `Scheduled execution is at-least-once and state reconstructable` and `Routing handoff persists evidence before ownership transfer`; design Decisions 2–3.

## Slice 3 — Short exact CI/Actions work conservation

- [ ] **RED** Add regression tests proving the first queued/in-progress observation of a just-triggered exact required run does not force a yield while bounded execution opportunity remains, that a terminal result reached in the same invocation is consumed immediately, and that a later wake fresh-reads the exact awaited run.
- [ ] **GREEN** Strengthen affected OpenSpec-change and implementation procedures to observe only the exact just-triggered required run and continue when it becomes terminal, while preserving real asynchronous wait and cross-role stop boundaries.
- [ ] **REFACTOR** Keep shared async semantics in `agents/AGENTS.md`; action skills contain only executable specialization and no timers, sleep policy, poll counters, heartbeat, or hidden waiter state.
- [ ] **VERIFY** Run focused tests, full pytest suite, mypy, Ruff, and strict OpenSpec validation for the exact branch revision.

Trace: proposal `What Changes` items 4–5; modified requirement `Scheduled execution is at-least-once and state reconstructable`; design Decision 4.

## Final verification

- [ ] Verify proposal → specs → design → tasks forward traceability and tasks → design → specs → proposal reverse traceability.
- [ ] Verify no unrelated Human-authority provenance, Python Ruff security, or prompt-security implementation entered this change.
- [ ] Run `pytest`, `mypy`, `ruff`, and strict OpenSpec validation; record exact-revision evidence before Reviewer handoff.
