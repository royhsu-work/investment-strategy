# Change: Enforce runtime dispatch preconditions

## Why

#105 / Change `enforce-dispatch-cardinality-preflight` correctly established WIP=1, complete repository-wide cardinality reconstruction, fail-closed dispatch, and pre-activation Explore/Propose guards. Its approved design also deliberately kept the executable classifier as a **test-only model** because Scheduled Tasks have no repository runtime dispatcher process.

The #100/#130 recurrence proves that this left one material enforcement gap. Durable #100 evidence shows `complete-required-followup-materialization` was formal-active at `Lead / finalize-change` by `2026-08-21T15:33:08Z`; durable #130 evidence nevertheless records `Lead / explore-change -> PROPOSAL_READY` at `2026-08-21T15:48:15Z`, followed by formal activation at `15:50:29Z`. The first conclusively reconstructable illegal mapped action was therefore already #130 Explore, before the second Change identity was persisted.

The test-only classifier rejects this state, but the live Agent path does not execute that classifier before direct GitHub work/mutations. Current durable messages also do not record the actual formal-Issue set, candidate set, completeness evidence, or selected Issue consumed at action entry, so the incident cannot distinguish incomplete enumeration from skipped/misapplied preflight after the fact.

## What Changes

- Replace the parallel test-only cardinality model with one repository-owned executable dispatch-precondition implementation that consumes an explicit repository Issue snapshot plus observable enumeration-completeness metadata and returns a structured deterministic decision.
- Require workflow-dynamic runtime selection and mapped action entry to consume that executable result. A missing, unexecutable, incomplete, stale, candidate-local, or contradictory input cannot authorize work.
- Require `Lead / explore-change` to consume an executable zero-formal-WIP + deterministic-winner decision before substantive research, and require `Lead / propose-change` to consume the same executable contract immediately before activation and again on the post-write reconstruction.
- Preserve current reconstruction-based semantics: the executable surface does not become a second workflow DAG or canonical state store. Coordination Issue `Change + agent + action` remains workflow state; `agents/AGENTS.md` remains the semantic owner.
- Treat activation as accepted only after the post-write executable reconstruction proves exactly one formal active workflow and it is the selected Issue. A competing post-write state fails closed; the Change does not invent automatic winner selection or rollback.
- Make `tests/test_dispatch_cardinality_preflight.py` exercise the same production decision implementation used by runtime authorization rather than a local model.
- Extend canonical `ACTION_RESULT` evidence for pre-activation Explore and Propose so the durable result carries the exact executable preflight output needed for diagnosis: enumeration completeness, formal-active Issue identities, applicable pre-activation candidate identities, selected Issue, and action-entry decision; Propose additionally records pre-write and post-write formal-active Issue identities and whether activation was accepted.
- Preserve optional runtime/wake-source correlation only when the execution environment actually exposes it; do not fabricate scheduler identity and do not make it workflow authority.
- Keep external Scheduled Task prompts bootstrap-only. The executable contract is repository-owned and progressively loaded/executed from default-branch governance, not copied into task prompts.

## Affected Capabilities

### Modified

- `scheduled-agent-workflow`
  - executable complete-cardinality/action-entry authorization;
  - executable pre/post formal-activation acceptance;
  - shared runtime/test classifier ownership;
  - durable preflight/activation observability tied to the same executable result.

## Scope

In scope:

- One deterministic repository-owned executable classifier/precondition surface for workflow-dynamic cardinality, queue selection, and action-entry authorization.
- Shared governance needed to require execution/consumption of that surface while retaining `agents/AGENTS.md` as semantic authority.
- Narrow `openspec-explore` and `openspec-change` procedural changes needed to consume the executable precondition at their demonstrated boundaries.
- Canonical `ACTION_RESULT` presentation fields for exact preflight/activation Issue identities and completeness evidence.
- Regression/integration tests that import and exercise the same executable decision implementation used by the runtime procedure, including the exact #100/#130 recurrence shape.
- Explicit failure behavior when the current execution environment cannot execute the repository-owned precondition or cannot establish complete enumeration.

Out of scope:

- Reopening or implementing #130's Invocation Exit scope.
- Automatically selecting a winner from an already multiple-active repository state.
- Automatically clearing or rewriting another workflow's immutable Change identity.
- A lock, lease, heartbeat, hidden queue, durable claim, central workflow engine, global priority score, or second workflow DAG.
- Moving workflow semantics into Scheduled Task prompts.
- Claiming an atomic GitHub cross-Issue compare-and-swap primitive that the current connector does not expose.
- Changing Human authority, Reviewer independence, role ownership, or ordinary OpenSpec lifecycle topology.

## Skill maintenance traceability

- `agents/skills/openspec-explore/SKILL.md` — **Modified**. Source: #133 `ACTION_RESULT` establishing `PROPOSAL_READY`. Preserve Explore's existing research responsibility and authority; add only the requirement to execute/consume the shared runtime precondition before substantive pre-activation research. Rationale: #130 Explore is the first reconstructable illegal action after #105.
- `agents/skills/openspec-change/SKILL.md` — **Modified**. Source: #133 `ACTION_RESULT` establishing `PROPOSAL_READY`. Preserve Lead specification/activation authority; replace prose-only complete-cardinality consumption with the same executable precondition immediately before and after the activation write. Rationale: #130 Propose was the downstream illegal formal activation.

No Skill is added or removed. Shared classifier code and message presentation remain outside the two action Skills so they do not duplicate global semantics.

## Traceability

- Source decision-complete Explore: #133 `issuecomment-5373937613`.
- Regression incident: #100 formal-active timeline and #130 Explore/Propose durable results.
- Prior semantic remediation: #105 / Change `enforce-dispatch-cardinality-preflight`, especially archived design Decision 5 documenting the intentionally test-only helper.
- Existing canonical requirement: `Active-workflow cardinality and Issue-state coherence precede queue selection`.
- Capability delta: `specs/scheduled-agent-workflow/spec.md`.
- Design: `design.md`.
- Implementation slices: `tasks.md`.
