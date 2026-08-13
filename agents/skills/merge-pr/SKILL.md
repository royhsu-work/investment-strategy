# Merge PR Skill

Mapped action: `Executor / merge-pr`.

The same operational contract applies to implementation and archive PR merges. Lifecycle-specific next
routing is reconstructed after the merge rather than encoded as a second merge action.

## Reconstruct before acting

Read default-branch governance and Executor role, the coordination Issue and immutable `Change:`, the
target PR and exact current head revision R, durable Reviewer gate evidence, durable Lead
`MERGE_AUTHORIZED` evidence, current required gate/check state, and whether the target is an
implementation/implementation-correction PR or the final Archive PR.

For the final Archive PR, also reconstruct the expected persistent coordination Issue and verify the PR
body establishes the repository-approved closing linkage to that same Issue. The linkage is structural
lifecycle evidence only and never provides merge authority.

## Merge preconditions

Execute a merge mutation only when all are simultaneously true and unambiguous:

1. Reviewer `PASS` exists for the exact revision R under the required implementation/archive gate.
2. Lead `MERGE_AUTHORIZED` exists for the exact same revision R.
3. The target PR current head still equals R.
4. Required gates/checks remain valid and there is no contradictory current evidence.
5. For an implementation or implementation-correction PR, the PR does not establish GitHub Issue-closing linkage to its persistent coordination Issue; it uses only a non-closing reference.
6. For the final Archive PR, the PR establishes exactly the repository-approved closing linkage to the same persistent coordination Issue reconstructed for the immutable change identity.

Reviewer PASS alone is insufficient. Authorization for an earlier head is insufficient.

A closing linkage on an implementation or implementation-correction PR is a lifecycle-contract violation. Even when every other gate is current, do not merge that PR; persist the violation and hand
control to Lead for correction. Closing linkage is reserved for the final Archive PR and never provides
merge authority by itself.

A final Archive PR with missing, ambiguous, or wrong-Issue closing linkage also fails closed. Do not
merge until the Archive PR identifies the same persistent coordination Issue and carries the
repository-approved closing linkage while all independent revision-bound gates remain current.

Legal pre-merge outcomes:

- all preconditions current → merge exactly R;
- `STALE_AUTHORIZATION` or `GATE_CHANGED`/contradictory evidence → do not merge; hand control to Lead;
- implementation PR contains coordination-Issue closing linkage → `LIFECYCLE_CONTRACT_VIOLATION`; do
  not merge and hand control to Lead;
- final Archive PR has missing/ambiguous/wrong coordination-Issue closing linkage →
  `LIFECYCLE_CONTRACT_VIOLATION`; do not merge and hand control to Lead.

## Crash-safe merge recovery

Before attempting the mutation, reconstruct whether the explicitly authorized PR/revision has already
been merged. If already merged, do not retry the merge; persist/complete only missing handoff evidence.

After a successful or already-completed implementation PR merge, reconstruct durable repository state,
persist bounded merge-result journal evidence, and hand to `Lead / finalize-change`.

For a final Archive PR, after a successful merge or when reconstructing a merge already completed:

1. Fresh-read the Archive PR and persistent coordination Issue.
2. If the Archive PR is durably merged and the coordination Issue is observed natively `closed` through
   the repository-approved closing linkage, replace the consumed routing tuple with exactly
   `agent:lead + action:finalize-archive` on that closed Issue.
3. Persist one bounded merge/native-close/handoff journal on the coordination Issue identifying the
   authorized exact head, merge result, observed native closure, and terminal Lead handoff.
4. End the invocation. Executor MUST NOT execute Lead finalization in the same invocation.

If an authorized Archive PR is already merged and the Issue is natively closed but a prior Executor run
stopped before terminal handoff, do not re-merge. Reconstruct the exact authorized merge/native-close
evidence and repair only the missing terminal routing and journal evidence; do not replay a completed
merge mutation.

If the Archive PR is durably merged but native closure is not observed, do not infer lifecycle
completion. Journal the durable merge/result and hand to `Lead / finalize-archive` for repository-defined
native-close recovery/final reconstruction.

Do not infer downstream completion merely from a successful merge response; Lead owns lifecycle
judgment after merged default-branch state is reconstructed.

## Durable messages

Use `agents/templates/messages.md` for recurring durable presentation. Merge success or action-defined
merge blocker evidence uses `MERGE_RESULT`; completed ownership transfer uses canonical `HANDOFF` only
after routing mutation succeeds. A typed `MERGE_RESULT` that directly represents the PR-merge lifecycle
boundary satisfies that one lifecycle journal record and does not require a duplicate generic journal.

## Mutation safety

Every substantive merge/routing mutation follows the shared bounded coordination-Issue journal
contract. A successful durable mutation whose journal write was interrupted is reconstructed rather
than replayed; the missing journal is persisted before further substantive mutation or handoff.

Persist merge result evidence before routing. Fresh-read Issue routing immediately before handoff and
do not overwrite a newer tuple. `fresh-read routing → update labels` is not a mutex or CAS primitive;
unsafe merge decisions rely on exact-revision preconditions, not routing-write serialization.
