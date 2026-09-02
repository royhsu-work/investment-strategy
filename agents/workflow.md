# Scheduled-Agent Workflow Topology

This file is the single authoritative repository owner of end-to-end Scheduled-Agent runtime workflow topology and lifecycle relationships.

`agents/AGENTS.md` remains authoritative for shared execution invariants such as dispatch/cardinality, durable reconstruction, Human authority, evidence consumption, work-conserving execution, Invocation Exit, concurrency safety, queue/admission rules, and validation evidence. `agents/roles/*.md` own role authority. Mapped `agents/skills/*/SKILL.md` own action-local executable procedure. Canonical OpenSpec owns approved capability requirements and acceptance semantics. README is Human/contributor orientation.

Local role/Skill references may name their immediate source or target action when needed to execute their procedure, but they do not redefine this global topology.

## Normal formal lifecycle

The persistent coordination Issue remains open throughout the formal lifecycle. `Lead / propose-change` persists the immutable non-`unset` Change identity and is the formal activation boundary.

| Current action | Governing result/condition | Next action |
| --- | --- | --- |
| `Lead / propose-change` | before the first independent `review-openspec` PASS, formalization proves a material causal Explore source/evidence/feasibility premise invalid but still researchable within the same bounded problem and no new Human-reserved decision is required | `Lead / explore-change` |
| `Lead / propose-change` | OpenSpec artifacts ready for independent semantic review | `Reviewer / review-openspec` |
| `Reviewer / review-openspec` | PASS | `Executor / implement-change` |
| `Reviewer / review-openspec` | specification finding/question | `Lead / resolve-question` |
| `Lead / resolve-question` | material semantic correction ready for independent semantic review | `Reviewer / review-openspec` |
| `Lead / resolve-question` | clarification resolved with no material semantic change and implementation remains the legal consumer | `Executor / implement-change` |
| `Executor / implement-change` | implementation READY | `Reviewer / review-implementation` |
| `Executor / implement-change` | specification meaning must change or be invented | `Lead / resolve-question` |
| `Reviewer / review-implementation` | implementation finding within approved meaning | `Executor / implement-change` |
| `Reviewer / review-implementation` | PASS for exact implementation head | `Executor / merge-pr` |
| `Executor / merge-pr` | implementation or implementation-correction PR exact accepted presentation is rejected with a lifecycle-contract violation that cannot be repaired within merge-pr authority | `Lead / resolve-question` |
| `Executor / merge-pr` | implementation PR merged | `Lead / finalize-change` |
| `Lead / finalize-change` | `MORE_IMPLEMENTATION_REQUIRED`: approved implementation still incomplete | `Executor / implement-change` |
| `Lead / finalize-change` | validated final Archive PR ready | `Reviewer / review-archive` |
| `Reviewer / review-archive` | archive/preparation finding | `Lead / finalize-change` |
| `Reviewer / review-archive` | PASS for exact Archive head | `Executor / merge-pr` |
| `Executor / merge-pr` | final Archive PR exact accepted presentation, linkage, or reviewed lifecycle preparation is rejected with a lifecycle-contract violation requiring Lead correction | `Lead / finalize-change` |
| `Executor / merge-pr` | final Archive PR merged, coordination Issue still open | `Lead / finalize-archive` |
| `Lead / finalize-archive` | terminal conditions satisfied | durable `LIFECYCLE_COMPLETE`, then coordination Issue close and closed re-observation |

The two `Executor / merge-pr` positions are distinguished by current durable PR/lifecycle evidence, not by a separate action name or hidden phase state.

## Explore boundaries

`Lead / explore-change` has two bounded entry modes:

1. optional pre-Propose investigation with `Change: unset`; and
2. formal pre-review correction for the same active coordination Issue when a non-`unset` immutable Change already exists, no independent `Reviewer / review-openspec` PASS has yet accepted that Change, and Propose has established that its causal Explore source/evidence/feasibility premise is materially invalid but still researchable within the same bounded problem without a new Human-reserved decision.

Formal pre-review correction preserves the existing Change identity, coordination Issue, PR/artifact history, durable evidence, and WIP. It does not deactivate/requeue the Change, create a second workflow, or restore a pre-Change queue position.

| Explore disposition | Topology result |
| --- | --- |
| `PROPOSAL_READY` within pre-Change Explore | route the same Issue to `Lead / propose-change` with `Change: unset`; same-role continuation may proceed immediately when its own preconditions hold |
| `PROPOSAL_READY` within formal pre-review correction | route the same Issue to `Lead / propose-change` while preserving the same non-`unset` Change identity and existing PR/artifact history |
| `HUMAN_DECISION_REQUIRED` | retain `Lead / explore-change` until the exact provenance-bound Human decision is legally consumable |
| `NO_CHANGE_REQUIRED` | legal only for pre-Change Explore: persist the bounded result, close the research Issue, and re-observe closed; no formal Change/archive lifecycle is created |
| `NO_GO` | legal only for pre-Change Explore: persist the bounded result, close the research Issue, and re-observe closed; no formal Change/archive lifecycle is created |

A formal pre-review correction MUST NOT use the pre-Change `NO_CHANGE_REQUIRED`/`NO_GO` terminal-close path to retire an already active non-`unset` Change. If its research exposes a Human-reserved decision or an inability to preserve the approved Change outcome, it uses the governed Human boundary and keeps the formal workflow active.

### Propose research correction

Before formal activation, a selected `Lead / propose-change` with `Change: unset` may discover that its exact durable Explore baseline has a material source/evidence or feasibility gap. When that gap is still researchable within the same bounded problem and no new Human-reserved decision is required, the action emits bounded `RESEARCH_REQUIRED`; repository-owned application derives only the same-Issue `Lead / propose-change` → `Lead / explore-change` correction while preserving `Change: unset` and the Issue's original queue identity. This correction retains the selected Issue; it is not dispatcher fallback to a later candidate and does not authorize the worker to choose an arbitrary successor.

After formal activation but before the first independent `Reviewer / review-openspec` PASS for the Change, the same bounded `RESEARCH_REQUIRED` disposition is legal when formalization proves its causal Explore source/evidence/feasibility premise materially invalid but still researchable within the same bounded problem and no new Human-reserved decision is required. Repository-owned application derives the same-Issue `Lead / propose-change` → `Lead / explore-change` correction while preserving the immutable non-`unset` Change identity, existing PR/artifacts/history, and formal WIP.

If the missing basis instead requires a new Human-reserved requirement, scope/risk acceptance, or architecture decision, use the governed Human boundary. After the first independent `Reviewer / review-openspec` PASS has accepted the Change, backward Explore correction is no longer legal; material formal semantic correction uses `Lead / resolve-question` and returns through independent review.

## Correction loops

Correction loops preserve the same persistent coordination Issue and immutable Change identity once formal activation has occurred.

- Pre-first-review formalization feasibility correction: `Lead / propose-change → Lead / explore-change → Lead / propose-change` while preserving the same non-`unset` Change, only before the first independent `Reviewer / review-openspec` PASS.
- OpenSpec semantic finding: `Reviewer / review-openspec → Lead / resolve-question → Reviewer / review-openspec` when semantic artifacts materially change.
- Implementation specification blocker: `Executor / implement-change → Lead / resolve-question → Reviewer / review-openspec → Executor / implement-change` when a material semantic correction is required.
- Implementation finding: `Reviewer / review-implementation → Executor / implement-change → Reviewer / review-implementation` on a new exact implementation head.
- Implementation merge-acceptance lifecycle-contract blocker: `Executor / merge-pr → Lead / resolve-question → Executor / implement-change → Reviewer / review-implementation → Executor / merge-pr` when the accepted implementation presentation cannot be merged and correction requires authority outside merge-pr while approved semantic meaning remains unchanged; a material semantic correction returns through `Reviewer / review-openspec` instead.
- Incomplete post-merge implementation: `Executor / merge-pr → Lead / finalize-change → Executor / implement-change` when approved work remains.
- Archive finding: `Reviewer / review-archive → Lead / finalize-change → Reviewer / review-archive` on the corrected exact Archive target.
- Archive merge-acceptance lifecycle-contract blocker: `Executor / merge-pr → Lead / finalize-change → Reviewer / review-archive → Executor / merge-pr` when the final Archive presentation, linkage, or reviewed lifecycle preparation requires Lead correction and renewed exact-head archive review.

Reviewer acceptance never transfers merge authority. Executor merge never transfers Lead lifecycle authority. Every action consumes its own current preconditions and evidence under `agents/AGENTS.md`.

## Same-role and cross-role boundaries

A transition whose target role differs from the fixed invocation role is a cross-role handoff. The source action persists its result, legally mutates routing, observes the target tuple, persists canonical `HANDOFF`, and the invocation ends.

A transition whose target role is the same fixed invocation role is a same-role continuation. The source result and routing mutation are persisted, the target tuple is observed, the target action's mapped default-branch Skill is loaded, its preconditions are reconstructed, and immediately actionable work continues without a synthetic `HANDOFF`.

These relationships do not change shared work-conserving/Invocation Exit semantics owned by `agents/AGENTS.md`.

## Formal terminal completion

The final Archive PR uses non-closing coordination linkage. Archive merge intentionally leaves the coordination Issue open and routes to `Lead / finalize-archive`.

The formal terminal order is exactly:

```text
final Archive PR exact-head review PASS
→ Executor merges exact accepted Archive revision
→ coordination Issue remains open
→ route Lead / finalize-archive
→ Lead reconstructs reviewed/merged Archive and all terminal obligations
→ persist valid LIFECYCLE_COMPLETE
→ close coordination Issue
→ re-observe the same Issue as closed
→ terminal history
```

There is no normal closed terminal-pending workflow. Interruption consumes already durable writes:

- Archive merged but `LIFECYCLE_COMPLETE` absent: open `Lead / finalize-archive` remains the formal workflow.
- `LIFECYCLE_COMPLETE` durable but close missing: Lead performs only the missing close and re-observes closed.
- close completed but later journal/re-observation work was interrupted: reconstruction consumes the existing completion result and current closed state; it does not replay the close.
- valid `LIFECYCLE_COMPLETE` plus observed closed Issue: terminal history excluded from formal WIP/cardinality.

A closed formal-looking Issue without valid `LIFECYCLE_COMPLETE` is not terminal success; only the bounded premature-close recovery contract in `agents/AGENTS.md` may recover it.

## Ownership discipline

Future workflow-topology changes modify this file as the runtime topology owner. Other surfaces change only when their independently owned requirement, shared invariant, role authority, action-local procedure, or Human-facing orientation genuinely changes. Do not maintain a second normative global DAG in `agents/AGENTS.md`, README, roles, or Skills, and do not introduce a generated registry, machine workflow engine, hidden lifecycle state, or synchronization-by-convention mechanism merely to mirror this document.
