# Tasks: Require CI re-observation before async Exit

Traceability baseline: Explore #124 `issuecomment-5366724594` → proposal → MODIFIED `scheduled-agent-workflow` work-conserving requirement → design decisions → slices below.

## Slice 1 — Derive async-wait Exit from observation sequence

- [ ] **RED** — Revise focused Invocation Exit regression coverage so a caller-supplied `exact_resource_unconsumable` truth value cannot directly establish async-wait Exit. Add cases for first absent/queued/in-progress observation, attempted async-wait Exit without re-observation, and stale routing/head/precondition discovered before the later observation. Run focused tests and verify RED failures are caused by the missing sequence-derived evidence behavior.
- [ ] **GREEN** — Implement the minimum deterministic test seam that derives continuation, existing async-wait Exit, terminal-result consumption, or existing stale/precondition Exit from first and subsequent fresh observations of the same exact target/resource. Keep the seam test-only; do not introduce production dispatcher or waiter state.
- [ ] **REFACTOR** — Preserve the existing bounded Exit taxonomy and remove any fixture shortcut that can bypass the required re-observation evidence. Add no wall-clock delay, sleep policy, polling counter, retry state, heartbeat, lease, durable waiter, or hidden runtime cursor.
- [ ] **VERIFY** — Run focused Slice tests, the full regression suite, Ruff lint/format checks, mypy, and strict OpenSpec validation; persist completion only after the Slice is green.

## Slice 2 — Operationalize the shared re-observation floor

- [ ] **RED** — Add executable/structural regression coverage proving the shared runtime owner and the two concrete trigger-and-consume mapped Skills require at least one subsequent fresh same-exact-target observation before ordinary async-wait Exit, consume terminal success/actionable failure immediately, and leave unrelated Reviewer/lifecycle Skills unchanged.
- [ ] **GREEN** — Apply the minimum approved edits to `agents/AGENTS.md`, `agents/skills/implementation/SKILL.md`, and `agents/skills/openspec-change/SKILL.md` so their exact-resource procedures consume the sequence-derived re-observation floor without copying the generic Exit taxonomy.
- [ ] **REFACTOR** — Keep `agents/AGENTS.md` as the single shared continuation/Exit owner, preserve current role/action authority and exact-head gates, and avoid expanding #111 recovery or `agents/workflow.md` topology ownership.
- [ ] **VERIFY** — Run focused Slice tests, the full regression suite, Ruff lint/format checks, mypy, and strict OpenSpec validation; persist completion only after the Slice is green.

## Completion

- [ ] Confirm proposal/spec/design/tasks preserve every material decision in Explore `issuecomment-5366724594` and do not redefine the existing Invocation Exit taxonomy.
- [ ] Confirm Skill maintenance traceability declares exactly `agents/skills/implementation/SKILL.md` and `agents/skills/openspec-change/SKILL.md` as `Modified`, with no Added/Removed Skill and no unexplained material Skill scope.
- [ ] Confirm no Reviewer/lifecycle Skill, workflow-topology, scheduler cadence, timer/counter/waiter machinery, or mechanical mutation-recovery scope is introduced.
- [ ] Run final exact-head strict OpenSpec validation before `READY_FOR_OPENSPEC_REVIEW`.