# source-decision-authority-for-human-requested-explore

## Intent

Clarify the producer/materialization boundary for one explicitly Human-requested bounded Formal Explore without changing ordinary Explore queue eligibility or reserved Human authority.

A physical connector/Agent writer is an actuator, not the authority source. When the interaction layer has already established an explicit Human request to materialize one bounded Formal Explore, repository materialization must atomically establish the complete pre-activation tuple: an open coordination Issue, `Change: unset`, and `action:explore-change`. A partial `exists but unrouted` Issue is not a successful materialization postcondition.

After materialization, ordinary repository-owned dispatch remains origin-neutral and uses current canonical routing/WIP/finish-first predicates. Connector authorship does not become proof for later Human-reserved decisions. An Agent recommendation without an explicit Human request or another repository-qualified producer remains advisory and cannot recursively authorize routed work.

## Scope

- Clarify the canonical scheduled-agent-workflow producer/materialization contract only where current canonical meaning is missing.
- Replace actor-centric shared wording with source-decision-centric orientation.
- Add focused regression coverage for atomic Human-requested bounded Explore materialization and later origin-neutral dispatch.
- Preserve the current executable Action model, Role derivation, routing topology, WIP=1/finish-first, and provenance-bound Human authority.

## Non-goals

- No generic Human approval requirement for ordinary Explore.
- No connector-as-Human identity.
- No new Action, Result kind, routing dimension, approval/delegation token, origin registry, authority registry, queue state, connector whitelist, or control-plane mechanism.
- No weakening of later Human-reserved provenance checks.
- No redesign of #229/#233 or generic required-follow-up materialization.

## Affected capabilities

- `scheduled-agent-workflow`: producer/materialization authority for explicit Human-requested bounded Formal Explore.

## Deferred / unchanged

- Role/Skill semantics, executable Action model, transport topology, and generic Human-reserved decision mechanics remain unchanged unless implementation evidence proves a direct contradiction with this bounded contract.
