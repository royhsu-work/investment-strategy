# Design

## Context

The repository already has three distinct ownership concepts: pre-activation queue eligibility is derived from coherent current routing; Human-reserved decisions use provenance-bound Human evidence; mutation carriers merely execute already-authorized effects. The demonstrated defect is at ingress: shared wording about an `Agent-created ticket` compresses source-decision authority and physical writer identity, making a connector-actuated explicit Human request appear unauthoritative.

Executor implementation exposed a second ambiguity in the first proposal revision: it described the atomic materialization as an existing repository application behavior even though current default-branch repository application deliberately does not own Issue creation and the interaction surface that receives the Human request is external to the repository. The correction therefore must specify the boundary without inventing a repository actuator that does not exist.

## Decision 1: Reuse the existing authority layers

Use the existing `scheduled-agent-workflow` capability as the single normative owner of the repository-visible contract. The interaction layer establishes whether there is an explicit Human mutation request for one bounded Formal Explore and uses its available GitHub mutation capability to materialize that already-authorized consequence. The repository dispatcher later consumes only the freshly observed current repository state.

The repository does not acquire a new Issue-creation capability, producer service, or application ingress for this change. No origin registry, delegation token, connector whitelist, approval label, or additional workflow state is introduced.

## Decision 2: Make bounded Explore materialization atomic at the interaction boundary

For an explicit Human request to open one bounded Formal Explore, the required externally observable consequence is one open Issue whose body contains `Change: unset` and whose routing contains exactly `action:explore-change`. The interaction-layer operation is complete only after a fresh GitHub read observes the whole tuple. Observing an Issue without the requested routing is an incomplete materialization, not success.

This is a producer/materialization postcondition, not a new repository dispatcher predicate and not a Scheduled worker effect. Once materialized, the Issue competes under existing formal-first, WIP=1, finish-first, and deterministic pre-activation ordering.

## Decision 3: Source decision is distinct from writer identity

The physical writer may be a connector or Agent actuator acting for the interaction layer. Writer identity neither grants authority for an autonomous recommendation nor removes authority already established by an explicit Human mutation request. Issue prose by itself is not promoted into authority and repository runtime is not required to classify arbitrary natural language.

## Decision 4: Preserve later Human-reserved provenance

The connector-created Issue/event is only evidence that an authorized materialization occurred. It cannot satisfy later Human-reserved requirement, scope, risk, architecture, or approval predicates. Those continue to require the existing provenance-bound Human decision path.

## Decision 5: Keep autonomous recommendations non-recursive

An Agent-originated recommendation without an explicit Human request or another repository-qualified producer remains advisory. It does not authorize Issue creation/routing and cannot recursively create new queue work.

## Blast radius

Implementation is intentionally split by ownership. Repository changes are limited to the canonical `scheduled-agent-workflow` contract, concise shared wording in `agents/AGENTS.md`, and focused repository regressions proving that dispatch/Human-authority consumers remain origin-neutral and provenance-safe. The interaction-layer atomic create/update + fresh-read postcondition is a required behavior of the external producer that already owns the Human-requested GitHub mutation; it is not implemented by Scheduled-Agent repository application. Role documents, Explore/Change Skills, executable Action model, routing topology, OpenSpec config, and normal worker effect capability require no semantic change.

## Validation

Repository regressions must prove that a coherently materialized tuple is consumed without writer-origin classification, formal WIP ordering remains intact, autonomous recommendation evidence does not become repository authority, and connector provenance cannot satisfy later Human-reserved authority. The interaction boundary must separately observe the complete open Issue + `Change: unset` + exactly one `action:explore-change` tuple before reporting Human-requested materialization success.
