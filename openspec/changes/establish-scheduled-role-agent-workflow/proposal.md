# Proposal — establish-scheduled-role-agent-workflow

## Why

The repository already uses OpenSpec, GitHub Issues, Pull Requests, and deterministic GitHub Actions automation, but collaboration between recurring AI roles is still informal and depends on interactive conversation context.

The project needs a repository-level governance contract that lets Scheduled Tasks wake a specific role, reconstruct durable state from GitHub and the repository, perform one explicitly admitted action, and hand work to the next role without relying on conversation memory or inventing a second workflow engine.

Issue #17 explored and reviewed this model. Issue #18 is the Human-authorized coordination instance that promotes the reviewed design into an OpenSpec change.

## What Changes

This change establishes a scheduled role-based agent workflow with these externally governable behaviors:

- Define three scheduled roles: `Lead`, `Reviewer`, and `Executor`.
- Add `agents/AGENTS.md` as the shared execution protocol loaded from the default branch.
- Add role-specific authority and prohibitions under `agents/roles/*.md`.
- Add a reduced set of reusable procedural skills under `agents/skills/*`; skills describe collaboration procedures and do not duplicate OpenSpec's proposal/spec/design/tasks artifact DAG.
- Use GitHub Issues as the scheduled-agent queue/control plane, with one persistent coordination Issue per OpenSpec change.
- Require exactly one logical routing tuple `(agent:<role>, action:<action>)` for actionable workflow work; invalid or contradictory routing fails closed.
- Support the nine normal MVP actions:
  - Lead: `propose-change`, `resolve-question`, `finalize-change`, `finalize-archive`;
  - Reviewer: `review-openspec`, `review-implementation`, `review-archive`;
  - Executor: `implement-change`, `merge-pr`.
- Separate authority by artifact: Lead owns specification decisions/artifacts and lifecycle authorization; Reviewer owns independent revision-bound gates; Executor owns implementation and authorized operational mutations; repository automation retains deterministic normal OpenSpec archive mechanics.
- Treat scheduled execution as at-least-once and reconstructable. Partial/interrupted work retains current routing until a durable handoff completes.
- Require revision-aware/idempotent preconditions and fail-closed behavior for stale or contradictory evidence. `fresh-read routing → update labels` is explicitly not a mutex or compare-and-swap guarantee.
- Preserve multi-PR OpenSpec lifecycles, including `MORE_IMPLEMENTATION_REQUIRED → Executor / implement-change` when merged default-branch state remains incomplete.
- Wait for normal archive automation only after merged default-branch state satisfies the existing repository archive eligibility contract.
- Require merge authorization to be revision-bound; Executor may merge only an explicitly authorized unchanged PR revision whose required gate still holds.
- Support Lead idle advisory mode with at most one open `advisory:idle` Issue and at most three recommendations.
- Preserve explicit Human workflow admission. Idle advisory admission requires both an unambiguous selected direction and reserved Human capability `intake:approved`; scheduled roles may consume but must never add, remove, restore, or manufacture that marker.
- Treat comments/review results as evidence rather than canonical lifecycle state. Final coordination completion requires the GitHub Issue to be observed `closed`; a completion comment or PASS alone is insufficient.
- Update the repository lifecycle documentation so the new role/gate ownership is explicit and consistent with the existing deterministic archive workflow.

## Capabilities

### New Capabilities

- `scheduled-agent-workflow`: repository governance and durable coordination semantics for scheduled `Lead`, `Reviewer`, and `Executor` roles operating through GitHub Issues, OpenSpec changes, PRs, and existing repository automation.

### Modified Capabilities

None. This change establishes a repository-development governance capability and does not change Strategy, market-data, Decision, or Backtest analytical behavior.

## Scope Boundaries

This change intentionally defines the governance and repository artifacts needed for scheduled role collaboration.

It does **not** introduce:

- a central DAG/workflow engine or declarative transition engine;
- leases, heartbeats, retry counters, progress percentages, `status:in-progress`, or exactly-once execution;
- autonomous admission of arbitrary Issues, PRs, repository activity, or discovered requirements into scheduled workflow;
- cryptographic proof that a GitHub action was performed by a Human rather than an agent; `intake:approved` is a governance capability boundary;
- a second OpenSpec artifact lifecycle parallel to proposal/specs/design/tasks;
- a scheduled-agent replacement for the existing deterministic normal OpenSpec archive GitHub Actions workflow;
- scheduled-agent archive repair/recovery actions beyond the repository's existing recovery/manual contracts;
- changes to production investment strategy, market-data, Decision, Backtest, execution, or portfolio behavior;
- implementation of an external scheduler platform itself. Scheduled Tasks remain a polling/wake-up mechanism.

## Impact

Expected affected areas:

- new `agents/AGENTS.md` shared governance;
- new `agents/roles/lead.md`, `reviewer.md`, and `executor.md`;
- reusable `agents/skills/*` procedures mapped to the nine action contracts;
- GitHub routing/admission labels and coordination-Issue conventions;
- README development lifecycle and responsibility documentation;
- repository tests or validation scripts needed to verify governance files, routing/action mappings, and required invariants;
- OpenSpec canonical capability documentation after archive.

No public investment-analysis artifact schema or market behavior changes in this proposal.

## Deferred Work

Follow-up changes may add stronger locking/CAS mechanisms, richer machine-readable handoff state, child work-item orchestration, additional roles/actions, or archive-recovery agent actions only if operational evidence demonstrates that the MVP reconstruction/idempotency model is insufficient.
