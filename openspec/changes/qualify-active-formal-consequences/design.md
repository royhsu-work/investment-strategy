# Design: Qualify active formal consequences

## Decision boundary

The approved parent outcome remains:

```text
observable current evidence
+ explicit machine-decidable predicates
→ qualification by the existing executable owner of the consequence
→ consequence becomes eligible
```

The active-formal scheduled-agent provenance gap is one concrete P0 proof case. The durable Human correction issuecomment-5602555101 preserves that parent outcome while materially tightening correlation, staged activation, continuation-carrier, lifecycle-ordering, and artifact-freshness semantics. It supersedes earlier revision-bound acceptance for the changed meaning.

The current Change and its existing physical carrier remain the semantic vehicle. A later physical implementation carrier is allowed only as the same Change's replaceable work-product carrier after the Stage 1 merge boundary; it is not a second workflow, Change, state machine, or stage registry.

## Ownership and subtraction

`repository-governance` owns one generic invariant: an existing canonical executable owner evaluates one affirmative qualification predicate before a machine-decidable repository consequence becomes eligible. It defines ownership and use of the result only. It does not define scheduled-agent routing, `Change`, `ObservationProvenance`, Action/Result, transport, carrier, terminal, or workflow-specific evidence.

The existing scheduled-agent owners remain:

- `scheduled_agent_runtime.py` and `workflow_dispatch.py` for fresh current-state reconstruction and dispatch input;
- `scheduled_agent_action_model.py` for the finite Action/Role/Result vocabulary, legal transitions, and model-derived successor;
- `scheduled_agent_effects.py` and the application bridge for fresh application authorization, existing formal evidence, and durable effect postconditions;
- GitHub Issue snapshots and lifecycle events for observable current evidence and ordering/supersession only; and
- the existing CarrierRequired plan for replaceable carrier execution.

The correction reuses these owners. It does not add a provenance framework, state registry, ledger, cursor, lease, retry state, receipt lifecycle, policy engine, carrier type, or competing authority.

## Stage 1 — produce correlation-bearing formal evidence and continuation capability

Stage 1 is the N-1 producer boundary. The existing application receives an exact worker Action/Result, fresh-authorizes the current Issue/Change/Action and default-branch revision, derives the legal successor from the finite model, and observes the durable effect postcondition.

Stage 1 must add the minimum application-owned correlation to existing formal evidence. The correlation is mandatory and must make this chain uniquely reconstructable:

```text
accepted Action / Result
→ exact repository application authorization
→ model-derived routing or terminal consequence
→ exact durable postcondition
```

Stage 1 must also provide the minimum existing-owner continuation-carrier capability needed after the Stage 1 implementation carrier is merged. After the existing review and merge Actions, `finalize-change` returns `MORE_IMPLEMENTATION_REQUIRED`; a later fresh wake may then materialize a fresh Stage 2 carrier from the then-current default branch through the same Change/Issue/application boundary.

Stage 1 keeps current acceptance compatible. It does not deploy the Stage 2 consumer, introduce a stage state, or treat a same-Action `MORE_IMPLEMENTATION_REQUIRED` result as a default-branch activation boundary.

## Stage 2 — consume qualification at existing boundaries

Stage 2 extends the existing current-state reconstruction and dispatch/application owners to consume:

1. the current Issue/Change/routing or terminal observation;
2. a complete relevant lifecycle observation;
3. the latest applicable correlation-bearing formal evidence for the same Issue and immutable Change;
4. the exact accepted Action/Result and application authorization binding;
5. the model-derived successor or terminal effect; and
6. the exact durable postcondition.

Lifecycle events establish the order of relevant mutations and identify later supersession or ABA. They are not authorization. Actor, timestamp, connector, carrier, and value equality remain descriptive or structural evidence only. If the relevant lifecycle observation is incomplete, contradictory, stale, or cannot establish a unique current binding, the owner returns `INDETERMINATE` and the existing fail-closed boundary applies.

The late formal equality shortcut is removed when the Stage 2 qualified path is consumed. Current equality can support an idempotent observation after qualification, but cannot establish qualification. No second predicate is retained as a competing authority.

## Latest transition and ABA

The current value is not provenance identity:

```text
T1 repository-authorized transition A → B
T2 out-of-band mutation B → C
T3 out-of-band mutation C → B
fresh current state == B
```

Lifecycle evidence establishes that T2/T3 are later relevant mutations. T1's correlation therefore cannot qualify the fresh B. The owner must find a later applicable repository-authorized correlation and exact postcondition for the current B; otherwise the observation is `INDETERMINATE`.

## Evidence reuse and minimum representation

Reuse, in order:

- existing formal Action/Result, review, and merge evidence;
- application authorization against the then-current default-branch revision;
- the finite Action/Role/Result transition derivation;
- current Issue and terminal postcondition observations;
- complete lifecycle events for ordering and supersession/ABA; and
- the existing CarrierRequired plan and later ref/PR/terminal postcondition.

Application-owned correlation is required. The implementation may choose only the minimum field or identity representation inside existing formal evidence that makes the chain unique. If existing evidence cannot do so, add only that minimum representation; do not create a registry, ledger, cursor, workflow state, receipt lifecycle, second protocol, or generic provenance service.

## No-delta dispositions

| Boundary | Disposition |
| --- | --- |
| First Change materialization | Existing Lead / propose-change application path remains the owner; exact validation and postconditions remain mandatory. |
| Continuation carrier | Reuse the existing content-addressed materialization and CarrierRequired boundary; add only the minimum capability needed to bind a fresh post-merge carrier to the same Issue/Change. |
| Change: unset intake | Existing Explore/Propose pre-activation contract remains. |
| Carrier execution | Existing CarrierRequired boundary and immutable plan remain; carrier identity is not authority. |
| OpenSpec authoring guidance | Current `openspec/config.yaml` remains the owner; no delta is required. |
| Action/Role/Result model | Existing finite model remains sole executable owner; no new vocabulary. |
| #218 | Downstream boundary remains unchanged and out of scope. |

## Verification boundary

Stage 1 must prove:

- new repository application transitions produce mandatory application-owned correlation in existing formal evidence;
- the correlation binds accepted Action/Result, application authorization, model-derived consequence, and exact durable postcondition;
- current acceptance behavior remains compatible;
- the minimum continuation-carrier capability can establish a fresh Stage 2 carrier from the then-current default branch after Stage 1 merge; and
- no new workflow state, protocol, registry, or permanent legacy fallback is introduced.

Stage 2 must prove:

- one qualified repository-owned active route or terminal boundary is accepted;
- a connector/out-of-band route or close without the application chain is `INDETERMINATE` and fails closed;
- equality without a current application binding is not qualification;
- incomplete lifecycle observation is `INDETERMINATE`;
- the ABA sequence cannot inherit T1 qualification;
- lifecycle events are used for ordering/supersession only;
- an exact carrier plan qualifies only after the later fresh postcondition observation;
- `Change: unset` intake remains compatible; and
- WIP, priority, finish-first, no-rewind, no-fallback, materialization, configuration, Action/Role/Result, and #218 boundaries remain unchanged.

Final gates for each exact implementation revision remain focused tests, full Python tests, Ruff check and format check, mypy, and strict OpenSpec validation. Independent semantic review is required after each material OpenSpec revision before the next stage is consumed.

## Delivery and continuation

The Change has two delivery stages, not two workflow states. Stage 1 crosses the existing implementation review, merge, and finalization lifecycle. `MORE_IMPLEMENTATION_REQUIRED` preserves the mandatory Stage 2 continuation. A later fresh wake uses the existing application/materialization owner to establish a new physical carrier from the then-current default branch, while preserving the same Issue, immutable Change, exact authorization, and postcondition boundaries.
