# Change: Qualify active formal consequences

## Why

Issue #229 is the current formal workflow for a bounded repository-wide correctness refinement. Its parent outcome remains:

```text
observable current evidence
+ explicit machine-decidable predicates
→ qualification by the existing executable owner of the consequence
→ consequence becomes eligible
```

The active-formal provenance gap is one concrete scheduled-agent proof case inside that parent outcome. It does not replace the repository-wide principle.

## Human-approved correction

The latest durable Human direction, including issuecomment-5598442708 and issuecomment-5600436554, requires the existing Change to converge subtractively before implementation:

- keep one small generic affirmative-qualification invariant in `repository-governance`;
- keep the concrete active-formal predicate in the existing scheduled-agent current-state and application owners;
- bind the current consequence through the existing application evidence chain, including the smallest application-owned correlation field(s) needed to connect accepted Action/Result, application authorization, model-derived consequence, and exact durable postcondition;
- use GitHub lifecycle events only for ordering, supersession, and ABA analysis;
- preserve consequence authority rather than treating actor, connector, carrier, timestamp, or value equality as authority; and
- retain explicit no-delta boundaries for already-correct materialization, pre-activation intake, carrier execution, OpenSpec configuration, Action/Role/Result topology, and #218.

This is material semantic input. The earlier exact-head `review-openspec` PASS for `ca4b66ca7cf5f89194ada8d4e5dcb2909807f640` does not approve this newer delivery and evidence contract.

## Current truth and disposition

Fresh reconstruction at default-branch revision `e4dcad8ad0326a6a38620998ee2f03ebcc060a19` found:

- Issue #229 is open with Change `qualify-active-formal-consequences` and `action:resolve-question`.
- It is the only open formal Change candidate; pre-activation Issues #233 and #234 do not displace formal priority.
- Pull request #232 is the existing same-Change carrier, open on `agent/qualify-active-formal-consequences` at exact head `ca4b66ca7cf5f89194ada8d4e5dcb2909807f640`.
- The exact-head semantic PASS is issuecomment-5599743969. The later durable correction is issuecomment-5600436554, followed by the application `SPEC_BLOCKER` issuecomment-5600641388 and the current `action:resolve-question` route.
- Current Issue lifecycle events expose durable label and lifecycle ordering, but the default-branch runtime does not yet consume complete lifecycle-event reconstruction in dispatch preflight.

The existing Change and PR are updated in place. No second Change, PR, routing mechanism, migration state, or permanent legacy fallback is created.

## Parent outcome and delivery stages

The parent outcome remains the repository-wide affirmative qualification principle. The active-formal scheduled-agent behavior is its concrete proof and current delivery target, not a narrowing of the parent outcome.

Delivery is split at the existing staged-delivery boundary:

```text
Stage 1
→ produce application-correlation-bearing formal evidence
→ preserve current acceptance behavior

Stage 2
→ consume correlation plus lifecycle ordering
→ qualify current active formal state
→ remove equality-only authority
→ enforce QUALIFIED / INDETERMINATE at existing ingress and application boundaries
```

Stage 1 is independently buildable and reviewable on current N-1. It must leave durable evidence that Stage 2 can consume. Stage 2 is the required continuation; it is not optional cleanup. The existing `MORE_IMPLEMENTATION_REQUIRED` result carries this continuation without introducing migration state.

## What changes

1. Keep the generic `repository-governance` invariant small: the existing canonical executable owner evaluates one affirmative predicate before a machine-decidable consequence becomes eligible. The generic rule does not define scheduled-agent routing, `Change`, `ObservationProvenance`, Action/Result, carrier, or terminal mechanics.
2. Extend the existing formal application evidence chain with the minimum application-owned correlation field(s) needed to bind the accepted Action/Result and application authorization to the model-derived routing/terminal effect and its exact durable postcondition. The field(s) remain part of existing formal evidence; they do not create a receipt lifecycle or second protocol.
3. At the existing scheduled-agent reconstruction/dispatch owner, consume the correlation-bearing formal evidence and relevant Issue lifecycle events. Events establish latest relevant ordering and supersession/ABA; actor and timestamp are metadata, not authorization.
4. Classify the active formal observation as `QUALIFIED` only when one current binding remains. Otherwise classify it as `INDETERMINATE` and use the existing fail-closed dispatch/application boundary.
5. Remove the existing equality-only formal authority shortcut once Stage 2 consumes the qualified path. Idempotent observation remains useful only after qualification.
6. Preserve the existing finite Action/Role/Result model, application reauthorization, CarrierRequired boundary, WIP/priority/finish-first/no-fallback behavior, and the `Change: unset` pre-activation path.

## No-delta dispositions

- First Change materialization remains owned by Lead / propose-change, exact default-branch authorization, existing Change branch/paths/PR, exact validation, application authorization, and fresh postconditions. No materialization delta is added.
- `Change: unset` intake remains under the existing Explore/Propose contract.
- Carrier execution remains a replaceable actuator under the existing CarrierRequired plan and postcondition boundary.
- `openspec/config.yaml` remains unchanged; current smallest-sufficient and existing-owner guidance is sufficient.
- Action/Role/Result vocabulary and topology remain unchanged.
- Issue #218 remains downstream and out of scope.

## Acceptance boundary

Stage 1 is complete only when one exact reviewed revision:

1. emits application-owned correlation in existing formal evidence for new repository application transitions;
2. keeps current acceptance behavior while producing that evidence;
3. proves the correlation is tied to the accepted Action/Result, application authorization, model-derived consequence, and exact postcondition; and
4. leaves Stage 2 explicitly mandatory through the existing continuation path.

Stage 2 is complete only when one later exact reviewed revision:

1. consumes the correlation and lifecycle ordering at the existing current-state/dispatch/application owners;
2. accepts one uniquely qualified repository-owned active transition;
3. rejects direct, equality-only, and ABA-superseded evidence through `INDETERMINATE` / fail-closed behavior;
4. accepts exact carrier completion only after the later fresh postcondition observation;
5. preserves `Change: unset`, WIP/priority/finish-first/no-fallback, materialization, configuration, Action/Role/Result, and #218 boundaries; and
6. contains no new workflow state, registry, ledger, cursor, receipt lifecycle, policy engine, carrier protocol, or competing owner.

## Scope and non-goals

In scope are the two canonical OpenSpec owners, the existing scheduled-agent reconstruction/dispatch/application/effect boundaries, existing formal evidence, Issue lifecycle-event ordering, and focused executable regressions. The only formal workflow target is Issue #229.

Out of scope are Issue #218, implementation execution in this Lead wake, historical Issue rewriting, semantic correctness requiring Human or mapped Role judgment, generic provenance/security infrastructure, new persistent state, a permanent legacy fallback, and unrelated product behavior.

## Delivery

This is one semantically coherent Change delivered through two independently reviewable implementation stages. The Change records the parent outcome, current stage boundary, N-1 prerequisites, stage exit criteria, remaining mandatory outcome, and required continuation. The application owns materialization and later routing; this Lead result does not execute the successor in the current wake.
