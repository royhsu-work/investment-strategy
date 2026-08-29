## 1. Slice: make current routing the only pre-activation operational selection state

- [ ] 1.1 RED — add production-boundary regressions proving that, with no formal workflow or routing debt, an older coherent `Lead / propose-change + Change: unset` Issue wins over a newer Explore by `created_at`/Issue number without requiring historical comment/event eligibility reconstruction.
- [ ] 1.2 RED — prove that duplicate or irrelevant Markdown fields such as an additional `- Workflow:` in prior comments cannot remove a current Propose tuple from the pre-activation candidate set.
- [ ] 1.3 GREEN — remove `preactivation_eligible` from dispatcher/runtime observation contracts and make both coherent unset Explore and unset Propose routing participate directly in the common pre-activation FIFO.
- [ ] 1.4 GREEN — remove the normal global `_apply_propose_preactivation_eligibility()` acquisition path and any comment/event reads used solely to authorize an already-current Propose tuple for queue participation.
- [ ] 1.5 REFACTOR — delete dead eligibility/parser/admission plumbing that no longer belongs upstream of the mapped-action boundary; do not replace it with origin/provenance/readiness state.
- [ ] 1.6 VERIFY — run targeted dispatcher/runtime tests plus existing invalid-routing, incomplete-enumeration, multiple-formal-workflow, closed-routing-debt, and stale-state regressions.

## 2. Slice: retain Propose semantic evidence at the selected action and remove direct-Propose intake

- [ ] 2.1 RED — add a regression where an older current Propose tuple is selected but its required same-Issue Explore `PROPOSAL_READY` semantic baseline is missing/ambiguous; prove the action fails/retains that Issue and later queued work is not selected as fallback.
- [ ] 2.2 RED — add regressions proving normal Human direct-Propose admission is absent while advisory admission, `HUMAN_DECISION_REQUIRED` answer/resume, Human-input freshness, and other still-governed Human predicates continue to work.
- [ ] 2.3 GREEN — make Propose reconstruct and validate the exact same-Issue durable Explore `PROPOSAL_READY` baseline as an action-local activation precondition, preserving still-applicable scope, constraints, exclusions, feasibility evidence, and selected direction.
- [ ] 2.4 GREEN — remove direct-Propose governance/runtime/Skill branches and direct-Propose-only Human-authority decision-ref/helper code that becomes unreachable; do not weaken independent Human-reserved mechanisms.
- [ ] 2.5 GREEN — preserve Reviewer upstream semantic traceability to the exact Explore baseline without using that evidence as dispatcher state.
- [ ] 2.6 REFACTOR — remove obsolete direct-Propose fallback/review exceptions and keep one normal intake story: routed Explore → `PROPOSAL_READY` → Propose.
- [ ] 2.7 VERIFY — run targeted Propose/Human-authority/review regressions and confirm an out-of-band coherent Propose tuple is operationally selectable but cannot activate without required semantic evidence.

## 3. Slice: make Explore dispositions structured and derive their effects in repository application

- [ ] 3.1 RED — add worker/application regressions for the exact structured Explore result vocabulary: `PROPOSAL_READY`, `HUMAN_DECISION_REQUIRED`, `NO_CHANGE_REQUIRED`, and `NO_GO`.
- [ ] 3.2 RED — prove `PROPOSAL_READY` deterministically derives same-Issue `Lead / propose-change` routing and that a worker-supplied conflicting/arbitrary successor cannot override the result-derived effect.
- [ ] 3.3 RED — prove narrative `result_content` containing additional `Workflow:`, `Action:`, or `Result:`-looking prose cannot redefine the structured result/effect.
- [ ] 3.4 GREEN — extend the worker/application result contract so the bounded Explore disposition is transported as validated structured data while narrative content remains audit/traceability evidence.
- [ ] 3.5 GREEN — derive Explore effects from freshly reauthorized `Lead / explore-change` plus the bounded result: Propose routing, existing Human escalation retention, or existing terminal research close/routing retirement.
- [ ] 3.6 GREEN — reject worker-chosen Explore routing transitions when repository result-derived application owns the successor/effect; continue validating legal successors against current default-branch topology.
- [ ] 3.7 REFACTOR — keep result-derived behavior action-local to Explore and remove any accidental generic workflow-engine abstraction or duplicate topology registry.
- [ ] 3.8 VERIFY — run targeted worker/effects/application tests for all four dispositions, stale-source reauthorization, fresh routing postconditions, and redispatch behavior.

## 4. Slice: align authoritative governance and complete cross-boundary regression coverage

- [ ] 4.1 RED — add governance/spec regression checks that fail while default-branch-compatible surfaces still describe normal Human direct-Propose admission, Propose queue eligibility by semantic reconstruction, or worker-selected Explore successors.
- [ ] 4.2 GREEN — align the approved implementation surfaces that genuinely own changed behavior: shared dispatch/Human-authority governance, workflow topology where Explore result effects are described, Lead role/Explore/Propose procedures, and canonical workflow-message guidance only where its presentation contract assumes worker-chosen routing.
- [ ] 4.3 GREEN — preserve explicit separation between current routing state and durable semantic evidence so no governance text instructs dispatch to parse historical LLM prose for current queue eligibility.
- [ ] 4.4 GREEN — preserve #137's evidence-backed `PROPOSAL_READY`/Propose revalidation intent at the action boundary; keep #138 as the broader executable-governance inventory and #168/#169 in their separate ownership scopes.
- [ ] 4.5 VERIFY — run the full relevant Python test suite and repository quality checks, with no OpenAI API/model-call fallback, label-writer provenance gate, hidden admission token, lock/lease/heartbeat/retry state, or second workflow DAG introduced.
- [ ] 4.6 VERIFY — run strict OpenSpec validation on the exact implementation revision and verify the approved proposal/spec/design/tasks traceability remains intact before implementation review.

## 5. Deployment and migration verification

- [ ] 5.1 VERIFY — after the implementation is merged and the new default-branch contract is authoritative, restore/reconstruct the temporarily parked #168/#169 only from their preserved current Issue evidence and the new dispatcher rules; do not manufacture a new provenance/admission token.
- [ ] 5.2 VERIFY — prove a restored coherent #168 Propose tuple participates in ordinary pre-activation FIFO directly from current routing while its Propose action still enforces the exact Explore semantic baseline.
- [ ] 5.3 VERIFY — confirm the one-time Human administrative sequencing override used to prioritize #175 is not encoded as a normal dispatcher priority or reusable bypass mechanism.