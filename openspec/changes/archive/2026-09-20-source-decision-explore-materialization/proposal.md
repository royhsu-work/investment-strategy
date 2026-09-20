# Change: Source-decision authority for bounded Explore materialization

## Why

Current Scheduled-Agent governance correctly separates ordinary pre-activation Explore queue eligibility from provenance-bound Human-reserved decisions, but shared wording can still be read as making the physical GitHub writer decisive. That ambiguity caused an explicit Human request to open one bounded Formal Explore to be materialized as an unrouted tracker instead of the complete pre-activation tuple.

The correction makes the producer/materialization boundary explicit without restoring generic Human Explore admission, creating a new repository Issue-creation surface, or creating a new authority mechanism.

## What Changes

- Clarify that authority to materialize a bounded Formal Explore follows the qualified source decision, not the physical connector/Agent writer.
- Require the interaction layer that establishes an explicit Human request and already owns the requested GitHub mutation to materialize the bounded Explore atomically as an open Issue with `Change: unset` and `action:explore-change`, with fresh-read postcondition verification of the complete tuple.
- Clarify that this ingress contract does not grant Issue-creation/routing capability to Scheduled-Agent workers or repository application.
- Preserve origin-neutral queue eligibility after materialization: formal-first, WIP=1, finish-first, and deterministic selection continue to operate only on current repository state.
- Preserve provenance-bound Human authority for later Human-reserved decisions; connector materialization is not Human proof.
- Preserve advisory-only Agent recommendations unless an existing repository-qualified producer or explicit Human request authorizes materialization.
- Replace misleading actor-centric shared wording; do not add Actions, result kinds, routing dimensions, tokens, registries, connector whitelists, or a second workflow graph.

## Capabilities

### Modified

- `scheduled-agent-workflow`: define the bounded Explore producer/materialization contract and its atomic postcondition while preserving existing dispatch, application-capability, and Human-authority semantics.

## Scope

In scope: producer/materialization authority for an explicit Human-requested bounded Formal Explore, the interaction/repository ownership boundary, shared governance wording, and focused repository regressions for downstream dispatch/Human-authority consumption.

Out of scope: implementing the external interaction product inside this repository, granting Issue creation to Scheduled-Agent application/workers, generic Human Explore approval, Human delegation protocols, #229 consequence qualification, #233 review-openspec semantics, required-follow-up creation semantics, Action-model/topology changes, and new workflow/control-plane state.

## Skill maintenance

No Role or Skill semantic responsibility change is required. `Lead / propose-change` and `Lead / resolve-question` consume the existing `openspec-change` procedure; implementation should not modify `agents/roles/lead.md` or `agents/skills/openspec-explore/SKILL.md` unless fresh implementation evidence demonstrates a concrete inconsistency with this approved contract.
