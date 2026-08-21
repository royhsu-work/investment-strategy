---
name: lifecycle-finalize
description: Reconstruct and advance post-merge and terminal OpenSpec lifecycle state for Lead / finalize-change and Lead / finalize-archive without performing PR merges or normal archive mutation.
---

# Lifecycle Finalize Skill

Mapped actions: `Lead / finalize-change`, `Lead / finalize-archive`.

These are lifecycle judgment actions. They do not execute PR merges and do not duplicate normal OpenSpec
archive mechanics.

## Shared reconstruction

Read default-branch governance and Lead role, the coordination Issue and immutable `Change:`, current
PR/default-branch/OpenSpec/Actions state, revision-bound Reviewer evidence, current task/completion state,
and applicable durable lifecycle evidence.

Stale, missing, contradictory, or revision-mismatched gate evidence fails closed.

Before either action persists a materially consequential lifecycle result or transfers ownership, consume
the shared `agents/AGENTS.md` substantive Human-input freshness/disposition invariant. Newer material
direct-Human input that could affect lifecycle judgment, preparation, scope, or terminal assumptions must
have a reconstructable exact-comment disposition or be routed to the legal owner/Human boundary. This
Skill does not redefine the shared classifier or expand Lead authority.

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
non-closing `Refs #<coordination-issue>` linkage. If an equivalent open Archive PR already exists, Lead
reuses it only when branch/base/linkage are current, unambiguous, non-closing, and non-contradictory. A
successful validated branch awaiting this PR creation is normal success, not `RECOVERY_DECISION_REQUIRED`.

### Archive preparation before independent review

The preparation below is complete before `Reviewer / review-archive`. Lead prepares the final Archive
target by reconstructing every still-applicable approved required deferred follow-up or required
separate-follow-up obligation and the same routing-complete required-follow-up postcondition owned by the
approved Lead producer: one source-linked tracker with the exact source coordination Issue/Change and defer
decision/reference, `Change: unset`, and canonical `agent:lead + action:explore-change` routing.

Lead reconstructs the approved source obligation and all matching trackers before any repair. If no
matching tracker exists, Lead may idempotently create exactly one tracker and complete that postcondition.
If exactly one matching incomplete required tracker exists and the authoritative approved source obligation
remains reconstructable, Lead may reuse it and repair only its missing durable fields or canonical routing;
it does not create a duplicate. Multiple or ambiguous matching trackers fail closed, as does missing or
contradictory source authority. Tracker prose is evidence only and never supplies missing admission or
routing authority. After any create or repair, Lead fresh-reads the tracker and treats preparation as
satisfied only when the complete postcondition is durably observable. Ordinary out-of-scope, non-goal,
optional, or merely deferred prose creates no materialization or routing obligation.

This is fail-safe reconstruction of the existing Lead-owned producer contract, not a second admission or
dispatcher model. Lifecycle preparation never infers workflow routing from prose and does not broaden which
future work is required.

Lead also reconstructs only separately workflow-owned temporary correction/recovery branches identified by
explicit durable lifecycle, correction, integration, or recovery provenance. The normal validated
`agent/archive-<change>` branch is a lifecycle artifact and is never inferred to be temporary merely from
its name. For each provenance-owned temporary correction/recovery branch, Lead classifies the known
terminal cleanup obligations and pre-merge disposition from current durable evidence as exactly one of:

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

Only after the final Archive PR and all applicable preparation evidence are current and reconstructable,
and the shared substantive Human-input freshness/disposition check is clear, may Lead persist
`ARCHIVE_PR_READY` and route to `Reviewer / review-archive`. The Archive PR's non-closing linkage preserves
traceability while intentionally keeping the persistent coordination Issue open; it never substitutes for
independent Reviewer PASS, Executor merge preconditions, or terminal `finalize-archive` reconstruction.

Archive waiting begins only after merged default-branch state satisfies the existing README archive
eligibility contract.

## `finalize-archive`

`finalize-archive` is a post-merge terminal reconstruction action. It does not perform a hidden pre-merge
acceptance or authorization phase. Archive lifecycle preparation already occurred before
`Reviewer / review-archive`; Reviewer PASS then routed the exact reviewed Archive revision to
`Executor / merge-pr`, which owns the final fresh-read operational merge and any predeclared safe cleanup
mutation. Normal Archive merge leaves the persistent coordination Issue open and hands this action that
same open Issue.

After Archive merge, or when reconstructing interrupted finalization, Lead reconstructs:

1. the exact Archive PR head revision R that received the applicable Reviewer archive `PASS`, including the
   materially reviewed preparation meaning;
2. the Archive PR merge result proving R was merged and the merge did not proceed from a later unreviewed
   head;
3. canonical archived default-branch state, removal of the active Change as intended, and the preserved
   dated archive history;
4. the persistent coordination Issue and its current open/closed state;
5. every still-applicable required deferred follow-up tracker that was prepared before review; and
6. the pre-merge cleanup/retention outcome for every explicitly prepared temporary correction/recovery
   obligation, including Executor evidence for any safe deletion that had to occur before Archive merge.

Discovery after PASS of a new required obligation, contradictory tracker state, materially changed
cleanup/retention classification, or other preparation meaning that was not independently reviewed fails
closed. Lead does not reinterpret such evidence as terminal completion.

The normal terminal invariant is `open coordination Issue = formal workflow not yet terminal` and
`closed coordination Issue = terminal history`. Archive merge alone therefore cannot make the workflow
terminal. If the Issue is observed closed before a valid terminal `LIFECYCLE_COMPLETE` result exists, that
closure is premature and must fail closed into the repository's bounded premature-close recovery contract;
it must not be accepted as successful archive completion.

When the reviewed Archive PR is merged, canonical archive state and prepared obligations are correct, the
coordination Issue is open, and the shared substantive Human-input freshness/disposition check is clear,
Lead first persists one bounded `LIFECYCLE_COMPLETE` result. That result identifies the Archive PR exact
head, merge commit, canonical archived default-branch state, reconstructed required deferred follow-up
tracker state, reconstructed pre-merge temporary correction/recovery cleanup/retention outcome, and states
that terminal verification succeeded while the Issue was still open.

Only after `LIFECYCLE_COMPLETE` is durable may Lead perform the GitHub coordination Issue close mutation.
Lead then fresh-reads the same Issue and requires observed `closed` before declaring the workflow terminal.
The close is the durable final lifecycle transition; a successful close without re-observation is an
interrupted-finalization boundary, not permission to invent another completion result.

Crash/interruption recovery is idempotent and reconstruction-based:

- Archive merged but `LIFECYCLE_COMPLETE` absent and Issue open → reconstruct terminal conditions, persist
  the one missing completion result, then continue to close.
- valid `LIFECYCLE_COMPLETE` already durable but Issue still open → do not rewrite the result; perform only
  the missing close mutation, then re-observe `closed`.
- valid `LIFECYCLE_COMPLETE` durable and Issue already closed → terminal history; do not reopen, rewrite the
  result, or replay the close mutation.
- Issue closed without valid `LIFECYCLE_COMPLETE` → premature-close contradiction; use only the shared
  bounded recovery predicate and never treat the closed state itself as terminal success.

If the close mutation succeeds and the invocation stops before re-observation, a later Lead run reconstructs
the existing `LIFECYCLE_COMPLETE` plus current Issue state and performs only the missing observation/journal
work. This action does not introduce terminal-pending happy-path state, a completion label, or hidden
finalization registry.

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
