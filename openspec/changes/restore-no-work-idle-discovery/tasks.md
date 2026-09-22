# Tasks

## 1. Contract and typed NO_WORK handoff

- [ ] 1.1 RED: add contract tests proving `AUTHORIZE` and `FAIL_CLOSED` never enter idle, while one exact completed `NO_WORK` artifact can invoke one bounded Lead idle semantic request.
- [ ] 1.2 GREEN: add the typed non-Action dispatch envelope/result parser and producer/consumer boundary, bound to exact request comment, bridge run, artifact, default-branch revision, and source evidence.
- [ ] 1.3 REFACTOR: keep normal `select_work()`, the Action enum, Role derivation, normal labels, and successor lifecycle unchanged; prove no idle routing state is introduced.

## 2. Safe idle admission application

- [ ] 2.1 RED: add tests for no-finding zero mutation, existing-candidate tuple completion with unrelated content/labels preserved, and new-candidate creation with exactly `Change: unset + action:explore-change`.
- [ ] 2.2 GREEN: implement the smallest repository-owned idle admission actuator using fresh default-branch reauthorization and one logical create/update boundary.
- [ ] 2.3 RED: add overlap, stale source/default branch, interruption-before-mutation, interruption-after-mutation, and ambiguous-write reconciliation tests.
- [ ] 2.4 GREEN: add minimal non-durable admission serialization and read-only reconciliation; fail closed when uniqueness or the complete postcondition cannot be proved.
- [ ] 2.5 REFACTOR: reuse current application/carrier/fresh-read primitives and remove any duplicate queue, lock, lease, cursor, heartbeat, registry, recovery workflow, or hidden backlog.

## 3. Scheduled Task/bootstrap cutover

- [ ] 3.1 RED: add a production-shaped bridge/bootstrap test showing exact `NO_WORK` reaches bounded Lead idle semantics and `AUTHORIZE`/`FAIL_CLOSED` do not.
- [ ] 3.2 GREEN: connect the real repository-visible bootstrap/carrier to the typed idle boundary without representing idle as an Action or relying on the daily control shard as accepted-intent state.
- [ ] 3.3 GREEN: execute the available external Scheduled Task configuration change if it is within capability; otherwise preserve the exact activation contract and record the authoritative external boundary as a blocker rather than weakening the parent outcome.
- [ ] 3.4 RED/GREEN: prove no-finding is repository-silent, and a successful admission is consumed by a later normal wake that authorizes ordinary `Lead / explore-change`.

## 4. Verification and delivery

- [ ] 4.1 Run focused idle contract, application, bridge, and dispatch tests.
- [ ] 4.2 Run full regression, type checks, lint, and repository workflow/static invariant checks.
- [ ] 4.3 Run strict OpenSpec validation on the active change and resolve every reported error.
- [ ] 4.4 Obtain independent OpenSpec review and implement only after its current PASS.
- [ ] 4.5 Obtain independent implementation review, pass current repository gates, and merge the implementation PR under exact-head governance.
- [ ] 4.6 Freshly verify post-merge canonical state, use governed archive automation, and verify archive review/merge/terminal lifecycle.
- [ ] 4.7 Capture production-shaped evidence for exact `NO_WORK` idle execution, no-finding silence, safe admission, and later normal Action handoff before declaring #322 complete.

## Parent-outcome continuation

The checklist above is delivery work, not a reduced completion condition. Any stage that merges while production activation or required validation remains incomplete MUST leave the active Change and #322 on their current governed successor and continue in a later fresh wake.
