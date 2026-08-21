# Change: Bound CI observation by execution opportunity

Explore baseline: issue #130 `issuecomment-5372110291` (`PROPOSAL_READY`).

## Why

#112 established continuation-by-default and positive Invocation Exit Proof. #124 added a necessary same-invocation re-observation floor for just-triggered exact validation runs, but current shared and action-local wording then treats a later absent/nonterminal observation plus no other same-authority work as sufficient proof of a genuine asynchronous wait.

PR #129 provides direct counterevidence: exact Python Quality/OpenSpec Validate runs remained `in_progress` across repeated observations yet became terminal within about 19–25 seconds. Observation count proves sampled resource state, not that the current invocation can no longer observe or consume the resource.

The workflow therefore needs a narrow prospective correction: preserve the #124 re-observation floor, but remove observation-count sufficiency and require independent positive evidence that the current legal execution opportunity can no longer perform another legal same-resource observation before ordinary asynchronous-wait Exit is allowed.

## What changes

- Clarify the shared Invocation Exit contract so absent/queued/in-progress observations, at any finite count, never independently prove that an exact external resource is unconsumable.
- Keep bounded same-invocation observation work-conserving while the current invocation can legally continue observing the same exact resource.
- Permit ordinary asynchronous-wait Exit only when a current invocation-local execution boundary independently proves that another legal same-resource observation/consumption cannot be performed now, while routing/revision/preconditions remain current.
- Preserve terminal-result consumption, stale/precondition Exit, hard execution-boundary Exit, exact-resource identity, and at-least-once reconstruction.
- Strengthen executable regressions so they model observation sequences plus execution-opportunity availability instead of accepting observation count or an unconstrained `exact_resource_unconsumable` assertion as decisive proof.
- Align the two trigger-and-consume mapped Skills that currently repeat the #124 sufficiency shortcut.

## Affected capabilities

- MODIFIED: `scheduled-agent-workflow` — Invocation Exit / exact external-resource observation semantics.

## Skill maintenance traceability

- **Modified — `agents/skills/implementation/SKILL.md`**
  - Source: #130 / `bound-ci-observation-by-execution-opportunity`.
  - Responsibility preserved: Executor implementation remains the trigger-and-consume owner for exact required implementation validation runs.
  - Rationale: remove the action-local statement that a later nonterminal observation itself establishes a real asynchronous wait; consume the corrected shared positive-proof boundary instead.
- **Modified — `agents/skills/openspec-change/SKILL.md`**
  - Source: #130 / `bound-ci-observation-by-execution-opportunity`.
  - Responsibility preserved: Lead Propose/Resolve remains the trigger-and-consume owner for exact required OpenSpec validation runs.
  - Rationale: remove the sibling action-local sufficiency shortcut and consume the same corrected shared positive-proof boundary.

No Skill is added or removed.

## Scope

In scope:

- `agents/AGENTS.md` shared exact-resource/Invocation Exit semantics;
- canonical `scheduled-agent-workflow` requirement/scenarios;
- `implementation` and `openspec-change` exact-run observation procedure;
- focused executable regression coverage for short-run, prolonged-nonterminal, terminal, stale, and explicit execution-boundary cases.

Out of scope:

- durable timers, polling/retry counters, heartbeat/lease/waiter/scheduler state;
- fixed N-observation thresholds as proof of unconsumability;
- changes to exact-head validation, role authority, workflow topology, or #111 mutation-recovery scope;
- rewriting #124 archived history;
- broad Reviewer/lifecycle Skill changes without equivalent trigger-and-consume evidence.
