# Change: Extract authoritative workflow topology

Explore source: `issuecomment-5363202052` on coordination Issue #80.

## Why

Current runtime workflow topology is materially distributed across `agents/AGENTS.md`, role files, mapped Skills, README orientation, and canonical workflow requirements. The distribution makes it difficult to identify the single runtime owner of action progression, correction loops, and terminal relationships and creates synchronization-by-convention risk.

The decision-complete Explore concluded that this is an ownership/SSOT problem, not a request to change lifecycle behavior. The current post-#115 terminal contract on default branch is part of the behavior that must be preserved.

## What changes

- Add `agents/workflow.md` as the authoritative runtime owner of end-to-end Scheduled-Agent workflow topology and lifecycle relationships.
- Move or replace duplicated topology definitions in `agents/AGENTS.md` with references while retaining shared dispatch, cardinality, Human-authority, invocation, reconstruction, and execution invariants there.
- Keep role files authoritative for role mission/authority/ownership and mapped Skills authoritative for action-local executable procedure; local predecessor/successor references may orient execution but must not redefine global topology.
- Keep canonical OpenSpec as the approved capability requirement/acceptance source rather than turning it into the runtime instruction-loading DAG.
- Keep README as Human/contributor orientation and point it to the authoritative topology surface instead of maintaining another normative workflow copy.
- Add focused structural/behavioral regressions proving one runtime topology owner while preserving the current legal action progression, correction loops, pre-Change Explore outcomes, and final terminal path.

## Affected capabilities

- `scheduled-agent-workflow` — add a requirement for one authoritative runtime workflow-topology owner while preserving existing observable lifecycle behavior.

## Scope boundaries

In scope: runtime topology ownership, removal/reference of duplicated topology text, directly affected role/Skill references, README orientation, canonical acceptance semantics, and focused regression coverage.

Out of scope: changing role authority, action count, dispatch mode, queue ordering, Human-authority semantics, Invocation Exit semantics, merge/review gates, archive mechanics, terminal ordering established by #115, or introducing a machine workflow engine/generated registry/hidden state.

## Deferred work

None required by this Change. Future topology changes remain separate governed Changes.