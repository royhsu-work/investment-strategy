# scheduled-agent-workflow Delta Specification

## ADDED Requirements

### Requirement: Explore-originated Propose preserves the exact decision-complete Explore result

When a coordination Issue reaches `Lead / propose-change` from a decision-complete `Lead / explore-change` result, the workflow SHALL treat the exact durable Explore `ACTION_RESULT` that established `PROPOSAL_READY` as the upstream semantic baseline for that formalization.

Lead MUST identify that exact Explore result in the OpenSpec proposal/readiness evidence and MUST preserve every material decided scope, constraint, exclusion, and selected direction that remains applicable. Lead MUST NOT silently replace or reinterpret a material Explore decision merely because Proposal, Specs, Design, and Tasks can be made internally consistent around a different premise.

If formalization requires a materially different product/project direction, externally observable behavior or scope trade-off, explicit risk acceptance, materially different security/privacy/cost/operational commitment, or another Human-reserved decision, Lead MUST use the governed decision path rather than claiming faithful Explore continuation.

`Reviewer / review-openspec` SHALL dereference the exact Explore result for an Explore-originated Change before applying the ordinary reverse-first and forward OpenSpec semantic gate. Reviewer SHALL verify preservation of that already-decided boundary but MUST NOT re-run Explore research, reconstruct conversation history, or infer undocumented Human intent.

A valid Human-admitted direct-to-Propose Change has no preceding Explore result and MUST NOT be required to fabricate one.

#### Scenario: Faithful Explore formalization proceeds to ordinary OpenSpec review

- GIVEN `Lead / explore-change` recorded decision-complete `PROPOSAL_READY` in durable Explore result E
- AND the same coordination Issue then reaches `Lead / propose-change`
- WHEN Lead authors the formal OpenSpec Change
- THEN the proposal/readiness evidence identifies E exactly
- AND Proposal, Specs, Design, and Tasks preserve the material decided boundaries in E
- AND Reviewer dereferences E before applying the ordinary bidirectional OpenSpec gate
- AND Reviewer does not repeat the research that produced E

#### Scenario: Internally consistent OpenSpec artifacts contradict the Explore decision

- GIVEN Explore result E decided a material scope or design boundary
- AND an Explore-originated Proposal / Specs / Design / Tasks set is internally bidirectionally traceable
- BUT the formalized set materially contradicts or drops that decided boundary
- WHEN `Reviewer / review-openspec` evaluates the Change
- THEN the gate returns `FINDINGS`
- AND internal Proposal ↔ Specs ↔ Design ↔ Tasks consistency does not substitute for preservation of E

#### Scenario: Materially different formalization returns through governed authority

- GIVEN Explore result E is proposal-ready within a bounded researched context
- AND Propose discovers that a materially different Human-reserved commitment is required
- WHEN Lead evaluates whether it may preserve E as the formalization basis
- THEN Lead does not silently rewrite E
- AND Lead uses the applicable governed Human decision path before formalizing the materially different commitment

#### Scenario: Direct Propose does not fabricate an Explore reference

- GIVEN a coordination Issue was legally admitted directly to `Lead / propose-change`
- AND no decision-complete Explore result exists for that entry
- WHEN Lead authors and Reviewer evaluates the OpenSpec Change
- THEN the workflow does not require a synthetic Explore-result reference
- AND the existing provenance-bound direct-Propose authority and ordinary OpenSpec review contracts remain applicable
