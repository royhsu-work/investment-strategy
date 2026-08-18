# Merge PR Skill

Mapped action: `Executor / merge-pr`.

The same operational action executes implementation and archive PR merges. Lifecycle-specific preparation
and next routing are reconstructed from the target type rather than encoded as a second merge action.

## Reconstruct before acting

Read default-branch governance and Executor role, the coordination Issue and immutable `Change:`, the
target PR and exact current head revision R, durable Reviewer gate evidence, current required gate/check
state, and whether the target is an implementation/implementation-correction PR or the final Archive PR.

For an implementation or implementation-correction PR, the applicable normal acceptance evidence is an
unambiguous `Reviewer / review-implementation` `PASS` bound to R.

For the final Archive PR, the applicable normal acceptance evidence is an unambiguous
`Reviewer / review-archive` `PASS` bound to R and the materially reviewed Lead preparation evidence. Also
reconstruct the expected persistent coordination Issue, verify the PR body establishes the
repository-approved closing linkage to that same Issue, and reconstruct only the explicitly
provenance-owned temporary correction/recovery branches and dispositions reviewed with the Archive target.
The normal `agent/archive-<change>` branch is the final PR source lifecycle artifact and is never a temporary
cleanup target merely because of its name. Closing linkage is structural lifecycle evidence only and never
substitutes for Reviewer PASS or the other merge preconditions.

## Merge preconditions

Execute a merge mutation only when all applicable conditions are simultaneously true and unambiguous:

1. Reviewer `PASS` exists for the exact revision R under the required implementation/archive gate.
2. The target PR current head still equals R.
3. Required gates/checks remain valid and there is no contradictory current evidence.
4. For an implementation or implementation-correction PR, the PR does not establish GitHub Issue-closing
   linkage to its persistent coordination Issue; it uses only a non-closing reference.
5. For the final Archive PR, the PR establishes exactly the repository-approved closing linkage to the same
   persistent coordination Issue reconstructed for the immutable change identity.
6. For the final Archive PR, the Lead preparation evidence reviewed with PASS remains materially current:
   required deferred/separate-follow-up tracker state has not become contradictory, no new required
   obligation has appeared, and no reviewed cleanup/retention classification has materially changed.
7. For the final Archive PR, every predeclared safely deletable temporary correction/recovery branch
   obligation is cleared immediately before merge, while every intentionally retained obligation still has
   its reviewed legal durable reason and owner.

A PASS for an earlier head is insufficient. A current PASS never waives unchanged-head, current-check,
linkage, lifecycle-preparation, cleanup, or contradiction checks. No separate Lead merge-authorization token
is required on either normal implementation or final Archive paths.

A closing linkage on an implementation or implementation-correction PR is a lifecycle-contract violation.
Even when every other gate is current, do not merge that PR; persist the violation and hand control to Lead
for correction. Closing linkage is reserved for the final Archive PR and never provides merge authority by
itself.

A final Archive PR with missing, ambiguous, or wrong-Issue closing linkage also fails closed. Do not merge
until the Archive PR identifies the same persistent coordination Issue and carries the repository-approved
closing linkage while all independent revision-bound gates and reviewed lifecycle preparation remain
current.

## Final Archive pre-close temporary branch cleanup

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

This is pre-close lifecycle hygiene, not broad branch garbage collection. Executor must not force-delete,
force-update, classify an arbitrary branch as temporary, or infer cleanup ownership from an `agent/*` name
pattern.

Legal pre-merge outcomes:

- all applicable preconditions current and reviewed final-Archive cleanup obligations cleared/retained as
  prepared → merge exactly R;
- stale exact-head PASS or changed/contradictory check state → do not merge; return to the legal review or
  correction owner;
- materially new/changed Archive lifecycle preparation evidence → do not merge; return to Lead and require
  renewed review when the reviewed meaning changed;
- implementation PR contains coordination-Issue closing linkage → `LIFECYCLE_CONTRACT_VIOLATION`; do not
  merge and hand control to Lead;
- final Archive PR has missing/ambiguous/wrong coordination-Issue closing linkage →
  `LIFECYCLE_CONTRACT_VIOLATION`; do not merge and hand control to Lead;
- final Archive cleanup obligation blocked/unsafe/unavailable → do not merge; keep the coordination Issue
  open and use existing exception/disposition/Lead-diagnosis semantics.

## Crash-safe merge recovery

Before attempting the mutation, reconstruct whether the explicitly accepted PR/revision has already been
merged. If already merged, do not retry the merge; persist/complete only missing handoff evidence.

After a successful or already-completed implementation PR merge, reconstruct durable repository state,
persist bounded merge-result journal evidence, and hand to `Lead / finalize-change`.

For a final Archive PR, after a successful merge or when reconstructing a merge already completed:

1. Fresh-read the Archive PR and persistent coordination Issue.
2. If the Archive PR is durably merged and the coordination Issue is observed natively `closed` through
   the repository-approved closing linkage, replace the consumed routing tuple with exactly
   `agent:lead + action:finalize-archive` on that closed Issue.
3. Persist one bounded merge/native-close/handoff journal on the coordination Issue identifying the exact
   accepted head, merge result, observed native closure, and terminal Lead handoff.
4. End the invocation. Executor MUST NOT execute Lead finalization in the same invocation.

If an accepted Archive PR is already merged and the Issue is natively closed but a prior Executor run
stopped before terminal handoff, do not re-merge. Reconstruct the exact accepted merge/native-close evidence
and repair only the missing terminal routing and journal evidence; do not replay a completed merge mutation.

If the Archive PR is durably merged but native closure is not observed, do not infer lifecycle completion.
Journal the durable merge/result and hand to `Lead / finalize-archive` for repository-defined native-close
recovery/final reconstruction.

Do not infer downstream completion merely from a successful merge response; Lead owns lifecycle judgment
after merged default-branch state is reconstructed.

## Durable messages

Use `agents/templates/messages.md` for recurring durable presentation. Merge success or action-defined
merge blocker evidence uses `MERGE_RESULT`; completed ownership transfer uses canonical `HANDOFF` only after
routing mutation succeeds. A typed `MERGE_RESULT` that directly represents the PR-merge lifecycle boundary
satisfies that one lifecycle journal record and does not require a duplicate generic journal.

## Mutation safety

Every substantive merge/routing mutation follows the shared bounded coordination-Issue journal contract.
A successful durable mutation whose journal write was interrupted is reconstructed rather than replayed;
the missing journal is persisted before further substantive mutation or handoff.

Persist merge result evidence before routing. Fresh-read Issue routing immediately before handoff and do
not overwrite a newer tuple. `fresh-read routing → update labels` is not a mutex or CAS primitive; unsafe
merge decisions rely on exact-revision preconditions, not routing-write serialization.
