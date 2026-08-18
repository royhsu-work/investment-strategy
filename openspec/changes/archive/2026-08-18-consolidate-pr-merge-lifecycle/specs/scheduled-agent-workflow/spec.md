## MODIFIED Requirements

### Requirement: Review and finalize actions have Lead-owned minimum gate contracts

The repository specification SHALL define the minimum checks and legal result categories for the three Reviewer gates and the two Lead finalize actions. Procedural skills MAY operationalize these checks but MUST NOT invent or weaken them.

`review-openspec` SHALL, at minimum:

- inspect the current OpenSpec change revision;
- verify forward traceability `proposal → specs → design → tasks` and reverse traceability `tasks → design → specs → proposal`;
- verify contract/scope coherence and compatibility with repository `README.md` and `openspec/config.yaml` governance that applies to the change;
- produce actionable findings when a material problem exists;
- produce only `PASS` or `FINDINGS` as the gate result; and
- bind the result to the reviewed repository/branch revision.

`review-implementation` SHALL, at minimum:

- inspect the current implementation PR head revision;
- compare implementation and task-completion state with the approved OpenSpec contract;
- inspect the relevant diff, tests, quality checks, and OpenSpec validation evidence;
- verify scope discipline and absence of unauthorized contract redefinition;
- classify material findings as implementation findings or specification findings;
- bind `PASS`/findings to the reviewed PR head revision; and
- on an unambiguous exact-head PASS, route directly to `Executor / merge-pr` without requiring an intervening Lead merge-authorization action.

`review-archive` SHALL, at minimum:

- inspect the current archive PR revision and the intended source change;
- verify the intended change is being archived from the correct merged default-branch state;
- verify resulting canonical specs represent the approved contract, active change state is removed as intended, archived history is preserved, and unrelated changes are absent;
- inspect strict OpenSpec and applicable repository validation evidence;
- verify that Lead-owned pre-review Archive lifecycle preparation is durably reconstructable for the same coordination workflow, including required separate-follow-up tracker state and any explicitly provenance-owned temporary correction/recovery cleanup obligation that must be satisfied before native close;
- bind `PASS`/findings to the reviewed archive PR revision; and
- on an unambiguous exact-head PASS, route directly to `Executor / merge-pr` without requiring an intervening Lead merge-authorization action.

`finalize-change` SHALL, at minimum:

- after an implementation merge, reconstruct actual default-branch/OpenSpec/archive state and choose only a legal outcome such as `MORE_IMPLEMENTATION_REQUIRED`, `WAITING_FOR_ARCHIVE_AUTOMATION`, `ARCHIVE_PR_READY`, or a repository-defined recovery decision;
- when a validated archive branch is ready, create or reuse the final Archive PR with the repository-approved closing linkage;
- before routing that Archive PR to `Reviewer / review-archive`, reconstruct every still-applicable approved required separate-follow-up obligation and ensure each has its required durable tracker;
- before routing that Archive PR to `Reviewer / review-archive`, reconstruct any separately workflow-owned temporary correction/recovery branch from explicit durable provenance and classify the pre-native-close cleanup/retention obligation without treating the normal `agent/archive-<change>` branch as temporary cleanup input; and
- fail closed instead of handing the Archive PR to Reviewer when those Lead-owned preparation obligations are ambiguous, missing, or contradictory.

`finalize-archive` SHALL, at minimum:

- execute only after the final Archive PR merge/native-close boundary or when reconstructing that already-completed boundary;
- reject stale or contradictory terminal evidence;
- reconstruct canonical default-branch/archive state, the exact reviewed Archive PR head and merge commit, observed native Issue completion, required separate-follow-up tracker state, and pre-merge temporary correction/recovery cleanup/retention evidence; and
- persist `LIFECYCLE_COMPLETE` only when final lifecycle conditions are actually satisfied, using explicit Issue-close recovery only when canonical archive merge is complete but the expected native close is missing.

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

### Requirement: Executor merges only an explicitly authorized unchanged revision

Executor SHALL execute `merge-pr` only when durable evidence establishes:

- an unambiguous independent Reviewer PASS for exact revision R under the required implementation or archive gate;
- the current target PR head still equals R;
- the required checks remain valid and non-contradictory; and
- all path-specific lifecycle and linkage preconditions required by the current merge target remain satisfied.

The exact-head Reviewer PASS is the normal durable acceptance authority for the merge action. The workflow MUST NOT require a second Lead `MERGE_AUTHORIZED(R)` token, or an equivalent replacement token under another name, solely to repeat the accepted revision/gate state.

If the target revision, Reviewer gate, required checks, lifecycle preparation, or linkage state becomes stale or contradictory, Executor MUST NOT merge and SHALL route to the legal correction/diagnosis owner according to the action contract.

For implementation and implementation-correction PRs associated with a persistent coordination Issue, Executor SHALL verify before merge that the PR does not establish GitHub Issue-closing linkage to that coordination Issue. A closing linkage on an implementation PR is a lifecycle-contract violation and MUST fail closed rather than being merged.

For the final Archive PR, Executor SHALL verify before merge that the PR establishes the repository-approved closing linkage to the same persistent coordination Issue. That linkage is a final-lifecycle side effect only and MUST NOT substitute for Reviewer PASS, unchanged-head verification, current checks, pre-review lifecycle preparation, or any other merge precondition.

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

- GIVEN Reviewer archive PASS exists for archive revision R
- AND the archive PR head is still R
- AND required checks and pre-review lifecycle preparation remain valid and non-contradictory
- AND any explicitly identified pre-close temporary correction/recovery cleanup obligation is cleared or has an approved durable retention disposition
- AND the Archive PR establishes the repository-approved closing linkage to its coordination Issue
- WHEN Executor performs `merge-pr`
- THEN Executor may execute the archive merge without a separate Lead authorization token
- AND GitHub native Issue completion caused by that merge is treated only as the expected final lifecycle side effect

#### Scenario: PR head changes after authorization

- GIVEN Reviewer accepted revision R1
- AND the PR head is now R2
- WHEN Executor evaluates `merge-pr`
- THEN Executor does not merge
- AND the PASS for R1 is not reused for R2
- AND the changed revision returns through the legal review/correction path

### Requirement: Normal OpenSpec archive mechanics remain owned by repository automation

Scheduled roles MUST NOT introduce a competing normal `archive-change` action that runs the deterministic OpenSpec archive mechanics already owned by repository GitHub Actions.

After eligible implementation merge, repository automation SHALL own deterministic archive candidate classification, OpenSpec archive mutation, canonical validation, commit, and push of the validated `agent/archive-<change>` branch. In the deployed environment, successful push of that validated archive branch SHALL be the normal automation terminal-success boundary; normal automation MUST NOT require GitHub Actions to create the final Archive PR.

Lead SHALL observe the existing archive automation/default-branch/archive-branch/Archive-PR state. While automation is still progressing, Lead SHALL retain ownership without creating competing archive work. When a validated archive branch is durably ready and no equivalent final Archive PR exists, `Lead / finalize-change` SHALL create or reuse the final Archive PR as ordinary lifecycle continuation, with the repository-approved deterministic closing linkage to the persistent coordination Issue. Before routing that PR to archive review, Lead SHALL complete the Lead-owned lifecycle-preparation obligations defined by the review/finalize contract.

A successful validated archive-branch result awaiting Lead PR creation MUST NOT be classified as archive failure or `RECOVERY_DECISION_REQUIRED`. Genuine archive classification, mutation, validation, commit, push, contradictory branch state, or unreconstructable ownership failure MUST remain fail-closed under the repository-defined diagnosis/recovery contract.

The final Archive PR creation path SHALL identify its persistent coordination Issue and establish the repository-approved GitHub closing linkage deterministically. Implementation PR creation/documentation paths SHALL use non-closing references for the same coordination Issue. Archive PR creation authority does not authorize merge and MUST NOT weaken independent `review-archive`, exact-head Reviewer acceptance, Executor fresh-read merge preconditions, native close, or terminal `finalize-archive` reconstruction.

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
- AND the PR establishes the repository-approved `Closes #<coordination-issue>` linkage
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

- GIVEN Lead creates or reuses the final Archive PR with approved closing linkage
- WHEN later lifecycle gates evaluate that PR
- THEN the linkage does not substitute for independent archive Reviewer PASS, Executor exact-head/current-check merge preconditions, or terminal lifecycle reconstruction

### Requirement: Final Archive native-close occurs only after known terminal cleanup obligations are cleared

Before Lead routes the final Archive PR to `Reviewer / review-archive`, Lead SHALL reconstruct any workflow-owned temporary correction/recovery branch known from explicit durable provenance and identify any terminal cleanup obligation that would become unreachable after native Issue closure. The normal validated `agent/archive-<change>` branch MUST NOT be inferred to be temporary cleanup input from its name or ordinary archive role.

For an Archive PR merge, `Executor / merge-pr` SHALL fresh-read only the explicitly identified workflow-owned temporary correction/recovery branches before the Archive PR merge mutation. Any such branch that is already unused, safely deletable, and Executor-owned under the existing temporary-branch contract SHALL be deleted before the final Archive PR merge. If deletion is blocked, unsupported, stale, or unsafe, Executor MUST NOT merge the Archive PR; while the coordination Issue is still open it SHALL follow the existing exception/disposition path and, when required, return bounded diagnosis to Lead.

The workflow SHALL prefer this pre-close ordering over adding a generic post-close Executor route. The change MUST NOT introduce a new post-close action, broad Issue reopen lifecycle, hidden cleanup state, branch registry, or normal-archive-branch cleanup rule.

#### Scenario: Safely deletable temporary branch exists before Archive merge

- GIVEN Lead reconstructs an explicitly provenance-owned temporary correction/recovery branch while preparing the final Archive PR
- AND the branch is no longer an open PR head/base or active recovery input
- AND fresh comparison proves it has no unique commits outside canonical `main` or an explicitly retained successor
- WHEN Lead evaluates handoff to `review-archive`
- THEN the cleanup obligation is recorded as part of lifecycle preparation for that Archive target
- AND Reviewer can inspect that preparation with the exact Archive PR
- AND Executor remains the owner of any later safe deletion immediately before merge

#### Scenario: Pre-close cleanup mutation is unavailable

- GIVEN an explicitly identified temporary branch is safely deletable and must be retired before terminal completion
- AND Executor cannot perform the required deletion with the current legal repository mutation surface
- WHEN `Executor / merge-pr` prepares the final Archive merge
- THEN it does not merge the Archive PR
- AND the coordination Issue remains open
- AND the failure follows existing durable exception/disposition and Lead diagnosis rules

#### Scenario: No known temporary cleanup obligation remains

- GIVEN Lead's pre-review preparation found no unresolved temporary correction/recovery cleanup obligation or all such obligations have durable valid dispositions
- AND Reviewer archive PASS exists for exact revision R
- AND Executor fresh-reads the same preparation evidence and current merge preconditions
- WHEN all Archive merge preconditions pass
- THEN the final Archive PR may be merged without a separate Lead merge-authorization token
- AND its closing linkage may natively close the coordination Issue

#### Scenario: Normal archive branch is never a cleanup candidate

- GIVEN repository automation produced `agent/archive-<change>` as the validated normal archive branch
- WHEN Lead, Reviewer, or Executor reconstructs temporary correction/recovery cleanup obligations
- THEN that normal archive branch is not treated as temporary cleanup input merely because its name begins with `agent/`
- AND only separately provenance-owned temporary correction/recovery branches participate in the cleanup contract
