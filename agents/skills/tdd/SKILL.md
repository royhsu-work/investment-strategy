---
name: tdd
description: Develop executable behavior test-first using public seams, one observable behavior at a time, and source-bound RED and GREEN evidence.
---

# Test-driven development

Use the approved OpenSpec context to choose a caller-visible behavior and a public test seam. If the interface or seam is unclear, consult `agents/skills/codebase-design/SKILL.md`. Escalate any material change to the approved contract through the existing Lead path.

## One behavior at a time

1. Select one small vertical behavior and derive an independent expected result from the contract or a worked example.
2. Write its test first and request an authorized physical-only save through the implementation procedure. Obtain actual repository-supported static-first CI evidence on the saved revision without the target implementation. Qualify RED only if the test executes and fails for the intended missing or incorrect behavior. Static, syntax, import, fixture, setup and unrelated regressions do not qualify.
3. Implement the minimum sufficient correct behavior and obtain GREEN for that test. Repeat for the next observable behavior, using what the preceding cycle taught you.

Avoid horizontal batches of tests followed by implementation. Preserve the actual ordering of source revisions and CI evidence. A test written after its implementation is valuable coverage but cannot establish Test First. Do not replay verified behavior to manufacture RED.

## Test surface

Test observable outcomes through interfaces used by callers. Avoid assertions bound to private functions, internal call order or expected values recomputed using the implementation's algorithm. Prefer a known result or an independent oracle. Prefer real in-process collaborators and representative test substitutes at genuine I/O seams. A substitute implements the boundary contract, including required operations.

Keep meaningful test coverage. When replacing or retiring affected tests, follow the applicable task/config and independent review evidence requirements.

## Delivery boundary

The behavior cycle ends at GREEN. Independent Implementation Review owns proactive refactoring assessment. Executor remains responsible for correct minimal implementation, genuine regressions and substantiated finding corrections.

Use existing repository-supported CI and exact revision evidence. Follow the applicable runtime and quality contracts, including the approved static-first and CI-only delivery requirements where implemented; this Skill introduces no new CI mechanism. The cycle is smaller than a verified Slice. A saved revision may be pending or failed; it is not a completed Slice. Continue after a qualified verdict under fresh applicable authority. Formal Slice delivery requires satisfied task criteria, durable markers, current exact full gates and the existing formal consequence, not a checkpoint comment. Follow the implementation procedure for marker-head verification, correction and actual exit boundaries.
