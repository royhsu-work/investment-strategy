# Design: Skill maintenance guidance and project-wide simplicity

## Decision 1 — Promote proportionality instead of adding another philosophy layer

The current proportionality rule is workflow-specific in both `agents/proportionality.md` and canonical `scheduled-agent-workflow`. #35 requires the same reasoning across the whole project. The narrowest correct ownership is therefore the existing `repository-governance` capability, with concise runtime implementation/reference in the already-authoritative surfaces that need to apply it.

Implementation should remove the standalone workflow-only ownership rather than keep two synchronized normative copies. This is an ownership relocation, not a weakening of the existing workflow constraint.

Trace: #35 project-wide simplicity direction → `repository-governance` project-wide proportionality requirement.

## Decision 2 — Adopt principles from skill-creator, not its mutable implementation

Anthropic's `skill-creator` supplies useful design patterns: keep the main Skill focused, use progressive disclosure, and place conditionally needed material in referenced resources. It also includes a much broader eval/benchmark/tooling workflow that this repository does not currently require.

The repository will adopt only the approved principles needed by #35. Scheduled execution will not fetch or obey upstream `skill-creator`; default-branch repository governance remains authoritative. No mandatory benchmark/eval subsystem is introduced.

Trace: #35 skill-creator direction → `repository-governance` Skill-maintenance requirement.

## Decision 3 — Shared Skill guidance follows existing authority boundaries

A mapped `SKILL.md` continues to own action-specific executable procedure. Shared runtime invariants stay in `agents/AGENTS.md`; role authority stays in `agents/roles/*`. If multiple Skills genuinely need identical procedural/reference material, implementation may extract one explicit reusable resource with clear load conditions, but must not create shared resources speculatively.

This keeps progressive disclosure compatible with #29 SSOT ownership and avoids moving global rules into Skill files merely for convenience.

Trace: `repository-governance` Skill-maintenance requirement → existing #29 ownership matrix.

## Decision 4 — Lead idle review remains advisory, not self-modification

The existing bounded idle advisory mode is extended only in recommendation content: recent durable workflow evidence may reveal repeated mistakes, missing/obsolete Skill instructions, unnecessary Skill complexity, or duplicated guidance. Lead may recommend the narrowest supported maintenance change, but cannot mutate governed Skill behavior from idle mode.

A recommendation becomes implementation work only after normal Human admission and OpenSpec workflow. No new routing tuple, maintenance state machine, memory store, or autonomous self-modification path is added.

Trace: #35 idle-maintenance direction → `scheduled-agent-workflow` modified idle-advisory requirement.

## Decision 5 — Apply simplicity within blast radius

Proposal, design, review, and implementation should ask whether added/retained concepts are required, but only for concepts materially touched by the current change. This avoids turning proportionality into a permanent repository-wide cleanup gate.

The rule applies equally to runtime state, dependencies, configuration, data models, production architecture, tests/tooling, Actions, and Agent governance because the capability-level owner is project-wide rather than workflow-specific.

Trace: #35 acceptance questions → `repository-governance` project-wide proportionality scenarios.

## Deferred

- Agent memory/knowledge/RAG systems remain unsupported absent new concrete evidence.
- Mandatory Skill eval/benchmark tooling is deferred; objective tests may be added when a specific Skill change benefits from them.
- Explore lifecycle remains #38.
- No unrelated existing architecture is refactored solely to demonstrate the new principle.
