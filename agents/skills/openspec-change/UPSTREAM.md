# Upstream responsibility provenance

- Upstream repository: `Fission-AI/OpenSpec`
- Upstream Skill path: `skills/openspec-propose/`
- Upstream revision: `2826b8889e5223a9a8095d4428b60b56597e1020`
- Local Skill: `agents/skills/openspec-change/SKILL.md`
- Relationship: semantic adaptation of upstream Propose plus repository-original specification-resolution composition.

## Relationship

The local Skill carries upstream Propose responsibility for creating the proposal/spec/design/tasks artifact set, while repository governance adds formal activation and combines that authoring path with the local `Lead / resolve-question` correction action.

## Added responsibilities

- Persistent Change activation, single-active admission checks, and combined pre-activation queue handling.
- `Lead / resolve-question` for Reviewer/specification findings and Human-reserved clarification.
- Exact-revision validation readiness, non-closing PR linkage, and durable cross-role handoff evidence.
- Consumption of the repository-owned substantive Human-input freshness/disposition invariant before consequential specification/readiness/resolution results and ownership transfers.

Reason: OpenSpec authoring is embedded in a scheduled multi-role repository workflow with explicit Human/Lead authority and revision-bound gates, and consequential handoffs must not silently skip newer material Human input.

Maintenance implication: these additions are repository governance integrations; future upstream Propose changes must not erase them unless the owning repository contracts change. The shared Human-input classifier remains owned by `agents/AGENTS.md`.

## Deleted or omitted responsibilities

- Upstream CLI-driven instruction/status orchestration is not adopted as the local runtime authority.
- Independent semantic review is not performed by this Skill; `Reviewer / review-openspec` owns that gate.

Reason: the scheduled environment reconstructs OpenSpec semantics through the repository semantic adapter and CI, while separation of duties forbids Lead from self-approving authored semantics.

Maintenance implication: if upstream moves semantic checks into Propose, evaluate them as authoring readiness only unless repository governance explicitly transfers independent review authority.

## Modified responsibilities

- Upstream Propose is constrained by repository admission, immutable Change identity, exact validation, and traceability/handoff contracts.
- Proposal correction is decomposed: Lead authors/revises meaning; Reviewer independently re-gates material semantic changes.
- Readiness/resolution completion additionally consumes shared current coordination-Issue Human-input freshness/disposition evidence without redefining provenance classification or Human authority.

Reason: repository role separation and at-least-once execution require durable authority, revision, and newer-material-input boundaries beyond the upstream single-agent flow.

Maintenance implication: future upstream revisions must be compared responsibility-by-responsibility so role decomposition and shared consequential-boundary consumption are preserved intentionally rather than appearing as drift.