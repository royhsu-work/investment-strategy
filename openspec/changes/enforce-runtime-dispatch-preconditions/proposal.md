# Change: Enforce runtime dispatch preconditions

## Why

#105 / Change `enforce-dispatch-cardinality-preflight` correctly established WIP=1, complete repository-wide cardinality reconstruction, fail-closed dispatch, and pre-activation Explore/Propose guards. Its approved design also deliberately kept the executable classifier as a **test-only model** because Scheduled Tasks have no repository runtime dispatcher process.

The #100/#130 recurrence proves that this left one material enforcement gap. Durable #100 evidence shows `complete-required-followup-materialization` was formal-active at `Lead / finalize-change` while durable #130 evidence nevertheless records later substantive `Lead / explore-change` work and formal activation. The first conclusively reconstructable illegal mapped action was therefore already #130 Explore, before the second Change identity was persisted.

The test-only classifier rejects this state, but the live Agent path does not execute that classifier before direct GitHub work/mutations. Current durable messages also do not record the actual formal-Issue set, candidate set, completeness evidence, or selected Issue consumed at action entry, so the incident cannot distinguish incomplete enumeration from skipped/misapplied preflight after the fact.

Reviewer correction on exact proposal revision `3508493673447d39b4ad0420ca7e1dfe2c333c64` identified a second trust boundary that the initial formalization did not state normatively: **decision correctness is insufficient unless the classifier's current-state inputs themselves come from authoritative GitHub observations obtained during the current invocation**. A previously routed Issue may retain historical routing text in its body/comments after its current routing labels are removed; such history is audit context, not current routing evidence. If same-invocation current Issue state, Change identity, routing labels, and repository enumeration completeness cannot be established from authoritative GitHub reads, authorization must be indeterminate rather than synthesized from conversation history, prior run output, cache, or historical Issue prose.

This correction strengthens the runtime-enforcement boundary without retroactively asserting that the later observation-provenance failure mode was established at the original Explore handoff. It is a material post-handoff specification correction accepted from Reviewer finding `issuecomment-5377194503`.

## What Changes

- Replace the parallel test-only cardinality model with one repository-owned executable dispatch-precondition implementation that consumes an explicit repository Issue snapshot plus observable enumeration-completeness metadata and returns a structured deterministic decision.
- Define the input-authority contract for that executable surface: current Issue state, Change identity, routing labels, and completeness fields used for dispatch MUST be derived from authoritative GitHub observations obtained during the same invocation. Conversation history, prior invocation output, model memory/cache, and historical Issue body/comment routing MUST NOT satisfy current-state predicates.
- Require workflow-dynamic runtime selection and mapped action entry to consume that executable result. A missing, unexecutable, provenance-invalid, incomplete, stale, candidate-local, or contradictory input cannot authorize work.
- Require `Lead / explore-change` to consume an executable zero-formal-WIP + deterministic-winner decision before substantive research, and require `Lead / propose-change` to consume the same executable contract immediately before activation and again on the post-write reconstruction.
- Preserve current reconstruction-based semantics: the executable surface does not become a second workflow DAG or canonical state store. Coordination Issue `Change + agent + action` remains workflow state; `agents/AGENTS.md` remains the semantic owner.
- Treat activation as accepted only after the post-write executable reconstruction proves exactly one formal active workflow and it is the selected Issue. A competing post-write state fails closed; the Change does not invent automatic winner selection or rollback.
- Make `tests/test_dispatch_cardinality_preflight.py` exercise the same production decision implementation used by runtime authorization rather than a local model.
- Extend executable/integration regression coverage to reject stale current-state inputs, including the shape where an Issue was historically routed but its current routing labels are absent, and to return indeterminate when same-invocation authoritative current labels cannot be obtained.
- Extend canonical `ACTION_RESULT` evidence for pre-activation Explore and Propose so the durable result carries the exact executable preflight output needed for diagnosis: enumeration completeness, formal-active Issue identities, applicable pre-activation candidate identities, selected Issue, action-entry decision, and the authoritative observation provenance/completeness evidence consumed; Propose additionally records pre-write and post-write formal-active Issue identities and whether activation was accepted.
- Preserve optional runtime/wake-source correlation only when the execution environment actually exposes it; do not fabricate scheduler identity and do not make it workflow authority.
- Keep external Scheduled Task prompts bootstrap-only. The executable contract is repository-owned and progressively loaded/executed from default-branch governance, not copied into task prompts.

## Affected Capabilities

### Modified

- `scheduled-agent-workflow`
  - executable complete-cardinality/action-entry authorization;
  - invocation-local authoritative-GitHub input provenance for current-state predicates;
  - executable pre/post formal-activation acceptance;
  - shared runtime/test classifier ownership;
  - durable preflight/activation observability tied to the same executable result and input provenance.

## Scope

In scope:

- One deterministic repository-owned executable classifier/precondition surface for workflow-dynamic cardinality, queue selection, and action-entry authorization.
- One explicit acquisition/provenance contract requiring every current Issue state / Change identity / routing input consumed by that surface to originate from authoritative GitHub observation in the current invocation, with explicit completeness evidence.
- Shared governance needed to require execution/consumption of that surface while retaining `agents/AGENTS.md` as semantic authority.
- Narrow `openspec-explore` and `openspec-change` procedural changes needed to consume the executable precondition at their demonstrated boundaries.
- Canonical `ACTION_RESULT` presentation fields for exact preflight/activation Issue identities, completeness evidence, and observation provenance sufficient to audit what the executable decision consumed.
- Regression/integration tests that import and exercise the same executable decision implementation used by the runtime procedure, including the exact #100/#130 recurrence shape and the historical-routing/current-label-absent stale-input shape.
- Explicit failure behavior when the current execution environment cannot execute the repository-owned precondition, cannot establish complete enumeration, or cannot obtain same-invocation authoritative current-state fields.

Out of scope:

- Reopening or implementing #130's Invocation Exit scope.
- Automatically selecting a winner from an already multiple-active repository state.
- Automatically clearing or rewriting another workflow's immutable Change identity.
- A lock, lease, heartbeat, hidden queue, durable claim, central workflow engine, global priority score, or second workflow DAG.
- Moving workflow semantics into Scheduled Task prompts.
- Treating historical comments, Issue prose, previous invocation output, model memory, or cache as a current-state source.
- Claiming an atomic GitHub cross-Issue compare-and-swap primitive that the current connector does not expose.
- Changing Human authority, Reviewer independence, role ownership, or ordinary OpenSpec lifecycle topology.

## Skill maintenance traceability

- `agents/skills/openspec-explore/SKILL.md` — **Modified**. Sources: #133 `ACTION_RESULT` establishing `PROPOSAL_READY` plus Reviewer finding `issuecomment-5377194503`. Preserve Explore's existing research responsibility and authority; add only the requirement to execute/consume the shared runtime precondition built from same-invocation authoritative GitHub observations before substantive pre-activation research. Rationale: #130 Explore is the first reconstructable illegal action after #105, and stale/historical routing input must not satisfy that action-entry gate.
- `agents/skills/openspec-change/SKILL.md` — **Modified**. Sources: #133 `ACTION_RESULT` establishing `PROPOSAL_READY` plus Reviewer finding `issuecomment-5377194503`. Preserve Lead specification/activation authority; replace prose-only complete-cardinality consumption with the same executable precondition immediately before and after the activation write, using only same-invocation authoritative current-state inputs. Rationale: #130 Propose was the downstream illegal formal activation and remains vulnerable if the executable classifier receives stale normalized input.

No Skill is added or removed. Shared classifier/acquisition contract code and message presentation remain outside the two action Skills so they do not duplicate global semantics.

## Traceability

- Source decision-complete Explore: #133 `issuecomment-5373937613`.
- Post-handoff semantic correction: Reviewer finding #133 `issuecomment-5377194503`.
- Evidence-discipline clarification consumed for temporal/source boundaries: #133 `issuecomment-5377184598`.
- Regression incident: #100 formal-active durable evidence and #130 Explore/Propose durable results; timeline claims that matter to causality must remain grounded in their authoritative source objects rather than cross-Issue summary prose.
- Current-vs-historical routing regression shape: current GitHub routing observations are authoritative; historical body/comment routing remains audit context only.
- Prior semantic remediation: #105 / Change `enforce-dispatch-cardinality-preflight`, especially archived design Decision 5 documenting the intentionally test-only helper.
- Existing canonical requirement: `Active-workflow cardinality and Issue-state coherence precede queue selection`.
- Capability delta: `specs/scheduled-agent-workflow/spec.md`.
- Design: `design.md`.
- Implementation slices: `tasks.md`.
