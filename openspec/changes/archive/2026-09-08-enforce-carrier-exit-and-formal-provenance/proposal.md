# Change: Enforce carrier invocation exit and formal transition provenance

## Why

Issue #227 is the bounded corrective workflow for the still-unaccepted Human
outcome of #221. The parent acceptance identity is #221; this Change must not
reopen, unarchive, rewrite, or replace #221's archived historical Change. The
current closed state of #221 is historical repository state, not Human
acceptance of its defective completion. Issue #218 remains blocked and outside
this Change.

The unchanged #221 outcome is:

```text
verified slice
→ durable checkpoint
→ interruption
→ reconstruct current truth
→ previously verified slices are not replayed
→ resume first incomplete slice
```

The exact durable Human evidence is preserved and is part of this decision
boundary:

- #221 rejection/root-cause evidence: `issuecomment-5575078000`. It
  identifies two formal durable-state write paths (repository-owned GitHub
  Actions/application and LLM/direct connector), explains that the connector
  path made formal progress fail-open from Slice 4 onward, and requires formal
  mutation only after exact successful repository-owned Actions, application
  authorization, and observed postcondition. It limits the connector to
  transport or execution of an authorized plan, requires zero progress without
  Actions proof, preserves one `implement-change` Action per
  first-incomplete bounded slice, and requires
  `newly checked task IDs == SLICE_CHECKPOINT Completed-Tasks == first
  incomplete slice task set`.
- Latest Human-approved minimal repair direction:
  `issuecomment-5578787305`. It explicitly approves the bounded
  `CarrierRequired` invocation-exit boundary, fresh reconstruction after a
  carrier, the narrow active formal-state provenance guard, bounded
  `EFFECT_REQUEST` ingress, and the listed regressions and non-goals. It is
  Human intent/evidence only: it is not an Action result, routing authority,
  terminal authority, reopening of #221, or activation of #218.

Current default-branch evidence at `main` revision
`889a559f5704e8034f050b0fd965c4f131566781`, together with the executable
dispatch selected for #227, confirms the next legal Action is
Lead / propose-change. The exact same-Issue Explore result is
`issuecomment-5581185977` (`PROPOSAL_READY`). It reports two bounded
current gaps: `CarrierRequired` is converted to an `ApplyResult` inside
`apply_effect_batch` while the bridge continues orchestration, and active
formal routing/terminal observations are not qualified by
repository-owned Actions/application transition provenance. It also records
that PR #226 is feasibility work product, not semantic authority, Reviewer
PASS, or merge authorization.

## What Changes

- Add one shared normative requirement to
  `openspec/specs/repository-governance/spec.md`: `CarrierRequired` is a
  hard invocation-exit boundary. The application may emit only the exact
  freshly authorized `CarrierPlan`; the carrier may execute only that exact
  operation, target, and expected values. After the carrier boundary, the
  invocation must not write `SLICE_CHECKPOINT`, `ACTION_RESULT`,
  `action:*`, terminal/close state, or a successor. Formal continuation is
  only a later fresh repository-owned Actions/application reconstruction.
- Add one narrow normative requirement to
  `openspec/specs/scheduled-agent-workflow/spec.md`: after `Change != unset`,
  current formal `action:*` routing and terminal/close transitions require
  repository-owned Actions/application provenance. Missing, incomplete,
  connector-authored, or out-of-band provenance is `INDETERMINATE` and fail
  closed; it is not normalized, auto-accepted, rewound, or laundered by
  reconciliation. `Change: unset` pre-activation compatibility remains
  unchanged.
- Implement these requirements by reusing the existing Action/Result vocabulary,
  application authorization, `EFFECT_REQUEST` ingress, `CarrierPlan`,
  carrier actuator, fresh observation, exact-head guards, postconditions,
  checkpoint cardinality, first-incomplete-slice matching, and stale/replay/
  no-rewind behavior. The connector ingress remains only bounded untrusted
  `EFFECT_REQUEST` transport and does not gain routing, successor, retry,
  merge, terminal, or success authority.
- Reuse, reduce, or correct PR #226 only after this Change is independently
  reviewed. Its successful checks are feasibility evidence; its branch, wording,
  implementation, or PR state is not an approved specification or merge gate.
- Keep the existing application/carrier separation. Do not replace it with a
  GITHUB_TOKEN-only architecture or add a dedicated GitHub App/token
  infrastructure unless later fresh evidence proves the existing carrier
  primitive cannot satisfy this approved boundary.
- After any carrier operation, use a later fresh wake. A non-merge wake may
  observe the already-current postcondition and apply only still-missing
  authorized effects. A merge wake must treat the old authorization as stale
  when `main` changed, perform historical exact-head read-only reconciliation,
  and obtain fresh current-main authorization before continuation.

## Canonical ownership and scope

The shared application/carrier hard-exit invariant belongs only to
`repository-governance`. Active formal routing/terminal provenance belongs
only to `scheduled-agent-workflow`, which references shared carrier semantics
instead of duplicating them. The executable Action model remains the sole
machine topology owner. README, AGENTS, workflow presentation, Roles, and
Skills may orient or reference these rules but must not become competing
normative copies. No Role or Skill change is proposed unless implementation
evidence proves an existing action-specific procedure is insufficient.

This Change does not add an Action, Result kind, checkpoint/progress registry,
cursor, lease, heartbeat, retry counter, mailbox, second DAG, new carrier type,
carrier-result protocol, generic provenance/recovery framework, dedicated token
architecture, ruleset redesign, #218 scope, #207 scope, or #180 scope. It does
not absorb #218 into #221.

## Required implementation regressions

The implementation must authoritatively prove:

1. `CarrierRequired` stops the current application/effect sequence before
   later checkpoint, result, routing, terminal, or successor effects.
2. An authorized carrier mutation can be resumed by a later fresh
   Actions/application wake without replaying already verified slices.
3. A merge carrier uses fresh historical exact-head reconciliation rather than
   replaying stale authorization.
4. `Change != unset` plus a connector-authored direct `action:*` transition
   fails closed as `INDETERMINATE`.
5. A connector-authored premature terminal/close mutation fails closed.
6. A repository-owned Actions/application formal transition is qualified.
7. `Change: unset` pre-activation behavior remains compatible.
8. Existing checkpoint cardinality, exact first-incomplete-slice matching,
   monotonic task bookkeeping, stale/replay/no-rewind behavior, exact-head
   review/merge gates, Reviewer independence, and Human authority remain
   unchanged.

## Acceptance boundary

The Change is ready to leave the current propose Action only after a fresh
repository-owned application has materialized this spec-driven Change from the
exact current `main` revision and its new canonical deltas pass strict
OpenSpec validation. Later lifecycle Actions must independently review,
implement, verify, merge, finalize, archive, and terminally complete this new
Change according to the current executable model.

`#227` repository lifecycle completion is not `#221` Human acceptance.
Until the Human separately accepts the original #221 outcome, #218 stays
blocked.
