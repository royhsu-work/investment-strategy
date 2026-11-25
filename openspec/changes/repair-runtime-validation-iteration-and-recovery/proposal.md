## Why

Runtime treats a qualified mechanical validation failure as an interrupted accepted Application. This blocks the author's normal correction loop. Repeated historical recovery evidence can also prevent evaluation of fresh repository postconditions. Both failure modes were observed on #474 and are in scope for #478.

## What Changes

- Keep qualified mechanical failures within the owning Action. Permit a corrected revision through fresh authorization, exact-revision validation, and the applicable completion gates.
- Use fresh repository postconditions to recover interrupted work. Deduplicate repeated writes and preserve observation of the current obligation.
- Reconcile legacy Accepted Applications with their original evidence and completed effects intact. Verify that the native workflow can resume #474 after release.

## Capabilities

### New Capabilities

### Modified Capabilities

- `scheduled-agent-workflow`: mechanical validation iterations, fresh recovery observation, and legacy Accepted Application reconciliation.

## Impact

Shared Runtime dispatch, application, validation, recovery, and tests. Independent reviews, exact revision checks, one Action per wake, dependency qualification, and existing #473/#474 deliverables remain release constraints. Proposal checkpointing is tracked by #473. Delivery is one release boundary because both paths share accepted completion and legacy compatibility. Implementation work is verified in vertical slices before release.
