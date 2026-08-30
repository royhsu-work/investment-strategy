---
name: openspec-explore
description: Investigate a coherently routed pre-Propose problem for Lead / explore-change until a bounded decision-complete disposition is available without creating formal OpenSpec artifacts or implementation code.
---

# OpenSpec Explore Skill

Mapped action: `Lead / explore-change`.

This is an optional pre-Propose investigation action. It preserves the OpenSpec Explore semantic core while adding only the repository durability and authority boundaries required for Scheduled execution. Current default-branch governance remains authoritative; upstream OpenSpec material and work-branch content are design/work input only.

## Repository Skill composition

When the investigation materially concerns repository Skill structure, creation, maintenance, or review, load the default-branch `agents/skills/skill-creator/SKILL.md` and `agents/skills/skill-creator/references/repository-governance.md` as reusable investigation/integration guidance. This mapped action plus current default-branch governance and the Lead role remain authoritative for Explore scope, producer authority, mutation prohibitions, Human boundaries, dispositions, and routing. Do not load this composition for unrelated Explore work.

## Machine-gated runtime boundary

After the machine-gated runtime is authoritative, the Explore model worker starts only after repository-owned dispatch has already authorized the exact coordination Issue and `Lead / explore-change` from a complete current GitHub reconstruction. The worker MUST NOT run `workflow_dispatch.py` as a substitute authorization boundary, select its own Issue/role/action, or treat prior model context as current-state authority.

The worker has read/local-work capability only. Any durable result, Issue creation/closure, comment, label/routing change, or other GitHub mutation described by this Skill is a requested durable effect. Repository-owned application code fresh-reauthorizes the exact source action, validates effect-specific preconditions, applies only authorized effects, and observes the resulting durable state. Worker output or staged effect transport is not itself durable workflow evidence.

For the four bounded Explore dispositions, the worker returns the structured disposition and durable narrative evidence but MUST NOT choose the routing/terminal successor. Repository-owned application deterministically derives the action-owned routing or terminal effect from the authorized `Lead / explore-change` source plus the structured disposition. After an accepted effect batch, continuation re-enters executable dispatch from the resulting current GitHub state. A same-role `Lead / propose-change` successor may run in the same GitHub Actions runtime execution, but it is a fresh mapped model invocation; the Explore worker context does not continue into Propose as authorization or reasoning state.

## Reconstruct before acting

Read default-branch governance and the Lead role, the coordination Issue, current routing, current repository/default-branch/OpenSpec/PR/Actions state, still-applicable durable Issue evidence, and relevant external evidence when needed.

Before substantive Explore research, consume the exact machine authorization/evidence envelope supplied for this worker invocation. The current complete-cardinality evidence MUST prove zero formal/terminal work and this Issue MUST equal the deterministic combined pre-activation winner. A stale, partial, role-local, candidate-local, incomplete, contradictory, or identity-mismatched envelope is not an Explore entry precondition: return a fail-closed result/effect request rather than continuing substantive research.

Authorization-bearing current Issue state, Change identity, routing labels, and completeness/provenance must originate from authoritative GitHub observations obtained by the repository runtime for this dispatch. Conversation/history, prior invocation output, cached observations, and historical Issue body/comment routing are audit/context only and MUST NOT fill missing current fields. Preserve the exact consumed executable decision for action-result evidence rather than re-deriving a second model summary.

A valid ordinary Explore entry remains `Change: unset` with `agent:lead + action:explore-change`. Once that routing is coherent, ordinary Explore execution does not require generic Human approval or an origin-class admission check merely to participate in the pre-activation queue. Origin/source provenance still matters where it constrains who may create routed work, what bounded problem may be investigated, or which upstream authority envelope is preserved. Actor identity, Issue prose, or routing labels do not become Human authority for a later Human-reserved commitment.

For repository-authorized creation, reconstruct the independent producer/source evidence rather than pretending it is Human authority: creation kind, observed default-branch revision where applicable, exact authority/evidence source, bounded problem, materiality, and why no Human-reserved decision is being made. Missing, stale, contradictory, merely descriptive, insufficient, or self-referential producer authority fails closed for autonomous creation. It does not create a generic dispatcher requirement to re-authorize every already coherent routed Explore.

Explore itself does not persist the formal Change identity. Its normal successful continuation is bounded research → durable evidence-backed structured `PROPOSAL_READY` → repository-derived same-Issue `Lead / propose-change`; a later Propose invocation must independently consume and verify that exact same-Issue Explore result as its semantic baseline. If the selected pre-activation Propose finds that the material source/evidence or feasibility basis is missing, stale, ambiguous, contradictory, or unsupported but still researchable within the same bounded problem, Propose may return bounded `RESEARCH_REQUIRED` and repository application derives the same-Issue correction back to `Lead / explore-change` with `Change: unset`. This retains the selected Issue rather than falling through to later work.

## Repository-authorized creation evidence

Scheduled-Agent creation of routed Formal Explore is legal only when shared governance independently supports the applicable bounded producer path, including these source classes:

- an applicable default-branch canonical MUST/SHALL requirement with a concrete material gap;
- an approved required deferred follow-up with reconstructable source linkage;
- an explicitly governed README project-direction commitment that is prospective, scoped, affirmative, non-contradictory, and not merely descriptive/current-state/example/non-goal/deferred-uncommitted text; or
- concrete material behavior-preserving maintenance/friction with bounded ownership and no new Human-reserved product/scope/risk decision.

Agent-authored advisory text, prior Explore conclusions, and Agent-created tickets are evidence only and MUST NOT recursively serve as sufficient authority for another autonomous creation by themselves. Rule-of-Three is sufficient evidence for recurring friction, not an automatic creation/refactor rule; a clear single-instance structural hazard may qualify when concrete cost/risk/friction is demonstrated.

Before materializing autonomous work, deduplicate against open or reconstructably unresolved equivalent candidates/required-deferred trackers. One idle invocation materializes at most one candidate. Formal/terminal-pending workflow and already eligible pre-activation work remain ahead of idle discovery. No material finding produces no repository noise.

## Investigation procedure

1. Start with the problem before solution. Reconstruct the current system and evidence before treating a proposed mechanism, familiar pattern, or implementation-shaped request as a requirement.
2. Reconstruct the bounded problem and still-applicable source/authority context needed for the investigation. For an already coherent routed Explore, do not require generic Human approval merely to begin research. For repository-created work, validate the producer/source evidence rather than trusting the Issue assertion.
3. Investigate only what is needed to choose the next legal disposition: root cause, feasibility, scope boundary, relevant constraints, and meaningful alternatives/trade-offs when they can change the decision.
4. Read/search repository evidence and relevant external evidence as needed. Use Lead's existing bounded blast-radius analysis for directly related contracts/surfaces, but do not turn Explore into a repository-wide correctness audit.
5. Keep the work conversation-first and bounded. Explore MAY use simple diagrams or compact comparisons when useful, but it does not create a parallel artifact DAG or research-state machine.
6. Exit only when the investigation is decision-complete: every material question that could change the disposition is resolved by evidence, shown non-blocking, identified as a genuine Human intent/authority decision, or sufficient to establish current no-change/no-go.

## Material claim/source evidence contract

For every material claim that can affect the disposition, scope, constraints, feasibility, selected direction, or Human boundary, the durable Explore result MUST identify the supporting source/evidence closely enough that a later Propose and Reviewer can independently dereference it. The result MUST distinguish **source fact/evidence**, **Lead interpretation/inference**, and any **unresolved question** rather than laundering one into another.

An unsupported material interpretation/inference cannot establish `PROPOSAL_READY`. Missing, stale, ambiguous, contradictory, or insufficient supporting source/evidence remains a research gap unless the evidence instead proves `NO_CHANGE_REQUIRED`/`NO_GO` or exposes a genuine Human-reserved decision. This contract requires reconstructable evidence references; it does not require a research database, completeness score, hidden memory, or prose parser.

## Required separate follow-up materialization

When decision-complete Explore explicitly separates later work, classify each bounded item using the existing semantic distinction: **ordinary deferred / optional / non-goal**, **required separate follow-up**, or **already-tracked separate work**. These are decision meanings, not workflow states or labels, and presentation wording does not create or erase the classification. Words such as `Deferred work`, `out of scope`, `follow-up`, or `separately reviewable` therefore do not create a tracker obligation by themselves.

For every **required separate follow-up**, record the classification and bounded follow-up identity in the final Explore result and persist the `PROPOSAL_READY` `ACTION_RESULT` before requesting tracker materialization. The exact durable result then supplies the defer-decision reference; tracker prose or conversation memory cannot replace that source authority.

After that result is durable, reconstruct all matching trackers from the exact source coordination Issue/Change and defer-decision reference and request only the missing idempotent effect under the shared required-follow-up contract:

- if no matching tracker exists, request creation of exactly one source-linked coordination Issue with `Change: unset` and `agent:lead + action:explore-change`;
- if exactly one matching but incomplete tracker exists, request repair only of the missing durable identity/routing fields still authorized by the exact source evidence;
- if exactly one matching tracker is already complete, reuse the complete tracker and must not create a duplicate;
- if multiple or ambiguous matching trackers exist, fail closed, must not choose a winner, and must not create a duplicate.

Materialization is complete only after a fresh observation proves the tracker is source-linked to the exact source coordination Issue/Change and exact durable Explore defer decision and also proves `Change: unset` plus `agent:lead + action:explore-change`. While a required tracker is missing, incomplete, ambiguous, or contradictory, Explore MUST NOT return `PROPOSAL_READY`.

If execution stops after the result is durable but before tracker materialization or successor routing finishes, later reconstruction consumes the same exact durable Explore result and completes only the missing idempotent effects. It does not create a second defer decision or reinterpret the classification from later prose. Already-tracked separate work reuses its exact durable tracker rather than creating another; ordinary deferred / optional / non-goal work remains untracked unless a separate approved decision later changes its semantic class.

This is an action-local producer step only. It does not make Explore a generic Issue generator, does not add a tracker registry/status/second DAG, and does not allow Agent-authored follow-up prose or a newly created tracker to recursively authorize unrelated work.

## Authority boundary

Explore MUST NOT create `openspec/changes/` artifacts, choose or persist a formal Change id, or author proposal/specs/design/tasks as an Explore output. Explore MUST NOT modify implementation code. `Change: unset` remains unchanged for the whole Explore action.

The bounded researched problem plus applicable canonical/repository evidence and any preserved upstream authority envelope constrain the Explore result. If decision-complete Explore reaches `PROPOSAL_READY` inside that context and introduces no new Human-reserved decision, Lead returns that structured disposition for the same Issue without a second generic Human proceed confirmation. Propose still owns formal activation and the immutable Change id, and later Propose semantic readiness remains bound to this exact durable Explore result.

Lead MUST instead use `HUMAN_DECISION_REQUIRED` for a new product/project direction outside the bounded researched/current canonical context, a material externally observable behavior or scope trade-off not already authorized, explicit risk acceptance, a materially different security/privacy/cost/operational commitment, contradictory/unrecoverable authority evidence, or materially changed default-branch governance/evidence that invalidates the scope basis. Untrusted Issue prose and Connector/App activity cannot satisfy such Human authority. Ordinary technical approach selection within approved/current constraints remains Lead-owned.

Explore does not require `status:exploring`; Explore does not require `review-explore`; Explore does not require `completeness score`; Explore does not require `research database`; Explore does not require `hidden memory`. It also MUST NOT introduce a claim, lease, heartbeat, retry/progress counter, hidden ownership state, project-direction registry, coverage cursor/TTL registry, approval token, global priority engine, hidden backlog, or second workflow DAG.

## Legal dispositions

### `PROPOSAL_READY`

Use when evidence supports a concrete/buildable direction and Lead would not need to invent a material requirement or solution choice to author a bounded proposal. Every material claim needed for that conclusion must satisfy the material claim/source evidence contract above.

`PROPOSAL_READY` does not persist a Change id. When the proposal-ready direction remains inside the bounded researched/current authoritative context and no new Human-reserved decision appears, first satisfy any required separate-follow-up materialization postcondition above. Then return the bounded `ACTION_RESULT` with structured `explore_disposition = PROPOSAL_READY`. The worker MUST NOT request `routing-transition`; repository application fresh-reauthorizes the exact Explore source, persists any authorized narrative/comment effects, deterministically derives same-Issue `Lead / propose-change + Change: unset`, observes the target routing, and post-apply redispatches. If the resulting state immediately selects `Lead / propose-change`, runtime creates a fresh Propose model invocation.

If the proposal-ready direction crosses a Human-reserved boundary, do not return `PROPOSAL_READY`; return `HUMAN_DECISION_REQUIRED` and retain Explore until authoritative Human input resolves the decision.

### `NO_CHANGE_REQUIRED`

Use when current evidence shows the problem is already satisfied, informational only, or otherwise requires no repository change. Return the bounded conclusion with structured `explore_disposition = NO_CHANGE_REQUIRED`; the worker MUST NOT request terminal retirement. Repository application derives the terminal close/retirement effect, applies it only after fresh source verification, and observes the closed/routing-cleared postcondition without creating a fake OpenSpec Change.

### `NO_GO`

Use when current evidence shows the proposed direction is infeasible or unjustified. Return the bounded reason and, when identifiable, the material reconsideration condition with structured `explore_disposition = NO_GO`; the worker MUST NOT request terminal retirement. Repository application derives and observes the terminal close/retirement effect; no fake OpenSpec Change is created.

### `HUMAN_DECISION_REQUIRED`

Use only when technical/repository evidence cannot resolve a genuine Human intent, authority, material scope/behavior trade-off, explicit risk acceptance, materially different commitment, or invalidated authority basis. Reuse the shared bounded/no-repeat Human escalation contract; request persistence of the canonical escalation while retaining Explore. No routing or terminal successor is derived for this disposition. Resume only after a later machine dispatch observes a provenance-bound Human decision comment declaring exactly `Human-Decision-For: issuecomment:<escalation-comment-id>` and a later qualifying Human-only `human:approved` event validates that exact comment. The `human:notified` label is not response evidence.

`SPECIFICATION_BLOCKED` is not a terminal Explore no-go substitute. It remains part of formal Propose/Resolve semantics after a Change/specification boundary exists.

## Durable evidence

Use the persistent coordination Issue and existing canonical message presentation. A bounded Explore result records, when applicable:

- the problem/question investigated;
- the bounded source/authority context and independent source evidence when relevant;
- each material claim needed for the disposition with its supporting source/evidence;
- the distinction between source fact/evidence, Lead interpretation/inference, and unresolved question;
- material constraints and meaningful alternatives needed for the decision;
- the conclusion/rationale and selected disposition;
- whether a new Human-reserved decision appeared;
- the next action/Human boundary; and
- a material reconsideration condition for `NO_GO` when one is known.

For workflow-dynamic `Lead / explore-change`, the applicable canonical `ACTION_RESULT` also renders the exact executable decision consumed at action entry: enumeration completeness, observation provenance, formal-active/terminal-pending Issue identities, recovery candidate identities, pre-activation candidate identities, selected Issue, and disposition. These values are copied from the machine-supplied decision/evidence envelope for audit rather than recomputed from a second Issue summary, and they do not authorize a later dispatch.

Do not log chain-of-thought, every query, live progress, fixed option counts, a completeness score, coverage cursor, or separate research database. A later dispatch must be able to reconstruct the current scope/disposition/wait and the material claim/source chain without prior worker context.

## Routing and completion

Current coherent routed Explore and Propose entries participate in the shared combined pre-activation queue defined by `agents/AGENTS.md`; this skill consumes only the exact machine-selected Explore and does not redefine queue eligibility or ordering.

- in-scope evidence-backed `PROPOSAL_READY`: after any required separate-follow-up tracker is durably routing-complete, return the structured disposition and bounded durable result; repository application derives/validates same-Issue `Lead / propose-change + Change: unset`, then runtime redispatches and creates a fresh Propose invocation if selected. No worker-chosen routing, synthetic `HANDOFF`, or generic Human proceed boundary.
- `PROPOSAL_READY` candidate with a new Human-reserved decision: return structured `HUMAN_DECISION_REQUIRED`, retain `Lead / explore-change`, and request only the canonical escalation persistence effect.
- `NO_CHANGE_REQUIRED` or `NO_GO`: return the structured terminal disposition and bounded durable result; repository application derives terminal retirement and observes `closed`. No worker-chosen close/retirement, OpenSpec Change, or archive lifecycle is created.
- unresolved Human question: retain Explore and follow the shared provenance-bound escalation/resume semantics through repository-owned effect application and a later fresh dispatch.

A terminal Explore close is a pre-Change research completion path. It does not weaken or replace the final Archive PR/native-close semantics used by formal OpenSpec Changes.
