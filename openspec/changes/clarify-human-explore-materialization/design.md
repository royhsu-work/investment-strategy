# Design: source-decision authority for Human-requested Explore materialization

## Boundary

The defect is not queue selection. Current routing already makes a coherently routed `Change: unset + action:explore-change` Issue eligible under ordinary pre-activation ordering. The defect is the producer/materialization boundary before that state exists: actor-centric wording can cause a connector carrying an explicit Human mutation request to create only an unrouted tracker.

Keep four identities separate:

1. **Source decision authority** — the explicit Human request established by the interaction layer for this bounded materialization.
2. **Mutation carrier/writer** — connector/Agent that performs the requested GitHub mutation.
3. **Canonical workflow state** — open Issue + `Change: unset` + `action:explore-change`.
4. **Later reserved Human authority** — separately provenance-bound evidence required by later Human-only decisions.

The writer neither grants nor removes source authority.

## Minimum correction

Reuse the existing canonical workflow and Action-only routing. Do not add a producer registry or new runtime state.

For an explicit Human request to open one bounded Formal Explore, the interaction-side materializer supplies the bounded Issue content and `action:explore-change` as one requested consequence. Success requires fresh observation of all three postconditions: Issue open, `Change: unset`, exact action label present. If creation yields an Issue without the requested routing, report incomplete materialization; do not reinterpret physical authorship as a reason to leave it unrouted.

Once those postconditions exist, the dispatcher uses the same current-state eligibility path as every other coherently routed pre-activation Explore. It does not classify eligibility by creator identity.

An autonomous Agent recommendation has no equivalent source decision and therefore remains advisory. Later Human-reserved decisions continue to require their existing exact provenance-bound evidence; the connector-created Issue/event is insufficient.

## Ownership

`openspec/specs/scheduled-agent-workflow/spec.md` owns the bounded producer/materialization behavior because it defines Formal Explore lifecycle semantics. `agents/AGENTS.md` should retain only concise source-decision-centric orientation. Role/Skill and `scheduled_agent_action_model.py` need no semantic change: they consume an already-materialized Action.

## Safety

This correction does not create a new admission path into formal Change activation. It only makes the already-Human-requested pre-activation materialization complete. Formal-first/WIP=1 ordering still determines when Explore runs; `propose-change` still requires exact durable same-Issue `PROPOSAL_READY`; later reserved Human decisions retain existing provenance checks.
