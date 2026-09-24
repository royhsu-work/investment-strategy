# Tasks

## 0. Shared application materialization recovery

- [ ] 0.1 RED: reproduce the first-carrier postcondition contradiction after a safe disjoint main advance, with real current materialization source and exact Issue/Change/branch/head/PR/content observations.
- [ ] 0.2 GREEN: make `materialization_postcondition()` compare the canonical fresh observer's exact target while retaining pending-continuation ancestry, path, identity, and ambiguity guards.
- [ ] 0.3 RED: reproduce interruption after branch-ref creation but before PR creation, followed by a disjoint main advance; prove a missing-carrier plan is required and unsafe/wrong/duplicate/incomplete PR evidence is rejected.
- [ ] 0.4 GREEN: resume only the missing PR carrier from the verified immutable intent and existing branch/head, using fresh current main and a shared exact plan builder.
- [ ] 0.5 RED: prove a fresh consequence observer with an empty adapter-local materialization-target map rejects no valid durable materialization/implementation carrier.
- [ ] 0.6 GREEN: reconstruct the `ConsequenceSpec.evidence_target` through the existing canonical current-state materialization or implementation-carrier owner.
- [ ] 0.7 VERIFY: cover all applicable durable prefixes from acceptance through final postcondition and prove no duplicate, rewind, semantic replay, target broadening, or new recovery state.
- [ ] 0.8 RED: reproduce an accepted intent with an exact current Issue/Change/Role/Action, a durable partial effect, an uncorrelated legacy `ACTION_RESULT`, and an invalid current frontier; prove the current bridge fails before resolving the accepted application run/job.
- [ ] 0.9 GREEN: resume only the unique exact accepted intent and its unique request-bound application run/job through the existing recovery owner; prove stale source, changed route/Change, duplicate acceptance/run/job, and incomplete evidence still fail closed without semantic replay.
- [ ] 0.10 VERIFY: execute the current-source reproduction and the full application/bridge interruption regression against fresh default-branch code; verify no semantic replay or duplicate mutation.

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
- [ ] 4.4 Capture production-shaped evidence for exact `NO_WORK` idle execution, no-finding silence, safe admission, and later normal Action handoff before declaring #322 complete.

## Lifecycle gates

These are workflow lifecycle gates, not implementation tasks: independent OpenSpec review must PASS before implementation is authorized; independent implementation review and all current repository gates must PASS before exact-head merge; post-merge canonical state must be freshly verified before governed archive review, merge, and terminal-state verification.

## Parent-outcome continuation

The checklist above is delivery work, not a reduced completion condition. Any stage that merges while production activation or required validation remains incomplete MUST leave the active Change and #322 on their current governed successor and continue in a later fresh wake.
