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

Normal implementation acceptance no longer enters this action before merge. Reviewer implementation `PASS`
for the exact current implementation PR head routes to `Executor / merge-pr`; Executor owns the
mutation-time unchanged-head, current-check, non-closing-linkage, and contradiction checks.
`finalize-change` remains the post-implementation-merge lifecycle owner.

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

### Archive preparation before independent review

The preparation below is complete before `Reviewer / review-archive`. Lead prepares the final Archive
target by reconstructing every still-applicable approved required deferred follow-up or required
separate-follow-up obligation and proving that each obligation has a durable tracker linked to the source
coordination Issue/Change and exact defer decision/reference. If the only missing work is an unambiguous
tracker write, Lead may idempotently create or reuse that tracker under the existing Lead-owned tracking
contract. The tracker MUST NOT be Human-admitted or receive workflow routing. Ordinary out-of-scope,
non-goal, or optional future work creates no such obligation.

Lead also reconstructs only separately workflow-owned temporary correction/recovery branches identified by
explicit durable lifecycle, correction, integration, or recovery provenance. The normal validated
`agent/archive-<change>` branch is a lifecycle artifact and is never inferred to be temporary merely from
its name. For each provenance-owned temporary correction/recovery branch, Lead classifies the known
terminal cleanup obligations and pre-close disposition from current durable evidence as exactly one of:

- safely deletable by Executor immediately before Archive merge because the branch is not an open PR
  head/base, is not active correction/recovery input, and has no unique commits outside canonical `main` or
  an explicitly retained successor;
- intentionally retained with a durable reconstructable reason and legal next owner; or
- ambiguous/unsafe/unproven, which blocks Archive review readiness and fails closed to the legal diagnosis
  owner.

Lead performs lifecycle judgment only; it does not delete a branch. The preparation evidence is the
existing durable Issue/PR/recovery/tracker evidence and classifications themselves, not a replacement
acceptance token or hidden authorization record. Missing, contradictory, or materially ambiguous required
preparation means the final Archive PR is not review-ready.

Only after the final Archive PR and all applicable preparation evidence are current and reconstructable may
Lead persist `ARCHIVE_PR_READY` and route to `Reviewer / review-archive`. Closing linkage identifies
lifecycle completion intent but never substitutes for independent Reviewer PASS, Executor merge
preconditions, native Issue close, or terminal `finalize-archive` reconstruction.

Archive waiting begins only after merged default-branch state satisfies the existing README archive
eligibility contract.

## `finalize-archive`

`finalize-archive` is a post-merge/native-close terminal reconstruction action. It does not perform a hidden
pre-merge acceptance or authorization phase. Archive lifecycle preparation already occurred before
`Reviewer / review-archive`; Reviewer PASS then routed the exact reviewed Archive revision to
`Executor / merge-pr`, which owns the final fresh-read operational merge and any predeclared safe cleanup
mutation.

After Archive merge, or when reconstructing the narrow closed-Issue terminal handoff, Lead reconstructs:

1. the exact Archive PR head revision R that received the applicable Reviewer archive `PASS`, including the
   materially reviewed preparation meaning;
2. the Archive PR merge result proving R was merged and the merge did not proceed from a later unreviewed
   head;
3. canonical archived default-branch state, removal of the active Change as intended, and the preserved
   dated archive history;
4. observed native Issue closure through the repository-approved final closing linkage;
5. every still-applicable required deferred follow-up tracker that was prepared before review; and
6. the pre-merge cleanup/retention outcome for every explicitly prepared temporary correction/recovery
   obligation, including Executor evidence for any safe deletion that had to occur before native close.

Discovery after PASS of a new required obligation, contradictory tracker state, materially changed
cleanup/retention classification, or other preparation meaning that was not independently reviewed fails
closed. Lead does not reinterpret such evidence as terminal completion.

The normal path first observes the expected native Issue completion and requires the Issue to be observed
closed. The observed closed state and the observed `closed` state are mandatory. If Issue closure is
observed before the reviewed Archive PR merge, that closure is premature and must fail closed; it must not
be treated as successful archive completion. A premature close must not be treated as successful under any
completion-looking evidence.

When final conditions are satisfied, Lead persists one bounded `LIFECYCLE_COMPLETE` result that identifies
the Archive PR exact head, merge commit, canonical archived default-branch state, observed native Issue
closure, reconstructed required deferred follow-up tracker state, and reconstructed pre-merge temporary
correction/recovery cleanup/retention outcome. Lead verifies the terminal invariant but does not replay an
Executor-owned deletion after native close, and does not reopen or redundantly close the Issue when native
closure is already present.

Only when the reviewed Archive PR is merged, canonical archive state is correct, and native completion is
missing may Lead use explicit Issue-close recovery. In that recovery-only path, Lead may perform the GitHub
coordination Issue close mutation. This is the only path allowed to perform the GitHub coordination Issue
close mutation, and Lead must re-observe `closed` before persisting `LIFECYCLE_COMPLETE`.

If a recovery run is interrupted after archive completion but before the recovery close, the next Lead run
reconstructs the completed archive and idempotently performs the missing close recovery only when native
completion is still absent. Normal native-close finalization never performs that redundant close.

If the run stops after archive merge/native close but before the bounded completion result, a later Lead
run reconstructs the same terminal evidence and persists only the missing result. A valid existing
`LIFECYCLE_COMPLETE` makes the closed tuple terminal history rather than eligible work.

## Durable messages

Use `agents/templates/messages.md` for recurring durable presentation. Non-review lifecycle outcomes,
including `ARCHIVE_PR_READY` and terminal `LIFECYCLE_COMPLETE`, use the applicable `ACTION_RESULT`;
completed routing transfer uses canonical `HANDOFF` only after the routing mutation succeeds. Do not
introduce a replacement merge-authorization token or duplicate the shared template bodies here.

## Handoff and concurrency safety

Persist result/preparation evidence before routing. Material workflow lifecycle transitions use the shared
bounded coordination-Issue journal contract. Fresh-read routing before handoff. A fresh read followed by a
label update is not CAS/mutex/single-flight; overlapping Lead runs must recheck unsafe preconditions and
stop on changed or contradictory durable state.
