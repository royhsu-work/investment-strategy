# scheduled-agent-workflow Delta Specification

## MODIFIED Requirements

### Requirement: Normal OpenSpec archive mechanics remain owned by repository automation

Scheduled roles MUST NOT introduce a competing normal `archive-change` action that runs the deterministic OpenSpec archive mechanics already owned by repository GitHub Actions.

After eligible implementation merge, repository automation SHALL own deterministic archive candidate classification, OpenSpec archive mutation, canonical validation, commit, and push of the validated `agent/archive-<change>` branch. In the deployed environment, successful push of that validated archive branch SHALL be the normal automation terminal-success boundary; normal automation MUST NOT require GitHub Actions to create the final Archive PR.

Lead SHALL observe the existing archive automation/default-branch/archive-branch/Archive-PR state. While automation is still progressing, Lead SHALL retain ownership without creating competing archive work. When a validated archive branch is durably ready and no equivalent final Archive PR exists, `Lead / finalize-change` SHALL create or reuse the final Archive PR as ordinary lifecycle continuation, with the repository-approved deterministic closing linkage to the persistent coordination Issue, and SHALL route to archive review only after that durable Archive PR is ready.

A successful validated archive-branch result awaiting Lead PR creation MUST NOT be classified as archive failure or `RECOVERY_DECISION_REQUIRED`. Genuine archive classification, mutation, validation, commit, push, contradictory branch state, or unreconstructable ownership failure MUST remain fail-closed under the repository-defined diagnosis/recovery contract.

The final Archive PR creation path SHALL identify its persistent coordination Issue and establish the repository-approved GitHub closing linkage deterministically. Implementation PR creation/documentation paths SHALL use non-closing references for the same coordination Issue. Archive PR creation authority does not authorize merge and MUST NOT weaken independent `review-archive`, exact-head Lead merge authorization, Executor merge, native close, or terminal `finalize-archive` reconstruction.

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

#### Scenario: Lead creates the final Archive PR from a ready branch

- GIVEN the validated archive branch for the active Change is durably ready
- AND no equivalent final Archive PR already exists
- AND Lead reconstructs the persistent coordination Issue unambiguously
- WHEN Lead executes `finalize-change`
- THEN Lead creates the final Archive PR from that archive branch to `main`
- AND the PR establishes the repository-approved `Closes #<coordination-issue>` linkage
- AND Lead routes the ready Archive PR to independent `Reviewer / review-archive`

#### Scenario: Existing equivalent Archive PR is reused idempotently

- GIVEN the validated archive branch is ready
- AND an equivalent open final Archive PR already exists for that branch and coordination Issue
- WHEN Lead reconstructs `finalize-change`
- THEN Lead reuses that durable PR instead of creating a duplicate
- AND proceeds only if its linkage/state are valid and non-contradictory

#### Scenario: Archive branch production fails before readiness

- GIVEN archive classification, mutation, validation, commit, or push fails
- WHEN Lead reconstructs the archive result
- THEN the state is not treated as successful branch readiness
- AND Lead follows the repository-defined fail-closed diagnosis/recovery boundary

#### Scenario: Archive PR closing linkage remains non-authorizing

- GIVEN Lead creates or reuses the final Archive PR with approved closing linkage
- WHEN later lifecycle gates evaluate that PR
- THEN the linkage does not substitute for independent archive Reviewer PASS, exact-head Lead authorization, Executor merge preconditions, or terminal lifecycle reconstruction
