# Merge PR Skill

Mapped action: `Executor / merge-pr`.

The same operational contract applies to implementation and archive PR merges. Lifecycle-specific next
routing is reconstructed after the merge rather than encoded as a second merge action.

## Reconstruct before acting

Read default-branch governance and Executor role, the coordination Issue and immutable `Change:`, the
target PR and exact current head revision R, durable Reviewer gate evidence, durable Lead
`MERGE_AUTHORIZED` evidence, current required gate/check state, and whether the target is an
implementation/implementation-correction PR or the final Archive PR.

## Merge preconditions

Execute a merge mutation only when all are simultaneously true and unambiguous:

1. Reviewer `PASS` exists for the exact revision R under the required implementation/archive gate.
2. Lead `MERGE_AUTHORIZED` exists for the exact same revision R.
3. The target PR current head still equals R.
4. Required gates/checks remain valid and there is no contradictory current evidence.
5. For an implementation or implementation-correction PR, the PR does not establish GitHub
   Issue-closing linkage to its persistent coordination Issue; it uses only a non-closing reference.

Reviewer PASS alone is insufficient. Authorization for an earlier head is insufficient.

A closing linkage on an implementation or implementation-correction PR is a lifecycle-contract
violation. Even when every other gate is current, do not merge that PR; persist the violation and hand
control to Lead for correction. Closing linkage is reserved for the final Archive PR and never provides
merge authority by itself.

Legal pre-merge outcomes:

- all preconditions current → merge exactly R;
- `STALE_AUTHORIZATION` or `GATE_CHANGED`/contradictory evidence → do not merge; hand control to Lead;
- implementation PR contains coordination-Issue closing linkage → `LIFECYCLE_CONTRACT_VIOLATION`; do
  not merge and hand control to Lead.

## Crash-safe merge recovery

Before attempting the mutation, reconstruct whether the explicitly authorized PR/revision has already
been merged. If already merged, do not retry the merge; persist/complete only missing handoff evidence.

After a successful or already-completed merge, reconstruct target type and durable repository state:

- implementation PR → hand to `Lead / finalize-change`;
- archive PR → hand to `Lead / finalize-archive`.

Do not infer downstream completion merely from a successful merge response; Lead owns lifecycle
judgment after merged default-branch state is reconstructed.

## Mutation safety

Persist merge result evidence before routing. Fresh-read Issue routing immediately before handoff and
do not overwrite a newer tuple. `fresh-read routing → update labels` is not a mutex or CAS primitive;
unsafe merge decisions rely on exact-revision preconditions, not routing-write serialization.
