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

Lead performs the cleanup reconstruction before archive `MERGE_AUTHORIZED`: it must reconstruct both the
exact archive gate and any known terminal cleanup obligations that would become unreachable after the
final Archive PR native-closes the coordination Issue.

1. Identify the exact current archive PR head revision R.
2. Require an unambiguous Reviewer archive `PASS` for R.
3. Recheck current head and gate state.
4. Reconstruct workflow-owned temporary integration/recovery branches from durable Issue/PR/recovery
   provenance. For each known branch, fresh-read current branch existence, open PR head/base usage,
   active recovery/integration references, and containment against canonical `main` or an explicitly
   retained successor.
5. Classify known terminal cleanup obligations without performing the Executor-owned delete. A branch
   that is unused, has no unique commits, is not an open PR head/base, and is not active recovery input is
   a safely deletable obligation that Executor must retire before the final Archive PR merge mutation.
   A branch that is intentionally retained needs a durable reconstructable reason and a legal next owner.
   Unique commits, active use, ambiguous ownership/use, or unavailable proof fail closed to the legal
   diagnosis owner rather than being silently discarded.
6. Persist archive `MERGE_AUTHORIZED` bound to R only after the known obligations are reconstructable and
   the authorization explicitly requires `Executor / merge-pr` to clear any safely deletable temporary
   integration/recovery branch before merging R.

The authorization is revision-bound and cleanup-precondition-bound. It does not authorize broad
`agent/*` garbage collection, force deletion, deletion of normal feature/archive PR heads, or cleanup of
branches without durable workflow provenance.

After archive merge, or when reconstructing the narrow closed-Issue terminal handoff, Lead reconstructs
canonical archived default-branch state, the authorized Archive PR exact head, its merge commit, observed
native Issue closure, and the cleanup evidence produced before that merge. A closed Issue with
`agent:lead + action:finalize-archive` is eligible only when that matching authorized merged-archive/native-
close evidence exists and no valid Lead `LIFECYCLE_COMPLETE` result already exists.

The normal path first observes the expected native Issue completion and requires the Issue to be observed
closed. The observed `closed` state is mandatory. If Issue closure is observed before the authorized
Archive PR merge, that closure is premature and must fail closed; it must not be treated as successful
archive completion.

When final conditions are satisfied, Lead persists one bounded `LIFECYCLE_COMPLETE` result that
identifies the Archive PR exact head, merge commit, canonical archived default-branch state, observed
native Issue closure, and the reconstructed pre-merge temporary-branch cleanup/retention outcome. Lead
verifies the terminal invariant but does not replay an Executor-owned deletion after native close, and
does not reopen or redundantly close the Issue when native closure is already present.

Only when the authorized Archive PR is merged, canonical archive state is correct, and native completion
is missing may Lead use explicit Issue-close recovery. In that recovery-only path, Lead may perform the
GitHub coordination Issue close mutation and must re-observe `closed` before persisting
`LIFECYCLE_COMPLETE`.

If a recovery run is interrupted after archive completion but before the recovery close, the next Lead
run reconstructs the completed archive and idempotently performs the missing close recovery only when
native completion is still absent. Normal native-close finalization never performs that redundant close.

If the run stops after archive merge/native close but before the bounded completion result, a later Lead
run reconstructs the same terminal evidence and persists only the missing result. A valid existing
`LIFECYCLE_COMPLETE` makes the closed tuple terminal history rather than eligible work.

## Durable messages

Use `agents/templates/messages.md` for recurring durable presentation. Lead merge authorization uses
`MERGE_AUTHORIZATION`; non-review lifecycle outcomes including terminal `LIFECYCLE_COMPLETE` use the
applicable `ACTION_RESULT`; and completed routing transfer uses canonical `HANDOFF` only after the routing
mutation succeeds. Do not duplicate the shared template bodies here.

## Handoff and concurrency safety

Persist authorization/result evidence before routing. Material workflow lifecycle transitions use the
shared bounded coordination-Issue journal contract. Fresh-read routing before handoff. A fresh read
followed by a label update is not CAS/mutex/single-flight; overlapping Lead runs must recheck unsafe
preconditions and stop on changed or contradictory durable state.
