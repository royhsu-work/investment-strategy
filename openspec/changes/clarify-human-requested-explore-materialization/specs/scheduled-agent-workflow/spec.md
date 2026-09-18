## ADDED Requirements

### Requirement: Explicit Human-requested bounded Explore materialization follows source-decision authority

When the interaction layer has established an explicit Human request to create or open one bounded Formal Explore, that qualified source decision SHALL authorize materialization of exactly one complete pre-activation coordination tuple consisting of an open Issue, `Change: unset`, and `action:explore-change`.

The physical Agent or connector that performs the GitHub mutation MUST be treated only as the mutation actuator: its writer identity MUST neither grant materialization authority in the absence of a qualified producer nor remove authority supplied by the explicit Human request.

Successful Formal Explore materialization MUST fresh-observe the complete requested tuple. Creation or existence of an Issue without the requested `Change: unset + action:explore-change` state MUST be treated as incomplete materialization rather than success.

After successful materialization, ordinary pre-activation selection SHALL evaluate the current repository Issue/routing state under the existing formal-first, WIP=1, finish-first, and deterministic ordering rules without introducing connector-versus-Human origin as a routing dimension or requiring a generic second Human approval for bounded Explore.

This materialization authority MUST NOT satisfy or weaken any later Human-reserved decision predicate. Connector activity, writer identity, and connector-created Issue/event evidence remain insufficient substitutes for the existing provenance-bound Human authority required at Human-reserved boundaries.

An Agent-originated recommendation without an explicit Human mutation request or another repository-qualified producer MUST remain advisory and MUST NOT by itself authorize creation or routing of additional Explore work.

#### Scenario: Human explicitly requests one bounded Formal Explore through a connector actuator

- GIVEN the interaction layer has established an explicit Human request to open one bounded Formal Explore
- WHEN an Agent or connector materializes that request in GitHub
- THEN the resulting coordination Issue is open with `Change: unset` and `action:explore-change`
- AND physical writer identity neither removes nor independently supplies the source-decision authority
- AND no generic second Human Explore approval is required

#### Scenario: Partial creation is not successful materialization

- GIVEN an explicit Human request authorized one bounded Formal Explore
- WHEN the mutation creates an Issue but the requested `Change: unset + action:explore-change` tuple is not fresh-observed
- THEN the materialization is incomplete
- AND the system does not report the Formal Explore as successfully materialized

#### Scenario: Materialized Explore waits behind formal WIP

- GIVEN a Human-requested connector-materialized Explore is coherently open with `Change: unset + action:explore-change`
- AND a formal workflow currently occupies WIP
- WHEN repository-owned dispatch selects work
- THEN the new Explore remains queued under existing formal-first semantics
- AND its connector-versus-Human writer origin does not bypass ordering

#### Scenario: Origin-neutral dispatch after materialization

- GIVEN a coherently routed connector-materialized Explore later becomes the deterministic pre-activation winner
- WHEN repository-owned dispatch evaluates current work
- THEN it evaluates the Issue from current lifecycle and routing state
- AND it does not require or reject the work based on physical creator origin

#### Scenario: Agent recommendation does not recursively authorize work

- GIVEN an Agent recommends opening another Explore
- AND no explicit Human mutation request or other repository-qualified producer authorizes that materialization
- WHEN the recommendation is evaluated
- THEN the recommendation remains advisory
- AND it does not authorize creation or routing of a new Formal Explore

#### Scenario: Connector materialization is not later Human-reserved proof

- GIVEN a connector materialized an Explore from an explicit Human request
- WHEN that connector-created Issue or event is presented as evidence for a later Human-reserved decision
- THEN the existing provenance-bound Human authority predicate still applies
- AND connector activity or writer identity alone is insufficient Human proof
