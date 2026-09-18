# Design: Source-decision-owned Explore materialization

## Context

The repository already separates runtime queue eligibility from Human-reserved authority. Once an open Issue has `Change: unset + action:explore-change`, dispatch evaluates current repository state without using connector-vs-Human origin as a routing dimension. The remaining ambiguity occurs earlier: an interaction layer may establish an explicit Human request while a connector performs the physical GitHub write.

## Decision 1: Reuse the existing authority layers

Classify this correction as `CONSOLIDATE`: retain the existing pre-activation queue owner and Human provenance owner, and clarify only the producer/materialization boundary. No new persisted authority state is introduced.

The interaction layer establishes whether there is an explicit Human mutation request for one bounded Formal Explore. That source decision authorizes the repository mutation to materialize exactly the complete pre-activation tuple. The connector/Agent is only the actuator. Its identity neither grants nor removes source-decision authority.

## Decision 2: Atomic materialization postcondition

A Human-requested Formal Explore materialization succeeds only after fresh observation proves all of:

- one open coordination Issue for the requested bounded target;
- exactly `Change: unset`;
- exactly `action:explore-change` as routing;
- no competing normal role-routing state.

A write that creates only the Issue but omits the requested routing tuple is incomplete and must not be reported as successful materialization. Existing repository mutation/application ownership should be reused rather than adding a new control-plane state.

## Decision 3: Later dispatch remains origin-neutral

After the tuple exists, normal repository-owned dispatch uses only current durable workflow state plus existing formal-first/WIP=1/finish-first predicates. Producer provenance is not persisted as a routing dimension and does not alter queue order.

## Decision 4: Human-reserved authority remains separate

Connector materialization is not proof of a later Human-reserved decision. Existing provenance-bound Human predicates continue to require their exact qualifying decision evidence. Actor identity and connector activity remain insufficient.

## Decision 5: Autonomous recommendations remain advisory

An Agent recommendation without an explicit Human request or another repository-qualified producer cannot authorize materialization. This prevents recursive queue generation without relying on the physical writer as an authority classifier.

## Implementation impact

The narrow implementation slice updates the canonical scheduled-agent-workflow producer/materialization requirement, replaces the conflicting shared AGENTS summary wording, and adds focused regressions at the actual interaction/materialization and dispatch boundary. Role definitions, Skills, Action model, OpenSpec config, and routing topology remain unchanged unless implementation evidence proves an unexpected incompatibility; such evidence is a specification blocker rather than permission to expand scope.

Refs #234
