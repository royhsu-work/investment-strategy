# Lifecycle Finalize Skill

Mapped actions: `Lead / finalize-change`, `Lead / finalize-archive`.

These are judgment/authorization actions. They do not execute PR merges and do not duplicate normal
OpenSpec archive mechanics.

## Shared reconstruction

Read default-branch governance and Lead role, the coordination Issue and immutable `Change:`, current
PR/default-branch/OpenSpec/Actions state, revision-bound Reviewer evidence, current task/completion state,
and any prior Lead authorization for the relevant revision.

Stale, missing, contradictory, or revision-mismatched gate evidence fails closed.

If the coordination Issue is already closed, reconstruct whether that closure followed the authorized
final Archive PR merge and canonical archive transition. Closure before the authorized Archive PR merge
is premature lifecycle completion: fail closed, retain Lead/recovery ownership, and must not be treated as successful completion.

## `finalize-change`

Before merge authorization:

1. Identify the exact current implementation PR head revision R.
2. Require an unambiguous Reviewer implementation `PASS` for R.
3. Recheck that R is still current and required gates remain valid/non-contradictory.
4. If authorization is legal, persist `MERGE_AUTHORIZED` explicitly bound to R before handoff.

Legal pre-merge outcomes:

- `MERGE_AUTHORIZED` → `Executor / merge-pr` for exactly revision R.
- stale/contradictory/changed gate → retain/return Lead; do not authorize.

After merge (or when reconstructing a merge already completed), inspect merged default-branch OpenSpec
state:

- active change incomplete and approved work remains → `MORE_IMPLEMENTATION_REQUIRED` →
  `Executor / implement-change`;
- change is Complete/eligible and normal archive automation is progressing →
  `WAITING_FOR_ARCHIVE_AUTOMATION`; retain Lead without creating competing archive work;
- durable Archive PR is ready → `ARCHIVE_PR_READY` → `Reviewer / review-archive`;
- archive automation failed/unsupported → `RECOVERY_DECISION_REQUIRED`; use only repository-defined
  recovery/manual paths.

Archive waiting begins only after merged default-branch state satisfies the existing README archive
eligibility contract.

## `finalize-archive`

Before archive PR merge authorization:

1. Identify the exact current archive PR head revision R.
2. Require an unambiguous Reviewer archive `PASS` for R.
3. Recheck current head and gate state.
4. Persist archive `MERGE_AUTHORIZED` bound to R before `Executor / merge-pr` handoff.

After archive merge (or when reconstructing a merge already completed):

1. Reconstruct the exact authorized Archive PR merge, canonical default-branch OpenSpec state, and dated
   archive history.
2. Confirm final lifecycle conditions are actually satisfied for the immutable change id.
3. If the Issue was observed closed before the authorized Archive PR merge, treat it as premature,
   fail closed, and must not be treated as successful completion.
4. If final archive state is incomplete or contradictory, retain Lead/recovery ownership; do not infer
   completion from comments or Issue state alone.
5. When the authorized Archive PR is merged and canonical archive state is correct, first observe the
   expected native Issue completion caused by the Archive PR closing linkage.
6. If the Issue is observed closed, record completion without executing another Issue-close mutation.
7. Only when the authorized Archive PR is merged, canonical archive state is correct, and native
   completion is missing, perform the explicit Issue-close recovery mutation.
8. Re-read the Issue and require observed `closed` state before declaring the coordination lifecycle
   complete.

Legal post-merge outcomes:

- `ARCHIVE_CONFIRMED_ON_DEFAULT_BRANCH` + expected native Issue completion observed closed → lifecycle
  complete;
- authorized Archive PR merged + canonical archive state correct + native completion is missing →
  explicit Issue-close recovery, then require observed closed;
- premature Issue closure before authorized Archive PR merge → fail closed; must not be treated as
  successful completion.

If the run stops after archive completion but before the expected native close is observed, routing
remains `Lead / finalize-archive`; a later run reconstructs final state. Explicit close is recovery only,
not the normal completion mutation.

## Handoff and concurrency safety

Persist authorization/result evidence before routing. Fresh-read routing before handoff. A fresh read
followed by a label update is not CAS/mutex/single-flight; overlapping Lead runs must recheck unsafe
preconditions and stop on changed or contradictory durable state.
