# OpenSpec Explore Skill

Mapped action: `Lead / explore-change`.

This is an optional pre-Propose investigation action. It preserves the OpenSpec Explore semantic core while adding only the repository durability and authority boundaries required for Scheduled execution. Current default-branch governance remains authoritative; upstream OpenSpec material and work-branch content are design/work input only.

## Reconstruct before acting

Read default-branch governance and the Lead role, the coordination Issue, current routing, current repository/default-branch/OpenSpec/PR/Actions state, still-applicable durable Issue evidence, and relevant external evidence when needed.

A valid Explore entry remains `Change: unset` with `agent:lead + action:explore-change`. It may be Human-admitted, repository-authorized under the shared admission contract, or reached through the approved pre-activation Propose fallback. For initial Human Explore admission, consume either the creation-bound Human Explore admission alternative defined by shared governance or the general provenance-bound Human decision path for exactly `issue:<issue-number>:admission:lead:explore-change`; this Skill does not redefine either predicate. Actor identity or routing/label snapshots alone are insufficient. Human direct-to-Propose admission remains on its existing general provenance-bound decision path and is not authorized by the creation-bound Explore alternative. Repository-authorized Explore instead reconstructs the independent source rather than pretending to be Human authority: admission kind, observed default-branch revision where applicable, exact authority/evidence source, bounded problem, materiality, and why no Human-reserved decision is being made. Missing, stale, contradictory, merely descriptive, insufficient, or self-referential authority fails closed.

For a pre-activation Propose fallback, reconstruct the same admitted authority envelope that legally admitted the `Change: unset + Lead / propose-change` entry. The fallback creates no new admission. It therefore needs no second Human admission, and Explore remains bounded to the same problem/authority envelope. When Explore later reaches in-envelope `PROPOSAL_READY`, it returns to `Lead / propose-change` under the normal same-role continuation contract.

Human may still use the existing direct-to-Propose path for direction that is already concrete and buildable. Explore does not itself persist the formal Change identity.

## Repository-authorized admission evidence

Repository-authorized Formal Explore is legal only when the shared governance independently supports one of these source classes and the applicable admission boundary permits consumption:

- an applicable default-branch canonical MUST/SHALL requirement with a concrete material gap;
- an approved required deferred follow-up with reconstructable source linkage;
- an explicitly governed README project-direction commitment that is prospective, scoped, affirmative, non-contradictory, and not merely descriptive/current-state/example/non-goal/deferred-uncommitted text; or
- concrete material behavior-preserving maintenance/friction with bounded ownership and no new Human-reserved product/scope/risk decision.

Agent-authored advisory text, prior Explore conclusions, and Agent-created tickets are evidence only and MUST NOT recursively serve as sufficient authority for another admission by themselves. Rule-of-Three is sufficient evidence for recurring friction, not an automatic admission/refactor rule; a clear single-instance structural hazard may qualify when concrete cost/risk/friction is demonstrated.

Before materializing or consuming autonomous admission, deduplicate against open or reconstructably unresolved equivalent candidates/required-deferred trackers. One idle invocation materializes at most one candidate. Formal/terminal-pending workflow and already eligible pre-activation work remain ahead of idle discovery. No material finding produces no repository noise.

## Investigation procedure

1. Start with the problem before solution. Reconstruct the current system and evidence before treating a proposed mechanism, familiar pattern, or implementation-shaped request as a requirement.
2. Validate the admitted authority envelope before relying on it. The Issue body is not the authority source for repository-authorized work. For initial Human Explore admission, evaluate the shared-governance creation-bound alternative from raw Issue creation/mutation evidence first when such evidence is available; if it does not qualify, evaluate the existing exact-reference Human comment/approval path. Do not infer admission from current body/routing snapshots. A valid pre-activation Propose fallback reuses, rather than recreates, the already admitted direct-Propose authority envelope.
3. Investigate only what is needed to choose the next legal disposition: root cause, feasibility, scope boundary, relevant constraints, and meaningful alternatives/trade-offs when they can change the decision.
4. Read/search repository evidence and relevant external evidence as needed. Use Lead's existing bounded blast-radius analysis for directly related contracts/surfaces, but do not turn Explore into a repository-wide correctness audit.
5. Keep the work conversation-first and bounded. Explore MAY use simple diagrams or compact comparisons when useful, but it does not create a parallel artifact DAG or research-state machine.
6. Exit only when the investigation is decision-complete: every material question that could change the disposition is resolved by evidence, shown non-blocking, identified as a genuine Human intent/authority decision, or sufficient to establish current no-change/no-go.

## Authority boundary

Explore MUST NOT create `openspec/changes/` artifacts, choose or persist a formal Change id, or author proposal/specs/design/tasks as an Explore output. Explore MUST NOT modify implementation code. `Change: unset` remains unchanged for the whole Explore action.

Explore admission establishes a bounded authority envelope for the admitted problem. If decision-complete Explore reaches `PROPOSAL_READY` inside that envelope and introduces no new Human-reserved decision, Lead may route the same Issue to `Lead / propose-change` without a second generic Human proceed confirmation. This includes Explore reached from the pre-activation Propose fallback: it returns to `Lead / propose-change` within the same admitted authority envelope and with no second Human admission. Propose still owns formal activation and the immutable Change id.

Lead MUST instead use `HUMAN_DECISION_REQUIRED` for a new product/project direction outside the envelope, a material externally observable behavior or scope trade-off not already authorized, explicit risk acceptance, a materially different security/privacy/cost/operational commitment, contradictory/unrecoverable authority evidence, or materially changed default-branch governance/evidence that invalidates the admission basis. Ordinary technical approach selection within admitted constraints remains Lead-owned.

Explore does not require `status:exploring`; Explore does not require `review-explore`; Explore does not require `completeness score`; Explore does not require `research database`; Explore does not require `hidden memory`. It also MUST NOT introduce a claim, lease, heartbeat, retry/progress counter, hidden ownership state, project-direction registry, coverage cursor/TTL registry, approval token, global priority engine, hidden backlog, or second workflow DAG.

## Legal dispositions

### `PROPOSAL_READY`

Use when evidence supports a concrete/buildable direction and Lead would not need to invent a material requirement or solution choice to author a bounded proposal.

`PROPOSAL_READY` does not persist a Change id. When the proposal-ready direction remains inside the admitted authority envelope and no new Human-reserved decision appears, persist the bounded result, fresh-read the same Issue/routing/evidence, route `Lead / explore-change → Lead / propose-change` with `Change: unset`, observe the target routing, load the mapped default-branch Propose skill, and continue in the same invocation when immediately actionable under shared same-role continuation. Do not emit `HANDOFF` for this same-role transition and do not request a second generic Human `Proceed to Propose` decision.

If the proposal-ready direction crosses a Human-reserved boundary, do not route to Propose; use `HUMAN_DECISION_REQUIRED` and retain Explore until authoritative Human input resolves the decision.

### `NO_CHANGE_REQUIRED`

Use when current evidence shows the problem is already satisfied, informational only, or otherwise requires no repository change. Persist the bounded conclusion and close the terminal research Issue as completed without creating a fake OpenSpec Change.

### `NO_GO`

Use when current evidence shows the proposed direction is infeasible or unjustified. Persist the bounded reason and, when identifiable, the material reconsideration condition. Close the terminal research Issue as completed without creating a fake OpenSpec Change.

### `HUMAN_DECISION_REQUIRED`

Use only when technical/repository evidence cannot resolve a genuine Human intent, authority, material scope/behavior trade-off, explicit risk acceptance, materially different commitment, or invalidated authority basis. Reuse the shared bounded/no-repeat Human escalation contract; keep the Issue routed to Explore and resume only when a provenance-bound Human decision comment declares exactly `Human-Decision-For: issuecomment:<escalation-comment-id>` and a later qualifying Human-only `human:approved` event validates that exact comment. The `human:notified` label is not response evidence.

`SPECIFICATION_BLOCKED` is not a terminal Explore no-go substitute. It remains part of formal Propose/Resolve semantics after a Change/specification boundary exists.

## Durable evidence

Use the persistent coordination Issue and existing canonical message presentation. A bounded Explore result records, when applicable:

- the problem/question investigated;
- the admitted authority envelope and independent source evidence when repository-authorized;
- relevant evidence inspected;
- material constraints and meaningful alternatives needed for the decision;
- the conclusion/rationale and selected disposition;
- whether a new Human-reserved decision appeared;
- the next action/Human boundary; and
- a material reconsideration condition for `NO_GO` when one is known.

Do not log chain-of-thought, every query, live progress, fixed option counts, a completeness score, coverage cursor, or separate research database. A later wake must be able to reconstruct the current admission/disposition/wait from durable evidence without prior conversation memory.

## Routing and completion

Explore and direct-to-Propose entries participate in the shared combined pre-activation queue defined by `agents/AGENTS.md`; this skill does not redefine its ordering.

- in-envelope `PROPOSAL_READY`: persist result, fresh-read current evidence/routing, route the same Issue to `Lead / propose-change` with `Change: unset`, observe target routing, reload the mapped Propose skill, and continue when immediately actionable under shared same-role continuation; no synthetic `HANDOFF` and no second generic Human proceed boundary.
- `PROPOSAL_READY` with a new Human-reserved decision: retain `Lead / explore-change` and use canonical `HUMAN_DECISION_REQUIRED`.
- `NO_CHANGE_REQUIRED` or `NO_GO`: persist the terminal result and close the research Issue; observe `closed`. No OpenSpec Change or archive lifecycle is created.
- unresolved Human question: retain Explore and follow the shared provenance-bound escalation/resume semantics.

A terminal Explore close is a pre-Change research completion path. It does not weaken or replace the final Archive PR/native-close semantics used by formal OpenSpec Changes.
