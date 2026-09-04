---
name: lifecycle-finalize
description: Lead procedure for finalize-change and finalize-archive lifecycle preparation and terminal evidence.
---

# Lifecycle Finalize

Mapped Actions: Lead / finalize-change and Lead / finalize-archive.

Fresh-read the current Issue/Change, PR/ref state, OpenSpec status, implementation/archive evidence,
Human input, and exact gates. For finalize-change, determine whether more approved implementation is
required or whether the Change is ready for independent archive review. For finalize-archive, verify
the Change is complete and archive terminal evidence is ready.

archive preparation owns semantic completeness, exact Change/Issue linkage, non-closing linkage,
deterministic cleanup obligations, and the evidence needed by Reviewer / review-archive. It does not
perform normal PR merge mutation. A premature close or ambiguous cleanup condition is blocked.

Return one structured archive-ready, more-implementation-required, lifecycle-complete,
human-decision-required, no-go, or blocked result. The executable model derives review-archive,
implement-change, finalize-archive, or terminal state; the successor executes only on a later wake.


The lifecycle result is evidence, not runtime state; successor execution happens only on a later wake.
Do not create a duplicate Change, PR, lifecycle state, recovery state, or control mailbox. Optional or
deferred prose is not a lifecycle obligation.

The exact archive preparation uses Refs #<coordination-issue> and the same persistent coordination
Issue. It does not perform normal PR merge mutation. There is no duplicate Change, PR, lifecycle state,
recovery state, or control mailbox.
