## 1. RED — lock the scheduled-wake role boundary

- [ ] 1.1 Add failing executable regressions around `continuation_requires_fresh_wake` proving same-role continuations do not require a new scheduled wake, while Lead→Reviewer, Reviewer→Executor, and Executor→Lead do.
- [ ] 1.2 Add/adjust governance contract regressions so one scheduled wake has a fixed initial role, same-role action successors remain work-conserving as fresh workers, and cross-role successors are wake-terminal.
- [ ] 1.3 Add a regression preserving the exact Explore-selected non-goals: no routing rewrite, fixed-role scheduler semantics, hidden queue/lease/heartbeat/state, or second workflow DAG.

## 2. GREEN — enforce the narrow continuation decision

- [ ] 2.1 Change the repository-owned continuation helper beside effect application so a selected successor requires a new scheduled wake only when its role differs from the current wake role; `None` remains no continuation.
- [ ] 2.2 Preserve `ApplyResult.continuation` as the exact fresh repository-owned dispatch result; do not alter dispatcher selection, routing topology, WIP/cardinality, or action ownership.
- [ ] 2.3 Align `agents/AGENTS.md` and `agents/templates/messages.md` with the scheduled-wake boundary: fresh worker for every successor, same-role same-wake continuation allowed, cross-role handoff durable but wake-terminal.
- [ ] 2.4 Keep `agents/workflow.md` unchanged unless implementation proves an actual topology inconsistency; it remains the sole topology owner.

## 3. REFACTOR — remove ambiguous continuation terminology

- [ ] 3.1 Ensure code/tests distinguish `fresh mapped worker` from `fresh scheduled wake`; rename only where needed to prevent the previous conflation without broad API churn.
- [ ] 3.2 Keep `initial_role` invocation-local; do not persist it in GitHub/OpenSpec/runtime transport state.

## 4. VERIFY — prove role isolation without liveness regression

- [ ] 4.1 Run focused Scheduled-Agent effect/continuation, invocation-exit, workflow-continuity, and governance tests.
- [ ] 4.2 Run the repository-required Python quality/test gate and strict OpenSpec validation against the exact implementation head.
- [ ] 4.3 Verify same-role `Lead / explore-change → Lead / propose-change` remains immediately continuable under fresh dispatch.
- [ ] 4.4 Verify cross-role Lead→Reviewer, Reviewer→Executor, and Executor→Lead preserve the successor routing but require a later scheduled wake before successor execution.
- [ ] 4.5 Verify the implementation preserves WIP=1, Human authority, at-least-once reconstruction, and no durable wake-role state.

Refs #161
Explore baseline: #161 comment `5440915970`
