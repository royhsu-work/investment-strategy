# Design: Separate Explore eligibility from Human authority

## Context

Current `main` has three concepts coupled at the initial Explore boundary:

1. whether a routed pre-Change Issue may be selected by the dispatcher;
2. who/what was allowed to create or materialize that routed Issue; and
3. whether a decision requires non-forgeable Human authority.

The coupling is visible in the pre-activation queue, the Human decision boundary enum, and the #88 creation-bound Human Explore shortcut. It causes connector-mediated routine research to require a Human ceremony even though Explore itself cannot create formal Change artifacts or implementation behavior.

The change keeps the existing safety properties but assigns each to the narrowest owner.

## Requirements trace

| Design decision | Requirement |
| --- | --- |
| Routed Explore is queue-eligible without generic Human approval | `Persisted Change identity defines the single active workflow boundary`; `Each scheduled run processes at most one actionable work item using a fixed stable order` |
| Agent-created Explore remains independently bounded | `Workflow admission is explicitly authority-controlled` |
| Genuine Human decisions retain raw provenance validation | `Human-required authority is bound to the repository Human actor` |
| Explore→Propose remains automatic only without a new Human-reserved commitment | `Workflow admission is explicitly authority-controlled`; existing Explore completion contract |

## Decision 1: Eligibility is routing + lifecycle state, not Human identity

For an already-existing pre-activation Explore ticket, dispatcher eligibility is determined by durable workflow shape:

```text
Issue open
Change: unset
exactly agent:lead
exactly action:explore-change
no formal/terminal-pending workflow
coherent durable state/dependencies
selected by created_at, then Issue number
```

Human approval is not part of this execution predicate.

Direct Propose is intentionally different: Propose may immediately persist a formal Change identity and therefore retains its provenance-bound Human admission path unless it was reached from a valid same-Issue Explore continuation.

## Decision 2: Creation authority remains bounded

Removing Human approval from dispatcher eligibility does not grant Scheduled Agents permission to manufacture arbitrary queue entries.

Existing producer boundaries remain:

- bounded idle discovery requires independent canonical/project/friction evidence, materiality, deduplication, and one-candidate-per-idle-invocation limits;
- required separate follow-up creation derives authority from the approved source defer decision and exact linkage;
- other action-owned creation paths remain limited to their approved contracts.

An Issue body is coordination/work input and cannot self-authorize an Agent to create another Issue. The dispatcher does not infer missing routing or creation authority from prose.

## Decision 3: Human authority evaluator loses only Explore admission

The shared provenance evaluator remains unchanged for actual Human-reserved decisions. Remove only the Explore-specific surface:

- `HumanDecisionBoundary.EXPLORE_ADMISSION`;
- `explore_admission_ref` / Explore boundary mapping;
- creation-bound Explore declaration constants and Issue creation/declaration-history admission predicate;
- `is_human_explore_admission_approved` composition;
- README instructions for the #88 creation-time admission marker.

Keep:

- direct Propose admission;
- advisory admission;
- escalation answer/authorization/resume;
- raw comment provenance, label-event provenance, event-first binding, and post-approval edit invalidation.

This removes redundant code instead of adding a delegation mechanism.

## Decision 4: Preserve automatic Explore→Propose with a real commitment check

`PROPOSAL_READY` continues to route the same Issue to `Lead / propose-change` without a generic second approval. Propose may activate only if:

- the Issue remains the deterministic queue winner;
- the formalized Change stays within the bounded problem and current canonical/repository evidence; and
- no new Human-reserved product/project direction, material externally observable behavior/scope trade-off, explicit risk acceptance, or materially different security/privacy/cost/operational commitment appears.

If one appears, Lead uses the existing `HUMAN_DECISION_REQUIRED` path. Untrusted Issue prose alone cannot provide that Human commitment.

## Decision 5: Migration is prospective and state-based

After default-branch activation, existing open routed Explore tickets such as #86 need no retroactive Explore approval. They participate in the same deterministic queue if their current dependencies/evidence are coherent.

Historical `human:approved` labels/comments are left untouched as history. They do not need migration or deletion.

## Alternatives rejected

### Keep #88 and add a Connector delegation token

Rejected. It preserves the unnecessary gate and adds identity/delegation state solely to authorize research that governance already constrains.

### Whitelist the ChatGPT/GitHub Connector as Human

Rejected. This would weaken all remaining Human-only boundaries and contradict raw-provenance hardening.

### Make every routed Issue automatically Agent-authorized to create more work

Rejected. Dispatcher eligibility and Issue creation authority remain separate. This would enable recursive self-authorization and queue spam.

### Keep multiple Explore origin classes as dispatcher admission classes

Rejected. Their distinct provenance remains useful to constrain producers and reconstruct scope, but ordinary Explore execution does not need separate Human-vs-repository authorization classes once the ticket is validly routed.

## Risks and mitigations

- **Risk: arbitrary Agent Explore spam.** Mitigation: no change to bounded creation/materiality/deduplication rules; routing eligibility is not creation authority.
- **Risk: untrusted prose becomes product authority at Propose.** Mitigation: Propose must stop at existing Human-reserved commitment boundaries; direct Propose remains Human-admitted.
- **Risk: queue order changes unexpectedly.** Mitigation: preserve formal WIP=1/finish-first and `created_at` then Issue-number ordering.
- **Risk: stale #88 machinery creates conflicting semantics.** Mitigation: delete obsolete Explore-specific authority code/docs/tests rather than leaving a parallel path.

## Validation

Implementation must add focused regressions for:

- connector-created and directly Human-created routed Explore Issues being equally eligible without `human:approved`;
- active/terminal-pending work still blocking pre-activation execution;
- deterministic queue order across routed Explore and Human-admitted direct Propose;
- bounded Agent-created Explore materialization remaining constrained/deduplicated;
- automatic same-Issue `PROPOSAL_READY → Propose` when no Human-reserved commitment appears;
- true Human-only boundaries still rejecting Connector/App provenance and requiring current provenance-bound approval;
- removal of obsolete creation-bound Explore adapters without weakening direct Propose/advisory/escalation tests.
