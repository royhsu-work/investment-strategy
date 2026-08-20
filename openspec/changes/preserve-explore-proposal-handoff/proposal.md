# Change: Preserve Explore-to-Propose semantic handoff

## Why

Decision-complete Explore provides a bounded durable result before formal Propose, but current Propose/Review contracts still do not require an Explore-originated Change to identify that exact result as its upstream semantic baseline. Proposal, Specs, Design, and Tasks can therefore remain internally coherent while silently reinterpreting a material boundary that Explore already decided.

The current decision-complete source is #86 issuecomment-5352138330, revalidated against default-branch `2ed9eaaab40b1b3e959b48f19703094e24cde3ab`. Historical PR #103 and issuecomment-5342834590 are comparison evidence only and are not inherited readiness or review gates.

## What Changes

- For a Change reached from decision-complete `Lead / explore-change`, require Propose to identify the exact durable Explore `ACTION_RESULT` that established `PROPOSAL_READY`.
- Require Lead to preserve the material boundaries of that referenced Explore result while formalizing Proposal / Specs / Design / Tasks. A materially different direction must return through the governed Lead/Human decision path instead of being silently reinterpreted.
- Require `Reviewer / review-openspec` to dereference the exact Explore result for Explore-originated Changes and verify preservation before ordinary reverse-first and forward OpenSpec traceability.
- Keep Reviewer verification narrow: compare the formalized target with the already-decided Explore boundary; do not re-run research, reconstruct conversation history, or infer undocumented Human intent.
- Leave direct-to-Propose unchanged; it has no fabricated Explore reference requirement.
- Keep the spec-driven semantic adapter focused on OpenSpec schema/delta/canonicalization semantics rather than workflow-handoff authority.

## Affected Capabilities

### Added

- `scheduled-agent-workflow`
  - Explore-originated Propose preserves the exact decision-complete Explore result.

## Scope

In scope:

- shared Scheduled-Agent workflow contract for Explore → Propose semantic preservation;
- Lead Propose and Reviewer OpenSpec review consumption of the exact Explore result;
- focused regression coverage for faithful preservation vs internally coherent semantic drift.

Out of scope:

- generic Human-intent registry/invariant;
- Reviewer re-performing Explore;
- conversation memory as authority;
- direct-to-Propose admission changes;
- OpenSpec artifact DAG or spec-driven delta semantics;
- unrelated Skill conversion or follow-up-routing work.

## Traceability

- Current source decision-complete Explore: #86 issuecomment-5352138330.
- Historical comparison evidence: #86 issuecomment-5342834590 and PR #103.
- Historical failure class: #35; #40 is semantic-adapter history, not ownership for this correction.
- Capability delta: `specs/scheduled-agent-workflow/spec.md`.
- Design: `design.md`.
- Implementation slices: `tasks.md`.
