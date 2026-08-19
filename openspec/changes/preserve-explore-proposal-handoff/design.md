# Design: Preserve Explore-to-Propose semantic handoff

## Context

The repository now has an explicit pre-Propose Explore lifecycle. Explore writes a durable `ACTION_RESULT` and may route the same Issue to Propose when the result is `PROPOSAL_READY`. Current Propose and Reviewer contracts already require bounded scope, durable evidence, OpenSpec traceability, and dereferencing of declared upstream decision references, but they do not make the exact Explore result mandatory provenance for an Explore-originated formal Change.

That leaves one semantic gap: the downstream OpenSpec artifact set can be internally coherent while replacing the premise Explore already decided.

## Decision

Use the existing durable Explore `ACTION_RESULT` as the handoff anchor. Do not add an intent registry, separate traceability DAG, or Human-intent audit.

For an Explore-originated Change:

```text
Lead / explore-change
  → ACTION_RESULT E: PROPOSAL_READY
        ↓ exact durable reference
Lead / propose-change
  → Proposal / Specs / Design / Tasks preserve E
        ↓
Reviewer / review-openspec
  → dereference E
  → verify preservation
  → then run ordinary reverse-first + forward OpenSpec gate
```

Direct-to-Propose remains:

```text
Human-authorized direct Propose
  → no synthetic Explore reference
  → ordinary OpenSpec authoring/review
```

## Ownership

- `openspec-explore` owns production of the decision-complete result and remains research-only.
- `openspec-change` owns exact reference capture and faithful formalization when Propose originated from Explore.
- `openspec-review` owns independent preservation verification before its existing OpenSpec semantic gate.
- `agents/AGENTS.md` and canonical `scheduled-agent-workflow` own the shared handoff invariant.
- `openspec-semantic-adapter.md` remains limited to spec-driven schema/artifact/delta/canonicalization semantics.

## Preservation semantics

Reviewer compares only material decided content that survives into formalization: selected direction, scope boundary, explicit exclusions/constraints, and decisions that would materially change requirements/design/tasks if altered. Reviewer does not reconstruct why Explore reached those decisions unless the durable result itself declares an upstream authoritative reference that must be dereferenced under existing rules.

An omission or contradiction is a finding when it changes the formalized meaning. Editorial restructuring or more precise formal wording is allowed when it preserves that meaning.

## Human boundary

The handoff reference does not grant new authority. If Propose would cross into a new Human-reserved product/scope/risk/security/privacy/cost/operational commitment, existing `HUMAN_DECISION_REQUIRED` semantics apply. The durable Explore result cannot be used to manufacture Human authority outside its bounded context.

## Alternatives rejected

### Reviewer re-runs Explore

Rejected because it duplicates Lead responsibility, weakens separation of duties, and makes review dependent on research reconstruction rather than durable outcome verification.

### Generic Human durable-intent invariant

Rejected because the demonstrated defect is narrower: preservation of an existing repository-defined Explore result. A cross-domain intent framework would add unnecessary authority semantics.

### Put the rule in the spec-driven semantic adapter

Rejected because the adapter represents OpenSpec schema semantics. Explore-to-Propose preservation is repository workflow semantics and must remain owned by workflow governance and mapped actions.

## Traceability

- Proposal: exact durable Explore-result handoff and Reviewer preservation gate.
- Capability requirement: `Explore-originated Propose preserves the exact decision-complete Explore result`.
- Source Explore: #86 issuecomment-5342834590.
- Historical counterexample class: #35; #40 provides downstream semantic-adapter history but is not the ownership layer for this correction.
