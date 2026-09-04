# Tasks

## Slice 1 — Normal Archive merge leaves coordination Issue open

- [x] RED: add focused regression proving final Archive PR preparation/merge contract rejects `Closes #N` and expects deterministic non-closing linkage while preserving exact-head Reviewer PASS and merge preconditions.
- [x] GREEN: update shared governance, Archive PR preparation, and `merge-pr` procedure so final Archive PR uses non-closing linkage and Executor hands off to open `Lead / finalize-archive` after merge.
- [x] REFACTOR: remove happy-path wording that treats native close at Archive merge as terminal progress while preserving bounded premature-close recovery semantics.
- [x] VERIFY: run focused tests, full regression suite, lint, type checks, and strict OpenSpec validation; persist slice completion only after all required gates are green.

Trace: proposal normal terminal invariant → delta requirements `Executor merges only an explicitly authorized unchanged revision` and `Normal OpenSpec archive mechanics remain owned by repository automation` → design Decisions 1 and 3.

## Slice 2 — Lead finalization owns completion then close

- [x] RED: add regression proving Archive merge alone cannot make the workflow terminal and proving `LIFECYCLE_COMPLETE` must be durable before Lead closes the coordination Issue.
- [x] GREEN: update Lead/lifecycle governance and `lifecycle-finalize` so `finalize-archive` reconstructs terminal evidence, persists `LIFECYCLE_COMPLETE`, closes the Issue, and re-observes `closed`.
- [x] REFACTOR: consolidate terminal wording so `closed + valid completion` is history and normal open workflow state requires no closed terminal-pending exception.
- [x] VERIFY: run focused tests, full regression suite, lint, type checks, and strict OpenSpec validation; persist slice completion only after all required gates are green.

Trace: proposal Lead terminal ownership → delta requirements `Review and finalize actions have Lead-owned minimum gate contracts` and `Coordination Issue closure is the durable final lifecycle transition` → design Decision 2.

## Slice 3 — Interrupted and premature close reconstruction

- [x] RED: add executable cases for durable completion with missing close, close with missing re-observation, premature close without valid completion, and closed+valid completion excluded from formal WIP/cardinality.
- [x] GREEN: update workflow-dynamic routing/cardinality/recovery procedure to idempotently finish interrupted final close and keep premature close under the existing bounded fail-closed recovery predicate.
- [x] REFACTOR: remove obsolete normal terminal-pending branches without introducing a replacement state machine or hidden completion registry.
- [x] VERIFY: run focused tests, full regression suite, lint, type checks, and strict OpenSpec validation; persist slice completion only after all required gates are green.

Trace: proposal interruption boundary → delta requirements `Actionable workflow routing is one logical role/action tuple` and `Coordination Issue closure is the durable final lifecycle transition` → design Decisions 3 and 4.

## Completion

- [x] Verify reverse traceability `tasks → design → specs → proposal`, including exact Explore upstream baseline `issuecomment-5355262548`.
- [x] Verify forward traceability `proposal → specs → design → tasks`.
- [x] Confirm #112 invocation-exit semantics and #80 workflow-topology SSOT extraction remain out of scope.
- [x] Run `openspec validate --all --strict --json --no-interactive` through the repository exact-revision validation contract.
