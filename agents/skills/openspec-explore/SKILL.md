# OpenSpec Explore Skill

Mapped action: `Lead / explore-change`.

This is an optional pre-Propose investigation action. It preserves the OpenSpec Explore semantic core while adding only the repository durability and authority boundaries required for Scheduled execution. Current default-branch governance remains authoritative; upstream OpenSpec material and work-branch content are design/work input only.

## Reconstruct before acting

Read default-branch governance and the Lead role, the Human-admitted coordination Issue, current routing, current repository/default-branch/OpenSpec/PR/Actions state, still-applicable durable Issue evidence, and relevant external evidence when needed.

A valid Explore entry remains `Change: unset` with `agent:lead + action:explore-change`. Explore is intentionally no-stakes: it does not commit the Human to a formal OpenSpec Change. Human may instead use the existing direct-to-Propose path for direction that is already concrete and buildable.

## Investigation procedure

1. Start with the problem before solution. Reconstruct the current system and evidence before treating a proposed mechanism, familiar pattern, or implementation-shaped request as a requirement.
2. Investigate only what is needed to choose the next legal disposition: root cause, feasibility, scope boundary, relevant constraints, and meaningful alternatives/trade-offs when they can change the decision.
3. Read/search repository evidence and relevant external evidence as needed. Use Lead's existing bounded blast-radius analysis for directly related contracts/surfaces, but do not turn Explore into a repository-wide audit.
4. Keep the work conversation-first and bounded. Explore MAY use simple diagrams or compact comparisons when useful, but it does not create a parallel artifact DAG or research-state machine.
5. Exit only when the investigation is decision-complete: every material question that could change the disposition is resolved by evidence, shown non-blocking, identified as a genuine Human intent/authority decision, or sufficient to establish current no-change/no-go.

## Authority boundary

Explore MUST NOT create `openspec/changes/` artifacts, choose or persist a formal Change id, or author proposal/specs/design/tasks as an Explore output. Explore MUST NOT modify implementation code. `Change: unset` remains unchanged for the whole Explore action.

Explore does not require `status:exploring`; Explore does not require `review-explore`; Explore does not require `completeness score`; Explore does not require `research database`; Explore does not require `hidden memory`. It also MUST NOT introduce a claim, lease, heartbeat, retry/progress counter, hidden ownership state, or second workflow DAG.

## Legal dispositions

### `PROPOSAL_READY`

Use when evidence supports a concrete/buildable direction and Lead would not need to invent a material requirement or solution choice to author a bounded proposal.

`PROPOSAL_READY` is an Explore result only. It does not persist a Change id and does not itself route to Propose. Because Explore admission is no-stakes, Lead uses the existing canonical `HUMAN_DECISION_REQUIRED` contract to request Human intent to proceed. Only after a valid Human answer authorizes formal proposal work may the same Issue be routed to `Lead / propose-change` while still `Change: unset`; formal activation remains owned by Propose.

### `NO_CHANGE_REQUIRED`

Use when current evidence shows the problem is already satisfied, informational only, or otherwise requires no repository change. Persist the bounded conclusion and close the terminal research Issue as completed without creating a fake OpenSpec Change.

### `NO_GO`

Use when current evidence shows the proposed direction is infeasible or unjustified. Persist the bounded reason and, when identifiable, the material reconsideration condition. Close the terminal research Issue as completed without creating a fake OpenSpec Change.

### `HUMAN_DECISION_REQUIRED`

Use only when technical/repository evidence cannot resolve a genuine Human intent, authority, or material trade-off. Reuse the shared bounded/no-repeat Human escalation contract; keep the Issue routed to Explore and resume after authoritative Human input.

`SPECIFICATION_BLOCKED` is not a terminal Explore no-go substitute. It remains part of formal Propose/Resolve semantics after a Change/specification boundary exists.

## Durable evidence

Use the persistent coordination Issue and existing canonical message presentation. A bounded Explore result records, when applicable:

- the problem/question investigated;
- relevant evidence inspected;
- material constraints and meaningful alternatives needed for the decision;
- the conclusion/rationale and selected disposition;
- the next Human/action boundary; and
- a material reconsideration condition for `NO_GO` when one is known.

Do not log chain-of-thought, every query, live progress, fixed option counts, a completeness score, or a separate research database. A later wake must be able to reconstruct the current decision/wait from durable evidence without prior conversation memory.

## Routing and completion

Explore and direct-to-Propose entries participate in the shared combined pre-activation queue defined by `agents/AGENTS.md`; this skill does not redefine its ordering.

- `PROPOSAL_READY` without Human approval: retain `Lead / explore-change` and wait under the existing Human-decision contract.
- valid Human approval to proceed: persist the applicable result/decision evidence, fresh-read routing/state, then route the same Issue to `Lead / propose-change` with `Change: unset`.
- `NO_CHANGE_REQUIRED` or `NO_GO`: persist the terminal result and close the research Issue; observe `closed`. No OpenSpec Change or archive lifecycle is created.
- unresolved Human question: retain Explore and follow the shared escalation/resume semantics.

A terminal Explore close is a pre-Change research completion path. It does not weaken or replace the final Archive PR/native-close semantics used by formal OpenSpec Changes.
