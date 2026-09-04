---
name: archive-review
description: Reviewer procedure for independent exact-head review of OpenSpec archive readiness.
---

# Archive Review

Mapped Action: Reviewer / review-archive.

Fresh-read current default-branch governance, the existing Change, archive branch/PR, exact head,
archive automation result, non-closing linkage, terminal preparation, cleanup obligations, Human
freshness, and prior findings.

Verify that archive content is the approved Change, the archive PR is current and non-Draft, linkage
is repository-approved and non-closing, and all deterministic cleanup/terminal prerequisites are
complete. A stale or contradictory observation is blocked.

Return one structured PASS, FINDINGS, HUMAN_DECISION_REQUIRED, NO_GO, or BLOCKED result. PASS on the
exact unchanged head derives merge-archive-pr. Reviewer does not merge, mutate routing, or execute
the successor.
