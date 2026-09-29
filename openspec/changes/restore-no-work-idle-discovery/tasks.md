# Tasks

## 0. Shared application materialization recovery

- [x] 0.1 RED: reproduce the first-carrier postcondition contradiction after a safe disjoint main advance, with real current materialization source and exact Issue/Change/branch/head/PR/content observations.
- [x] 0.2 GREEN: make `materialization_postcondition()` compare the canonical fresh observer's exact target while retaining pending-continuation ancestry, path, identity, and ambiguity guards.
- [x] 0.3 RED: reproduce interruption after branch-ref creation but before PR creation, followed by a disjoint main advance; prove a missing-carrier plan is required and unsafe/wrong/duplicate/incomplete PR evidence is rejected.
- [x] 0.4 GREEN: resume only the missing PR carrier from the verified immutable intent and existing branch/head, using fresh current main and a shared exact plan builder.
- [x] 0.5 RED: prove a fresh consequence observer with an empty adapter-local materialization-target map rejects no valid durable materialization/implementation carrier.
- [x] 0.6 GREEN: reconstruct the `ConsequenceSpec.evidence_target` through the existing canonical current-state materialization or implementation-carrier owner.
- [x] 0.7 VERIFY: cover all applicable durable prefixes from acceptance through final postcondition and prove no duplicate, rewind, semantic replay, target broadening, or new recovery state.
- [x] 0.8 RED: reproduce an accepted intent with an exact current Issue/Change/Role/Action, a durable partial effect, an uncorrelated legacy `ACTION_RESULT`, and an invalid current frontier; prove the current bridge fails before resolving the accepted application run/job.
- [x] 0.9 GREEN: resume only the unique exact accepted intent and its unique request-bound application run/job through the existing recovery owner; prove stale source, changed route/Change, duplicate acceptance/run/job, and incomplete evidence still fail closed without semantic replay.
- [x] 0.10 VERIFY: execute the current-source reproduction and the full application/bridge interruption regression against fresh default-branch code; verify no semantic replay or duplicate mutation.
- [x] 0.11 RED/GREEN: reproduce a completed accepted application at `run_attempt > 1` (including the live #322 attempt-7+ fixture), then fail closed with `application-completion-rerun-limit` and prove later scheduled wakes emit no rerun job and perform no semantic replay.
- [x] 0.12 RED/GREEN: reproduce an accepted materialization whose exact PR carrier merged before the application process resumed; reconcile the merged head from complete GitHub compare history and exact historical blob evidence without creating a same-Change replacement, while retaining the existing replacement path when content or ancestry proof is incomplete.

Stage 0 is merged and active on current `main@d019fdc604e8a7fa40e2f3e6436a12b076658057`: PR #331 merged as `6586b5e6b40d84717b73fb7548d778e177fd826f` from exact head `9d7fc4810ad921e17bc6c2bfc0fa955fc848e9b3` (Python Quality run `35953768705`, 729 tests reported); PR #332 merged as `817176cd1b74f8bc04c1e480e0b5335514c5e4ee` from exact head `49ad4d2aa55738b548ffb4b84f57741cd249247e` (run `35958582031`, 736 full-suite and 24 focused tests reported); PR #333 merged as `d019fdc604e8a7fa40e2f3e6436a12b076658057` from exact head `a47519dae24b853b0eda2a6a2c3fd9991f1b4aad` (run `35963968270`, 751 tests reported). PR bodies record the corresponding current-source materialization, interruption, consequence, and lineage regressions plus applicable Ruff/format/mypy checks. Stage 0 is complete as delivered; the remaining parent outcome is not complete.

## 1. Contract and typed NO_WORK handoff

- [x] 1.1 RED/GREEN: add contract tests proving `AUTHORIZE` and `FAIL_CLOSED` never enter idle, while one exact completed `NO_WORK` artifact can invoke one bounded Lead idle semantic request.
- [x] 1.2 GREEN: add the typed non-Action dispatch envelope/result parser and producer/consumer boundary, bound to exact request comment, bridge run, artifact id/digest, default-branch revision, and source evidence.
- [x] 1.3 REFACTOR: keep normal `select_work()`, the Action enum, Role derivation, normal labels, and successor lifecycle unchanged; the implementation introduces no idle routing state.

## 2. Safe idle admission application

- [x] 2.1 RED/GREEN: add tests for no-finding zero mutation, existing-candidate tuple completion with unrelated content/labels preserved, and new-candidate creation with exactly `Change: unset + action:explore-change`.
- [x] 2.2 GREEN: implement the smallest repository-owned idle admission actuator using fresh default-branch reauthorization and one logical create/update boundary.
- [x] 2.3 RED/GREEN: cover stale source/default branch, real Actions run/artifact identity and content, interruption-before/after mutation, overlap recovery through all-state correlation, closed/contradictory matches, body/label preservation, and ambiguous-write reconciliation.
- [x] 2.4 GREEN: add minimal non-durable workflow concurrency and read-only ambiguous-write reconciliation; fail closed when uniqueness or the complete postcondition cannot be proved.
- [x] 2.5 REFACTOR: reuse current dispatch/application carrier and fresh-read primitives; no duplicate queue, lock state, lease, cursor, heartbeat, registry, recovery workflow, or hidden backlog is introduced.

## 3. Scheduled Task/bootstrap cutover

- [x] 3.1 RED/GREEN: add a production-shaped bridge/bootstrap test showing the exact `NO_WORK` artifact reaches one typed bounded Lead idle ingress and `AUTHORIZE`/`FAIL_CLOSED` do not.
- [x] 3.2 GREEN: connect the repository-visible application carrier to the typed idle boundary through one `IDLE_ADMISSION_REQUEST` Issue-comment RPC on the current daily runtime shard, without representing idle as an Action or relying on the comment as accepted-intent state; reuse the same boundary for content-addressed `APPLICATION_CONTINUATION` recovery.
- [x] 3.3 GREEN: update the available external Lead Scheduled Task prompt to consume the repository-produced `NO_WORK` artifact, post only exact typed idle requests/continuations through the current connector boundary, and remain silent for no-finding or unproven evidence.
- [ ] 3.4 RED/GREEN: prove no-finding is repository-silent, and a successful admission is consumed by a later normal wake that authorizes ordinary `Lead / explore-change`.

## 4. Verification and delivery

- [x] 4.1 Run focused idle contract, application, bridge, and dispatch tests.
- [x] 4.2 Run full regression, type checks, lint, and repository workflow/static invariant checks on the current-main merge snapshot; remote Python Quality also passes on the exact PR head.
- [x] 4.3 Run strict OpenSpec validation on the active change and resolve every reported error; remote OpenSpec Validate also passes on the exact PR head.
- [ ] 4.4 Capture production-shaped evidence for exact `NO_WORK` idle execution, no-finding silence, safe admission, and later normal Action handoff before declaring #322 complete.

## Lifecycle gates

These are workflow lifecycle gates, not implementation tasks: independent OpenSpec review must PASS before implementation is authorized; independent implementation review and all current repository gates must PASS before exact-head merge; post-merge canonical state must be freshly verified before governed archive review, merge, and terminal-state verification.

## Parent-outcome continuation

The checklist above is delivery work, not a reduced completion condition. Any stage that merges while production activation or required validation remains incomplete MUST leave the active Change and #322 on their current governed successor and continue in a later fresh wake.
