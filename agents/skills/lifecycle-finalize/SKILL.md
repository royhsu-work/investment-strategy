# Lifecycle Finalize Skill

Mapped actions: `Lead / finalize-change`, `Lead / finalize-archive`.

These are judgment/authorization actions. They do not execute PR merges and do not duplicate normal
OpenSpec archive mechanics.

## Shared reconstruction

Read default-branch governance and Lead role, the coordination Issue and immutable `Change:`, current
PR/default-branch/OpenSpec/Actions state, revision-bound Reviewer evidence, current task/completion state,
and any prior Lead authorization for the relevant revision.

Stale, missing, contradictory, or revision-mismatched gate evidence fails closed.

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

1. Reconstruct canonical default-branch OpenSpec state and dated archive history.
2. Confirm final lifecycle conditions are actually satisfied for the immutable change id.
3. If final state is not complete, retain Lead/recovery ownership; do not close from comments alone.
4. If final state is complete, perform the GitHub coordination Issue close mutation.
5. Re-read the Issue and require observed `closed` state before declaring the coordination lifecycle
   complete.

Legal post-merge outcome:

- `ARCHIVE_CONFIRMED_ON_DEFAULT_BRANCH` + observed closed Issue → lifecycle complete.

If the run stops after archive completion but before Issue closure, routing remains
`Lead / finalize-archive`; a later run reconstructs final state and idempotently performs the missing
close.

## Handoff and concurrency safety

Persist authorization/result evidence before routing. Fresh-read routing before handoff. A fresh read
followed by a label update is not CAS/mutex/single-flight; overlapping Lead runs must recheck unsafe
preconditions and stop on changed or contradictory durable state.
