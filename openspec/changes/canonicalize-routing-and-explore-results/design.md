## Context

Current production dispatch already intends a small persistent workflow identity: current Issue state, `Change:`, and the current routing tuple. However, unset Propose candidates are additionally gated by `preactivation_eligible`, which the runtime reconstructs from historical semantic evidence before FIFO selection. That creates a second control-state path: a current routing tuple can exist while dispatch separately decides that the tuple is not eligible because an earlier LLM-authored comment cannot be parsed as one exact `ACTION_RESULT(PROPOSAL_READY)` envelope.

#168 → #169 is the primary current regression. GitHub routing events prove #168 had already reached `Lead / propose-change` at `2026-08-27T17:25:09Z`, while a production dispatch ten seconds later authorized the newer #169 Explore. The currently visible #168 Explore-result comment was edited after the bad dispatch, so the historical duplicate-field trigger itself is not treated as currently provable source evidence. The production parser remains independently observable: it accepts canonical and bullet-form `Workflow|Change|Action|Result` fields across the whole Markdown body and requires singleton values. #161 → #168 independently establishes the same high-level recurrence without claiming the same exact parser trigger.

The Human direction for #175 fixes the responsibility boundary rather than the parser: current routing is operational state; semantic evidence remains action-local; direct Human-to-Propose is removed from normal intake; and deterministic repository application, not worker-selected routing, derives Explore effects from a bounded result.

Implementation then exposed a semantic drift in the approved artifacts: “selected Issue must not fall through to later work” had been expanded into “selected Propose must retain the Propose action and must not route back to Explore.” The Human explicitly rejected that expansion. The intended invariant is Issue ownership, not action immobility. Pre-activation Propose must be able to route the same Issue back to Explore when its evidence/source/feasibility basis is incomplete but still researchable within the same bounded problem.

The same correction also exposes an upstream quality gap: an Explore conclusion can be faithfully preserved into Proposal/Specs/Design/Tasks while still being unsupported by its own sources. #175 therefore strengthens the existing action-local traceability chain without adding a new review stage: Explore must make material claim provenance reconstructable; Propose independently validates the source/evidence and feasibility basis before activation; Reviewer independently validates the durable source → Explore → OpenSpec chain.

## Goals / Non-Goals

**Goals:**

- Stop global dispatch from re-proving current Propose routing by parsing comments or Human-admission history.
- Keep WIP=1, finish-first, routing-debt handling, authoritative enumeration, structural routing validation, FIFO, and fail-closed behavior intact.
- Preserve same-Issue queue ownership across pre-activation semantic correction while allowing the legal action to change from Propose back to Explore.
- Require every material Explore claim that affects disposition, scope, constraints, feasibility, or selected direction to identify supporting source/evidence and distinguish evidence from interpretation/inference and unresolved questions.
- Require Propose to independently/reversely validate the material source → Explore conclusion chain and feasibility sufficiency before formal activation.
- Route incomplete-but-researchable pre-activation Propose back to same-Issue Explore with `Change: unset`, without dispatcher fallback to later work.
- Require Reviewer to independently validate the durable material source/evidence → Explore conclusion → OpenSpec chain without re-running Explore or reconstructing undocumented Human intent.
- Remove Human direct-Propose from normal workflow while preserving genuine Human-reserved decisions and advisory admission.
- Make the four Explore dispositions structured worker values and derive their effects deterministically in repository application.
- Provide executable regression coverage at the actual dispatcher/application and semantic action boundaries.

**Non-goals:**

- No generic workflow engine or machine-readable second DAG.
- No label-writer provenance gate or hidden origin/admission registry.
- No parser hardening as the control-plane fix.
- No OpenAI API/model call for result classification or semantic validation.
- No lock, lease, heartbeat, retry counter, claim state, or hidden sequence.
- No new `review-explore` action or fourth role/stage.
- No repository-wide citation/evidence framework; evidence traceability is bounded to material Explore/Propose semantics needed by this Change.
- No generalization of result-derived effects to unrelated actions in this Change.
- No change to #168's request/run transport contract or #169's lifecycle-correction ownership.

## Decisions

### Decision 1: Dispatch consumes current routing as operational truth

At the normal pre-activation boundary, dispatcher inputs remain current authoritative GitHub facts needed for structural selection: Issue identity/open state, `Change:`, legal routing tuple, `created_at`, enumeration/provenance completeness, and existing routing-debt/recovery facts where applicable.

`preactivation_eligible` is removed from `RepositoryIssueSnapshot`, runtime observations, and dispatch preflight. A coherent open `Lead / explore-change + Change: unset` or `Lead / propose-change + Change: unset` is a pre-activation candidate whenever formal-work/debt rules permit. Both forms share the same FIFO key: GitHub `created_at`, then Issue number.

The runtime therefore removes the global unset-Propose eligibility pass that currently reads comments/events to classify direct-Propose admission or reconstruct Explore-originated `PROPOSAL_READY`. No replacement origin/admission field is introduced.

**Why:** routing is already the durable operational ownership state. Re-proving why the tuple exists on every read creates probabilistic state reconstruction and can delete an otherwise valid tuple before ordering.

### Decision 2: Queue ownership and action-local semantic correction are separate

The selected pre-activation Issue remains the queue owner until it legally transitions, terminates, or activates. That ownership invariant does not require `action:propose-change` to remain unchanged.

`Lead / propose-change` must dereference the exact durable same-Issue Explore `ACTION_RESULT(PROPOSAL_READY)` and independently validate the material source/evidence behind its still-applicable scope, constraints, exclusions, selected direction, and feasibility claims. `PROPOSAL_READY` is an upstream disposition, not permission to trust an unsupported conclusion.

When the material source/evidence/feasibility chain is incomplete, unsupported, stale, ambiguous, or contradictory, Propose classifies the disposition:

- **Researchable within the same bounded problem, no new Human-reserved decision:** persist no Change identity and route the same Issue to `Lead / explore-change` with `Change: unset`. Explore fills the missing evidence and may later produce a new evidence-backed `PROPOSAL_READY`. The Issue keeps its original GitHub queue identity/`created_at`; dispatch must not authorize a later candidate merely because this semantic correction was required.
- **A genuinely new Human-reserved requirement, scope/risk/architecture commitment is required:** stop at the existing Human decision boundary; the model does not weaken or redefine the Human requirement to avoid escalation.
- **Change identity already non-`unset`:** do not return to pre-Change Explore. Material semantic corrections use the existing `Lead / resolve-question → Reviewer / review-openspec` formal correction loop.

**Why:** the demonstrated dispatcher defect is solved by keeping structural selection independent of semantic evidence, but action-local failure still needs a legal semantic disposition. “Retain selected Issue” means preserve workflow ownership, not freeze the source action.

### Decision 3: Explore material claims have reconstructable source/evidence provenance

Explore remains a semantic research action owned by Lead, not a deterministic classifier. For every material claim that can affect disposition, scope, constraint, feasibility, selected direction, or a Human-reserved boundary, durable Explore evidence must identify the supporting source and distinguish:

1. source fact/evidence;
2. Lead interpretation/inference derived from that evidence; and
3. unresolved question or uncertainty.

A material inference with no supporting evidence cannot establish `PROPOSAL_READY`. A feasibility assertion must be backed by evidence appropriate to that assertion, such as current repository observations, authoritative documentation, tests/prototype results, or another source whose authority and applicability are identified. Model confidence is not feasibility evidence.

This does not require a single serialization format or repository-wide citation registry. The contract requires a reconstructable claim/source chain, not a new workflow database.

### Decision 4: Propose independently validates the source → Explore chain before formalization

Propose consumes the exact same-Issue `PROPOSAL_READY` result and reverse-checks every material formalized requirement/direction against the relevant Explore claim and its cited source/evidence. It also revalidates whether feasibility evidence is sufficient for the meaning being formalized.

The gate is therefore:

```text
source/evidence
    ↓
Explore fact / interpretation / conclusion
    ↓
Propose formal meaning
```

A complete chain permits formalization. A broken but researchable chain follows Decision 2 back to same-Issue Explore before Change activation. This gate is action-local and must not be moved into global dispatcher eligibility.

### Decision 5: Reviewer independently verifies source → Explore → OpenSpec traceability

For an Explore-originated Change, `Reviewer / review-openspec` first dereferences the exact durable Explore result and its declared material source/evidence references. Reviewer independently verifies that material Explore conclusions are actually supported by those sources and that Proposal/Specs/Design/Tasks preserve the supported meaning before applying the existing reverse-first and forward traceability gate.

Reviewer does **not** re-run Explore, perform an unbounded new research project, reconstruct conversation history, or infer undocumented Human intent. If the durable source/evidence chain needed to verify a material conclusion is missing, contradictory, or insufficient, that absence is itself a finding. This prevents unsupported Explore interpretation from being legitimized merely because downstream artifacts are internally consistent.

### Decision 6: Remove Human direct-Propose from normal intake

The normal path becomes:

```text
routed Explore
→ evidence-backed structured PROPOSAL_READY
→ repository-derived Lead / propose-change routing
→ Propose source/evidence + feasibility revalidation
   ├─ sufficient → Change activation
   └─ incomplete but researchable → same Issue Explore
```

The direct-Propose decision reference and its legacy admission/fallback/review exceptions are deleted. This does not change the provenance-bound Human predicate for `HUMAN_DECISION_REQUIRED`, advisory admission, or later Human-reserved scope/risk/architecture decisions.

A coherent Propose tuple written administratively/out-of-band is still current operational routing and therefore selectable. It does not manufacture semantic evidence or Human authority; absent a sufficient same-Issue Explore source/evidence chain, the mapped Propose action applies Decision 2 rather than disappearing from dispatch.

### Decision 7: Explore disposition is structured separately from narrative evidence

The mapped Lead worker returns one validated result code from:

```text
PROPOSAL_READY
HUMAN_DECISION_REQUIRED
NO_CHANGE_REQUIRED
NO_GO
```

Narrative `result_content` remains available for durable `ACTION_RESULT` explanation and traceability, including the material claim/source chain required by Decision 3. The machine result code is not parsed back out of that Markdown.

This keeps semantic judgment with Lead while removing a second probabilistic interpretation step from repository application.

### Decision 8: Repository application derives Explore effects

After fresh authorization of source `Lead / explore-change`, application maps the bounded result to the action-owned effect:

| Result | Derived effect |
| --- | --- |
| `PROPOSAL_READY` | Same Issue → `Lead / propose-change`, keep `Change: unset` |
| `HUMAN_DECISION_REQUIRED` | Retain Explore; use existing Human escalation path |
| `NO_CHANGE_REQUIRED` | Existing pre-Change terminal close + workflow-routing retirement |
| `NO_GO` | Existing pre-Change terminal close + workflow-routing retirement |

The worker does not provide arbitrary routing control for Explore. If it supplies a conflicting or additional routing transition, application rejects the worker-chosen transition. `agents/workflow.md` remains the legal topology authority for the derived successor; the mapping is an action-local application contract, not a second global DAG.

The same deterministic application boundary must support the governed same-Issue Propose → Explore correction result/effect once the corrected Propose action contract defines its bounded disposition. The worker may identify that additional research is required, but it must not choose an arbitrary successor; repository application derives only the action-defined same-Issue Explore correction. The implementation mechanism may reuse the structured-result pattern without generalizing into a generic workflow engine.

### Decision 9: Migration is state-preserving

No migration token or provenance reconstruction is required. After default-branch activation, any current coherent unset Propose tuple participates directly in pre-activation FIFO. Action-local semantics are then evaluated normally.

This specifically permits the administratively parked #168 to be restored after #175 becomes authoritative without manufacturing a new approval/provenance token. #168/#169 parking is one-time deployment sequencing evidence only and is not encoded as a normal dispatcher feature.

## Responsibility split

```text
GitHub acquisition
  → prove current/completed structural observations

workflow_dispatch.py
  → formal/debt/pre-activation structural selection only

Lead / explore-change
  → research material claims
  → record source fact/evidence vs interpretation/inference vs unresolved
  → choose bounded Explore disposition

Lead / propose-change
  → independently reverse-check source/evidence + feasibility
  → formalize only when sufficient
  → otherwise request governed same-Issue Explore correction or Human boundary

Reviewer / review-openspec
  → independently verify source → Explore → OpenSpec chain
  → then ordinary reverse-first + forward semantic gate

repository application
  → fresh source reauthorization
  → validate bounded result/effect preconditions
  → derive action-owned legal effect
  → mutate
  → fresh postcondition
  → redispatch
```

This keeps classifier correctness separate from input authority/completeness, keeps semantic evidence downstream of the mapped-action boundary, and adds no independent Explore-review stage.

## Failure behavior

- Invalid/incomplete current routing or enumeration continues to fail closed before action selection.
- Current closed-routing debt continues through the existing exceptional classifier before normal intake.
- A selected Propose with insufficient material source/evidence does not disappear from queue ownership and cannot cause fallback to a later Issue.
- If that insufficiency is researchable within the existing bounded problem before activation, the legal correction is same-Issue `Lead / explore-change + Change: unset`.
- If resolving the insufficiency requires a new Human-reserved decision, the existing Human boundary is used rather than model invention.
- After Change activation, material semantic corrections stay on the formal `resolve-question`/review loop rather than returning to pre-Change Explore.
- An Explore material claim lacking identified supporting evidence cannot establish `PROPOSAL_READY`.
- Reviewer treats a missing/contradictory/insufficient source → Explore → OpenSpec chain as a finding; internal artifact consistency alone is not enough.
- An invalid Explore result code is rejected before effect application.
- A worker-chosen Explore successor is rejected when the result-derived contract owns the effect.
- A stale source routing/change/revision between worker result and application causes normal stale/precondition failure; no effect is applied from stale authorization.
- Missing Human authority at genuine Human-reserved boundaries remains fail-closed under the existing provenance contract.

## Validation strategy

Regression coverage must exercise production-consumed boundaries rather than only parallel helpers:

1. Runtime acquisition + dispatcher: older coherent Propose/newer Explore selects older Propose without comment/event eligibility reads.
2. Runtime acquisition + dispatcher: duplicate/irrelevant `Workflow:` prose in historical comments cannot alter selection.
3. Explore semantics: a material disposition/scope/constraint/direction/feasibility claim without identified supporting evidence cannot produce valid `PROPOSAL_READY`; durable result distinguishes source evidence, interpretation/inference, and unresolved questions.
4. Propose semantics/application: insufficient or contradictory source/evidence/feasibility before activation derives same-Issue Explore correction with `Change: unset`, preserving Issue/queue identity and preventing later-Issue fallback.
5. Propose semantics: sufficient source/evidence chain permits formalization; a new Human-reserved commitment stops at the Human boundary; a non-`unset` Change uses the formal resolve-question path instead of pre-Change Explore.
6. Reviewer semantics: independently verify representative material source → Explore → Proposal/Specs/Design/Tasks chains; an unsupported Explore conclusion is a finding even when OpenSpec artifacts preserve it consistently.
7. Worker/application: structured `PROPOSAL_READY` derives Propose routing and fresh redispatch sees the tuple directly.
8. Worker/application: inconsistent worker-supplied routing cannot override structured action result.
9. All four Explore results preserve governed successor/Human/terminal semantics.
10. Direct-Propose admission paths/helpers disappear while advisory and escalation Human authority remain covered.
11. Existing invalid-routing, incomplete-enumeration, multiple-formal-workflow, closed-debt, stale-state, and cardinality regressions stay green.

Strict OpenSpec validation and a fresh independent semantic review remain required on the exact corrected OpenSpec revision before implementation resumes. The earlier Reviewer PASS applies only to the superseded semantic target and is stale for this corrected meaning.