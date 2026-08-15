# Change: Introduce optional pre-Propose Explore lifecycle

## Why

#38 identifies a semantic gap between the repository's scheduled OpenSpec workflow and current upstream OpenSpec: the repository can only enter `Lead / propose-change`, which immediately creates an immutable Change identity and formal `proposal/specs/design/tasks`, while upstream `/opsx:explore` is an optional no-stakes investigation step used before committing to a change.

This matters for Scheduled execution because fuzzy feasibility/scope questions currently have no first-class durable lifecycle. They are either forced into `propose-change`, left as informal Issues, or misrepresented as specification blockers even when research can conclude that no change should be proposed.

Current upstream OpenSpec documentation inspected for this change describes Explore as optional, codebase-reading/thinking-oriented, non-artifact-producing, non-implementation work that can examine dead ends and transition to Propose once the picture is clear. The repository should preserve that semantic core while adding only the minimum durable routing, reconstruction, Human-authority, and terminal-outcome behavior required for unattended Scheduled execution.

## What Changes

1. Add a tenth normal Scheduled action, `Lead / explore-change`, as an **optional pre-Propose investigation action**.
   - Human may directly admit concrete/buildable work to existing `Lead / propose-change` without Explore.
   - Human may admit fuzzy problem/feasibility/scope work to `Lead / explore-change`.
   - Explore keeps `Change: unset`, creates no OpenSpec change folder/artifacts, and modifies no implementation code.

2. Define decision-complete Explore outcomes.
   - `PROPOSAL_READY`: research has produced a concrete/buildable direction without unresolved material requirement/solution guesses. Because Explore admission is intentionally no-stakes, this outcome requires Human intent before routing into `propose-change`; it does not silently commit the Human to a formal Change.
   - `NO_CHANGE_REQUIRED`: evidence shows no repository change is needed.
   - `NO_GO`: evidence shows the idea is currently infeasible or unjustified; the conclusion records the material condition that could make reconsideration appropriate when one exists.
   - genuine unresolved Human intent/authority questions continue to use the existing `HUMAN_DECISION_REQUIRED` contract.

3. Extend deterministic discovery/admission without adding an Explore state machine.
   - When no formal active or terminal-pending workflow exists, Human-admitted queued `explore-change` and direct `propose-change` entries participate in one deterministic pre-activation queue ordered by earliest GitHub `created_at`, then lower Issue number.
   - The earliest open Explore remains the deterministic winner across wakes until it reaches a terminal outcome or is Human-authorized to transition to `propose-change`; no claim/lease/heartbeat/hidden `in_progress` state is added.
   - Formal Change activation still occurs only in `propose-change` when Lead persists the immutable non-`unset` Change identity.

4. Add a repository `openspec-explore`-informed Lead skill that preserves upstream problem-before-solution semantics while adapting it to durable Scheduled execution.
   - Read/search repository and relevant external evidence; compare options/trade-offs; use simple diagrams when helpful; perform existing bounded blast-radius analysis.
   - Persist only bounded conclusion/decision evidence needed for reconstruction, not live research progress or a second artifact DAG.
   - Do not introduce a separate `review-explore` gate.

5. Define terminal research Issue behavior.
   - `NO_CHANGE_REQUIRED` and `NO_GO` are valid terminal Explore results and may close the research Issue without creating a fake OpenSpec Change solely to archive it.
   - `PROPOSAL_READY` waits for Human intent on the same Issue; after valid Human approval, Lead may route the same persistent Issue to `Lead / propose-change`, still with `Change: unset`.

## Affected Capabilities

- **MODIFIED** `scheduled-agent-workflow`: action surface, Human admission/pre-activation selection, pre-Propose Explore authority, durable evidence, legal outcomes, and bootstrap/migration behavior.

## Scope Boundaries

In scope:
- optional pre-Propose `Lead / explore-change`;
- current upstream Explore semantic preservation needed for Scheduled execution;
- `Change: unset` research and formal Change activation boundary;
- deterministic queued Explore/direct-Propose coexistence;
- proposal-ready, terminal no-change/no-go, and Human-decision behavior;
- minimum role/skill/message/governance/test updates required by the new action;
- migration of deferred research Issues after this change becomes authoritative.

Out of scope:
- mid-change/sub-problem Explore lifecycle;
- independent `review-explore` gate;
- mandatory Explore for concrete work;
- implementation/archive PR consolidation;
- changing archive automation ownership or merge gates;
- Agent-triggered `workflow_dispatch` capability;
- central workflow engine, lock, lease, heartbeat, retry/progress counter, hidden ownership state, research database, memory/RAG system, or completeness scoring framework.

## Design References / Trace

- Human-admitted direction and acceptance scope: #38.
- Current repository contract: `openspec/specs/scheduled-agent-workflow/spec.md`, `agents/AGENTS.md`, `agents/roles/lead.md`, and `agents/skills/openspec-change/SKILL.md` on the default-branch baseline used to activate this Change.
- Upstream OpenSpec reference inspected on 2026-08-15: `docs/explore.md`, `docs/commands.md`, `docs/overview.md`, `docs/workflows.md`, and `docs/supported-tools.md` from `Fission-AI/OpenSpec` current `main`. These are design/reference evidence only; repository default-branch governance remains runtime authority.
- Upstream semantics preserved: Explore is optional; reads/searches the codebase and compares options; creates no change folder, formal planning artifacts, or code; can investigate dead ends; transitions to Propose when the direction is clear; workflow actions are enablers rather than rigid waterfall gates.
- Deferred single-PR archive research remains out of this Change and must be revisited only after this Explore lifecycle is authoritative.