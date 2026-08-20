# Tasks: Enforce invocation exit proof

## Slice 1 — Shared positive Exit Proof contract

- [x] **RED** — Add focused executable regression cases proving that an invocation with no positively proven legal Exit must continue, including RED→GREEN, failed-but-actionable validation, and a verified Slice with remaining approved same-action work. Run the focused tests and verify the failures are caused by the missing positive Exit Proof behavior rather than fixture/setup/import errors.
- [x] **GREEN** — Implement the minimum shared `agents/AGENTS.md` continuation-by-default / termination-by-proof contract and deterministic bounded test seam needed to satisfy the approved requirement. Keep Exit Proof internal and reuse existing durable evidence surfaces.
- [x] **REFACTOR** — Remove or consolidate only directly redundant local wording when the shared owner makes it unnecessary; do not move workflow topology, recovery algorithms, or role authority into the Exit contract.
- [x] **VERIFY** — Run the focused Slice tests, full regression suite, Ruff lint/format checks, mypy, and strict OpenSpec validation; persist task completion only after the Slice is green.

## Slice 2 — Action-boundary consumers

- [x] **RED** — Add executable cases for first absent/queued/in-progress exact resource observation, genuine unconsumable async wait, immediately actionable Lead same-role successor, completed Reviewer cross-role handoff, stale/precondition loss, and hard unrecoverable execution boundary. Verify the intended RED is attributable to missing Exit classification/consumption rather than unrelated workflow behavior.
- [x] **GREEN** — Apply only the minimum mapped-Skill procedure changes needed so implementation/async, same-role continuation, and cross-role handoff boundaries consume the shared Exit Proof invariant without copying its taxonomy. Preserve #111 mechanical recovery ownership and #115 terminal semantics.
- [x] **REFACTOR** — Keep mapped Skills action-local and progressively disclosed; remove duplicated termination wording only where the shared contract is now authoritative and no action-specific meaning is lost.
- [x] **VERIFY** — Run focused Slice tests, full regression suite, Ruff lint/format checks, mypy, and strict OpenSpec validation; persist task completion only after the Slice is green.

## Slice 3 — Invocation Exit regression closure

- [ ] **RED** — Add/complete an executable case proving an attempted invocation return is rejected when none of the bounded legal Exit classes is proven, while each accepted representative Exit class requires its positive evidence.
- [ ] **GREEN** — Complete the minimum deterministic regression fixture/classification behavior needed to cover the approved legal and non-exit cases without adding production dispatcher state or a second workflow engine.
- [ ] **REFACTOR** — Ensure tests encode behavior rather than Markdown substring presence where behavioral enforcement is required; retain lightweight structural checks only for genuine ownership/integration assertions.
- [ ] **VERIFY** — Run the focused Slice tests, full regression suite, Ruff lint/format checks, mypy, and strict OpenSpec validation.

## Completion

- [ ] Confirm every material behavior in `issuecomment-5360318078` is represented by proposal, capability requirement/scenarios, design, and executable tasks without redefining #111, #115, or #80 ownership.
- [ ] Confirm no new workflow action/status, timer/counter, heartbeat, lease, durable waiter, hidden cursor, central dispatcher engine, or second DAG was introduced.
- [ ] Run final Python Quality and exact-revision strict OpenSpec validation for the implementation head before `READY`.
