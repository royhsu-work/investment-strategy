# Design: Preserve Explore-to-Propose semantic handoff

## Context

Explore already produces a durable decision-complete `ACTION_RESULT` and may continue same-Issue to Propose. Current contracts require bounded scope and ordinary OpenSpec traceability, but do not make that exact Explore result mandatory provenance for Explore-originated formalization.

## Decision

Use the existing durable Explore result as the handoff anchor. For Explore-originated Propose:

```text
Lead / explore-change
  → ACTION_RESULT E: PROPOSAL_READY
        ↓ exact reference
Lead / propose-change
  → Proposal / Specs / Design / Tasks preserve E
        ↓
Reviewer / review-openspec
  → dereference E
  → verify preservation
  → ordinary reverse-first + forward gate
```

Direct-to-Propose remains unchanged and has no synthetic Explore reference.

## Ownership

- `openspec-explore`: produces decision-complete result.
- `openspec-change`: captures exact result reference and faithfully formalizes it.
- `openspec-review`: independently verifies preservation before ordinary semantic review.
- `agents/AGENTS.md` plus canonical `scheduled-agent-workflow`: shared invariant.
- spec-driven semantic adapter remains limited to OpenSpec artifact/delta semantics.

## Preservation semantics

Material decided scope, constraints, exclusions, and selected direction that remain applicable must survive formalization. Editorial restructuring is allowed when meaning is preserved. A material contradiction or omission is a finding even if downstream artifacts are internally consistent.

Reviewer verifies the durable decided result; it does not re-run Explore or reconstruct conversation intent.

## Human boundary

The Explore result grants no new Human authority. A materially different Human-reserved commitment must use the existing governed Human decision path.

## Alternatives rejected

- Reviewer re-runs Explore: duplicates Lead responsibility and weakens separation of duties.
- Generic Human-intent registry/invariant: broader than demonstrated defect.
- Put rule in spec-driven adapter: wrong ownership layer.

## Traceability

- Proposal: exact durable Explore-result handoff and preservation gate.
- Requirement: `Explore-originated Propose preserves the exact decision-complete Explore result`.
- Current Explore source: #86 issuecomment-5352138330.
