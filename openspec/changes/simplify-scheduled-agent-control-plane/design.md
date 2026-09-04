## Context

Current formalization is governed by #138 formal-correction Explore `issuecomment-5482546619` on `main@f8f2c49d255997889dcdd406cabd504f03367f07`. That result preserves the earlier root-cause evidence from `issuecomment-5474475020` and resolves the bounded Stage -1B feasibility gap without changing the approved architecture outcome: repository application can explicitly dispatch an exact-`R` validator using the existing deterministic GitHub Actions substrate. Human clarification `issuecomment-5475109024` adds #168 de-mailbox, bounded pre-acceptance Explore correction and mandatory N-1 order. Human clarification `issuecomment-5477274582` establishes that exact-revision validation must self-host inside the repository-owned deterministic boundary: earlier formalization head `611157a43b9eb0c42345fa56ca93ebb0d524e2b8` produced OpenSpec Validate run `33380560988` with `conclusion=action_required` and no validator job, proving an execution-boundary deadlock rather than authority to relax the gate.

## Decisions

### 1. Minimum state and explicit merge phase

After cutover, normal routed state is `Issue + open/closed + immutable Change + exactly one Action`; Role is derived. Results/reviews/Human decisions are semantic evidence; transport/HANDOFF/history are not routing. Replace generic `merge-pr` with `merge-implementation-pr` and `merge-archive-pr`, both using the existing merge procedure Skill while preserving their distinct review/head/check/linkage/cleanup gates.

### 2. One executable machine authority

A small kernel owns Action vocabulary, Action->Role, finite result->transition/effect mappings, WIP/FIFO/debt classification, effect capabilities, source reauthorization, stale/replay handling and structural postconditions. Dispatch, application and tests consume it directly. `agents/workflow.md` becomes generated or mechanically verified presentation. AGENTS/roles/Skills retain shared protocol, role authority and semantic procedure without a competing executable transition table.

### 3. Typed semantic/application boundary

One authorized worker returns its source Issue/Action, bounded action-owned typed result, narrative/source evidence and bounded effect inputs. The worker cannot select arbitrary successors. Application validates the result, derives legal effects, fresh-reauthorizes source/effect predicates, mutates narrowly and fresh-observes postconditions. Meaning-dependent Explore/Human/OpenSpec/review/implementation judgments remain model-owned.

### 4. #168 run-scoped transport

Runtime check-in comments are request/trigger/audit only. Dispatch/application/validation results belong to the exact Actions run caused by the request and are consumed from that run-scoped surface. Exact request->run->structured-result correlation is mandatory. Missing, ambiguous, failed, cancelled, malformed or expired evidence fails closed; no response-comment fallback exists. Coordination-Issue semantic comments remain separate governed evidence.

### 5. Exact-revision validation is a deterministic application resource

When repository-owned application changes OpenSpec artifacts and the selected semantic Action requires exact-revision validation before ownership transfer, the write produces exact revision `R` and the same deterministic application/control-plane boundary must provide an exact-resource result for `R`. The implementation may run pinned strict validation directly after mutation/postcondition or explicitly trigger a dedicated deterministic validator bound to `R`; mechanism choice is implementation-owned.

Accepted evidence must prove all of: target revision `R`; validator checkout `HEAD == R`; pinned OpenSpec compatibility is qualified; strict OpenSpec validation is PASS. The structured validation result belongs to the exact deterministic application/validation execution and is consumed by the already selected semantic Action. Missing, failed, cancelled, ambiguous, revision-mismatched, checkout-mismatched, malformed or expired evidence fails closed. Stale CI, `run.head_sha == R` without checkout proof, manual approval/operator workarounds, a direct connector write outside repository application, or another semantic Action/model wake cannot satisfy the gate.

This resource does not create a second orchestration plane: GitHub Actions remains deterministic-only and one-action-per-wake remains unchanged.

### 6. One mapped Action per wake

Normal wake: fresh bootstrap -> exact dispatch -> one mapped Action -> deterministic application/postcondition/exact-resource consumption -> exit. No successor Action executes in that wake even when Role is unchanged. The selected Action remains internally work-conserving through immediately actionable RED->GREEN->REFACTOR->VERIFY, local correction and bounded exact-resource consumption. Same-role chaining, cross-role wake barriers, fresh-worker same-wake identity and continuation flags are deleted.

### 7. Bounded formalization correction

Before first independent semantic `review-openspec` acceptance, if Propose proves its Explore source/evidence/feasibility premise materially invalid, the executable contract may return the same Issue to `explore-change` even after provisional non-`unset` Change activation. Preserve Change identity, Proposal/PR history and audit evidence; this is not a scope reset or generic backward transition. After independent semantic acceptance, material correction uses `resolve-question` -> independent review.

### 8. Stale/replay and execution-boundary safety

Every consequence fresh-reads exact source state and effect-specific evidence. Already-satisfied legal postconditions are idempotent and never rewound. Recovery reconstructs actual completed mutations and causal descendants rather than replaying historical routing. Before consequential results/effects/ownership changes, direct-Human freshness/disposition remains the shared bounded provenance check and never grants separately Human-reserved authority. A just-triggered exact external resource may be boundedly re-observed inside the selected Action without permitting successor Action execution in that wake. Catchable failures retain canonical `EXECUTION_EXCEPTION` evidence and legal same-authority recovery while source routing/revision/preconditions remain current; no generic blocked/retry/fault state machine is added. Incompatible state, incomplete provenance, ambiguous transport or invalid exact-revision validation fails closed. Fresh read is not a mutex/CAS.

## Mandatory N-1 delivery

Each stage must be independently executable/testable/mergeable/deployable on N-1; otherwise split it. #138 completes only after stage 6 and full parent verification. The Stage 1 exact-revision validation-bootstrap sub-slice is also a prerequisite for this Propose action's eventual ownership transfer: it must be merged and deployed on then-current N-1 before #178 can claim `READY_FOR_OPENSPEC_REVIEW`. A green but unmerged bootstrap implementation proves buildability only; it is not deployed substrate and cannot substitute for exact-`R` validation evidence for the actual #178 handoff revision.

| Stage | Advances | Still incomplete | N-1 / boundary | Next |
| --- | --- | --- | --- | --- |
| 1 Transport de-mailbox + exact-revision validation bootstrap | Run-scoped dispatch/application/validation results; no normal response comments; closed loop `repository-owned write -> exact resulting revision R -> exact-R deterministic validation -> structured consumable result` | Kernel/state/wake unchanged | Current comment-trigger/application bridge remains. Stage 1 may split into independently deployable transport and validation-bootstrap slices, but both must land before later stages depend on repository-owned artifact mutation; rollback restores only the N-1 transport/validation substrate | 2 |
| 2 Kernel shadow | One executable topology computes shadow decisions | Old production control still owns effects | Stage 1 carries shadow evidence and can validate exact artifact revisions; no mutation cutover | 3 |
| 3 Typed result/application | Typed result->kernel effect->fresh application | Wake and Role+Action state unchanged | Stage 2 equivalence proven on the Stage-1 closed loop; rollback before cutover | 4 |
| 4 Wake simplification | Exactly one mapped Action/wake | Canonical state still old | Stage 3 safely persists successor for later wake | 5 |
| 5 Canonical-state cutover | Action-only routing + explicit merge Actions | Legacy code/prose remains cleanup | Complete live-state plan; irreversible semantic cutover | 6 |
| 6 Deletion/context reduction | Removes superseded selectors/parsers/mailbox/continuation/model-host/prose | Parent outcome complete after full gates | Rollback translates from new state; never restores permanent second authority | Verify |

## Validation and deletion

Tests cover the live run-scoped transport E2E and, before later artifact-mutation-dependent stages, a live repository-owned OpenSpec write that produces exact revision `R`, obtains structured exact-run validation evidence proving target `R`, validator checkout `R`, qualified pinned OpenSpec compatibility and strict PASS, then consumes that evidence inside the same selected Action. Tests also cover exhaustive kernel topology, fresh application/stale/replay, one-action wake with internal work conservation, governance projection, complete live-state migration, full Python quality and exact-revision strict OpenSpec. The current `action_required`/no-validator-job failure is a required RED case, not an allowed bypass.

Final production removes normal `agent:*` routing, generic merge-phase inference, Issue-response result mailbox/history correlation, Markdown topology/effect parsing, same-wake successor/wake-barrier logic, obsolete historical compatibility, legacy Responses/model-worker host code and corresponding redundant tests/prose. Historical evidence remains readable but non-authoritative.
