# Change: Consolidate PR merge lifecycle

## Why

The current scheduled-agent lifecycle inserts a Lead `MERGE_AUTHORIZED(R)` hop after an independent Reviewer PASS for both implementation and final Archive PRs. On the implementation path that Lead hop rechecks the same exact-head/gate facts that `Executor / merge-pr` must already reconstruct immediately before mutation, without adding an independent specification or lifecycle decision. On the Archive path Lead still owns real lifecycle preparation, but the current contract performs that judgment after Reviewer PASS instead of making the Archive target fully prepared before independent review.

Archive semantics have also evolved. #58 established validated `agent/archive-<change>` branch production plus Lead-created final Archive PR as the normal happy path in the deployed environment. Current authoritative wording still mixes this normal artifact with generic `temporary integration/recovery branch` language inherited from earlier recovery-oriented designs, increasing the risk of preserving an unnecessary authorization stage or misclassifying normal archive state.

This change removes the redundant normal merge-authorization token while preserving independent review, exact-revision safety, fail-closed merge mutation, role separation, final closing linkage, and post-merge lifecycle reconstruction.

## What Changes

- Treat an unambiguous exact-head Reviewer PASS as the durable acceptance authority for `Executor / merge-pr`; do not require a second Lead `MERGE_AUTHORIZED(R)` token for normal implementation or Archive merges.
- Keep `Executor / merge-pr` responsible for fresh-reading the current head, current required checks, gate contradictions, implementation-vs-Archive closing linkage, and all path-specific operational preconditions immediately before mutation.
- Keep implementation PR Draft-to-Ready ownership at the existing pre-review Executor boundary; this change does not move PR presentation semantics after review.
- Move Archive-specific Lead lifecycle preparation before `review-archive`: required separate-follow-up tracker reconstruction and classification of any explicitly provenance-owned temporary correction/recovery branch must be complete before the Archive PR is handed to Reviewer.
- Route `Reviewer / review-implementation` PASS directly to `Executor / merge-pr`; after merge, Executor hands to `Lead / finalize-change` for merged-state/archive continuation.
- Route `Reviewer / review-archive` PASS directly to `Executor / merge-pr`; after merge/native close, Executor hands to terminal `Lead / finalize-archive` for canonical archive reconstruction and `LIFECYCLE_COMPLETE`.
- Normalize current terminology so `agent/archive-<change>` is always the normal validated archive lifecycle artifact. Cleanup semantics apply only to a separately identified workflow-owned temporary correction/recovery branch with durable provenance; branch naming alone never creates cleanup authority.
- Preserve genuine recovery-only paths such as the explicit `openspec-archive-recovery` / manual `workflow_dispatch` fallback when normal archive mechanics cannot be used.
- Retire normal `MERGE_AUTHORIZATION` presentation/consumption where it exists solely to carry the removed Lead token; do not replace it with another equivalent token under a different name.

## Capabilities

### Modified

- `scheduled-agent-workflow`
  - simplify implementation and Archive acceptance-to-merge routing;
  - move Archive lifecycle preparation before independent archive review;
  - preserve exact-head/fail-closed merge preconditions without Lead authorization duplication;
  - distinguish normal archive artifacts from actual temporary recovery/correction branches.

## Scope Boundaries

In scope:
- `agents/AGENTS.md` shared routing/merge invariants that currently require Lead authorization;
- Lead, Reviewer, and Executor role contracts directly affected by the merge boundary;
- `implementation-review`, `archive-review`, `lifecycle-finalize`, and `merge-pr` skills;
- recurring message presentation that still exposes normal `MERGE_AUTHORIZATION`;
- canonical `scheduled-agent-workflow` requirements and focused governance regression coverage.

Out of scope:
- changing OpenSpec archive mutation/classification mechanics or the validated archive-branch ownership established by #58;
- removing explicit archive recovery/manual fallback introduced for exceptional cases;
- moving implementation Draft-to-Ready after Reviewer acceptance;
- introducing a merge queue, lock/lease/heartbeat, hidden state, new authorization token, or second workflow DAG;
- extracting global workflow topology into `agents/workflow.md`; #80 should consume the post-merge semantics from this change rather than run in parallel.

## Evidence and Intent

- #12 established normal automatic archive mechanics separately from explicit recovery/manual fallback.
- #58 made validated archive-branch readiness plus Lead-created final Archive PR the normal deployed path; `agent/archive-<change>` is no longer a recovery artifact.
- #65 evaluated the merge-authorization hop but deliberately deferred removing it because Archive-specific obligations needed a separate bounded redesign.
- Current default-branch `lifecycle-finalize` and `merge-pr` both recheck Reviewer PASS/current head/gates around `MERGE_AUTHORIZED`, demonstrating duplicate normal implementation merge judgment.

## Traceability

- Proposal intent → `scheduled-agent-workflow` MODIFIED requirement `Review and finalize actions have Lead-owned minimum gate contracts`.
- Direct PASS-to-merge authority → MODIFIED requirement `Executor merges only an explicitly authorized unchanged revision`.
- Normal archive artifact semantics → MODIFIED requirement `Normal OpenSpec archive mechanics remain owned by repository automation`.
- Pre-review Archive cleanup/preparation → MODIFIED requirement `Final Archive native-close occurs only after known terminal cleanup obligations are cleared`.
- Design Decisions 1–5 operationalize those requirements; task slices map back to those decisions and requirements.

Refs #79
