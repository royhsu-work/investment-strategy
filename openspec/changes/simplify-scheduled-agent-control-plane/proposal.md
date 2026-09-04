## Why

#138 formalizes the architecture reset from the current same-Issue formal-correction Explore `issuecomment-5482546619` on `main@f8f2c49d255997889dcdd406cabd504f03367f07`. That result revalidates and preserves the earlier architecture evidence from `issuecomment-5474475020` while incorporating Human architecture clarifications `issuecomment-5475109024` and `issuecomment-5477274582`. The root cause is duplicated machine workflow ownership across routing labels, prose topology, history parsing, transport and wake orchestration; the latest correction also resolves the bounded feasibility question created by the execution-boundary deadlock where repository-owned OpenSpec mutation can create revision `R` without a runnable exact-`R` validator.

Required outcome: ChatGPT Scheduled Tasks are the only normal model wake; GitHub Actions run deterministic code only; no OpenAI/Responses/other model API worker. Repository code owns mechanical observation/dispatch/typed-result validation/effects/fresh reauthorization/postconditions and exact-revision deterministic validation resources; Lead/Reviewer/Executor retain semantic judgment. Reuse Change `simplify-scheduled-agent-control-plane` and PR #178.

## What Changes

- Canonical routing becomes one `action:*`; Role is derived. `Change:` remains formal identity; Issue open/closed remains lifecycle state. Results/reviews/Human decisions are evidence; HANDOFF/transport/history are audit.
- Replace generic `merge-pr` Action with `merge-implementation-pr` and `merge-archive-pr`.
- One executable kernel owns Action vocabulary, Action->Role, finite result/transition rules, WIP/FIFO/debt dispatch, effect capability, fresh authorization, stale/replay and postconditions. `agents/workflow.md` becomes generated/mechanically verified presentation, not a production-parsed DAG.
- Workers return bounded typed results plus evidence; application derives only kernel-legal effects and fresh-verifies source/effect predicates.
- One wake executes exactly one authorized mapped Action, work-conserving inside it, then exits after application. A successor always waits for later fresh dispatch.
- #168 is mandatory: runtime Issue comments are request/trigger/audit only. Normal dispatch/application/validation results belong to one exact Actions run and are consumed from its run-scoped surface. Exact request->run->result correlation is required; missing/multiple/failed/cancelled/malformed/expired evidence fails closed with no Issue-response fallback. Coordination-Issue semantic comments remain evidence.
- Repository-owned OpenSpec artifact mutation must self-host its exact-revision readiness dependency. After a consequential write creates exact revision `R`, the same selected semantic Action must be able to consume deterministic evidence proving target revision `R`, validator checkout `HEAD == R`, qualified pinned OpenSpec compatibility, and strict validation PASS before ownership transfer. The implementation may validate inside application or invoke a dedicated exact-`R` deterministic validator, but stale CI, `run.head_sha` without checkout proof, manual approval workarounds, direct connector bypass, or another model wake cannot satisfy the gate.
- Before first independent `review-openspec` acceptance, a material formalization defect in the Explore source/evidence/feasibility premise may return the same Issue to Explore after provisional non-`unset` activation while preserving Change, PR/artifact history, evidence and WIP. After acceptance, use resolve-question plus independent review.
- Preserve WIP=1, Human authority, completeness/provenance, role separation, exact-revision gates, semantic evidence, stale/concurrency fail-closed behavior and deterministic archive automation.
- Mandatory N-1 order: (1) transport de-mailbox/daily check-in plus exact-revision validation bootstrap, (2) kernel shadow, (3) typed result/application, (4) wake simplification, (5) Action-only/explicit-merge cutover, (6) deletion/context reduction. Stage 1 may be split into independently executable transport and validation-bootstrap slices, but both must be merged and deployed on the then-current N-1 before #178 may claim OpenSpec review readiness or any later stage may depend on repository-owned OpenSpec mutation. An unmerged or merely green maintenance implementation is evidence of buildability, not deployment or exact-`R` readiness evidence. Each stage states outcomes advanced/still incomplete, N-1 prerequisite, rollback/cutover boundary and continuation; split unsafe stages rather than weaken the parent.
- Completion deletes/disables superseded Role routing, response mailbox/history coupling, Markdown topology/effect parsing, same-wake continuation/wake barriers, obsolete compatibility hot paths, legacy Responses/model-worker host code and redundant machine-control prose/tests. No permanent dual control plane.

## Capabilities

### Modified Capabilities

- `scheduled-agent-workflow`: canonical state/routing, explicit merge Actions, run-scoped transport, self-hosted exact-revision validation, typed application, one-action-per-wake, bounded pre-acceptance Explore correction, staged cutover/deletion.
- `repository-governance`: executable kernel becomes the single machine-decidable workflow-semantics owner; Human-readable governance/Skills retain semantic ownership.

## Skill maintenance traceability

Current causal source for every entry: #138 formal-correction Explore `issuecomment-5482546619`; preserved upstream architecture evidence `issuecomment-5474475020`; Human clarifications `issuecomment-5475109024` and `issuecomment-5477274582`; Change `simplify-scheduled-agent-control-plane`.

| Skill | Class | Before / preserved responsibility | After / rationale / supersession |
| --- | --- | --- | --- |
| `openspec-explore` | Modified | Research/evidence, feasibility/materiality, Human boundary, Explore dispositions; also routing/continuation mechanics. | Preserve semantic Explore work; kernel/application supersede routing, successor and wake mechanics. |
| `openspec-change` | Modified | Proposal/spec/design/tasks, causal Explore verification, scope/contract, traceability/readiness; also application/routing mechanics. | Preserve Lead specification authority and exact-revision readiness; add approved pre-acceptance Explore correction; deterministic application/validation self-host the exact-revision resource while kernel/application supersede machine control. |
| `openspec-review` | Modified | Independent source-chain + reverse/forward semantic review, Skill/config checks and validation; also handoff mechanics. | Preserve independent PASS/FINDINGS and exact-target validation verification; kernel owns structural Action/successor selection. |
| `implementation` | Modified | Approved Apply context, RED-GREEN-REFACTOR-VERIFY, checkpoints, spec blockers; current continuation semantics. | Preserve implementation/testing/checkpoints inside `implement-change`; application ends the wake and supersedes successor execution. |
| `implementation-review` | Modified | Exact-head conformance/tests/gates/Skill trace and finding class; PASS -> generic merge. | Preserve exact-head independent gate; PASS feeds `merge-implementation-pr`; generic merge Action is superseded here. |
| `archive-review` | Modified | Exact Archive head/canonical/preparation/cleanup-retention gate; PASS -> generic merge. | Preserve Archive gate; PASS feeds `merge-archive-pr`; generic merge phase inference is superseded here. |
| `merge-pr` | Modified | Generic Action infers phase while enforcing exact PASS/head/check/linkage/native-closing/preparation/cleanup/Human safety. | Keep one shared merge procedure for two explicit merge Actions and all applicable safety gates; only generic Action identity/phase inference is superseded. |
| `lifecycle-finalize` | Modified | Post-merge lifecycle, archive automation/PR preparation, trackers/cleanup, terminal close; also finite routing details. | Preserve Lead lifecycle/archive/terminal judgment; kernel/explicit merge Actions supersede finite routing/continuation mechanics. |

No Skill is removed/replaced and no new Skill is added. `skill-creator` remains guidance only and is not materially modified. The generic `merge-pr` **Action** is superseded; the `merge-pr` Skill remains the shared merge procedure.

## Impact

Affected surfaces: shared governance, `agents/workflow.md`, the eight Skills above, message references, both capability specs, and dispatcher/runtime/worker/effect/transport/application/validation code plus production-boundary tests. Final production must have fewer independent control-state representations and executable decision paths than current `main`.

Refs #138
Refs #168
