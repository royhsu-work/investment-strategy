# Design: Source-decision authority for bounded Explore materialization

## Context

The repository already separates workflow state from evidence and makes `Role = role_for(Action)`. A coherently routed `Change: unset + action:explore-change` Issue is ordinary pre-activation work and is selected by current-state formal-first/WIP/ordering rules. Later Human-reserved decisions require provenance-bound Human evidence and cannot be satisfied by connector activity.

The remaining ambiguity is earlier: who authorizes creation of that complete pre-activation tuple when the Human explicitly asks the interaction layer to open one bounded Formal Explore. Shared wording about an “Agent-created ticket” can be misread as making physical writer identity dispositive.

## Decisions

### 1. Authority follows the qualified source decision

The interaction layer establishes whether the Human explicitly requested mutation: creation of one bounded Formal Explore. The connector is only the actuator. Its writer identity neither creates authority nor cancels authority already supplied by the Human request.

This rule does not ask repository runtime to classify arbitrary natural-language Issue prose. The interaction layer must already have established the explicit mutation request before invoking the repository mutation.

### 2. Materialize one complete tuple atomically

The requested consequence is one bounded object:

```text
open Issue
Change: unset
action:explore-change
```

The materialization operation must create/update only what is necessary for that tuple and fresh-observe all three postconditions. `Issue exists` without the requested Action routing is incomplete, not success.

### 3. Reuse current queue and Human-authority owners

After the tuple exists, the dispatcher evaluates current repository state exactly as it does for any other coherent pre-activation Explore. No origin field, creator class, delegation token, or second approval participates in selection.

Later Human-reserved decisions continue to use the existing provenance-bound Human predicate. Connector-created Issue/event evidence is not promoted into Human-only proof.

### 4. Autonomous Agent recommendations remain advisory

An Agent recommendation without an explicit Human mutation request or another repository-qualified producer does not authorize materialization. The positive rule names the qualifying producer; it does not infer authority from physical writer identity or recommendation prose.

## Ownership and proportionality

- `scheduled-agent-workflow` canonical spec owns the producer/materialization domain rule.
- `agents/AGENTS.md` keeps only a concise non-conflicting projection and removes actor-centric compression.
- Existing pre-activation dispatch, Action model, Lead role/Skills, and Human-reserved authority are reused with no semantic delta.
- Focused tests should exercise the materialization/postcondition and later dispatch boundary rather than freeze prose wording.

No new control-plane mechanism is justified: the existing consequence owners remain sufficient once the missing producer rule is explicit.

## Risks

The main risk is accidentally treating any Human-looking text or connector actor as authority. Tests and implementation must bind the positive rule to an already-established explicit Human mutation request at the interaction boundary, while leaving repository dispatch and Human-reserved predicates unchanged.
