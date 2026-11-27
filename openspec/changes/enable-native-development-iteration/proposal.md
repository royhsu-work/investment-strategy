## Why

The current Runtime couples development writes to a fully verified slice. Current implementation procedure requires all-green candidate verification before ACCEPT; completion planning requires task delta and checkpoint. Candidate verification starts with pytest and drops test diagnostics. The first legitimate test-only RED cannot be durably produced through normal ingress. #496 cannot use #478's unmerged replacement contract as current authority; #478 is blocked through #493 on #496. Historical native CI proves that actual test-only revisions can reach static PASS and target RED, but does not confer current write authority.

Human authorized the bounded independent maintenance bootstrap in [#496](https://github.com/royhsu-work/investment-strategy/issues/496#issuecomment-7216731327). Preserve the original [parent acceptance](https://github.com/royhsu-work/investment-strategy/issues/496) and [accepted exploration](https://github.com/royhsu-work/investment-strategy/issues/496#issuecomment-7216692088). The [approved #478 architecture](https://github.com/royhsu-work/investment-strategy/issues/478#issuecomment-7163243974) supplies the shared design direction. This extracts the minimum necessary delivery prerequisite, not a second architecture.

## What Changes

- Separate authorized development materialization from verified slice completion on the existing implementation carrier, including genuine test-only RED.
- Replace the separate executable pre-ACCEPT implementation overlay with the existing static-first native quality gate for both development and verified completion, preserving all non-executable authorization, manifest, task and checkpoint checks. Require exact native evidence on the implementation revision and the subsequent marker revision.
- Settle each development attempt against its own immutable materialization witness and qualified CI; reconstruct lawful same-frontier continuation without hiding competing acceptance. Obtain an outstanding exact verification through the same native quality job and existing source-bound dispatch run, without a second asynchronous workflow-dispatch request.
- Preserve exact-head review, task criteria, one verified checkpoint/formal result, full quality/strict and merge gates. No second runner, special test mode, token, new Action/ResultKind, persisted phase, worker-selected target, or incident-specific Runtime exception.

## Capabilities

### New Capabilities

### Modified Capabilities

- `scheduled-agent-workflow`: development/completion consequence separation, exact native CI and same-slice continuation.

## Impact

Existing Application, Dispatch, materialization/Carrier, qualification/validation owners, Python Quality workflow and implementation procedure. This non-closing helper is independently reviewed, released and archived before normal #496 relies on it. #496 remains open and retains every normal return-path, occurrence, historical compatibility, review-correction and deployment acceptance. #478 retains its broader composite Task Contract, normal validation failure/recovery and legacy integration requirements; reconcile already deployed overlap instead of duplicating it. No helper Issue or parent routing/dependency changes.
