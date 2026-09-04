# Upstream responsibility provenance

- Upstream repository: `Fission-AI/OpenSpec`
- Upstream Skill path: `skills/openspec-explore/`
- Upstream revision: `2826b8889e5223a9a8095d4428b60b56597e1020`
- Local Skill: `agents/skills/openspec-explore/SKILL.md`
- Relationship: semantic adaptation for repository-scheduled Formal Explore.

## Relationship

The local Skill preserves the upstream Explore responsibility of investigating a problem before committing to a formal change. Repository governance wraps that responsibility in durable admission, routing, evidence, and bounded-disposition rules needed by scheduled execution.

## Added responsibilities

- Human-created/general Human admission and repository-authorized admission reconstruction.
- Durable `PROPOSAL_READY`, `NO_CHANGE_REQUIRED`, `NO_GO`, and Human-decision boundaries.
- Same-Issue transition and same-role continuation into repository Propose.

Reason: scheduled runs must reconstruct authority and ownership from durable repository state rather than conversation context.

Maintenance implication: preserve these repository-owned admission and durability additions when refreshing the upstream Explore baseline; reassess only if upstream gains equivalent durable workflow semantics.

## Deleted or omitted responsibilities

- Upstream interaction patterns that rely on a live conversational session rather than repository routing/evidence are not adopted as runtime authority.
- Formal proposal/spec/design/task creation remains omitted from Explore and is owned locally by `Lead / propose-change` through `openspec-change`.

Reason: repository Explore is intentionally pre-Change and must not create a second artifact lifecycle.

Maintenance implication: future upstream Explore additions that cross into formal authoring must be evaluated against the repository's explicit Explore→Propose authority boundary rather than copied automatically.

## Modified responsibilities

- Upstream exploratory judgment is constrained to one admitted authority envelope and a finite repository disposition set.
- Exploration completion is represented through durable Issue evidence and routing instead of session-local continuation.

Reason: at-least-once scheduled execution requires deterministic reconstruction and fail-closed authority handling.

Maintenance implication: compare future upstream semantic changes against the bounded disposition and admission contract before adapting them.