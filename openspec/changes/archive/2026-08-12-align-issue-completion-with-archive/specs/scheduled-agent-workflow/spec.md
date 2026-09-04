## MODIFIED Requirements

### Requirement: Executor merges only an explicitly authorized unchanged revision

Executor SHALL execute `merge-pr` only when durable evidence establishes:

- Reviewer PASS for revision R;
- Lead merge authorization for revision R;
- the current target PR head still equals R; and
- the required gate remains valid and non-contradictory.

Reviewer PASS alone MUST NOT imply merge authority.

If the target revision, authorization, or required gate becomes stale or contradictory, Executor MUST NOT merge and SHALL return control to Lead according to the action contract.

For implementation and implementation-correction PRs associated with a persistent coordination Issue, Executor SHALL verify before merge that the PR does not establish GitHub Issue-closing linkage to that coordination Issue. A closing linkage on an implementation PR is a lifecycle-contract violation and MUST fail closed rather than being merged.

For the final Archive PR, Executor SHALL verify before merge that the PR establishes the repository-approved closing linkage to the same persistent coordination Issue. That linkage is a final-lifecycle side effect only and MUST NOT substitute for Reviewer PASS, Lead authorization, unchanged-head verification, or any other merge precondition.

#### Scenario: Authorized implementation revision remains current without closing linkage

- GIVEN Reviewer PASS exists for implementation revision R
- AND Lead has explicitly authorized merge of revision R
- AND the target PR head is still R
- AND no contradictory current gate evidence exists
- AND the implementation PR does not establish closing linkage to its coordination Issue
- WHEN Executor performs `merge-pr`
- THEN Executor may execute the merge mutation
- AND the coordination Issue remains open for post-merge and archive lifecycle work

#### Scenario: Implementation PR would close the coordination Issue

- GIVEN an implementation PR is otherwise eligible for merge
- AND the PR establishes GitHub Issue-closing linkage to its persistent coordination Issue
- WHEN Executor evaluates `merge-pr`
- THEN Executor does not merge
- AND the closing linkage is treated as a lifecycle-contract violation requiring correction

#### Scenario: Archive PR has the approved closing linkage

- GIVEN Reviewer archive PASS exists for archive revision R
- AND Lead has explicitly authorized merge of revision R
- AND the archive PR head is still R
- AND the required gate remains valid and non-contradictory
- AND the Archive PR establishes the repository-approved closing linkage to its coordination Issue
- WHEN Executor performs `merge-pr`
- THEN Executor may execute the archive merge
- AND GitHub native Issue completion caused by that merge is treated only as the expected final lifecycle side effect

#### Scenario: PR head changes after authorization

- GIVEN Lead authorized revision R1
- AND the PR head is now R2
- WHEN Executor evaluates `merge-pr`
- THEN Executor does not merge
- AND stale authorization for R1 is not reused for R2

### Requirement: Normal OpenSpec archive mechanics remain owned by repository automation

Scheduled roles MUST NOT introduce a competing normal `archive-change` action that runs the deterministic OpenSpec archive mechanics already owned by repository GitHub Actions.

After eligible implementation merge, Lead SHALL observe the existing archive automation/default-branch/Archive PR state and route to archive review only when a durable archive PR is ready.

The repository's Archive PR creation path SHALL make the final Archive PR identify its persistent coordination Issue and establish the repository-approved GitHub closing linkage deterministically. Implementation PR creation/documentation paths SHALL use non-closing references for the same coordination Issue.

#### Scenario: Archive automation is still progressing

- GIVEN merged default-branch state is archive-eligible
- AND the existing repository archive workflow has not yet produced a reviewable archive PR
- WHEN Lead evaluates `finalize-change`
- THEN Lead retains ownership in a waiting state
- AND no scheduled Executor archive mutation is invented

#### Scenario: Archive PR is produced for a coordination Issue

- GIVEN normal archive automation produces the final Archive PR for an eligible OpenSpec change
- WHEN the Archive PR metadata/body is created
- THEN it establishes the repository-approved closing linkage to that change's persistent coordination Issue
- AND that linkage does not itself authorize merge

### Requirement: Coordination Issue closure is the durable final lifecycle transition

A completion comment, Reviewer PASS, Lead finalization decision, or statement that an Issue may be closed MUST NOT constitute completed coordination lifecycle by itself.

Implementation and implementation-correction PRs MUST NOT establish Issue-closing linkage to the persistent coordination Issue. The final Archive PR SHALL establish the repository-approved closing linkage so that an authorized successful Archive PR merge normally causes GitHub to complete the coordination Issue.

After archive merge, Lead `finalize-archive` SHALL reconstruct canonical default-branch/archive state and treat the workflow as complete only when the coordination Issue is observed closed. Native Issue completion is an observed final-state transition; it does not replace archive-state reconstruction or any review/authorization gate.

If canonical archive state is correct and the authorized Archive PR is merged but the expected native Issue completion side effect is missing, Lead SHALL use the repository-defined recovery path: explicitly close the coordination Issue and re-observe it closed. If the Issue is observed closed before the authorized Archive PR merge, the lifecycle SHALL fail closed as premature completion and MUST NOT be treated as successfully finalized.

#### Scenario: Authorized Archive PR merge completes the Issue natively

- GIVEN canonical archive state is produced by an authorized Archive PR merge
- AND the Archive PR carries the repository-approved closing linkage
- WHEN GitHub applies the merge side effect
- THEN the coordination Issue becomes closed
- AND Lead declares lifecycle completion only after reconstructing canonical archive state and observing the Issue closed

#### Scenario: Archive state is correct but native completion is missing

- GIVEN the authorized Archive PR is merged
- AND canonical archived default-branch state satisfies final lifecycle conditions
- AND the coordination Issue remains open despite the approved closing linkage
- WHEN Lead runs `finalize-archive`
- THEN Lead performs the explicit Issue-close recovery mutation
- AND lifecycle completion is recorded only after the Issue is re-observed closed

#### Scenario: Coordination Issue closes during implementation merge

- GIVEN the final Archive PR has not yet been authorized and merged
- AND the coordination Issue becomes closed because an implementation PR established closing linkage
- WHEN a scheduled role reconstructs lifecycle state
- THEN the closed Issue is treated as premature illegal lifecycle state rather than successful completion
- AND normal archive completion is not inferred from the premature closure