# Proposal — align-issue-completion-with-archive

## Why

The scheduled-agent workflow currently treats explicit Lead closure after canonical archive reconstruction as the normal final coordination transition. During Issue #18, implementation PR #19 unintentionally used GitHub closing linkage and caused the coordination Issue to complete at implementation merge, before archive review and merge. The Issue had to be reopened to restore the legal lifecycle.

GitHub's native linked-PR completion behavior is useful when bound to the correct lifecycle boundary. The repository should make it intentional: implementation PRs must not close the persistent coordination Issue, while the final Archive PR should carry the approved closing linkage so successful authorized archive merge completes the Issue as a native platform side effect.

## What Changes

- Require implementation and implementation-correction PRs to reference, but not establish closing linkage to, the persistent coordination Issue.
- Require the final Archive PR for a normal change to establish exactly the repository-approved closing linkage to its coordination Issue.
- Preserve the existing archive merge gate: Reviewer archive PASS for revision R, Lead `MERGE_AUTHORIZED` for R, current archive PR head R, and Executor unchanged-head/current-gate preconditions.
- Treat native Issue completion caused by the authorized Archive PR merge as the normal final lifecycle side effect, not as merge authorization or review evidence.
- Keep `Lead / finalize-archive` responsible for reconstructing canonical archived default-branch state and observing the coordination Issue completed before declaring lifecycle completion.
- Define recovery for a missing native completion side effect: when canonical archive state is correct, the authorized archive PR is merged, and the coordination Issue remains open, Lead may perform the existing explicit Issue-close mutation and then re-observe closed state.
- Treat premature Issue completion before authorized archive merge as an illegal lifecycle state that must fail closed and be recovered before normal work continues; closing linkage on an implementation PR is therefore a contract violation.
- Retain one persistent coordination Issue, the existing nine normal actions, and repository-owned archive automation. No second workflow engine or progress state is introduced.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scheduled-agent-workflow`: refine PR linkage, archive merge, final Issue completion, and recovery semantics so native GitHub Issue completion occurs only at the final archive boundary.

## Scope Boundaries

This change does not alter Strategy, market-data, Decision, Backtest, execution, or portfolio behavior. It does not add a new scheduled action, archive engine, lock, lease, progress state, or Human-admission mechanism. It does not change the revision-bound Reviewer/Lead/Executor merge authority model.

## Impact

Expected affected areas are the scheduled-agent canonical specification, `agents/AGENTS.md`, lifecycle/merge/archive skills, README lifecycle documentation, PR/archive automation or templates where needed to make linkage deterministic, and focused repository contract tests.