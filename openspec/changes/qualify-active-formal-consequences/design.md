# Design: Qualify active formal consequences

## Decision boundary

The approved parent outcome remains:

```text
observable current evidence
+ explicit machine-decidable predicates
→ qualification by the existing executable owner of the consequence
→ consequence becomes eligible
```

The active-formal scheduled-agent provenance gap is one concrete P0 proof case. The latest correction, issuecomment-5600436554, adds a required application-correlation and staged-cutover boundary without changing the parent outcome.

Fresh evidence at default-branch revision `e4dcad8ad0326a6a38620998ee2f03ebcc060a19` is:

- Issue #229 is open with Change `qualify-active-formal-consequences` and `action:resolve-question`.
- PR #232 is the existing same-Change carrier, open on `agent/qualify-active-formal-consequences` at exact head `ca4b66ca7cf5f89194ada8d4e5dcb2909807f640`.
- Review PASS issuecomment-5599743969 targets that head, but the material correction issuecomment-5600436554 is newer; application result issuecomment-5600641388 correctly returned the workflow to Lead / resolve-question.
- Current Issue events provide durable label/lifecycle ordering evidence, while current `scheduled_agent_runtime` preflight reconstructs Issue snapshots without complete lifecycle-event consumption.

The existing Change and PR are updated in place. No new Change, PR, workflow state, or control mechanism is introduced.

## Ownership and subtraction

`repository-governance` owns one generic invariant: an existing canonical executable owner evaluates one affirmative qualification predicate before a machine-decidable repository consequence becomes eligible. It defines ownership and use of the result only. It does not define scheduled-agent routing, `Change`, `ObservationProvenance`, Action/Result, transport, carrier, terminal, or workflow-specific evidence.

The existing scheduled-agent owner owns the concrete predicate. Existing executable owners remain:

- `scheduled_agent_runtime.py` and `workflow_dispatch.py` for fresh current-state reconstruction and dispatch input;
- `scheduled_agent_action_model.py` for the finite Action/Role/Result vocabulary, legal transitions, and model-derived successor;
- `scheduled_agent_effects.py` and the application bridge for fresh application authorization, existing formal evidence, and durable effect postconditions;
- GitHub Issue comments, lifecycle events, labels, branches, PRs, commits, and checks for observable evidence; and
- the existing CarrierRequired plan for replaceable carrier execution.

The correction reuses these owners. It does not add a provenance framework, state registry, ledger, cursor, lease, retry state, receipt lifecycle, policy engine, carrier type, or competing authority.

## Stage 1 — produce correlation-bearing formal evidence

Stage 1 is the N-1 producer boundary. The existing application already receives an exact worker Action/Result, fresh-authorizes the current Issue/Change/Action and default-branch revision, derives the legal successor from the finite model, and observes the durable effect postcondition. Stage 1 adds the smallest application-owned correlation field(s) to the existing formal evidence written for that transition.

The correlation representation is part of the existing formal evidence, not a new receipt protocol. It is generated or completed by the repository application from the exact application request/run and authorization context; a connector, actor, timestamp, or worker-supplied value is not trusted as the binding. It must make the following chain reconstructable:

```text
accepted Action / Result
→ exact repository application authorization
→ model-derived routing or terminal consequence
→ exact durable postcondition
```

Stage 1 keeps the current acceptance behavior. It produces correlation-bearing evidence for new application transitions but does not yet make the existing dispatch consumer require that evidence. That separation prevents a first Stage-2 wake from treating an old pre-Stage-1 route as proof or from introducing a permanent legacy exception.

## Stage 2 — consume qualification at existing boundaries

Stage 2 extends the existing current-state reconstruction and dispatch preflight to consume:

1. the current Issue/Change/routing or terminal observation;
2. the latest applicable correlation-bearing formal evidence;
3. the exact accepted Action/Result and application authorization binding;
4. the model-derived successor or terminal effect; and
5. the exact durable postcondition.

The existing GitHub Issue lifecycle-event surface is read to order relevant mutations and identify later supersession. It is not used as authorization. Actor and timestamp remain descriptive metadata. A unique current binding yields `QUALIFIED`; missing, contradictory, or superseded binding yields `INDETERMINATE`, which flows through the existing complete-observation and fail-closed dispatch/application boundary.

The late formal equality shortcut is removed when the Stage-2 ingress/application qualification path is active. Current equality can support an idempotent observation after qualification, but it cannot establish qualification. No second predicate is retained as a competing authority.

## Latest transition and ABA

The current value is not provenance identity:

```text
T1 repository-authorized transition A → B
T2 out-of-band mutation B → C
T3 out-of-band mutation C → B
fresh current state == B
```

Lifecycle events establish that T2/T3 are later relevant mutations. T1's correlation therefore cannot qualify the fresh B. The owner must find a later applicable repository-authorized correlation and exact postcondition for the current B; otherwise the observation is `INDETERMINATE`.

## Evidence reuse and minimal representation

Reuse, in order:

- existing formal Action/Result, review, and merge evidence;
- application authorization against the exact current default-branch revision;
- the finite Action/Role/Result transition derivation;
- current Issue and terminal postcondition observations;
- Issue lifecycle events for ordering and supersession/ABA; and
- the existing CarrierRequired plan and later ref/PR/terminal postcondition.

Only if implementation proves that this existing chain cannot be correlated uniquely may the application add the minimum field(s) to the existing formal evidence. That field addition is the approved correlation boundary; it must not become a registry, ledger, cursor, workflow state, receipt lifecycle, second protocol, or generic provenance service.

## No-delta dispositions

| Boundary | Disposition |
| --- | --- |
| First Change materialization | Existing Lead / propose-change application path is sufficient; no delta. |
| Change: unset intake | Existing Explore/Propose pre-activation contract remains; no active-formal guard before Change persistence. |
| Carrier execution | Existing CarrierRequired boundary and immutable plan remain; carrier identity is not authority. |
| OpenSpec authoring guidance | Current `openspec/config.yaml` is sufficient; no delta. |
| Action/Role/Result model | Existing finite model remains sole executable owner; no new vocabulary. |
| #218 | Downstream boundary remains unchanged and out of scope. |

## Verification boundary

Stage 1 must prove that new repository application transitions produce durable correlation-bearing formal evidence while current acceptance remains compatible. Stage 2 must prove:

- one qualified repository-owned active route or terminal boundary is accepted;
- a connector/out-of-band route or close without the application chain is `INDETERMINATE` and fails closed;
- equality without a current application binding is not qualification;
- the ABA sequence cannot inherit T1 qualification;
- lifecycle events are used for ordering/supersession only;
- an exact carrier plan qualifies only after a later fresh postcondition observation;
- `Change: unset` intake remains compatible; and
- WIP, priority, finish-first, no-rewind, no-fallback, materialization, configuration, Action/Role/Result, and #218 boundaries remain unchanged.

Final gates for each exact implementation revision remain focused tests, full Python tests, Ruff check and format check, mypy, and strict OpenSpec validation. Independent semantic review is required after each material OpenSpec revision before the next stage is consumed.

## Delivery and continuation

Stage 1 is independently executable, testable, reviewable, mergeable, and deployable on current N-1. Its exit evidence is correlation-bearing formal application evidence plus preserved current acceptance. Stage 2 is the mandatory continuation and consumes that evidence on the then-current default branch. The existing `MORE_IMPLEMENTATION_REQUIRED` result records the continuation; no stage label, migration state, or alternate runtime path is added.
