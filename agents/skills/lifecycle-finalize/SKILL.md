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

After archive merge, or when reconstructing the narrow closed-Issue terminal handoff, Lead reconstructs
canonical archived default-branch state, the authorized Archive PR exact head, its merge commit, and
observed native Issue closure. A closed Issue with `agent:lead + action:finalize-archive` is eligible only
when that matching authorized merged-archive/native-close evidence exists and no valid Lead
`LIFECYCLE_COMPLETE` result already exists.

When those final conditions are satisfied, Lead persists one bounded `LIFECYCLE_COMPLETE` result that
identifies the Archive PR exact head, merge commit, canonical archived default-branch state, and observed
native Issue closure. This result is durable execution evidence only; canonical completion still depends
on the authorized archive merge, correct archived state, and observed `closed` state. Lead does not reopen
or redundantly close the Issue when native closure is already present; in other words, finalization does
not reopen or redundantly close the Issue.

If canonical archive state is correct after the authorized merge but native close is unexpectedly
missing, explicit Issue close remains recovery-only. In that recovery-only path, Lead may perform the GitHub coordination Issue close mutation and must re-observe `closed` before persisting
`LIFECYCLE_COMPLETE`.

If a recovery run is interrupted after archive completion but before the recovery close, the next Lead
run reconstructs the completed archive and idempotently performs the missing close recovery only when
native completion is still absent. Normal native-close finalization never performs that redundant close.

If the run stops after archive merge/native close but before the bounded completion result, a later Lead
run reconstructs the same terminal evidence and persists only the missing result. A valid existing
`LIFECYCLE_COMPLETE` makes the closed tuple terminal history rather than eligible work.

## Handoff and concurrency safety

Persist authorization/result evidence before routing. Material workflow lifecycle transitions use the
shared bounded coordination-Issue journal contract. Fresh-read routing before handoff. A fresh read
followed by a label update is not CAS/mutex/single-flight; overlapping Lead runs must recheck unsafe
preconditions and stop on changed or contradictory durable state.
