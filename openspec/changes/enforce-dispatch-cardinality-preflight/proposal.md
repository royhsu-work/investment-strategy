# Change: Enforce dispatch cardinality preflight

## Why

The Scheduled-Agent workflow already requires WIP=1, finish-first scheduling, complete repository-wide active/terminal-pending cardinality, and fail-closed handling of ambiguous or multiple active workflows. The #86/#100 incident demonstrates that these semantic requirements are not sufficiently operationalized at the Scheduled-Agent execution boundary: a later pre-activation Explore ran while a formal workflow already existed, then activated as a second formal workflow, and later wakes continued normal actions instead of failing closed.

The durable timeline rules out a simultaneous activation race as the sole explanation. The failure persisted across separate wake windows. Current tests largely prove that governance text contains the intended invariants; they do not prove that a Scheduled-Agent pre-dispatch reconstruction uses a complete repository-wide enumeration before selecting work.

## What Changes

- Make complete repository-wide dispatch reconstruction a concrete mandatory pre-dispatch procedure before any role/action selection.
- Require the reconstruction evidence to establish enumeration completeness; a partial page, role-local search, candidate-local read, or otherwise incomplete result is never proof of zero or one formal workflow.
- Define one explicit cardinality decision table in shared governance: zero formal/terminal work may enter the deterministic pre-activation queue; exactly one selects only that workflow; multiple or indeterminate cardinality fails closed before a mapped action proceeds.
- Strengthen the pre-activation action boundary so `explore-change` may begin only from a preflight proving zero formal/terminal work and deterministic queue-winner identity, while `propose-change` continues to re-check the same complete-cardinality contract immediately before and after activation.
- Preserve fail-closed handling when multiple formal workflows already exist. Scheduled Agents must not choose a winner, clear Change identities, or rewrite routing to repair that state automatically; Human/maintainer administrative repair remains outside normal Scheduled-Agent lifecycle execution.
- Add fixture-driven regression coverage for 0/1/2/indeterminate active cardinality, partial enumeration, active-over-pre-activation ordering, stale activation, and multiple-active fail-closed behavior without introducing a runtime dispatcher engine or duplicate workflow DAG.
- Keep external Scheduled Task prompts bootstrap-only; slot names/count/cadence remain external configuration rather than workflow authority.

## Affected Capabilities

### Modified

- `scheduled-agent-workflow`
  - active/terminal-pending cardinality reconstruction;
  - workflow-dynamic dispatch preflight;
  - pre-activation Explore/Propose execution preconditions;
  - multiple-active fail-closed recovery boundary;
  - regression evidence for deterministic dispatch safety.

## Scope

In scope:

- Shared Scheduled-Agent governance needed to make cardinality reconstruction an explicit executable procedure and decision table.
- Narrow `openspec-explore` / `openspec-change` procedural references needed to consume the shared preflight at the pre-activation boundary without duplicating global semantics.
- Canonical scheduled-agent-workflow requirement/scenario updates.
- Deterministic fixture-driven tests for complete-cardinality and fail-closed dispatch behavior.

Out of scope:

- Implementing #86, #100, or #98 substantive changes.
- Automatically choosing a winning workflow when durable state already contains multiple active workflows.
- Automatically clearing or rewriting immutable Change identities as recovery.
- A lock, lease, heartbeat, claim, hidden queue, global priority engine, exactly-once subsystem, or second workflow DAG.
- Copying dispatch semantics into external Scheduled Task prompts.
- Changing Human authority, role separation, Reviewer independence, or normal lifecycle gates.

## Traceability

- Source decision-complete Explore: #105 issuecomment-5344430363.
- Incident evidence: #86 and #100 durable lifecycle comments and their former PRs #103/#104.
- Existing canonical safety requirement: `Active-workflow cardinality and Issue-state coherence precede queue selection`.
- Capability delta: `specs/scheduled-agent-workflow/spec.md`.
- Design: `design.md`.
- Implementation slices: `tasks.md`.
