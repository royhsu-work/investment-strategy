# Change: Clarify Human-requested Explore materialization authority

## Why

Current bounded-Explore dispatch is already origin-neutral once an Issue is coherently routed, but shared governance compresses source authority and physical writer identity into the phrase that an “Agent-created ticket” cannot self-authorize work. Under connector-mediated interaction this can leave an explicitly Human-requested Formal Explore materialized as an unrouted tracker even though the Human authorized creation of that bounded work.

The correction is to make producer/materialization authority source-decision based while preserving current queue eligibility and provenance-bound Human-reserved authority as separate concepts.

## What Changes

- Define the qualified interaction-layer Human request as authority to materialize one bounded Formal Explore as the complete pre-activation tuple: open Issue, `Change: unset`, and `action:explore-change`.
- Make physical connector/Agent writer identity neither a grant nor a denial of that materialization authority.
- Require materialization to verify the complete tuple; an Issue that exists without the requested routing is not successful Formal Explore materialization.
- Preserve origin-neutral ordinary Explore dispatch after materialization and preserve existing provenance-bound Human authority for later reserved decisions.
- Replace actor-centric shared wording with source-decision-centric wording; do not add a new workflow state, token, origin registry, Action, Result kind, or second approval.

## Capabilities

### Modified Capabilities

- `scheduled-agent-workflow`: clarify the producer/materialization boundary for an explicit Human request to open one bounded Formal Explore, without changing ordinary dispatch or reserved Human-authority semantics.

## Impact

Expected implementation is limited to the canonical workflow requirement, its concise shared-governance projection, and focused behavioral regression coverage for atomic materialization and later origin-neutral dispatch. Role, Skill, executable Action topology, generic Human Explore admission, and provenance-bound Human-reserved decision predicates remain unchanged unless implementation evidence proves an existing owner cannot express the approved rule.

Refs #234
