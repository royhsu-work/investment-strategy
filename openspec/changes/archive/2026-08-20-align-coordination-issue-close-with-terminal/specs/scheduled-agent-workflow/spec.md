# scheduled-agent-workflow Delta

## MODIFIED Requirements

### Requirement: Actionable workflow routing is one logical role/action tuple

A coordination Issue SHALL be actionable by scheduled roles only when it is open and contains exactly one valid `agent:<role>` label and exactly one valid `action:<action>` label forming a legal routing tuple for that role.

A closed coordination Issue with valid `LIFECYCLE_COMPLETE` evidence and observed close is terminal history and MUST NOT participate in normal formal-workflow routing/cardinality. A closed Issue without valid terminal completion is contradictory or bounded premature-close recovery input; it MUST NOT become a normal closed terminal-pending happy-path workflow.

Zero, multiple, contradictory, or illegal routing labels MUST fail closed and MUST NOT be resolved by model inference.

Unrelated Issue labels MUST be preserved during routing changes.

#### Scenario: Open coordination Issue has valid routing

- GIVEN an open coordination Issue has exactly one `agent:reviewer` label
- AND exactly one `action:review-openspec` label
- WHEN Reviewer discovers eligible work
- THEN the Issue is eligible for the Reviewer `review-openspec` action

#### Scenario: Closed terminal-pending Issue has the one legal exception

- GIVEN a coordination Issue is closed
- AND valid `LIFECYCLE_COMPLETE` evidence for final terminal conditions is absent
- WHEN scheduled work discovery evaluates routing eligibility
- THEN the Issue is not eligible as a normal closed terminal-pending happy-path workflow
- AND only the bounded premature-close recovery or fail-closed contract may apply

#### Scenario: Closed completed Issue is terminal history

- GIVEN a coordination Issue is closed
- AND valid `LIFECYCLE_COMPLETE` evidence exists for its final reviewed and merged Archive revision
- AND the close is observed after that completion evidence
- WHEN scheduled work discovery evaluates routing eligibility
- THEN the Issue is terminal history
- AND it does not consume formal WIP or require terminal-pending routing

#### Scenario: Coordination Issue has conflicting role labels

- GIVEN an open coordination Issue has both `agent:lead` and `agent:reviewer`
- WHEN a scheduled role evaluates eligibility
- THEN the routing is invalid
- AND no role proceeds by guessing which role owns the work

### Requirement: Review and finalize actions have Lead-owned minimum gate contracts

The repository specification SHALL define the minimum checks and legal result categories for the three Reviewer gates and the two Lead finalize actions. Procedural skills MAY operationalize these checks but MUST NOT invent or weaken them.

`review-openspec` SHALL, at minimum:

- inspect the current OpenSpec change revision;
- verify forward traceability `proposal → specs → design → tasks` and reverse traceability `tasks → design → specs → proposal`;
- verify contract/scope coherence and compatibility with repository `README.md` and `openspec/config.yaml` governance that applies to the change;
- consume the shared substantive direct-Human input freshness/disposition contract before finalizing the review result when newer coordination-Issue input could affect scope, traceability, or gate validity;
- produce actionable findings when a material problem exists;
- produce only `PASS` or `FINDINGS` as the gate result; and
- bind the result to the reviewed repository/branch revision.

`review-implementation` SHALL, at minimum:

- inspect the current implementation PR head revision;
- compare implementation and task-completion state with the approved OpenSpec contract;
- inspect the relevant diff, tests, quality checks, and OpenSpec validation evidence;
- verify scope discipline and absence of unauthorized contract redefinition;
- consume the shared substantive direct-Human input freshness/disposition contract before finalizing the gate when newer coordination-Issue input could affect correctness, approved scope, traceability, or gate validity;
- classify material findings as implementation findings or specification findings;
- bind `PASS`/findings to the reviewed PR head revision; and
- on an unambiguous exact-head PASS, route directly to `Executor / merge-pr` without requiring an intervening Lead merge-authorization action.

`review-archive` SHALL, at minimum:

- inspect the current archive PR revision and the intended source change;
- verify the intended change is being archived from the correct merged default-branch state;
- verify resulting canonical specs represent the approved contract, active change state is removed as intended, archived history is preserved, and unrelated changes are absent;
- inspect strict OpenSpec and applicable repository validation evidence;
- verify that Lead-owned pre-review Archive lifecycle preparation is durably reconstructable for the same coordination workflow, including required separate-follow-up tracker state and any explicitly provenance-owned temporary correction/recovery cleanup obligation that must be satisfied before terminal completion;
- consume the shared substantive direct-Human input freshness/disposition contract before finalizing the gate when newer coordination-Issue input could affect archive correctness, lifecycle preparation, or gate validity;
- bind `PASS`/findings to the reviewed archive PR revision; and
- on an unambiguous exact-head PASS, route directly to `Executor / merge-pr` without requiring an intervening Lead merge-authorization action.

`finalize-change` SHALL, at minimum:

- after an implementation merge, reconstruct actual default-branch/OpenSpec/archive state and choose only a legal outcome such as `MORE_IMPLEMENTATION_REQUIRED`, `WAITING_FOR_ARCHIVE_AUTOMATION`, `ARCHIVE_PR_READY`, or a repository-defined recovery decision;
- when a validated archive branch is ready, create or reuse the final Archive PR with the repository-approved deterministic non-closing coordination-Issue reference;
- before routing that Archive PR to `Reviewer / review-archive`, reconstruct every still-applicable approved required separate-follow-up obligation and ensure each has its required durable tracker;
- before routing that Archive PR to `Reviewer / review-archive`, reconstruct any separately workflow-owned temporary correction/recovery branch from explicit durable provenance and classify the pre-terminal cleanup/retention obligation without treating the normal `agent/archive-<change>` branch as temporary cleanup input;
- consume the shared substantive direct-Human input freshness/disposition contract before a lifecycle result or handoff when newer coordination-Issue input could materially affect the lifecycle judgment; and
- fail closed instead of handing the Archive PR to Reviewer when those Lead-owned preparation obligations are ambiguous, missing, or contradictory.

`finalize-archive` SHALL, at minimum:

- execute only after the final Archive PR merge boundary or when reconstructing that already-completed boundary;
- reject stale or contradictory terminal evidence;
- reconstruct canonical default-branch/archive state, the exact reviewed Archive PR head and merge commit, required separate-follow-up tracker state, and pre-merge temporary correction/recovery cleanup/retention evidence;
- require the coordination Issue to remain open on the normal path until terminal evidence is durable;
- consume the shared substantive direct-Human input freshness/disposition contract before persisting terminal completion when newer coordination-Issue input could materially affect the terminal judgment;
- persist `LIFECYCLE_COMPLETE` only when final lifecycle conditions are actually satisfied;
- after durable `LIFECYCLE_COMPLETE`, close the coordination Issue and re-observe `closed`; and
- treat interruption between completion evidence and close/re-observation idempotently, without inventing a new lifecycle state.

#### Scenario: Reviewer performs OpenSpec review

- GIVEN a coordination Issue is routed to `Reviewer / review-openspec`
- AND an OpenSpec change revision is identified
- WHEN Reviewer executes the gate
- THEN Reviewer checks bidirectional traceability, contract/scope coherence, and applicable repository governance
- AND records revision-bound `PASS` or actionable `FINDINGS`
- AND the procedural skill does not invent additional contract meaning to make the gate pass

#### Scenario: Lead evaluates implementation merge authorization

- GIVEN Reviewer recorded an unambiguous implementation PASS for exact revision R
- AND the implementation PR is still at R
- WHEN `review-implementation` completes its legal PASS result
- THEN routing moves directly to `Executor / merge-pr`
- AND no normal Lead `MERGE_AUTHORIZED` action or replacement authorization token is required between review and merge
- AND Executor still fresh-reads all merge preconditions before mutation

#### Scenario: Archive preparation completes before independent review

- GIVEN merged implementation/default-branch state has produced a validated archive branch and final Archive PR
- WHEN Lead prepares the Archive PR for `review-archive`
- THEN Lead reconstructs required separate-follow-up tracker obligations before the handoff
- AND Lead reconstructs any separately provenance-owned temporary correction/recovery cleanup obligation before the handoff
- AND the normal `agent/archive-<change>` branch is not classified as temporary recovery input
- AND unresolved Lead-owned preparation blocks review handoff rather than being deferred until after Reviewer PASS

#### Scenario: Archive review PASS routes directly to merge

- GIVEN Reviewer recorded an unambiguous archive PASS for exact revision R
- AND the reviewed lifecycle-preparation evidence remains applicable
- WHEN `review-archive` completes its legal PASS result
- THEN routing moves directly to `Executor / merge-pr`
- AND no normal Lead `MERGE_AUTHORIZED` action or replacement authorization token is required between archive review and merge
- AND Executor still fresh-reads all Archive merge and cleanup preconditions before mutation

#### Scenario: Human asks material question before implementation review PASS

- GIVEN Executor has handed an implementation PR to `Reviewer / review-implementation`
- AND a newer direct-Human coordination-Issue comment asks a question that may affect approved scope or traceability correctness
- AND that exact comment has no durable disposition
- WHEN Reviewer evaluates PASS for the current implementation head
- THEN Reviewer MUST NOT record PASS while silently ignoring the comment
- AND Reviewer dispositions it through the legal review finding, bounded answer, or owner-routing path before the gate can complete

#### Scenario: Finalize archive closes only after durable completion

- GIVEN the exact reviewed Archive revision has been merged
- AND canonical archive state, required trackers, cleanup/retention evidence, and Human-input freshness all satisfy terminal conditions
- AND the coordination Issue remains open
- WHEN Lead executes `finalize-archive`
- THEN Lead persists `LIFECYCLE_COMPLETE` first
- AND closes the Issue only after that evidence is durable
- AND re-observes `closed` before declaring workflow terminal

### Requirement: Executor merges only an explicitly authorized unchanged revision

Executor SHALL execute `merge-pr` only when durable evidence establishes:

- an unambiguous independent Reviewer PASS for exact revision R under the required implementation or archive gate;
- the current target PR head still equals R;
- the required checks remain valid and non-contradictory;
- the shared substantive direct-Human input freshness/disposition contract has been consumed at mutation time for newer coordination-Issue input that could affect accepted meaning or merge assumptions; and
- all path-specific lifecycle and linkage preconditions required by the current merge target remain satisfied.

The exact-head Reviewer PASS is the normal durable acceptance authority for the merge action. The workflow MUST NOT require a second Lead `MERGE_AUTHORIZED(R)` token, or an equivalent replacement token under another name, solely to repeat the accepted revision/gate state.

If the target revision, Reviewer gate, required checks, lifecycle preparation, Human-input disposition state, or linkage state becomes stale or contradictory, Executor MUST NOT merge and SHALL route to the legal correction/diagnosis owner according to the action contract.

For implementation and implementation-correction PRs associated with a persistent coordination Issue, Executor SHALL verify before merge that the PR does not establish GitHub Issue-closing linkage to that coordination Issue. A closing linkage on an implementation PR is a lifecycle-contract violation and MUST fail closed rather than being merged.

For the final Archive PR, Executor SHALL verify before merge that the PR establishes the repository-approved deterministic non-closing reference to the same persistent coordination Issue and does not establish Issue-closing linkage. Archive merge MUST leave the coordination Issue open for `Lead / finalize-archive`; the linkage is traceability only and MUST NOT substitute for Reviewer PASS, unchanged-head verification, current checks, pre-review lifecycle preparation, or any other merge precondition.

#### Scenario: Authorized implementation revision remains current without closing linkage

- GIVEN Reviewer PASS exists for implementation revision R
- AND the target PR head is still R
- AND no contradictory current gate or check evidence exists
- AND the implementation PR does not establish closing linkage to its coordination Issue
- WHEN Executor performs `merge-pr`
- THEN Executor may execute the merge mutation without a separate Lead authorization token
- AND the coordination Issue remains open for post-merge and archive lifecycle work

#### Scenario: Implementation PR would close the coordination Issue

- GIVEN an implementation PR is otherwise eligible for merge
- AND the PR establishes GitHub Issue-closing linkage to its persistent coordination Issue
- WHEN Executor evaluates `merge-pr`
- THEN Executor does not merge
- AND the closing linkage is treated as a lifecycle-contract violation requiring correction

#### Scenario: Archive PR has the approved closing linkage

- GIVEN an Archive PR is otherwise eligible for merge
- AND the Archive PR establishes GitHub Issue-closing linkage to its persistent coordination Issue
- WHEN Executor evaluates `merge-pr`
- THEN Executor does not merge
- AND the closing linkage is treated as a lifecycle-contract violation requiring correction to the approved non-closing reference

#### Scenario: Archive PR has the approved non-closing linkage

- GIVEN Reviewer archive PASS exists for archive revision R
- AND the archive PR head is still R
- AND required checks and pre-review lifecycle preparation remain valid and non-contradictory
- AND any explicitly identified pre-terminal temporary correction/recovery cleanup obligation is cleared or has an approved durable retention disposition
- AND the Archive PR establishes the repository-approved non-closing reference to its coordination Issue
- AND the Archive PR does not establish Issue-closing linkage
- WHEN Executor performs `merge-pr`
- THEN Executor may execute the archive merge without a separate Lead authorization token
- AND the coordination Issue remains open
- AND routing may proceed to `Lead / finalize-archive`

#### Scenario: PR head changes after authorization

- GIVEN Reviewer accepted revision R1
- AND the PR head is now R2
- WHEN Executor evaluates `merge-pr`
- THEN Executor does not merge
- AND the PASS for R1 is not reused for R2
- AND the changed revision returns through the legal review/correction path

#### Scenario: Human input arrives after Reviewer PASS but before merge

- GIVEN Reviewer recorded exact-head PASS for revision R
- AND before `Executor / merge-pr` mutates the PR, a newer direct-Human comment appears that could invalidate a relied-upon merge assumption or the accepted meaning
- WHEN Executor performs mutation-time fresh-read
- THEN the older PASS alone is insufficient to authorize merge
- AND Executor MUST NOT merge until the exact comment is durably dispositioned through the legal owner/path and all resulting merge preconditions are current

### Requirement: Normal OpenSpec archive mechanics remain owned by repository automation

Scheduled roles MUST NOT introduce a competing normal `archive-change` action that runs the deterministic OpenSpec archive mechanics already owned by repository GitHub Actions.

After eligible implementation merge, repository automation SHALL own deterministic archive candidate classification, OpenSpec archive mutation, canonical validation, commit, and push of the validated `agent/archive-<change>` branch. In the deployed environment, successful push of that validated archive branch SHALL be the normal automation terminal-success boundary; normal automation MUST NOT require GitHub Actions to create the final Archive PR.

Lead SHALL observe the existing archive automation/default-branch/archive-branch/Archive-PR state. While automation is still progressing, Lead SHALL retain ownership without creating competing archive work. When a validated archive branch is durably ready and no equivalent final Archive PR exists, `Lead / finalize-change` SHALL create or reuse the final Archive PR as ordinary lifecycle continuation, with the repository-approved deterministic non-closing reference to the persistent coordination Issue. Before routing that PR to archive review, Lead SHALL complete the Lead-owned lifecycle-preparation obligations defined by the review/finalize contract.

A successful validated archive-branch result awaiting Lead PR creation MUST NOT be classified as archive failure or `RECOVERY_DECISION_REQUIRED`. Genuine archive classification, mutation, validation, commit, push, contradictory branch state, or unreconstructable ownership failure MUST remain fail-closed under the repository-defined diagnosis/recovery contract.

The final Archive PR creation path SHALL identify its persistent coordination Issue and establish the repository-approved non-closing reference deterministically. Implementation PR creation/documentation paths SHALL also use non-closing references for the same coordination Issue. Archive PR creation authority does not authorize merge and MUST NOT weaken independent `review-archive`, exact-head Reviewer acceptance, Executor fresh-read merge preconditions, or terminal `finalize-archive` reconstruction.

The normal validated `agent/archive-<change>` branch is a lifecycle artifact and MUST NOT be classified as a temporary recovery/correction branch merely because historical recovery flows also used agent-owned branches. Explicit `openspec-archive-recovery` and manual `workflow_dispatch` fallback remain exceptional recovery/migration entry points and do not redefine the normal archive branch as recovery state.

#### Scenario: Archive automation is still progressing

- GIVEN merged default-branch state is archive-eligible
- AND repository archive automation has not yet produced a validated pushed archive branch or terminal failure
- WHEN Lead evaluates `finalize-change`
- THEN Lead retains ownership in a waiting state
- AND no scheduled role runs competing archive mutation mechanics

#### Scenario: Archive branch readiness is normal automation success

- GIVEN repository archive automation successfully archives the eligible change
- AND strict canonical validation succeeds
- AND the archive commit is pushed to the validated `agent/archive-<change>` branch
- WHEN the normal automation reaches its terminal boundary
- THEN the run is a normal successful archive-branch-ready result
- AND it does not require an attempted GitHub Actions PR-creation mutation
- AND the branch is not a temporary recovery artifact

#### Scenario: Lead creates the final Archive PR from a ready branch

- GIVEN the validated archive branch for the active Change is durably ready
- AND no equivalent final Archive PR already exists
- AND Lead reconstructs the persistent coordination Issue unambiguously
- WHEN Lead executes `finalize-change`
- THEN Lead creates the final Archive PR from that archive branch to `main`
- AND the PR establishes the repository-approved deterministic non-closing reference to the coordination Issue
- AND the PR does not establish Issue-closing linkage
- AND Lead completes required lifecycle preparation before routing the PR to independent `Reviewer / review-archive`

#### Scenario: Existing equivalent Archive PR is reused idempotently

- GIVEN the validated archive branch is ready
- AND an equivalent open final Archive PR already exists for that branch and coordination Issue
- WHEN Lead reconstructs `finalize-change`
- THEN Lead reuses that durable PR instead of creating a duplicate
- AND proceeds only if its linkage/state are valid and non-contradictory
- AND completes any still-required Lead-owned lifecycle preparation before review handoff

#### Scenario: Archive branch production fails before readiness

- GIVEN archive classification, mutation, validation, commit, or push fails
- WHEN Lead reconstructs the archive result
- THEN the state is not treated as successful branch readiness
- AND Lead follows the repository-defined fail-closed diagnosis/recovery boundary

#### Scenario: Archive PR closing linkage remains non-authorizing

- GIVEN a final Archive PR establishes legacy Issue-closing linkage
- WHEN later lifecycle gates evaluate that PR
- THEN the linkage does not authorize merge or terminal completion
- AND under the current contract it must be corrected to the approved non-closing reference before merge

#### Scenario: Archive PR linkage remains non-authorizing

- GIVEN Lead creates or reuses the final Archive PR with approved non-closing linkage
- WHEN later lifecycle gates evaluate that PR
- THEN the linkage does not substitute for independent archive Reviewer PASS, Executor exact-head/current-check merge preconditions, or terminal lifecycle reconstruction

### Requirement: Coordination Issue closure is the durable final lifecycle transition

A completion comment, Reviewer PASS, Archive merge, Lead terminal-verification decision, or statement that an Issue may be closed MUST NOT constitute completed coordination lifecycle by itself.

Implementation, implementation-correction, and final Archive PRs MUST NOT establish Issue-closing linkage to the persistent coordination Issue. The final Archive PR SHALL establish the repository-approved deterministic non-closing reference so Archive merge preserves traceability while leaving the coordination Issue open for required Lead terminal verification.

After Archive merge, Lead `finalize-archive` SHALL reconstruct the exact reviewed and merged Archive revision, canonical default-branch/archive state, required tracker state, cleanup/retention evidence, and applicable Human-input freshness. When those terminal conditions are satisfied, Lead SHALL persist `LIFECYCLE_COMPLETE`, then close the coordination Issue, re-observe `closed`, and only then treat the workflow as terminal.

If `LIFECYCLE_COMPLETE` is durable but the Issue close mutation or re-observation is missing, a later Lead run SHALL reconstruct the same terminal evidence and idempotently complete/re-observe the close. If the Issue is observed closed before valid `LIFECYCLE_COMPLETE` and terminal conditions, the lifecycle SHALL fail closed as premature completion and MAY use only the bounded shared premature-close recovery contract when its predicates prove one unambiguous unfinished candidate.

A closed Issue with valid `LIFECYCLE_COMPLETE` and observed close is terminal history and SHALL NOT consume normal formal-workflow cardinality.

#### Scenario: Authorized Archive PR merge completes the Issue natively

- GIVEN an authorized final Archive PR uses the repository-approved non-closing coordination-Issue reference
- WHEN GitHub merges that Archive PR
- THEN the coordination Issue remains open
- AND native Issue completion at Archive merge is no longer the normal lifecycle behavior
- AND routing continues to `Lead / finalize-archive`

#### Scenario: Archive state is correct but native completion is missing

- GIVEN the authorized Archive PR is merged
- AND canonical archived default-branch state satisfies final lifecycle conditions
- AND the coordination Issue remains open
- WHEN Lead runs `finalize-archive`
- THEN the open Issue is normal terminal-verification input rather than a missing native-close error
- AND Lead persists `LIFECYCLE_COMPLETE`, closes the coordination Issue, and re-observes `closed`

#### Scenario: Coordination Issue closes during implementation merge

- GIVEN the final Archive lifecycle has not reached valid `LIFECYCLE_COMPLETE`
- AND the coordination Issue becomes closed because an implementation PR established closing linkage
- WHEN a scheduled role reconstructs lifecycle state
- THEN the closed Issue is treated as premature illegal lifecycle state rather than successful completion
- AND normal archive completion is not inferred from the premature closure

#### Scenario: Archive merge leaves the Issue open for finalization

- GIVEN canonical archive state is produced by an authorized Archive PR merge
- AND the Archive PR carries the repository-approved non-closing reference
- WHEN GitHub applies the merge
- THEN the coordination Issue remains open
- AND routing continues to `Lead / finalize-archive`

#### Scenario: Lead completion closes the Issue

- GIVEN the authorized Archive PR is merged
- AND canonical archived default-branch state satisfies final lifecycle conditions
- AND the coordination Issue remains open
- WHEN Lead runs `finalize-archive`
- THEN Lead persists `LIFECYCLE_COMPLETE`
- AND then closes the coordination Issue
- AND re-observes `closed` before declaring terminal completion

#### Scenario: Completion is durable but close was interrupted

- GIVEN valid `LIFECYCLE_COMPLETE` is already durable for the final Archive merge
- AND the coordination Issue remains open because the close mutation or its re-observation was interrupted
- WHEN Lead reconstructs `finalize-archive`
- THEN Lead does not duplicate terminal verification meaning
- AND idempotently closes or re-observes the Issue as needed
- AND terminal completion requires the observed closed state

#### Scenario: Coordination Issue closes prematurely

- GIVEN valid `LIFECYCLE_COMPLETE` has not been established for the final Archive merge
- AND the coordination Issue becomes closed
- WHEN a scheduled role reconstructs lifecycle state
- THEN the closed Issue is treated as premature contradictory/recovery input rather than successful completion
- AND normal archive completion is not inferred from the premature closure
