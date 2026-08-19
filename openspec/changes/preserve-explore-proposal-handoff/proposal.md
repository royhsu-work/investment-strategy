# Change: Preserve Explore-to-Propose semantic handoff

## Why

Decision-complete Explore now provides a bounded durable result before formal Propose, but the current Propose/Review contract does not require an Explore-originated Change to identify that exact result as its upstream semantic baseline. Proposal, Specs, Design, and Tasks can therefore remain internally coherent while silently reinterpreting a material boundary that Explore already decided. #35 demonstrates the historical failure class; #86 issuecomment-5342834590 confirms the narrower post-Explore form remains possible on current `main`.

The correction should preserve the existing role split rather than make Reviewer repeat Explore or introduce a second intent/traceability system.

## What Changes

- For a Change reached from decision-complete `Lead / explore-change`, require Propose to identify the exact durable Explore `ACTION_RESULT` that authorized `PROPOSAL_READY` continuation.
- Require Lead to preserve the material boundaries of that referenced Explore result while formalizing Proposal / Specs / Design / Tasks. A materially different direction must return through the governed Lead/Human decision path instead of being silently reinterpreted.
- Require `Reviewer / review-openspec` to dereference the exact Explore result for Explore-originated Changes and verify preservation before ordinary reverse-first and forward OpenSpec traceability.
- Keep Reviewer verification narrow: compare the formalized target with the already-decided Explore boundary; do not re-run research, reconstruct conversation history, or infer undocumented Human intent.
- Leave Human-admitted direct-to-Propose unchanged; it has no fabricated Explore reference requirement.
- Keep the spec-driven semantic adapter focused on OpenSpec schema/delta/canonicalization semantics rather than workflow-handoff authority.

## Affected Capabilities

### Modified

- `scheduled-agent-workflow`
  - Explore-to-Propose semantic handoff;
  - Propose readiness/traceability for Explore-originated Changes;
  - `review-openspec` minimum semantic gate.

## Scope

In scope:

- default-branch Scheduled-Agent governance/Lead/Propose/Reviewer skill wording required for the exact Explore-result handoff contract;
- canonical workflow requirement/scenarios;
- focused regression coverage that distinguishes faithful formalization from internally consistent semantic drift.

Out of scope:

- a generic Human-intent invariant or registry;
- requiring Reviewer to perform Explore research;
- conversation memory as authority;
- changing direct-to-Propose Human admission;
- changing OpenSpec artifact DAG or spec-driven delta semantics;
- converting `openspec-semantic-adapter.md` into its separate reusable Skill (#98);
- the separate required-follow-up routing defect tracked by #100.

## Traceability

- Source decision-complete Explore: #86 issuecomment-5342834590.
- Historical failure evidence: #35; downstream OpenSpec semantic-adapter history: #40; corrected Skill baseline: #84/#85.
- Capability delta: `specs/scheduled-agent-workflow/spec.md`.
- Design: `design.md`.
- Implementation slices: `tasks.md`.
