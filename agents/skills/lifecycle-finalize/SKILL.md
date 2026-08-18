# Lifecycle Finalize Skill

Mapped actions: `Lead / finalize-change`, `Lead / finalize-archive`.

These are lifecycle judgment actions. They do not execute PR merges and do not duplicate normal OpenSpec
archive mechanics.

## Shared reconstruction

Read default-branch governance and Lead role, the coordination Issue and immutable `Change:`, current
PR/default-branch/OpenSpec/Actions state, revision-bound Reviewer evidence, current task/completion state,
and applicable durable lifecycle evidence.

Stale, missing, contradictory, or revision-mismatched gate evidence fails closed.

## `finalize-change`

Normal implementation acceptance no longer enters this action before merge. An exact-head
`Reviewer / review-implementation` `PASS` routes to `Executor / merge-pr`; Executor owns the mutation-time
unchanged-head, current-check, non-closing-linkage, and contradiction checks. `finalize-change` remains the
post-implementation-merge lifecycle owner.

After implementation merge (or when reconstructing a merge already completed), inspect merged
default-branch OpenSpec, archive automation, archive-branch, and Archive-PR state:

- active change incomplete and approved work remains → `MORE_IMPLEMENTATION_REQUIRED` →
  `Executor / implement-change`;
- change is Complete/eligible and normal archive automation is still progressing →
  `WAITING_FOR_ARCHIVE_AUTOMATION`; retain Lead without creating competing archive work;
- archive automation has terminally failed before validated branch readiness, or branch ownership/state is
  contradictory or unreconstructable → `RECOVERY_DECISION_REQUIRED`; use only repository-defined
  recovery/manual paths;
- validated `agent/archive-<change>` branch is durably ready → reconstruct the exact branch and persistent
  coordination Issue, then create or reuse the final Archive PR as ordinary lifecycle continuation.

For normal branch-ready continuation, Lead MUST NOT rerun OpenSpec archive mutation. Lead fresh-reads the
validated archive branch, `main`, the coordination Issue, and existing PRs for that branch. If no equivalent
final Archive PR exists, Lead creates one from `agent/archive-<change>` to `main` with deterministic
`Closes #<coordination-issue>` linkage. If an equivalent open Archive PR already exists, Lead reuses it only
when branch/base/linkage are current, unambiguous, and non-contradictory. A successful validated branch
awaiting this PR creation is normal success, not `RECOVERY_DECISION_REQUIRED`.

Only after the durable final Archive PR is present and valid may Lead persist `ARCHIVE_PR_READY` and route
to `Reviewer / review-archive`. Closing linkage identifies lifecycle completion intent but never substitutes
for Reviewer PASS, the current archive acceptance contract, Executor merge preconditions, native Issue
close, or terminal `finalize-archive` reconstruction.

Archive waiting begins only after merged default-branch state satisfies the existing README archive
eligibility contract.

## `finalize-archive`

Under the current default-branch archive boundary, Lead performs cleanup reconstruction before archive
`MERGE_AUTHORIZED`: it must reconstruct both the exact archive gate and any known terminal cleanup
obligations that would become unreachable after the final Archive PR native-closes the coordination Issue.
The approved later slices of the active change move this preparation before archive review; until those
slices are implemented and verified, this archive-only boundary remains unchanged.

Before any archive `MERGE_AUTHORIZED` or `LIFECYCLE_COMPLETE`, Lead also reconstructs every still-applicable
approved required deferred follow-up obligation. Each such obligation must have a durable tracker linked to
the source coordination Issue/Change and exact defer decision/reference. If the obligation meaning is
unambiguous and the only missing work is the tracker write, Lead may idempotently create or reuse that
tracker using the same Lead-owned tracking contract; the tracker MUST NOT be Human-admitted or receive
workflow routing. If scope meaning, applicability, or linkage is ambiguous, fail closed to the legal
specification/Human boundary instead of inventing a tracker. Missing still-applicable required deferred
follow-up tracking blocks lifecycle completion. Ordinary out-of-scope/non-goal/optional future work creates
no such obligation.

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

The archive authorization is revision-bound and cleanup-precondition-bound. It does not authorize broad
`agent/*` garbage collection, force deletion, deletion of normal feature/archive PR heads, or cleanup of
branches without durable workflow provenance.

After archive merge, or when reconstructing the narrow closed-Issue terminal handoff, Lead reconstructs
canonical archived default-branch state, the accepted Archive PR exact head, its merge commit, observed
native Issue closure, and the cleanup evidence produced before that merge. A closed Issue with
`agent:lead + action:finalize-archive` is eligible only when that matching merged-archive/native-close
evidence exists and no valid Lead `LIFECYCLE_COMPLETE` result already exists.

The normal path first observes the expected native Issue completion and requires the Issue to be observed
closed. The observed `closed` state is mandatory. If Issue closure is observed before the accepted Archive
PR merge, that closure is premature and must fail closed; it must not be treated as successful archive
completion.

When final conditions are satisfied, Lead persists one bounded `LIFECYCLE_COMPLETE` result that identifies
the Archive PR exact head, merge commit, canonical archived default-branch state, observed native Issue
closure, the reconstructed required deferred follow-up tracker state, and the reconstructed pre-merge
temporary-branch cleanup/retention outcome. Lead verifies the terminal invariant but does not replay an
Executor-owned deletion after native close, and does not reopen or redundantly close the Issue when native
closure is already present.

Only when the accepted Archive PR is merged, canonical archive state is correct, and native completion is
missing may Lead use explicit Issue-close recovery. In that recovery-only path, Lead may perform the GitHub
coordination Issue close mutation and must re-observe `closed` before persisting `LIFECYCLE_COMPLETE`.

If a recovery run is interrupted after archive completion but before the recovery close, the next Lead run
reconstructs the completed archive and idempotently performs the missing close recovery only when native
completion is still absent. Normal native-close finalization never performs that redundant close.

If the run stops after archive merge/native close but before the bounded completion result, a later Lead
run reconstructs the same terminal evidence and persists only the missing result. A valid existing
`LIFECYCLE_COMPLETE` makes the closed tuple terminal history rather than eligible work.

## Durable messages

Use `agents/templates/messages.md` for recurring durable presentation. Archive-only Lead merge authorization
uses `MERGE_AUTHORIZATION` while that current archive boundary remains active; non-review lifecycle outcomes
including terminal `LIFECYCLE_COMPLETE` use the applicable `ACTION_RESULT`; completed routing transfer uses
canonical `HANDOFF` only after the routing mutation succeeds. Do not duplicate the shared template bodies
here.

## Handoff and concurrency safety

Persist result/required evidence before routing. Material workflow lifecycle transitions use the shared
bounded coordination-Issue journal contract. Fresh-read routing before handoff. A fresh read followed by a
label update is not CAS/mutex/single-flight; overlapping Lead runs must recheck unsafe preconditions and
stop on changed or contradictory durable state.
