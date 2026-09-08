# Design: Enforce carrier invocation exit and formal transition provenance

## Current decision boundary

This new Change is a corrective implementation of the unchanged #221 outcome:

```text
verified slice
→ durable checkpoint
→ interruption
→ reconstruct current truth
→ previously verified slices are not replayed
→ resume first incomplete slice
```

The boundary was reverse-verified from:

- the exact #221 rejection/root-cause evidence,
  `issuecomment-5575078000`;
- the exact latest Human-approved minimal repair direction,
  `issuecomment-5578787305`;
- current `main` at
  `889a559f5704e8034f050b0fd965c4f131566781`;
- `README.md`, `agents/AGENTS.md`, `agents/workflow.md`,
  `openspec/config.yaml`, the executable Action model, dispatch, Lead Role,
  and OpenSpec Change Skill;
- the current canonical
  `repository-governance` and `scheduled-agent-workflow` specifications;
- fresh current source and tests; and
- the same-Issue `PROPOSAL_READY` result
  `issuecomment-5581185977`, including PR #226's feasibility evidence.

#221's archived Change and terminal history are historical evidence only. They
are not reactivated or edited. #227 remains the only formal workflow being
advanced, while #218 remains open, unrouted, and blocked.

The current default branch already owns the Action/Role vocabulary, one-wake
successor model, application authorization, exact postconditions, checkpoint
cardinality, first-incomplete-slice matching, stale/replay/no-rewind guards,
and carrier primitives. The repair therefore adds only the two missing
normative qualifications identified by the fresh Explore result.

## Ownership and implementation surfaces

The canonical ownership is deliberately split:

- `openspec/specs/repository-governance/spec.md` owns the shared
  application/carrier contract, including the hard `CarrierRequired` exit.
- `openspec/specs/scheduled-agent-workflow/spec.md` owns qualification of
  active formal `action:*` routing and terminal/close transitions.
- The executable workflow model remains the sole machine topology and
  Action/Role/transition owner.
- Existing application/effect, bridge, carrier, runtime observation, and
  workflow files implement those requirements.
- README, AGENTS, workflow presentation, Roles, and Skills may orient or
  reference the canonical requirements; they do not receive a competing
  normative copy.

No new Action, Result kind, state, registry, cursor, lease, heartbeat, retry
counter, mailbox, second DAG, carrier type, carrier-result protocol, or generic
provenance/recovery framework is part of this design.

## D1 — Hard invocation exit at CarrierRequired

`CarrierRequired` remains the existing carrier boundary and
`CarrierPlan` remains the existing immutable exact-plan primitive. The
application first fresh-authorizes the source Issue, immutable Change, Action,
default-branch revision, target, expected values, and allowed operation. It may
then emit only that exact plan.

When the application reaches `CarrierRequired`:

1. the application/effect layer stops the current effect sequence at that
   boundary;
2. the bridge exposes only the exact carrier plan and the boundary outcome;
3. the current invocation performs no later `SLICE_CHECKPOINT`,
   `ACTION_RESULT`, `action:*`, terminal/close, or successor effect; and
4. the carrier executes only the plan's exact operation, target, and expected
   values, with no meaning, routing, retry, or success authority.

This is an invocation boundary, not a new result protocol. The current
application must not convert the exception into an ordinary successful
`ApplyResult` that permits orchestration to continue. Workflow continuation
steps are skipped for this invocation, and the invocation exits. A later
repository-owned Actions/application wake is the only formal continuation
path.

## D2 — Reconstruct current truth after a carrier

A later wake re-reads current default-branch state, the same Issue and Action,
the immutable Change, current PR/head and evidence, and all effect
postconditions. It applies only still-missing effects authorized by that fresh
observation.

For a non-merge carrier effect, the later application may observe that the
exact postcondition already exists and reconcile only the missing authorized
effects. It does not replay a verified slice, create a second state record, or
let the carrier assert success.

For a merge carrier effect, the mutation changes `main`. The old
`EFFECT_REQUEST` is expected to become stale. The later wake performs the
existing historical exact-head merge read-only reconciliation, verifies the
historical carrier postcondition, obtains fresh current-main authorization,
and then continues under the current revision. It never replays the stale
authorization or derives a successor from the carrier's assertion.

This reuses current exact-head, stale, replay, no-rewind, and postcondition
machinery. It adds no mailbox, registry, continuation token, retry state, or
second graph.

## D3 — Narrow provenance qualification for active formal state

When `Change: unset`, existing pre-activation Explore/Propose selection and
compatibility remain unchanged.

When `Change != unset`, the fresh current formal observation must qualify any
current `action:*` routing transition and terminal/close transition with
repository-owned Actions/application provenance. The evidence must be tied to
the application authorization and its repository-owned Actions execution and
durable postcondition; structural Issue fields, label shape, timestamps, or
the fact that a comment is syntactically valid are not sufficient.

A connector-authored or other out-of-band direct formal route or close is
classified `INDETERMINATE` and fails closed. The application does not
normalize it as qualified state, auto-accept it, rewind it, or launder it
through an idempotent reconciliation. A repository-owned Actions/application
transition with complete fresh evidence remains qualified.

This is one guard at the existing runtime observation/application boundary. It
is not a reusable generic provenance framework and it does not grant the
connector authority. Connector ingress remains the bounded untrusted
`EFFECT_REQUEST` transport; requested routing, successor, retry, merge,
terminal, and success effects are still rejected or derived by the
application.

## D4 — Converge existing PR #226 as work product

PR #226 at head
`f3fa882dd00456eb1bcf63e929eccb00d275a9d8`, based on current `main`
`889a559f5704e8034f050b0fd965c4f131566781`, is a minimum feasibility path.
Its exact-head Python Quality and OpenSpec Validate runs are evidence that the
candidate surfaces are implementable; they are not approval, semantic
authority, Reviewer PASS, or merge authorization.

After this Change is independently approved, implementation may reuse or
reduce the PR's existing bridge/effect/workflow/runtime/test changes. It must
retain only behavior traced to D1, D2, or D3 and to the existing approved
checkpoint/recovery contract. Repeated normative prose in AGENTS, workflow
presentation, Roles, or Skills is not a reason to widen ownership. If any
candidate edit is unnecessary, remove it. If a current existing surface is
insufficient, add only the smallest change at its owning layer.

## D5 — Preserved invariants and failure behavior

The implementation must preserve:

- exact one-Action-per-wake dispatch and successor-on-later-wake behavior;
- repository-owned Actions/application as the formal correctness boundary;
- one `implement-change` Action per first-incomplete bounded slice;
- exact checkpoint cardinality and task-ID equality;
- monotonic task bookkeeping;
- current PR/revision and exact-head review/merge gates;
- stale/replay/no-rewind rejection and idempotent missing-effect reconciliation;
- independent Reviewer and Human authority boundaries; and
- #218's blocked, unrouted state.

If any fresh authorization, carrier plan, provenance evidence, target,
revision, or postcondition is missing, stale, ambiguous, contradictory, or
unqualified, the application fails closed with no formal progress. Raw
failure evidence remains available for the next fresh wake; it is not turned
into a successor or terminal state.

## Acceptance and verification

The design is accepted only when focused production-boundary regressions and
the full repository checks prove both new requirements and all preserved
invariants. The proof must include the hard carrier exit, non-merge
reconstruction, merge historical reconciliation, direct connector routing and
close rejection, repository-owned transition qualification, and
`Change: unset` compatibility. It must also demonstrate that no previously
verified slice is replayed and that no prohibited mechanism or unrelated Issue
scope was introduced.
