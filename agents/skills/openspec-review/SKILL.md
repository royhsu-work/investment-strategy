---
name: openspec-review
description: Reviewer procedure for independent exact-revision OpenSpec semantic review and gate results.
---

# OpenSpec Review

Mapped Action: Reviewer / review-openspec.

Fresh-read the current default branch, Issue/Change/PR, exact proposed revision, canonical specs,
design, tasks, Human input, and exact-R validation evidence. Review the semantic source chain
reverse-first: tasks -> design -> specs -> proposal, then proposal -> specs -> design -> tasks.
Both directions must be complete before PASS.

Check scope boundaries, externally verifiable requirements/scenarios, safety invariants, design
trade-offs, task traceability, and Skill maintenance traceability. A missing, contradictory,
stale, or unqualified source is a finding or blocked result; do not guess.

Return one structured PASS, FINDINGS, HUMAN_DECISION_REQUIRED, NO_GO, or BLOCKED result with exact
revision and evidence. PASS is an independent gate. The executable model and application derive the
next Action; the worker does not choose routing or execute the successor.
