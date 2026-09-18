# Design

## Context

The repository already has three distinct ownership concepts: pre-activation queue eligibility is derived from coherent current routing; Human-reserved decisions use provenance-bound Human evidence; mutation carriers merely execute already-authorized effects. The demonstrated defect is at ingress: shared wording about an `Agent-created ticket` compresses source-decision authority and physical writer identity, making a connector-actuated explicit Human request appear unauthoritative.

## Decision 1: Reuse the existing authority layers

Use the existing `scheduled-agent-workflow` capability as the single normative owner. The interaction layer establishes whether there is an explicit Human mutation request for one bounded Formal Explore. Repository mutation then materializes the already-authorized consequence. The dispatcher later consumes only current repository state.

No origin registry, delegation token, connector whitelist, approval label, or additional workflow state is introduced.

## Decision 2: Make bounded Explore materialization atomic by postcondition

For an explicit Human request to open one bounded Formal Explore, the required consequence is one open Issue whose body contains `Change: unset` and whose routing contains exactly `action:explore-change`. Creation is complete only after a fresh read observes the whole tuple. Observing an Issue without the requested routing is an incomplete materialization, not success.

This is an ingress/application invariant, not a new dispatcher predicate. Once materialized, the Issue competes under existing formal-first, WIP=1, finish-first, and deterministic pre-activation ordering.

## Decision 3: Source decision is distinct from writer identity

The physical writer may be a connector or Agent actuator. Writer identity neither grants authority for an autonomous recommendation nor removes authority already established by an explicit Human mutation request. Issue prose by itself is not promoted into authority and repository runtime is not required to classify arbitrary natural language.

## Decision 4: Preserve later Human-reserved provenance

The connector-created Issue/event is only evidence that an authorized materialization occurred. It cannot satisfy later Human-reserved requirement, scope, risk, architecture, or approval predicates. Those continue to require the existing provenance-bound Human decision path.

## Decision 5: Keep autonomous recommendations non-recursive

An Agent-originated recommendation without an explicit Human request or another repository-qualified producer remains advisory. It does not authorize Issue creation/routing and cannot recursively create new queue work.

## Blast radius

Expected implementation surfaces are the canonical `openspec/specs/scheduled-agent-workflow/spec.md`, concise shared wording in `agents/AGENTS.md`, and focused existing tests at the materialization/dispatch boundary. Role documents, Explore/Change Skills, executable Action model, routing topology, and OpenSpec config require no semantic change.

## Validation

Behavioral regressions must prove: explicit Human-requested connector materialization yields the complete tuple; incomplete tuple fails postcondition; queued work does not bypass formal WIP; connector origin does not affect later dispatch eligibility; autonomous recommendation alone cannot authorize materialization; and connector provenance cannot satisfy later Human-reserved authority.
