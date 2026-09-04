## Why

Production Scheduled-Agent dispatch can currently remove an already-routed `Lead / propose-change + Change: unset` Issue from the pre-activation queue before FIFO ordering by re-reading and re-parsing prior LLM-authored `ACTION_RESULT` prose. #168 → #169 and the earlier #161 → #168 recurrence show that an older Issue can already have current Propose routing yet a later Explore is authorized. This makes historical prose reconstruction act like workflow state even though current GitHub routing is intended to be the operational state.

The fix must reduce control-plane interpretation rather than add another parser/provenance layer. The Human-established direction for #175 is to make current coherent routing canonical for dispatch, remove Human direct-Propose as a normal intake path, keep semantic evidence checks action-local, and make deterministic repository application derive Explore successor effects from a bounded result code without introducing another model call or workflow engine.

The Human subsequently clarified a second invariant exposed while implementing #175: action-local semantic evidence cannot merely exist as an Explore result; every material Explore claim that affects disposition, scope, constraints, feasibility, or selected direction must be traceable to identified source evidence, and Propose must independently verify that source/evidence chain before formal activation. If that chain is incomplete but the same bounded problem remains researchable without a new Human-reserved decision, the legal correction is the same Issue back to `Lead / explore-change` with `Change: unset`; queue ownership is preserved and dispatch must not leapfrog to a later Issue. Reviewer independently verifies the durable source → Explore → OpenSpec chain without re-running Explore or reconstructing undocumented conversation intent.

Authoritative original Explore baseline: #175 `ACTION_RESULT(PROPOSAL_READY)` comment `5461100685`, produced from current `main` revision `a0a30a9d87d420d23e04a04b656d39f6e1e037c7`. Material correction evidence is #175 `SPEC_BLOCKER` comment `5464300806` plus the Human-confirmed correction summarized there; that blocker supersedes the earlier interpretation that semantic failure must retain the Propose action.

## What Changes

- Remove `preactivation_eligible` and the global Propose admission/readiness reconstruction that reads Issue comments/events before FIFO selection.
- Define pre-activation operational selection from current coherent `Lead / explore-change + Change: unset` and `Lead / propose-change + Change: unset` routing, using the existing GitHub `created_at` then Issue-number ordering after formal-work and routing-debt handling.
- Remove Human direct-Propose as a normal workflow/admission path. Normal formal intake becomes routed Explore → bounded `PROPOSAL_READY` → Propose, while genuine `HUMAN_DECISION_REQUIRED`, advisory admission, Human-input freshness, and other Human-reserved boundaries remain unchanged.
- Strengthen Explore's semantic evidence contract: every material claim used to determine disposition, scope, constraints, feasibility, or selected direction must identify its supporting source/evidence and distinguish source fact/evidence from Lead interpretation/inference and unresolved questions. Unsupported material inference cannot establish `PROPOSAL_READY`; feasibility assertions require evidence appropriate to the claim rather than model confidence.
- Keep the exact durable Explore result as action-local semantic input for Explore-originated Propose, but require Propose to independently/reversely verify the material source → Explore conclusion chain and feasibility sufficiency before formalization. `PROPOSAL_READY` is not permission to blindly formalize.
- When pre-activation Propose finds the Explore source/evidence/feasibility chain incomplete, unsupported, stale, ambiguous, or contradictory but the same bounded problem remains researchable without a new Human-reserved decision, route the same Issue back to `Lead / explore-change` with `Change: unset`. This is a legal same-Issue semantic correction, not dispatcher fallback; the Issue retains its original queue identity and a later Issue must not leapfrog solely because more research is required.
- Keep genuine Human-reserved discoveries at the existing Human decision boundary. Once a non-`unset` Change identity exists, do not use the pre-Change Explore correction path; material semantic corrections continue through `Lead / resolve-question` and independent review.
- Strengthen `Reviewer / review-openspec` to independently verify the durable source/evidence → Explore conclusion → Proposal/Specs/Design/Tasks chain for material claims, while still not re-running Explore or inferring undocumented Human intent. Reviewer remains a downstream independent gate and does not substitute for Propose's pre-activation revalidation.
- Carry the four governed Explore dispositions — `PROPOSAL_READY`, `HUMAN_DECISION_REQUIRED`, `NO_CHANGE_REQUIRED`, and `NO_GO` — as bounded structured worker results rather than reconstructing the machine result from free-form Markdown.
- Make repository application derive Explore routing/terminal effects from the freshly authorized source action plus the bounded result. The worker no longer chooses an arbitrary successor routing tuple for Explore.
- Preserve WIP=1/finish-first, complete authoritative GitHub reconstruction, routing-debt handling, structural routing validation, Change immutability, exact-revision gates, role separation, and existing fail-closed behavior.
- Keep the result-derived mechanism and evidence-chain correction bounded to the demonstrated Explore/Propose boundary. This Change does not add a `review-explore` action or generic evidence framework; #138 remains the owner of any broader executable-governance inventory.

## Capabilities

### Modified Capabilities

- `scheduled-agent-workflow`: make current routing the pre-activation operational selection state; remove direct-Propose admission; require source-backed Explore results, Propose source/feasibility revalidation with a same-Issue Explore correction loop, independent source → Explore → OpenSpec review traceability, and bounded structured Explore result → repository-owned effect derivation.

## Skill maintenance traceability

Source/change reference for all entries below: #175 original Explore result `5461100685`, material correction blocker `5464300806`, and Change `canonicalize-routing-and-explore-results`.

- **Modified — `agents/skills/openspec-explore/SKILL.md`**
  - Responsibility before: Lead owns bounded Explore judgment and returns one governed disposition plus worker-requested routing/terminal effects; the Skill also carries the direct-Propose fallback/preserved-authority path.
  - Responsibility after: Lead still owns semantic Explore judgment and durable narrative evidence, but every material decision-affecting claim must identify its supporting source/evidence and separate evidence from interpretation/inference and unresolved questions. `PROPOSAL_READY` requires a reconstructable evidence-backed direction. Lead returns one bounded structured Explore disposition; repository application derives the governed successor/terminal effect from the authorized source action plus that disposition. Normal direct-Propose fallback language is removed, while a later same-Issue correction from Propose may legally route back into Explore for additional research before activation.
  - Rationale: prevent unsupported Explore interpretation from becoming formal contract while removing arbitrary worker-selected successor control state and the legacy direct-Propose special path.
  - Replacement/supersession: no replacement Skill; the same Skill retains Explore procedure ownership with stronger evidence traceability and narrower effect-selection authority.

- **Modified — `agents/skills/openspec-change/SKILL.md`**
  - Responsibility before: Propose supports both provenance-bound Human direct-to-Propose and Explore-originated entry, including direct-Propose fallback to Explore and special combined-queue admission handling.
  - Responsibility after: normal Propose formalization consumes the exact same-Issue durable `PROPOSAL_READY` Explore result and independently/reversely verifies the material source/evidence and feasibility basis behind the proposed meaning. If that basis is incomplete but researchable within the same bounded problem and no new Human-reserved decision is required, pre-activation Propose requests a same-Issue route to `Lead / explore-change` with `Change: unset`; it does not activate a Change and does not release queue ownership to a later Issue. Direct-Propose admission/fallback branches are removed. After Change activation, material corrections remain on the formal `resolve-question` path rather than returning to pre-Change Explore.
  - Rationale: keep semantic readiness at the mapped Propose boundary, preserve the Human-required research correction loop, and prevent historical prose/Human-admission reconstruction from becoming global dispatcher eligibility.
  - Replacement/supersession: no replacement Skill; direct-Propose-only procedure is removed rather than moved elsewhere.

- **Modified — `agents/skills/openspec-review/SKILL.md`**
  - Responsibility before: Reviewer verifies Explore-result preservation for Explore-originated Changes but also carries an explicit valid direct-to-Propose exception that requires no synthetic Explore result.
  - Responsibility after: Reviewer independently verifies the durable material source/evidence → Explore conclusion → Proposal/Specs/Design/Tasks chain before its ordinary reverse-first/forward semantic gate. Reviewer does not re-run Explore, reconstruct conversation history, or infer undocumented Human intent; it verifies the sources and traceability declared by the governed artifacts/result. The direct-to-Propose exception is removed with the normal direct-Propose path.
  - Rationale: prevent an unsupported Explore interpretation from being legitimized merely because downstream OpenSpec artifacts preserve it faithfully, while retaining Reviewer independence and bounded responsibility.
  - Replacement/supersession: no replacement Skill; independent review ownership remains unchanged and no `review-explore` action is added.

No repository Skill is added or removed by this Change. `skill-creator` is composition guidance consumed while specifying these modifications and is not itself a modification target.

## Impact

Expected implementation surfaces include shared workflow governance and Lead procedures, canonical `scheduled-agent-workflow` requirements, `workflow_dispatch.py`, `scheduled_agent_runtime.py`, `scheduled_agent_worker.py`, `scheduled_agent_effects.py`, direct-Propose-only Human-authority helpers that become dead, and production-boundary regression tests.

The corrected semantic target requires rework of the previously checkpointed Slice 2 semantics and invalidates the earlier `review-openspec` PASS for the superseded meaning. Slice 1's routing/FIFO implementation remains within the corrected contract; affected Slice 2 completion markers must be reopened and reverified against the new evidence-backed Explore / Propose correction / Reviewer traceability requirements before Executor may resume later slices.

The independent OpenSpec semantic target is this Change's proposal, delta spec, design, and tasks. Governance, Skill, runtime, and test files are implementation surfaces; material semantic correction to those implementation surfaces occurs only after the corrected OpenSpec target receives a fresh independent `Reviewer / review-openspec` PASS.

No OpenAI API/model-call fallback, label-writer provenance gate, hidden admission token, lock/lease/heartbeat, retry counter, second workflow DAG, generic workflow engine, separate `review-explore` action, or repository-wide citation framework is introduced.

The one-time Human administrative sequencing override that temporarily parked #168 and #169 is deployment context only. Those Issues remain open and preserved; they are not part of the normal priority contract introduced by this Change.