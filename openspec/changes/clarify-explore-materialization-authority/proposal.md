# Change: Clarify bounded Explore materialization authority

## Why

Current workflow semantics already keep ordinary pre-activation Explore queue eligibility origin-neutral once an Issue is coherently routed, but shared governance still compresses producer authority into actor-centric wording about an "Agent-created ticket". In connector-mediated interaction this can misclassify an explicit Human request to open one bounded Formal Explore as unauthoritative merely because the connector is the physical writer, leaving an incomplete `Change: unset` tracker.

The demonstrated defect is at the producer/materialization boundary, not in dispatch, Human-reserved authority, or the Action model.

## What Changes

- Clarify that authority to materialize one bounded Formal Explore follows the qualified source decision, not the physical writer identity.
- Define the explicit Human interaction-layer request as sufficient producer authority for materializing exactly one complete pre-activation tuple: open Issue + `Change: unset` + `action:explore-change`.
- Require materialization success to observe that complete tuple atomically; Issue existence without coherent routing is incomplete.
- Preserve origin-neutral later dispatch from current repository state and preserve provenance-bound Human authority for later reserved decisions.
- Preserve autonomous Agent recommendations as advisory unless an existing repository-qualified producer or explicit Human request authorizes materialization.
- Replace misleading actor-centric shared wording with source-decision-centric wording and add focused behavioral regressions at the materialization/dispatch boundary.

## Affected Capabilities

- `scheduled-agent-workflow` (modified)

## Scope Boundaries

No new Action, Result kind, workflow phase, label class, approval/delegation token, origin registry, authority registry, queue state, connector whitelist, second DAG, cursor, or policy engine. Generic Human Explore admission is not restored. Connector identity is not Human identity. Existing formal-first/WIP=1/finish-first ordering, Action-only routing, same-Issue Explore→Propose continuation, and later Human-reserved provenance checks remain unchanged. #229 and #233 remain separate scopes.

## Skill Maintenance

No repository Skill change is required. `Lead` and `openspec-explore` already consume bounded Explore authority after coherent routing; the defect is producer/materialization ownership plus shared projection wording. The Action model and routing topology also require no change.

Refs #234
