## Why

Runtime treats a qualified mechanical validation failure as an interrupted accepted Application, blocking ordinary correction. Repeated historical recovery evidence can also prevent observation of fresh postconditions. Both were observed on #474. The current implementation write gate additionally requires a verified candidate before materialization while the worker cannot rely on an installed local toolchain: the normal CI-only RED/GREEN development loop cannot start. #478 corrects this shared development/completion/recovery boundary, not an incident-specific retry.

## What Changes

- Separate authorized development materialization from verified slice completion. Permit multiple commits, native CI runs and wakes inside one vertical slice, with one effective verified checkpoint and formal completion result. Keep one Action per wake and WIP=1.
- Use the existing CI environment as the sole formal test environment. Run Ruff lint, Ruff format check, Mypy, then pytest with native fail-fast semantics. Require intended behavioral RED, full GREEN, and exact current completion gates; static, environment and unrelated failures are not RED. No TEST/VERIFY modes or special test-only runner.
- Keep qualified mechanical FAIL within the owning Action; preserve normal review findings and specification-correction routes. Permit fresh corrected revisions without treating a settled failure as mutation Recovery.
- Recover outstanding durable obligations from fresh postconditions, independently of historical failure-digest equality; deduplicate physical writes and preserve immutable accepted evidence, completed effects, exact authorization and no replay/no rewind.
- Reconcile legacy accepted applications and verify the native workflow can resume #474 after release.

## Capabilities

### New Capabilities

### Modified Capabilities

- `scheduled-agent-workflow`: authorized development iteration, exact verified completion, normal failure vs recovery, fresh recovery observation and legacy acceptance reconciliation.

## Impact

Shared Runtime dispatch, Application, Carrier, validation, CI, implementation Skill, authoring rules and tests. Preserve independent review, exact revision/merge gates, dependency qualification, SSOT and existing #473/#474 obligations. #473 owns proposal checkpointing; #474 owns required follow-up materialization, duplicate retirement and dependency preservation. No new Issue/PR/branch, semantic Action, runner, external service, persisted TDD/recovery state, or token/local dependency assumption. One release boundary preserves all mandatory outcomes and compatibility; implementation proceeds in three independently verifiable vertical slices. The bounded N-1 maintenance bootstrap is expressly approved for this existing Change/PR by Human comment 7163684737 and direct reapproval event 37256073447, answering 7163640714. It is delivery authority input, not prospective governance or a permanent exception. Design decision source: #478 comment 7163243974.
