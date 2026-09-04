---
name: implementation-review
description: Reviewer procedure for exact-head independent review of completed implementation.
---

# Implementation Review

Mapped Action: Reviewer / review-implementation.

Fresh-read the current exact implementation PR head, base, files, task markers, quality runs, OpenSpec
gate, Human freshness, and prior findings. Review implementation behavior, approved scope, tests,
stale/replay/no-rewind guards, effect authorization, carrier separation, and unrelated-file changes.
The exact implementation head is the review identity; historical PASS for another head is invalid.

Check Skill maintenance traceability: every materially affected Skill has a declaration, and a
differently classified or undeclared Skill change is a finding.

Return one structured PASS, FINDINGS, HUMAN_DECISION_REQUIRED, NO_GO, or BLOCKED result. PASS on the
exact unchanged head derives merge-implementation-pr in the executable Action model. Reviewer does
not merge, mutate routing, select a PR, or execute the successor.
