# Separate feature commits from Git integration

## Why
Issue #468 is an explicitly Human-authorized correction prerequisite of #435. Formal Explore result [7124850882](https://github.com/royhsu-work/investment-strategy/issues/468#issuecomment-7124850882) establishes the bounded direction. Current main `7ad60ca6417d6ca42656cf0fca00d33d6e16b8ed` rejects some materialization based on requested-path intersection with main, even where the actual feature preimage is valid. #435's failed Application run [45210227847](https://github.com/royhsu-work/investment-strategy/actions/runs/45210227847/job/137816733479) reports effect index 0, zero completed effects and effect-precondition-unsatisfied; this is not evidence of every historical attempt. The current #437 feature HEAD `9d7bb17b96376e8f4dd27fec83e3e54aa727d56b` has 21/21 matching manifest preimages, yet 19 paths were also changed on main. Main and feature diverged at `3d0d1da5905f9f91f15da6af7e70d9173d4b06b3`. The exact canonical and production source paths are recorded in design. This is a structural engineering boundary, not a special #435 exception.

## What Changes
- Separate authorization and proof of a feature-local commit from integration with main. Preserve the actual feature preimage, non-force conditional ref publication, complete content and lineage, and fresh observations.
- Use native Git three-way integration; allow clean same-file edits and route actual conflicts through existing Executor and independent review.
- Distinguish feature revision checks from exact integration candidate checks; requalify merge eligibility on actual current base/head and postconditions without freezing main.
- Preserve immutable accepted intents and UNKNOWN, recognize legal integration/resolution descendants and recover only missing work. Preserve the existing original T1 goal and downstream native resumption.
- Reuse #467's already researched implementation candidate at `e59b4c1ac1a51e1224a882c3672d2bb2ae7bf4c6` as an input, not an accepted implementation or second delivery. Its maintenance branch is not the canonical first formal Change carrier; use the existing formal materialization owner and reuse its work product at implementation after independent review.
- No new role, action, queue, dispatcher, approval, persistent workflow state, mandatory continual synchronization, or global write ordering. No replay of historical rejected requests or rewrite of original accepted evidence. No strategy or public artifact behavior change.

## Capabilities
### Modified Capabilities
- `scheduled-agent-workflow`: separate exact materialization, integration, recovery and implementation merge eligibility.

## Impact
Application materialization and existing carrier, merge acceptance, validation resource and quality workflow owners; associated tests and canonical scheduled-agent-workflow. Existing non-closing PR linkage, review, human freshness, activation and archive gates are retained. #468 must complete its normal lifecycle before the dependency automatically releases #435; the original #435/#437 native T1 acceptance is downstream, not a task marker or excuse to omit this change's implementation verification. No required separate new follow-up issue.
