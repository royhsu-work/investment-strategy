---
name: merge-pr
description: Execute an exact accepted implementation or Archive PR merge for Executor / merge-pr after reconstructing current Reviewer PASS, checks, linkage, lifecycle preparation, and crash-recovery safety.
---

# Merge PR Skill

Mapped action: `Executor / merge-pr`.

The same operational action executes implementation and archive PR merges. Lifecycle-specific preparation
and next routing are reconstructed from the target type rather than encoded as a second merge action.

## Reconstruct before acting

Read default-branch governance and Executor role, the coordination Issue and immutable `Change:`, the
target PR and exact current head revision R, durable Reviewer gate evidence, current required gate/check
state, and whether the target is an implementation/implementation-correction PR or the final Archive PR.
Also reconstruct the selected merge strategy and the repository-owned deterministic native-closing
preflight surface. That preflight is the single executable classifier for GitHub-native textual closing
semantics; this Skill does not implement a second closing-keyword parser.

For an implementation or implementation-correction PR, the applicable normal acceptance evidence is an
unambiguous `Reviewer / review-implementation` `PASS` bound to R.

For the final Archive PR, the applicable normal acceptance evidence is an unambiguous
`Reviewer / review-archive` `PASS` bound to R and the materially reviewed Lead preparation evidence. Also
reconstruct the expected persistent coordination Issue, verify the PR body establishes the
repository-approved non-closing linkage (`Refs #<coordination-issue>` or its exact repository-approved
equivalent) to that same Issue, and reconstruct only the explicitly provenance-owned temporary
correction/recovery branches and dispositions reviewed with the Archive target. The normal
`agent/archive-<change>` branch is the final PR source lifecycle artifact and is never a temporary cleanup
target merely because of its name. Non-closing linkage is structural lifecycle evidence only and never
substitutes for Reviewer PASS, the executable native-closing preflight, or the other merge preconditions.

## Merge preconditions

Execute a merge mutation only when all applicable conditions are simultaneously true and unambiguous:

1. Reviewer `PASS` exists for the exact revision R under the required implementation/archive gate.
2. The target PR current head still equals R.
3. Required gates/checks remain valid and there is no contradictory current evidence.
4. For an implementation or implementation-correction PR, the PR establishes the repository-approved
   non-closing reference to its persistent coordination Issue.
5. For the final Archive PR, the PR establishes exactly the repository-approved non-closing linkage to the
   same persistent coordination Issue reconstructed for the immutable change identity.
6. Immediately before the merge mutation, obtain a fresh repository-owned deterministic native-closing
   preflight for the exact repository, persistent coordination Issue, PR, current head R, lifecycle context,
   selected merge strategy, complete included commit messages, and effective generated merge/squash
   presentation. The result must be complete, current, bound to those exact inputs, and allow the merge.
   Missing/ambiguous presentation, incomplete commit acquisition, a changed head/strategy/message input,
   or a rejecting result fails closed. Reviewer evidence may consume the same deterministic classifier, but
   an earlier review/preflight result never substitutes for this application-time evaluation.
7. For the final Archive PR, the Lead preparation evidence reviewed with PASS remains materially current:
   required deferred/separate-follow-up tracker state has not become contradictory, no new required
   obligation has appeared, and no reviewed cleanup/retention classification has materially changed.
8. For the final Archive PR, every predeclared safely deletable temporary correction/recovery branch
   obligation is cleared immediately before merge, while every intentionally retained obligation still has
   its reviewed legal durable reason and owner.
9. Immediately before the merge mutation, consume the shared `agents/AGENTS.md` substantive Human-input
   freshness/disposition invariant against the current coordination Issue. A newer material direct-Human
   comment that can affect the accepted gate, linkage, lifecycle preparation, or mutation assumptions must
   have a reconstructable exact-comment disposition; this Skill does not redefine the shared classifier or
   grant Human authority.

A PASS for an earlier head is insufficient. A current PASS never waives unchanged-head, current-check,
structural linkage, fresh native-closing preflight, lifecycle-preparation, cleanup, contradiction, or
substantive-Human-input freshness checks. No separate Lead merge-authorization token is required on either
normal implementation or final Archive paths.

A repository-owned native-closing preflight that detects an effective closing reference to the persistent
coordination Issue is a lifecycle-contract violation. Even when every other gate is current, do not merge
that PR. Persist the violation and hand control to Lead for correction. A missing, stale, incomplete, or
ambiguous preflight also fails closed rather than being treated as safe. Normal PRs in this lifecycle keep
the persistent coordination Issue open until `Lead / finalize-archive` has durably recorded
`LIFECYCLE_COMPLETE` and then performs terminal closure.

A final Archive PR with missing, ambiguous, or wrong-Issue structural non-closing linkage also fails closed.
Do not merge until it identifies the same persistent coordination Issue with the repository-approved
non-closing linkage while the shared native-closing preflight and all independent revision-bound gates and
reviewed lifecycle preparation remain current.

If a previously reviewed head or effective presentation is rejected by the native-closing preflight, any
correction creates a new exact acceptance target. The corrected head/presentation must re-enter the ordinary
exact-head review and required-check gates. This action does not infer authority to force-push, rewrite
history, change merge strategy as a waiver, or otherwise bypass the invariant.

## Final Archive pre-merge temporary branch cleanup

Immediately before the final Archive PR merge mutation, Executor processes only the explicitly identified
workflow-owned temporary correction/recovery branches whose dispositions were included in the Lead
preparation evidence independently reviewed with the target.

For each branch whose reviewed disposition requires safe deletion:

1. Fresh-read the branch, all open PR head/base usage, active correction/recovery references, and
   containment against canonical `main` or the explicitly retained successor used by the reviewed
   disposition.
2. Delete only when it is still the exact provenance-owned temporary correction/recovery branch, is not an
   open PR head or base, is not active correction/recovery input, and has no unique commits (`ahead_by == 0`
   or equivalent current containment proof).
3. After deletion, re-read enough durable state to prove the reviewed obligation is cleared before merging
   the final Archive PR.
4. If the branch has unique commits, active use, ambiguous ownership/use, unavailable proof, a denied
   cleanup mutation, or a materially changed disposition, do not merge. Preserve the observable failure;
   changed lifecycle meaning returns to Lead and requires renewed independent review when applicable.

This is pre-merge lifecycle hygiene, not broad branch garbage collection. Executor must not force-delete,
force-update, classify an arbitrary branch as temporary, or infer cleanup ownership from an `agent/*` name
pattern.

Legal pre-merge outcomes:

- all applicable preconditions current, fresh native-closing preflight allows the exact selected
  presentation, and reviewed final-Archive cleanup obligations are cleared/retained as prepared → merge
  exactly R;
- stale exact-head PASS or changed/contradictory check state → do not merge; return to the legal review or
  correction owner;
- native-closing preflight missing/stale/incomplete/ambiguous → do not merge; fail closed until a complete
  fresh exact-input result is available;
- native-closing preflight rejects the implementation/implementation-correction/final Archive presentation
  for the persistent coordination Issue → `LIFECYCLE_CONTRACT_VIOLATION`; do not merge and hand control to
  Lead for ordinary correction and re-gating;
- materially new/changed Archive lifecycle preparation evidence → do not merge; return to Lead and require
  renewed review when the reviewed meaning changed;
- final Archive PR has missing/ambiguous/wrong coordination-Issue non-closing linkage →
  `LIFECYCLE_CONTRACT_VIOLATION`; do not merge and hand control to Lead;
- final Archive cleanup obligation blocked/unsafe/unavailable → do not merge; keep the coordination Issue
  open and use existing exception/disposition/Lead-diagnosis semantics.

## Crash-safe merge recovery

Before attempting the mutation, reconstruct whether the explicitly accepted PR/revision has already been
merged. If already merged, do not retry the merge. Derive the exact recovered merge invocation from the
target PR type, accepted revision, applicable Reviewer PASS, merge result, and target-specific
linkage/preparation evidence before deciding whether any routing repair remains legal.

Recovery of an already-completed merge is transition-specific. Apply the shared causal-descendant
consumption guard before any routing mutation. Descendant evidence must belong to the same persistent
coordination Issue/Change and materially correspond to the specific recovered transition. Ambiguous or
contradictory descendant evidence fails closed. This specialization does not introduce new routing state
and preserves legitimate correction loops outside crash recovery of the exact completed transition.

For implementation merge recovery, valid causal descendants include a post-merge `Lead / finalize-change`
result for the recovered implementation merge and any valid descendants of that result, including a
validated Archive branch or Archive PR, `ARCHIVE_PR_READY`, archive review evidence, Archive merge evidence,
or terminal archive evidence. When any such descendant proves that the implementation-merge handoff was
already consumed, recovery MUST NOT route backward to `Lead / finalize-change`. It may repair only missing
non-routing journal evidence that remains required and non-contradictory.

For Archive merge recovery, valid causal descendants include `Lead / finalize-archive` evidence materially
bound to that exact Archive merge, especially a valid `LIFECYCLE_COMPLETE`. A closed Issue with valid
`LIFECYCLE_COMPLETE` is terminal history for that transition. Recovery MUST NOT recreate or rewrite terminal
routing; it may repair only missing non-routing journal evidence that remains required and non-contradictory.

When no causal descendant proves consumption and the expected post-merge routing/journal boundary is
actually incomplete, recovery may repair only that missing boundary after fresh-reading current routing and
all action-specific preconditions. It never replays the completed merge mutation.

After a successful or already-completed implementation PR merge whose transition is not already consumed,
reconstruct durable repository state, persist bounded merge-result journal evidence, and hand to
`Lead / finalize-change`.

For a final Archive PR, after a successful merge or when reconstructing a merge already completed and not
already consumed by terminal descendants:

1. Fresh-read the Archive PR and persistent coordination Issue.
2. Require the Archive PR to be durably merged at the exact accepted revision and require the coordination
   Issue to remain open. If the Issue is already closed without valid terminal `LIFECYCLE_COMPLETE`, treat
   that as premature-close contradiction/recovery input rather than successful Archive merge completion.
3. replace the consumed routing tuple with exactly `agent:lead + action:finalize-archive` on the open Issue.
4. Persist one bounded merge/handoff journal identifying the exact accepted head, merge result, observed
   open coordination Issue, and terminal Lead handoff.
5. End the invocation. Executor MUST NOT execute Lead finalization in the same invocation.

If an accepted Archive PR is already merged and the Issue remains open but a prior Executor run stopped
before terminal handoff, do not re-merge. Reconstruct the exact accepted merge evidence and repair only the
missing terminal routing and journal evidence when the transition-consumption guard proves that terminal
handoff is still incomplete.

If an accepted Archive PR is durably merged but the Issue is already closed without valid
`LIFECYCLE_COMPLETE`, do not infer lifecycle completion and do not silently reopen it from this action.
Preserve the contradictory evidence for the bounded repository-defined premature-close recovery owner.

Do not infer downstream completion merely from a successful merge response; Lead owns lifecycle judgment
after merged default-branch state is reconstructed. In particular, a successful final Archive merge is not
workflow terminal closure; `Lead / finalize-archive` retains exclusive normal ownership of
`LIFECYCLE_COMPLETE` and Issue closure.

## Durable messages

Use `agents/templates/messages.md` for recurring durable presentation. Merge success or action-defined
merge blocker evidence uses `MERGE_RESULT`; completed ownership transfer uses canonical `HANDOFF` only after
routing mutation succeeds. A typed `MERGE_RESULT` that directly represents the PR-merge lifecycle boundary
satisfies that one lifecycle journal record and does not require a duplicate generic journal.

## Mutation safety

Every substantive merge/routing mutation follows the shared bounded coordination-Issue journal contract.
A successful durable mutation whose journal write was interrupted is reconstructed rather than replayed;
the missing journal is persisted before further substantive mutation or handoff, subject to the shared
causal-descendant consumption guard before any routing repair.

Persist merge result evidence before routing. Fresh-read Issue routing immediately before handoff and do
not overwrite a newer tuple. `fresh-read routing → update labels` is not a mutex or CAS primitive; unsafe
merge decisions rely on exact-revision preconditions, not routing-write serialization.
