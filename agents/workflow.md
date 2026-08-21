# Scheduled-Agent Workflow Topology

This file is the single authoritative repository owner of end-to-end Scheduled-Agent runtime workflow topology and lifecycle relationships.

`agents/AGENTS.md` remains authoritative for shared execution invariants such as dispatch/cardinality, durable reconstruction, Human authority, evidence consumption, work-conserving execution, Invocation Exit, concurrency safety, queue/admission rules, and validation evidence. `agents/roles/*.md` own role authority. Mapped `agents/skills/*/SKILL.md` own action-local executable procedure. Canonical OpenSpec owns approved capability requirements and acceptance semantics. README is Human/contributor orientation.

Local role/Skill references may name their immediate source or target action when needed to execute their procedure, but they do not redefine this global topology.

## Normal formal lifecycle

The persistent coordination Issue remains open throughout the formal lifecycle. `Lead / propose-change` persists the immutable non-`unset` Change identity and is the formal activation boundary.

| Current action | Governing result/condition | Next action |
| --- | --- | --- |
| `Lead / propose-change` | OpenSpec artifacts ready for independent semantic review | `Reviewer / review-openspec` |
| `Reviewer / review-openspec` | PASS | `Executor / implement-change` |
| `Reviewer / review-openspec` | specification finding/question | `Lead / resolve-question` |
| `Lead / resolve-question` | material semantic correction ready for independent semantic review | `Reviewer / review-openspec` |
| `Lead / resolve-question` | clarification resolved with no material semantic change and implementation remains the legal consumer | `Executor / implement-change` |
| `Executor / implement-change` | implementation READY | `Reviewer / review-implementation` |
| `Executor / implement-change` | specification meaning must change or be invented | `Lead / resolve-question` |
| `Reviewer / review-implementation` | implementation finding within approved meaning | `Executor / implement-change` |
| `Reviewer / review-implementation` | PASS for exact implementation head | `Executor / merge-pr` |
| `Executor / merge-pr` | implementation PR merged | `Lead / finalize-change` |
| `Lead / finalize-change` | `MORE_IMPLEMENTATION_REQUIRED`: approved implementation still incomplete | `Executor / implement-change` |
| `Lead / finalize-change` | validated final Archive PR ready | `Reviewer / review-archive` |
| `Reviewer / review-archive` | archive/preparation finding | `Lead / finalize-change` |
| `Reviewer / review-archive` | PASS for exact Archive head | `Executor / merge-pr` |
| `Executor / merge-pr` | final Archive PR merged, coordination Issue still open | `Lead / finalize-archive` |
| `Lead / finalize-archive` | terminal conditions satisfied | durable `LIFECYCLE_COMPLETE`, then coordination Issue close and closed re-observation |

The two `Executor / merge-pr` positions are distinguished by current durable PR/lifecycle evidence, not by a separate action name or hidden phase state.

## Optional pre-Change Explore

`Lead / explore-change` is optional pre-Propose investigation and keeps `Change: unset` for the whole action.

| Explore disposition | Topology result |
| --- | --- |
| `PROPOSAL_READY` within the bounded researched/authorized context | route the same Issue to `Lead / propose-change` with `Change: unset`; same-role continuation may proceed immediately when its own preconditions hold |
| `HUMAN_DECISION_REQUIRED` | retain `Lead / explore-change` until the exact provenance-bound Human decision is legally consumable |
| `NO_CHANGE_REQUIRED` | persist the bounded result, close the research Issue, and re-observe closed; no formal Change/archive lifecycle is created |
| `NO_GO` | persist the bounded result, close the research Issue, and re-observe closed; no formal Change/archive lifecycle is created |

A valid Human-admitted direct-Propose entry may fall back to Explore without creating a new authority envelope; an in-scope `PROPOSAL_READY` returns to Propose under that preserved envelope.

## Correction loops

Correction loops preserve the same persistent coordination Issue and immutable Change identity once formal activation has occurred.

- OpenSpec semantic finding: `Reviewer / review-openspec → Lead / resolve-question → Reviewer / review-openspec` when semantic artifacts materially change.
- Implementation specification blocker: `Executor / implement-change → Lead / resolve-question → Reviewer / review-openspec → Executor / implement-change` when a material semantic correction is required.
- Implementation finding: `Reviewer / review-implementation → Executor / implement-change → Reviewer / review-implementation` on a new exact implementation head.
- Incomplete post-merge implementation: `Executor / merge-pr → Lead / finalize-change → Executor / implement-change` when approved work remains.
- Archive finding: `Reviewer / review-archive → Lead / finalize-change → Reviewer / review-archive` on the corrected exact Archive target.

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
