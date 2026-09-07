---
name: openspec-explore
description: Lead procedure for bounded problem exploration and proposal-ready results without creating a second workflow authority.
---

# OpenSpec Explore

Mapped Action: Lead / explore-change.

Fresh-read the current default branch, Issue/Change state, Human-approved intent, applicable canonical
specs/config, and current repository evidence. Reconstruct the current decision boundary from those sources before
forming solution candidates. Preserve already-decided outcomes, invariants,
constraints, architecture decisions, safety properties, and scope boundaries; do not substitute
implementation convenience or artifact wording for current authority.

Within that boundary, consume the existing project-wide proportionality owner
(`openspec/specs/repository-governance/spec.md`, referenced by `agents/proportionality.md`) and
apply the smallest-sufficient order: remove -> reuse -> consolidate -> existing ownership layer.
Only when those options are insufficient may a new mechanism be retained, and the result must name
the exact current requirement, concrete safety property, or demonstrated failure mode that requires
it. Hypothetical future generality is not sufficient evidence. This action-local procedure does not
define a competing normative owner.

Explore one bounded problem and return one typed result: proposal-ready,
research-required, human-decision-required, no-change-required, no-go, or blocked.

Distinguish approved scope from optional, deferred, or non-goal prose. A required separate follow-up
needs an exact source decision and one deduplicated target; it is not inferred from wording alone.
Do not create arbitrary Issues or use origin history to replace current Action state.

Use current truth for ordinary rationale and scope. Dereference Issue, PR, or archive history only
when current truth is insufficient for rationale, ambiguity, conflict, provenance, or a forensic
question; history is not the normal decision database.

The worker reports evidence and untrusted requested effects only. Repository application owns any
Issue creation, Change identity, action label, postcondition, and next_action decision. A research
gap routes through the same current Issue and preserves its existing pre-activation/formal identity.
The next Action is executed only by a later fresh wake.

Human authority requires provenance-bound evidence. Connector activity, labels, and model output do not
satisfy a Human decision.

## Conditional skill composition

When this Action materially creates or modifies a repository Skill, load
agents/skills/skill-creator/SKILL.md and
agents/skills/skill-creator/references/repository-governance.md. This repository Skill guidance is
procedural input and does not grant runtime authority.

## Conditional staged-delivery composition

When feasibility or delivery scope may require staged implementation on a then-current N-1 substrate, load
agents/skills/openspec-delivery/SKILL.md as procedural input. Use it to establish the approved
parent outcome, feasibility boundary, and continuation evidence while preserving this Action's existing
proposal-ready/research-required/human-decision-required result boundary and effect authority.
