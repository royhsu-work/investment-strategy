## Context

Current formalization is governed by #138 formal-correction Explore `issuecomment-5482546619` on `main@f8f2c49d255997889dcdd406cabd504f03367f07`. That result preserves the earlier root-cause evidence from `issuecomment-5474475020` without changing the approved architecture outcome. Human clarification `issuecomment-5475109024` makes #168 de-mailbox part of #138, permits bounded pre-acceptance Explore correction, and requires staged N-1 delivery. Human clarification `issuecomment-5477274582` establishes that exact-revision validation must self-host inside the repository-owned deterministic boundary: earlier formalization head `611157a43b9eb0c42345fa56ca93ebb0d524e2b8` produced OpenSpec Validate run `33380560988` with `conclusion=action_required` and no validator job, proving an execution-boundary deadlock rather than authority to relax the gate. Merged PR #185 deployed the first validator-bootstrap mechanism on `main`, but current implementation evidence shows that mechanism remains too source-action-specific for the required Stage 1A contract.

## Decisions

### 1. Minimum state and explicit merge phase

After cutover, normal routed state is `Issue + open/closed + immutable Change + exactly one Action`; Role is derived. Results/reviews/Human decisions are semantic evidence; transport/HANDOFF/history are not routing. Replace generic `merge-pr` with `merge-implementation-pr` and `merge-archive-pr`, both using the existing merge procedure Skill while preserving their distinct review/head/check/linkage/cleanup gates.

### 2. One executable machine authority

A small kernel owns Action vocabulary, Action->Role, finite result->transition/effect mappings, WIP/FIFO/debt classification, effect capabilities, source reauthorization, stale/replay handling and structural postconditions. Dispatch, application and tests consume it directly. `agents/workflow.md` becomes generated or mechanically verified presentation. AGENTS/roles/Skills retain shared protocol, role authority and semantic procedure without a competing executable transition table.

### 3. Typed semantic/application boundary

One authorized worker returns its source Issue/Action, bounded action-owned typed result, narrative/source evidence and bounded effect inputs. The worker cannot select arbitrary successors. Application validates the result, derives legal effects, fresh-reauthorizes source/effect predicates, mutates narrowly and fresh-observes postconditions. Meaning-dependent Explore/Human/OpenSpec/review/implementation judgments remain model-owned.

### 4. #168 run-scoped transport

Runtime check-in comments are request/trigger/audit only. Dispatch/application/validation results belong to the exact Actions run caused by the request and are consumed from that run-scoped surface. Exact request->run->structured-result correlation is mandatory. Missing, ambiguous, failed, cancelled, malformed or expired evidence fails closed; no response-comment fallback exists. Coordination-Issue semantic comments remain separate governed evidence.

### 5. Exact-revision validation is a gate-derived deterministic application resource

When the governed readiness contract requires exact-revision OpenSpec validation before ownership transfer, repository application must be able to obtain an exact-resource result for target revision `R` independently of a hard-coded source Role/Action whitelist. `R` may be the revision just produced by the current authorized OpenSpec mutation or an already-current Change/PR head that requires validation but no artifact rewrite. Application MUST NOT rewrite or dummy-touch an already-correct artifact merely to manufacture a mutation-triggered validator path.

The implementation may run pinned strict validation directly against `R` or explicitly trigger a dedicated deterministic validator bound to `R`; mechanism choice is implementation-owned. Accepted evidence must prove all of: target revision `R`; validator checkout `HEAD == R`; pinned OpenSpec compatibility is qualified; strict OpenSpec validation is PASS. The structured validation result belongs to the exact deterministic application/validation execution and is consumed by the already selected semantic Action. Missing, failed, cancelled, ambiguous, revision-mismatched, checkout-mismatched, malformed or expired evidence fails closed. Stale CI, `run.head_sha == R` without checkout proof, manual approval/operator workarounds, a direct connector write outside repository application, or another semantic Action/model wake cannot satisfy the gate.

This resource does not create a second orchestration plane: GitHub Actions remains deterministic-only and one-action-per-wake remains unchanged. A material `Lead / resolve-question` correction requiring exact-R readiness must be able to consume the same resource as `Lead / propose-change`; source Action identity can constrain semantic ownership, but MUST NOT suppress a readiness resource required by the governed gate.

### 6. One mapped Action per wake

Normal wake: fresh bootstrap -> exact dispatch -> one mapped Action -> deterministic application/postcondition/exact-resource consumption -> exit. No successor Action executes in that wake even when Role is unchanged. The selected Action remains internally work-conserving through immediately actionable RED->GREEN->REFACTOR->VERIFY, local correction and bounded exact-resource consumption. Same-role chaining, cross-role wake barriers, fresh-worker same-wake identity and continuation flags are deleted.

### 7. Bounded formalization correction

Before first independent semantic `review-openspec` acceptance, if Propose proves its Explore source/evidence/feasibility premise materially invalid, the executable contract may return the same Issue to `explore-change` even after provisional non-`unset` Change activation. Preserve Change identity, Proposal/PR history and audit evidence; this is not a scope reset or generic backward transition. After independent semantic acceptance, material correction uses `resolve-question` -> independent review.

### 8. Stale/replay and execution-boundary safety

Every consequence fresh-reads exact source state and effect-specific evidence. Already-satisfied legal postconditions are idempotent and never rewound. Recovery reconstructs actual completed mutations and causal descendants rather than replaying historical routing. Before consequential results/effects/ownership changes, direct-Human freshness/disposition remains the shared bounded provenance check and never grants separately Human-reserved authority. A just-triggered exact external resource may be boundedly re-observed inside the selected Action without permitting successor Action execution in that wake. Catchable failures retain canonical `EXECUTION_EXCEPTION` evidence and legal same-authority recovery while source routing/revision/preconditions remain current; no generic blocked/retry/fault state machine is added. Incompatible state, incomplete provenance, ambiguous transport or invalid exact-revision validation fails closed. Fresh read is not a mutex/CAS.

## Mandatory N-1 delivery

Each stage must be independently executable/testable/mergeable/deployable on N-1; otherwise split it. #138 completes only after stage 6 and full parent verification. Stage 1 is explicitly ordered: Stage 1A exact-revision application resource first, then Stage 1B transport de-mailbox. Stage 1A is the prerequisite for this materially revising Resolve action's eventual ownership transfer because the exact current handoff revision must be validatable without an artifact rewrite or source-action whitelist. Stage 1B remains mandatory before Stage 2 consumes run-scoped transport, but is not a prerequisite for semantic OpenSpec review readiness. A green but unmerged implementation proves buildability only; it is not deployed substrate and cannot substitute for exact-`R` validation evidence for the actual #178 handoff revision.

| Stage | Advances | Still incomplete | N-1 / boundary | Next |
| --- | --- | --- | --- | --- |
| 1A Exact-revision application resource | Gate-derived exact-R validation for both newly produced and already-current targets; checkout/compatibility/strict-PASS structured evidence consumable by the selected Action | Transport/kernel/state/wake unchanged | Current comment-trigger/application bridge and qualified pinned OpenSpec remain; no dummy-touch and no source-Action whitelist may be required to obtain the resource | 1B |
| 1B Transport de-mailbox | #168 run-scoped dispatch/application/validation results; no normal response comments | Kernel/state/wake unchanged | Stage 1A remains deployed; transport adapter changes only request/run/result carriage and may roll back without changing workflow semantics | 2 |
| 2 Kernel shadow | One executable topology computes shadow decisions | Old production control still owns effects | Stages 1A+1B carry shadow evidence and exact-revision resources; no mutation cutover | 3 |
| 3 Typed result/application | Typed result->kernel effect->fresh application | Wake and Role+Action state unchanged | Stage 2 equivalence proven on the Stage-1 closed loop; rollback before cutover | 4 |
| 4 Wake simplification | Exactly one mapped Action/wake | Canonical state still old | Stage 3 safely persists successor for later wake | 5 |
| 5 Canonical-state cutover | Action-only routing + explicit merge Actions | Legacy code/prose remains cleanup | Complete live-state plan; irreversible semantic cutover | 6 |
| 6 Deletion/context reduction | Removes superseded selectors/parsers/mailbox/continuation/model-host/prose | Parent outcome complete after full gates | Rollback translates from new state; never restores permanent second authority | Verify |

## Validation and deletion

Stage 1A tests cover both forms of the same readiness resource: (a) a live repository-owned OpenSpec write that produces exact revision `R`; and (b) an already-current exact Change/PR head `R` that needs validation with no artifact rewrite. Both must obtain structured deterministic evidence proving target `R`, validator checkout `R`, qualified pinned OpenSpec compatibility and strict PASS, and make that evidence consumable by the same selected Action. A focused regression must prove materially revising `Lead / resolve-question` cannot be excluded by a Propose-only resource whitelist. The current `action_required`/no-validator-job failure remains a required RED case, not an allowed bypass.

Stage 1B tests cover exact request->run->structured dispatch/application result correlation and no normal machine-response mailbox. Later tests cover exhaustive kernel topology, fresh application/stale/replay, one-action wake with internal work conservation, governance projection, complete live-state migration, full Python quality and exact-revision strict OpenSpec.

Final production removes normal `agent:*` routing, generic merge-phase inference, Issue-response result mailbox/history correlation, Markdown topology/effect parsing, same-wake successor/wake-barrier logic, obsolete historical compatibility, legacy Responses/model-worker host code and corresponding redundant tests/prose. Historical evidence remains readable but non-authoritative.
