## Why

#138’s exact Explore baseline is `issuecomment-5474475020` on `main@2eb17faa57248ed8218d6ccd47441837268e51e9`; Human clarification `issuecomment-5475109024` is additional durable scope. Together they identify duplicated workflow-state-machine ownership as the patch-spiral root cause and require #168 run-scoped transport, N-1 delivery, and a bounded pre-independent-acceptance return to Explore even after provisional non-`unset` Change activation.

ChatGPT Scheduled Tasks are the only normal model wake. GitHub Actions run deterministic code only; no OpenAI/Responses/other model API worker. Repository code owns mechanical observation/dispatch/result validation/transition/effects/postconditions; Lead/Reviewer/Executor retain semantic judgment. Reuse Change `simplify-scheduled-agent-control-plane` and PR #178.

## What Changes

- Canonical current routing is one `action:<action>` dimension; Role is derived. `Change:` remains formal identity and Issue open/closed lifecycle state. Results/reviews/Human decisions are evidence; HANDOFF/transport/history are audit/provenance.
- Replace generic `merge-pr` with `merge-implementation-pr` and `merge-archive-pr`.
- One executable topology/kernel is the machine SSOT for Action vocabulary, Action→Role, finite results/transitions, WIP/FIFO/debt dispatch, effect capabilities, fresh reauthorization, stale/replay handling and postconditions. `agents/workflow.md` becomes generated/mechanically verified presentation, not a production-parsed second DAG.
- Workers return bounded typed results plus narrative/source evidence; application derives legal effects rather than re-extracting control from Markdown.
- One wake executes exactly one authorized mapped Action. Work remains work-conserving inside it; after application, the wake ends and a later wake fresh-dispatches.
- #168 transport is mandatory: runtime Issue comments are request/trigger/audit only; normal dispatch/application results belong to one exact Actions run and are consumed from its run-scoped surface. Exact request→run→result correlation is required; missing/multiple/failed/cancelled/malformed/expired evidence fails closed with no Issue-response fallback. Coordination-Issue semantic comments remain governed evidence.
- Before independent `review-openspec` acceptance, a material formalization defect in the Explore source/evidence/feasibility premise may route the same Issue back to `explore-change` after provisional non-`unset` activation while preserving Change identity, Proposal/PR history and audit evidence. After independent semantic acceptance, use the formal resolve/review loop.
- Preserve WIP=1, completeness/provenance, Human authority, exact-revision gates, role separation, semantic evidence, stale/concurrency fail-closed behavior and deterministic archive automation.
- Mandatory N-1 order: (1) transport de-mailbox/daily check-in, (2) kernel shadow, (3) typed result/application, (4) wake simplification, (5) Action-only/explicit-merge cutover, (6) deletion/context reduction. Each stage states outcomes advanced, remaining incomplete, N-1 prerequisite, rollback/cutover boundary and continuation; split unsafe stages further rather than weaken the parent.
- Completion retires Role-label normal routing, response-mailbox/history coupling, Markdown topology/effect parsing, same-wake continuation/wake barriers, obsolete history compatibility, legacy Responses/model-worker host code and redundant machine-control prose/tests. No permanent dual control plane.

## Capabilities

### Modified Capabilities

- `scheduled-agent-workflow`: state/routing, explicit merge Actions, run-scoped transport, typed application, one-action-per-wake, bounded pre-acceptance Explore correction, staged cutover/deletion.
- `repository-governance`: executable topology/kernel becomes the single machine-decidable workflow-semantics owner; Human-readable governance/Skills keep semantic ownership without competing transition tables.

## Skill maintenance traceability

Source for all entries: #138 `issuecomment-5474475020`, Human clarification `issuecomment-5475109024`, Change `simplify-scheduled-agent-control-plane`.

| Skill | Class | After / rationale / supersession |
| --- | --- | --- |
| `openspec-explore` | Modified | Keep research/evidence/materiality/disposition; consume executable routing/result boundaries. |
| `openspec-change` | Modified | Keep authoring/traceability; add bounded pre-acceptance Explore correction; remove machine routing/mailbox/continuation duplication. |
| `openspec-review` | Modified | Keep independent semantic review; consume machine structural entry/next-Action facts. |
| `implementation` | Modified | Keep RED→GREEN→REFACTOR→VERIFY/checkpoints; end after one applied Action. |
| `implementation-review` | Modified | Keep exact-head acceptance; PASS targets explicit implementation-merge Action. |
| `archive-review` | Modified | Keep exact-head Archive review; PASS targets explicit archive-merge Action; generic phase inference is superseded. |
| `merge-pr` | Modified | Keep one merge procedure Skill mapped from two explicit merge Actions; generic Action identity is superseded. |
| `lifecycle-finalize` | Modified | Keep lifecycle/terminal judgment; consume executable successors and one-action boundary. |

No listed Skill is replaced; only the generic `merge-pr` Action identity is superseded. No new Skill is added; `skill-creator` remains guidance only.

## Impact

Affected surfaces: shared governance, `agents/workflow.md`, the eight Skills above, relevant message references, both capability specs, and dispatcher/runtime/worker/effect/transport code plus production-boundary tests. The final state must have fewer independent control-state representations and executable decision paths than current `main`.

Refs #138
Refs #168
