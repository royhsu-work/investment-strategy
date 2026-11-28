## Why

The current Runtime couples development writes to a fully verified slice. Current implementation procedure requires all-green candidate verification before ACCEPT; completion planning requires task delta and checkpoint. Candidate verification starts with pytest and drops test diagnostics. The first legitimate test-only RED cannot be durably produced through normal ingress. #496 cannot use #478's unmerged replacement contract as current authority; #478 is blocked through #493 on #496. Historical native CI proves that actual test-only revisions can reach static PASS and target RED, but does not confer current write authority.

Human authorized the bounded independent maintenance bootstrap in [#496](https://github.com/royhsu-work/investment-strategy/issues/496#issuecomment-7216731327). Preserve the original [parent acceptance](https://github.com/royhsu-work/investment-strategy/issues/496) and [accepted exploration](https://github.com/royhsu-work/investment-strategy/issues/496#issuecomment-7216692088). The [approved #478 architecture](https://github.com/royhsu-work/investment-strategy/issues/478#issuecomment-7163243974) supplies the shared design direction. This extracts the minimum necessary delivery prerequisite, not a second architecture. The later [Human checkpoint clarification](https://github.com/royhsu-work/investment-strategy/issues/496#issuecomment-7217540806) explicitly supersedes checkpoint-as-completion and makes the persistence/resumption responsibility common to Propose and Implement. Preserve [#473 artifact-level acceptance](https://github.com/royhsu-work/investment-strategy/issues/470#issuecomment-7126303580) and its later shift-left validation requirement in #473; this helper does not claim that entire artifact workflow is delivered.

## What Changes

- Separate saving work from verification and formal delivery. Reuse durable Git/PR content and the existing Application/Carrier proof to save partial, pending, failed or later revised work. No separate checkpoint record per save, no checkpoint-derived acceptance, progress cursor, immutability or forced exit. Propose artifacts and implementation slices share the persistence/continuation contract; their own verification and completion contracts remain distinct.
- Authorize code/test development, including genuine test-only RED, without an all-green pre-ACCEPT overlay. Keep exact native static-first quality, task criteria, authorized task markers after verified implementation, and exact current marker-bearing revision gates before formal delivery.
- Settle physical effects using their own immutable witnesses; qualify applicable CI at the exact relevant revision. Continue lawful same-scope work and preserve historical evidence without replay. Derive ordinary delivery and authorized correction scope from approved tasks, current repository evidence, formal occurrence and findings, never checkpoint existence. Publish one valid formal result per authorized formal consequence after required gates, without a separate checkpoint publication.
- Keep independent OpenSpec/implementation/Archive reviews, exact-head merge, one Action/wake, dependency and Human authority. No extra runner, mode, token, Action, ResultKind, progress state or case-specific recovery branch.

## Capabilities

### New Capabilities

### Modified Capabilities

- `scheduled-agent-workflow`: shared checkpoint persistence/continuation, development and formal delivery separation, exact native CI and same-scope continuation.
- `repository-governance`: align the existing test-first requirement with checkpoint as saved work rather than a verified completion gate.

## Impact

Existing Application, Dispatch, materialization/Carrier, qualification/validation owners, Python Quality workflow and implementation procedure. This non-closing helper is independently reviewed, released and archived before normal #496 relies on it. #496 remains open and retains every normal return-path, occurrence, historical compatibility, review-correction and deployment acceptance. #478 retains its broader composite Task Contract, normal validation failure/recovery and legacy integration requirements. #473 retains the full artifact DAG, artifact-local successful verification/reporting, preactivation durability, early native strict and final consistency/review acceptance; both consumers reuse the shared persistence contract instead of inventing a parallel checkpoint framework. Reconcile deployed overlap instead of duplicating it. No helper Issue or parent routing/dependency changes.
