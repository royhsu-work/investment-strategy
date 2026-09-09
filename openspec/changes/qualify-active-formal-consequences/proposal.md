# Change: Qualify active formal consequences

## Why

Issue #229 owns a bounded repository-wide correctness refinement. Its parent outcome remains:

```text
observable current evidence
+ explicit machine-decidable predicates
→ qualification by the existing executable owner of the consequence
→ consequence becomes eligible
```

The active-formal provenance gap is one concrete scheduled-agent proof case inside that parent outcome. It does not replace the repository-wide principle.

## Human-approved correction

The durable Human direction is recorded by issuecomment-5598442708, issuecomment-5600436554, and issuecomment-5602555101. The latest correction preserves the parent outcome and requires the existing Change to converge subtractively before implementation:

- keep one small generic affirmative-qualification invariant in `repository-governance`;
- keep the concrete active-formal predicate in the existing scheduled-agent current-state and application owners;
- require application-owned correlation that binds accepted Action/Result, application authorization, model-derived consequence, and exact durable postcondition;
- use a complete relevant lifecycle observation for ordering, supersession, and ABA analysis; lifecycle actor, timestamp, connector, carrier, and value equality are not authority;
- make the real Stage 1 → Stage 2 activation boundary cross a default-branch merge;
- allow successive replaceable implementation carriers for one coordination Issue and one immutable Change when separate deployment boundaries require them;
- keep permanent specifications focused on steady-state behavior and keep one-time rollout mechanics in proposal, design, and tasks;
- keep the implementation plan to two independently bounded stages; and
- retain explicit no-delta boundaries for pre-activation intake, Action/Role/Result topology, carrier authority, OpenSpec configuration, and #218.

The Stage 1 lifecycle is:

```text
implement-change
→ READY
→ review-implementation
→ PASS
→ merge-implementation-pr
→ MERGED
→ finalize-change
→ MORE_IMPLEMENTATION_REQUIRED
→ Stage 2 implement-change
```

`MORE_IMPLEMENTATION_REQUIRED` is the existing same-Change continuation result. It does not deploy Stage 1 to `main`, create a stage state, or authorize the strict Stage 2 consumer before Stage 1 has been reviewed, merged, and observed on the default branch.

This is material semantic input. Any earlier exact-head semantic PASS is revision-bound and does not approve this correction. Lead must revise this existing Change through the existing carrier, obtain exact-R validation, and obtain a fresh independent `review-openspec` gate before implementation resumes.

## Parent outcome and delivery stages

The parent outcome remains the repository-wide affirmative qualification principle. The active-formal scheduled-agent behavior is its concrete proof and current delivery target, not a narrowing of the parent outcome.

Delivery is split at the existing staged-delivery boundary:

```text
Stage 1
→ produce mandatory application-correlation-bearing formal evidence
→ preserve current acceptance behavior
→ provide the minimum existing-owner continuation-carrier capability needed after merge

default-branch merge
→ finalize-change
→ MORE_IMPLEMENTATION_REQUIRED

Stage 2
→ use a fresh carrier based on the then-current default branch
→ consume correlation plus complete lifecycle ordering
→ qualify current active formal state
→ remove equality-only authority
→ enforce QUALIFIED / INDETERMINATE at existing ingress and application boundaries
```

Stage 1 and Stage 2 are delivery stages of one Change, not workflow states. Stage 2 is mandatory continuation, not optional cleanup.

## What changes

1. Keep the generic `repository-governance` invariant small: the existing canonical executable owner evaluates one affirmative predicate before a machine-decidable consequence becomes eligible. The generic rule does not define scheduled-agent routing, `Change`, `ObservationProvenance`, Action/Result, carrier, or terminal mechanics.
2. Require the existing formal application evidence chain to carry the minimum application-owned correlation needed to bind accepted Action/Result, exact application authorization, model-derived routing or terminal consequence, and exact durable postcondition. Correlation is mandatory; only its minimum representation is an implementation choice.
3. At the existing scheduled-agent reconstruction and dispatch owner, consume the current formal observation together with a complete relevant lifecycle observation. Use lifecycle evidence only to order relevant mutations and identify supersession or ABA. Incomplete, contradictory, stale, or unqualified relevant observation is `INDETERMINATE` and fails closed.
4. Classify the active formal observation as `QUALIFIED` only when one unique current binding remains. Otherwise use the existing fail-closed dispatch and application boundary.
5. Remove the equality-only formal authority shortcut once the qualified path is consumed. Equality may support idempotent observation after qualification, but never establish qualification.
6. Preserve the finite Action/Role/Result model, application reauthorization, CarrierRequired boundary, WIP/priority/finish-first/no-fallback behavior, and the `Change: unset` pre-activation path.
7. At Stage 1, extend the existing materialization owner only as necessary to establish a fresh implementation carrier from the then-current default branch after the prior carrier has merged. Reuse the same Issue, immutable Change, content-addressed ingress, exact postconditions, and carrier separation; do not create a second workflow, Change, stage registry, or generic multi-stage framework.

## Boundaries

- First Change materialization remains owned by the existing Lead / propose-change application path and its exact validation and postconditions.
- A later continuation carrier is a replaceable physical work-product carrier for the same Issue and immutable Change; it is not a second workflow or Change.
- `Change: unset` intake remains under the existing Explore/Propose contract.
- Carrier execution remains an actuator under an application-authorized plan; carrier identity does not supply authority.
- `openspec/config.yaml` remains the existing OpenSpec authoring owner; no second authoring authority is added.
- Action/Role/Result vocabulary and topology remain unchanged.
- Issue #218 remains downstream and out of scope.

## Acceptance boundary

Stage 1 is complete only when one exact reviewed implementation revision:

1. emits mandatory application-owned correlation in existing formal evidence for new repository application transitions;
2. keeps current acceptance behavior while producing that evidence;
3. proves the correlation is tied to the accepted Action/Result, application authorization, model-derived consequence, and exact postcondition;
4. includes the minimum existing-owner capability to create a fresh Stage 2 implementation carrier from the then-current default branch after Stage 1 merges; and
5. leaves Stage 2 explicitly mandatory through the existing `MORE_IMPLEMENTATION_REQUIRED` continuation.

Stage 1 then crosses the existing review/merge/finalize lifecycle. Stage 2 begins only on a later fresh wake after the Stage 1 merge and application postcondition.

Stage 2 is complete only when one later exact reviewed implementation revision:

1. consumes correlation and complete lifecycle ordering at the existing current-state, dispatch, and application owners;
2. accepts one uniquely qualified repository-owned active transition;
3. rejects direct, equality-only, incomplete, contradictory, and ABA-superseded evidence through `INDETERMINATE` / fail-closed behavior;
4. accepts exact carrier completion only after the later fresh postcondition observation;
5. preserves `Change: unset`, WIP/priority/finish-first/no-fallback, materialization, configuration, Action/Role/Result, and #218 boundaries; and
6. contains no new workflow state, stage registry, ledger, cursor, receipt lifecycle, policy engine, carrier protocol, permanent legacy fallback, or competing owner.

## Scope and non-goals

In scope are the two canonical OpenSpec owners, the existing scheduled-agent reconstruction/dispatch/application/effect boundaries, existing formal evidence, complete relevant lifecycle-event ordering, replaceable continuation-carrier materialization, and focused executable regressions. The only formal workflow target is Issue #229.

Out of scope are Issue #218, historical Issue rewriting, semantic correctness requiring Human or mapped Role judgment, generic provenance/security infrastructure, new persistent state, a permanent legacy fallback, and unrelated product behavior.

## Delivery

This is one semantically coherent Change delivered through two independently reviewable implementation stages. Permanent specifications describe the steady-state qualification contract; the proposal, design, and tasks carry the one-time staged rollout and continuation mechanics. The application owns materialization and later routing, and each successor waits for a later fresh wake.
