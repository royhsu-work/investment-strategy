---
name: openspec-change
description: Author or materially revise OpenSpec proposal/spec/design/tasks for Lead / propose-change and Lead / resolve-question while preserving semantic baselines, traceability, validation, and specification-authority boundaries.
---

# OpenSpec Change Skill

Mapped actions: `Lead / propose-change`, `Lead / resolve-question`.

This skill operationalizes approved OpenSpec authoring and specification-question resolution. It does
not replace the repository OpenSpec proposal/specs/design/tasks lifecycle.

## Repository Skill composition

When proposal or specification-resolution work materially specifies creation or modification of repository Skills, load the default-branch `agents/skills/skill-creator/SKILL.md` and `agents/skills/skill-creator/references/repository-governance.md` before authoring or revising that Skill-related OpenSpec meaning. Use them as reusable procedural/integration guidance only; this mapped action plus current default-branch governance and the Lead role retain specification authority, scope, routing, validation, escalation, and result semantics. Do not load this composition for unrelated OpenSpec changes.

### Skill maintenance traceability authoring

When approved Change scope materially affects repository Skills, Lead owns the Change-local `Skill maintenance traceability` declaration as specification meaning. Enumerate every materially affected Skill as Added, Modified, or Removed; identify the approved source/change reference, the responsibility boundary before/after or explicitly preserved responsibility, the rationale, and any replacement/supersession target that materially applies. One capability change may legitimately declare multiple materially affected Skills and MUST NOT be expanded into one capability delta per Skill merely for traceability.

Formatting, wording, or reference-only edits that do not alter responsibility, executable semantics, composition/loading behavior, trigger behavior, authority, or maintenance meaning do not create declaration noise. `UPSTREAM.md` remains a distinct upstream/current-local-divergence provenance axis; repository-authored Skills MUST NOT receive fictional upstream metadata. If implementation later reveals a materially different Skill set, classification, or responsibility change than the approved declaration, Executor cannot self-authorize that meaning and must return through the governed specification path.

## Spec-driven semantic adapter

When default-branch `openspec/config.yaml` declares `schema: spec-driven`, load
`agents/skills/openspec-semantic-adapter.md` before authoring or materially revising OpenSpec artifacts.
Consume its artifact-readiness, applicable config/context, delta-authoring, canonicalization-readiness,
and provenance contracts together with applicable canonical specs. If the configured schema or material
represented baseline is unsupported/mismatched, fail closed rather than substituting model memory,
mutable upstream `main`, or an inferred rule. The adapter is semantic input only; it does not change
runtime routing or Lead authority.

## Machine-gated runtime boundary

After the machine-gated runtime is authoritative, a Propose/Resolve model worker starts only after repository-owned dispatch has authorized the exact coordination Issue and mapped Lead action. The worker MUST NOT execute `workflow_dispatch.py` as its own authorization boundary, self-select another Issue/role/action, or treat prior worker context as current-state authority.

The worker may author approved specification artifacts in its local checkout when its action capability permits local writes. It has no durable GitHub write authority. Any requested Issue/comment/label/routing/Change-identity persistence, branch/commit/PR update, Human-escalation write, or other durable GitHub effect is invocation-local output for repository-owned application. Application fresh-reauthorizes the exact source action, checks effect-specific preconditions, applies authorized effects, observes postconditions, and re-dispatches from resulting current state.

For `propose-change`, the activation write is therefore an application-time effect boundary. The immediate pre-write machine decision must authorize this exact Issue as `Lead / propose-change`; after the requested Change-identity write is applied, repository runtime must fresh-reconstruct current GitHub state and execute the classifier again. Activation is accepted only when that post-write decision proves this Issue is the sole formal active workflow with the expected Change identity and current routing. The worker does not manufacture either decision and does not treat its requested activation as accepted before application returns that durable evidence.

Every continuation re-enters executable dispatch. A same-role successor may execute within the same GitHub Actions runtime execution, but it receives a fresh mapped model invocation; prior Lead worker context is not carried forward as authorization or reasoning state. Cross-role continuation likewise receives a fresh invocation for the newly selected role.

## Reconstruct before acting

Read from durable state:

- default-branch `agents/AGENTS.md`, `agents/roles/lead.md`, and this skill;
- coordination Issue routing and immutable `Change:` identity when set;
- current active OpenSpec proposal/specs/design/tasks and applicable canonical specs;
- applicable `README.md` and `openspec/config.yaml` governance;
- relevant durable Issue/review findings;
- exact current repository/branch revision and strict OpenSpec validation evidence.

For `propose-change`, consume the exact machine authorization/evidence envelope supplied for this worker invocation. Candidate-local or partial enumeration is never sufficient activation evidence, and the worker MUST NOT re-derive an alternative dispatcher decision from Issue prose. The executable decision proves current selection only; it does not establish semantic readiness or replace the action-local Explore baseline.

If the coordination Issue or current OpenSpec artifacts contain declared upstream authoritative decision/gate references, Lead MUST dereference those sources during `propose-change` and any materially revised `resolve-question`. A cross-Issue summary is orientation only and is not replacement authority for the declared source evidence.

For every `propose-change`, reconstruct exactly one durable same-Issue Explore `ACTION_RESULT` that established `PROPOSAL_READY`. Treat that exact result as the upstream semantic baseline for formalization and independently verify its material source/evidence chain before activation: each material Explore claim needed for scope, constraints, feasibility, selected direction, or the Human boundary must still be supported by the referenced source/evidence, with source fact/evidence distinguishable from Lead interpretation/inference and unresolved questions. Proposal/readiness evidence MUST identify the exact Explore result and the material source/evidence it relies on, and Lead MUST preserve every material decided scope, constraint, exclusion, feasibility conclusion, and selected direction that remains supported and applicable.

Missing, ambiguous, stale, contradictory, unsupported, or materially invalidated baseline/source evidence does not cause dispatcher fallback to another queued Issue. If the gap is still researchable within the same bounded problem, `Change: unset` is still true, and no new Human-reserved decision is required, Propose returns structured `RESEARCH_REQUIRED`; the worker MUST NOT request the correction routing itself. Repository-owned application derives the same Issue `Lead / propose-change → Lead / explore-change` correction while preserving `Change: unset` and the Issue's original queue identity. If the gap instead requires a new Human-reserved requirement, scope/risk acceptance, or architecture decision, use the governed Human boundary. Once a non-`unset` Change identity exists, pre-activation Explore correction is not legal; formal semantic correction uses `Lead / resolve-question`.

If routing, change identity, active-workflow identity, or required evidence is contradictory, fail closed.

Before requesting a consequential specification/readiness/resolution result or ownership transfer, consume the shared `agents/AGENTS.md` substantive Human-input freshness/disposition invariant. Newer material direct-Human input that can affect scope, contract meaning, traceability, or handoff assumptions must have a reconstructable exact-comment disposition or be routed/escalated through the existing legal owner or Human boundary. This Skill does not redefine the shared classifier or expand Lead/Human authority.

## `propose-change`

1. Confirm current valid `Lead / propose-change + Change: unset` routing from the machine-authorized source and dereference exactly one same-Issue durable Explore `ACTION_RESULT(PROPOSAL_READY)` before authoring or requesting any consequential effect. Independently verify the supporting source/evidence for every material baseline claim and the feasibility sufficiency needed for formalization; preserve the still-applicable supported material boundary throughout formalization. Current coherent routing is sufficient for dispatcher selection but is not sufficient semantic evidence for Propose activation.
   - If the baseline/source evidence is missing, ambiguous, stale, contradictory, unsupported, or materially invalidated but the gap remains researchable within the same bounded problem, no new Human-reserved decision is required, and `Change: unset` still holds, return `propose_disposition = RESEARCH_REQUIRED`. Request no Change-identity/specification mutation and no `routing-transition`; repository application owns the deterministic same-Issue correction to `Lead / explore-change + Change: unset` and fresh postcondition/redispatch. The selected Issue remains the queue owner, so this MUST NOT cause dispatcher fallback to a later candidate.
   - If the insufficiency exposes a new Human-reserved requirement, product/scope/risk acceptance, or architecture decision, use the governed Human boundary rather than disguising it as research.
   - If a non-`unset` Change identity already exists, do not return the pre-activation research correction; use the formal `Lead / resolve-question` correction path.
   - Never invent a direct-Propose Human authority envelope or substitute Issue prose/conversation memory/routing provenance for missing source evidence.
2. If `Change:` is unset and Propose is semantically ready, consume formal active/terminal-pending workflow state and the current pre-activation winner from the exact machine authorization/evidence envelope before requesting any Change-identity persistence.
   - If a formal active/terminal-pending workflow exists, keep this Issue queued and request no activation effect.
   - If multiple formal active workflows, indeterminate enumeration/provenance, machine authorization failure, or contradictory durable identity evidence exist, fail closed.
   - At formal-zero with current routing debt empty, the shared dispatcher owns one combined pre-activation queue containing every coherent open `Lead / explore-change + Change: unset` and `Lead / propose-change + Change: unset` entry. The worker MUST NOT reconstruct origin/admission history, comment-based queue eligibility, or an action-local candidate list.
   - Require the consumed pre-write machine decision to authorize this exact Issue as `Lead / propose-change` with formal cardinality zero and current winner identity. The worker MUST NOT request activation from a stale or model-reconstructed substitute decision or independently choose among queued candidates.
   - Return the requested immutable Change-identity effect. Overlapping attempts preserve first-valid-write-wins semantics rather than introducing a lock/claim/lease/heartbeat.
   - Repository application MUST fresh-reconstruct before applying the write, execute the machine classifier, apply only when the exact source remains authorized and the action-local semantic preconditions still pass, then fresh-reconstruct and classify again after the write. Activation is accepted only when the post-write decision proves exactly one formal active workflow, this Issue, with the expected Change identity and current routing. A competing activation, multiple-active state, incomplete/indeterminate provenance, machine execution failure, newer contradiction, or missing/ambiguous Propose baseline rejects continuation; no worker may choose a winner, reuse the pre-write decision, or rewrite another Change/routing tuple.
3. Author the minimum proposal, delta specs, design, and tasks needed by the approved direction. Keep the change single-purpose and preserve repository scope boundaries. Formalize from the exact referenced Explore result and verified source/evidence rather than silently replacing, omitting, or strengthening a still-applicable material decision; editorial restructuring is allowed only when meaning is preserved. If formalization requires a materially different Human-reserved commitment, use the governed Human decision path rather than claiming faithful Explore continuation. Under `spec-driven`, satisfy the loaded semantic adapter's dependency/readiness and applicable config/context rules; for delta specs, apply its complete ADDED/MODIFIED/REMOVED/RENAMED and canonicalization-readiness contract rather than relying on strict validation alone.
   - For a required separate follow-up recorded by the exact durable Explore result E, preserve the required-follow-up classification, exact defer-decision reference, bounded follow-up identity, and routing-complete tracker evidence through proposal/readiness. The later work MAY remain outside the current Change implementation scope; that editorial placement does not downgrade its required class. Conversely, presentation wording does not create or erase the required-followup classification: `Deferred work`, `out of scope`, `follow-up`, or `separately reviewable` alone do not authorize or cancel a tracker.
   - Before OpenSpec readiness, reconstruct all matching tracker state from E and current durable source authority. If no matching tracker exists for a required separate follow-up, fail closed and do not report readiness; Propose must not infer or manufacture replacement source authority from prose.
   - If exactly one matching but incomplete tracker exists and current source authority still permits the missing durable identity/routing fields, repair only the missing durable fields/routing, then fresh-observe the exact source linkage plus `Change: unset + agent:lead + action:explore-change`; must not create a duplicate.
   - If exactly one complete matching tracker exists, reuse its routing-complete tracker evidence rather than creating another tracker.
   - If multiple or ambiguous matching trackers for that Explore decision exist, or source authority/tracker evidence is contradictory, fail closed; do not choose a winner or create a duplicate.
4. Any proposal/implementation PR associated with the persistent coordination Issue must use a non-closing reference to the coordination Issue (for example `Refs #N`). It must not establish Issue-closing linkage. Closing linkage is reserved for the final Archive PR lifecycle boundary.
5. Before handoff, verify required artifacts exist and author/maintain the required trace declarations/references across proposal, specs, design, and tasks. When repository Skills are materially affected, this includes the Change-local Skill maintenance traceability declaration above. Proposal/readiness evidence also identifies the exact durable same-Issue Explore `ACTION_RESULT` and material source/evidence chain used as the upstream semantic baseline so independent review can dereference and verify them. These authoring references must be present and mechanically consistent enough to hand to independent review, but the semantic bidirectional PASS gate belongs to `Reviewer / review-openspec`; Lead MUST NOT execute or claim that independent PASS gate. For a NEW capability, require exactly one non-empty canonicalization-ready `## Purpose`; for existing capabilities, verify delta targets against canonical requirement identities and preserve all still-applicable MODIFIED scenarios/content.
6. Obtain strict OpenSpec validation for the exact handoff revision R. CI is sufficient only when durable validator evidence proves checkout `HEAD == R` before strict validation; `run.head_sha == R` alone is association metadata and is not checkout proof. If valid exact-head CI evidence is unavailable, use the repository-pinned local CLI directly against checkout R. Stale, missing, failed, revision-mismatched, or checkout-mismatched evidence fails closed.
7. Re-run the shared substantive Human-input freshness/disposition check immediately before the readiness result/effect request. Return revision-aware readiness evidence plus the requested routing effect to `Reviewer / review-openspec`; repository application fresh-reauthorizes, persists, observes the target tuple, and records canonical handoff evidence when applicable.

Legal outcomes:

- `READY_FOR_OPENSPEC_REVIEW` → `propose_disposition = null`, request handoff to `Reviewer / review-openspec`.
- researchable pre-activation material source/evidence or feasibility insufficiency, with `Change: unset` and no new Human-reserved decision → `RESEARCH_REQUIRED`; request no routing/Change/specification mutation. Repository application derives same-Issue `Lead / explore-change + Change: unset`; no dispatcher fallback occurs.
- new Human-reserved requirement/scope/risk/architecture decision → use the governed Human decision boundary; do not relabel it as research.
- source no longer machine-authorized or activation is displaced by current formal/debt/pre-activation state → retain `Lead / propose-change` without activation noise and let fresh repository dispatch own later selection.
- `SPECIFICATION_BLOCKED` or another formal semantic problem after a non-`unset` Change identity exists → use `Lead / resolve-question`; do not use pre-activation Explore correction.
- invalid/stale evidence that is neither safely researchable nor a valid Human/formal correction case → retain Lead and fail closed without readiness or arbitrary routing.

## `resolve-question`

### Machine-selected closed-routing debt branch

When the machine-authorized `Lead / resolve-question` worker carries a machine-derived debt disposition,
handle that exact selected closed-routing-debt candidate before the ordinary specification-resolution steps
below. The worker does not enumerate historical Issues, choose another candidate, or infer a disposition from
Issue prose.

- `terminal-cleanup`: require this exact Issue, immutable Change identity, and machine disposition
  `terminal-cleanup`. Reconstruct the terminal/retired evidence required by current default-branch governance,
  but do not turn that bounded candidate proof into repository-history enumeration. Request only the
  `terminal-retirement` effect for the same `issue_number` and `expected_change`. Keep the Issue closed; do not
  reopen it, edit OpenSpec artifacts, rewrite routing/history/body meaning, or request removal of unrelated
  labels. Repository application fresh-reauthorizes the exact source/disposition, fresh-observes that the same
  Issue remains closed with routing debt, removes only currently observed workflow `agent:*`/`action:*` labels
  through narrow effects, preserves unrelated labels, and accepts completion only after fresh observation of
  `closed + no workflow routing`. If another invocation already completed that postcondition, request no replay
  and allow fresh dispatch to consume the resulting state.
- `unfinished-recovery`: preserve the existing bounded premature-close recovery contract from
  `agents/AGENTS.md` and `agents/roles/lead.md`. The exact selected Issue must remain the sole qualifying
  unfinished debt candidate at formal-zero with no competing current debt or open formal workflow. Request only
  the same-Issue reopen/restoration effect that preserves immutable Change identity and the proven pre-close
  routing tuple. This recovery invocation does not execute that restored normal action; fresh dispatch selects
  the next mapped worker from the postcondition.
- Missing, indeterminate, contradictory, stale, or changed candidate/disposition evidence prohibits the debt
  effect and fails closed to the existing diagnosis/authority boundary. A machine debt disposition never grants
  broader specification-authoring authority.

When no machine debt disposition is present, use the ordinary specification-resolution procedure below.

1. Reconstruct the finding/blocker and the exact currently governed OpenSpec state.
2. Decide whether the finding is accepted, rejected, or already resolved using approved scope and evidence. Explain the decision durably. When that approved specification/scope decision explicitly creates a required deferred follow-up that must still be handled as a separate change, express it as one routing-complete requested logical postcondition. First reconstruct the approved source obligation and all matching trackers from durable evidence; tracker prose is evidence only and never supplies missing authority.
   - If no matching tracker exists, request creation of exactly one source-linked tracker with the exact source coordination Issue/Change and defer-decision/reference, `Change: unset`, and `agent:lead + action:explore-change` routing without Human admission.
   - If exactly one matching tracker exists and is incomplete only in durable fields or routing that Lead is already authorized to establish, request repair only of the missing durable fields/routing; do not request a duplicate.
   - If multiple or ambiguous matching trackers exist, fail closed; Lead must not choose a winner by model judgment and must not request another tracker.
   - Repository application fresh-reauthorizes the source, applies any create/repair atomically enough for the governed effect boundary, fresh-reads the tracker, and recognizes success only after the exact source linkage, `Change: unset`, and `agent:lead + action:explore-change` routing are durably observable.
   - Ordinary out-of-scope, non-goal, optional, or merely deferred prose does not create or route a tracker.
3. If the unresolved blocker is explicitly Human-reserved, only a valid provenance-bound Human decision may resolve it. For a canonical `HUMAN_DECISION_REQUIRED` escalation comment C, the exact expected reference is `issuecomment:<C>`; the qualifying Human-created answer comment must declare exactly `Human-Decision-For: issuecomment:<C>` and be bound by a later qualifying Human-only `human:approved` label event while that label is currently present. Actor identity, `human:notified`, or label snapshot alone does not resume the workflow.
4. If accepted, revise only Lead-owned OpenSpec specification artifacts needed to resolve it; do not modify implementation code to make a gate pass. Under `spec-driven`, materially revised artifacts must continue to satisfy the loaded adapter contract; do not let a correction drop surviving canonical scenarios/content or other canonicalization-ready information.
5. If OpenSpec artifacts changed materially, repeat the same required-artifact, required trace declarations/references authoring, and exact-revision strict-validation readiness checks used by `propose-change`. The semantic bidirectional PASS gate remains independent Reviewer work.
6. If the same implementation or correction PR remains in use, keep its coordination-Issue reference non-closing; resolving a specification question never authorizes adding Issue-closing linkage to an implementation PR.
7. Re-run the shared substantive Human-input freshness/disposition check immediately before returning the resolution and any requested routing effect.

Legal target action depends on the gate/blocker being resolved:

- revised OpenSpec requiring independent review → request `Reviewer / review-openspec`;
- implementation may continue under unchanged approved meaning → request `Executor / implement-change`;
- lifecycle/archive question → request the appropriate Lead finalize action only when the approved contract makes that legal;
- unresolved ambiguity or failed readiness evidence → retain Lead.

When the legal target is another Lead action on the same coordination Issue, return the source `ACTION_RESULT` plus requested routing effect. Repository application fresh-reauthorizes and applies the source result/routing, observes the target tuple, then fresh-dispatches. If that target is immediately selected, runtime creates a fresh Lead model invocation with the target action's mapped default-branch Skill. Same-role boundaries do not use `HANDOFF`; cross-role targets use canonical `HANDOFF` only after application observes the ownership transfer.

## Exact validation run observation

When `propose-change` or a materially revised `resolve-question` has just caused a just-triggered exact required run for OpenSpec validation, the first observation of that run as absent, `queued`, or `in_progress` is not by itself a reason to yield and does not establish async-wait Exit evidence. While bounded execution opportunity remains and no different authority boundary is required, observe only the same exact run using bounded same-invocation observation. After that first nonterminal observation, perform at least one subsequent fresh observation of the same exact target/resource before an ordinary asynchronous-wait Exit may be classified. If the subsequent fresh observation becomes terminal, consume its terminal result immediately and continue with the current action's next legal step.

Before returning from an exact-validation boundary, consume the shared Invocation Exit Proof invariant. A first absent/queued/in-progress observation is non-exit evidence. If a subsequent fresh observation still finds the same exact resource absent/nonterminal, current routing/revision/preconditions remain valid, and no other immediately actionable same-authority work remains, the existing asynchronous-wait Exit may be proven. Preserve the exact run identity for later fresh reconstruction rather than copying the generic Exit taxonomy into this Skill.

A later fresh mapped invocation does not trust the earlier nonterminal observation. It must fresh-read that exact run before deciding that waiting still applies. This specialization adds no timer, sleep policy, polling counter, heartbeat, retry counter, background service, or hidden waiter; the shared asynchronous-resource contract remains authoritative in `agents/AGENTS.md`.

## Human escalation producer

A genuine unresolved Human authority/intent decision uses canonical `HUMAN_DECISION_REQUIRED`. Lead returns the requested durable escalation effect. Repository application persists it first; the exact persisted escalation comment id C defines the current Human-response anchor `issuecomment:<C>`. A later response does not satisfy the boundary until the Human-created decision comment declares exactly `Human-Decision-For: issuecomment:<C>` and the provenance-bound approval predicate succeeds with a later qualifying Human-only `human:approved` event and current label presence.

After the escalation write succeeds, repository application idempotently ensures the `human:notified` label. The label is historical analytics-only observability: it does not participate in routing, waiting, authorization, resume conditions, or proof of Human response, and ordinary resolution does not remove it.

If `human:notified` is already present, the ensure is a no-op. If the label mutation fails while the escalation evidence is already durable, preserve the observable failure through the shared exception contract and disposition it from current evidence; do not request an identical denied mutation unless a fresh-read material precondition changed or a different legal repository operation path is available. The already-durable escalation remains authoritative even when label production fails.

## Durable messages

Use `agents/templates/messages.md` for recurring durable presentation. Lead readiness/resolution outcomes use the applicable `ACTION_RESULT`; a genuine unresolved Human authority/intent decision uses Lead-only `HUMAN_DECISION_REQUIRED`; a cross-role completed ownership transfer uses canonical `HANDOFF` only after repository application observes the routing mutation. Same-role action transitions continue from source result + applied routing + fresh dispatch without `HANDOFF`; do not add an action-transition message type.

For workflow-dynamic `Lead / propose-change`, the applicable `ACTION_RESULT` renders the exact activation evidence consumed by repository dispatch/application: the immediate pre-write executable decision, expected Change identity, post-write formal-active/terminal-pending Issue identities, post-write completeness, post-write observation provenance, post-write disposition, and whether activation accepted. These fields preserve the consumed pre-write/post-write decisions for audit and are not recomputed from a later model summary or reused as authorization by another invocation.

## Safety

- Do not infer missing specification meaning on behalf of Executor.
- Do not treat `run.head_sha` or a successful synthetic-merge validation for another checkout as exact-head proof for revision R.
- Do not require a duplicate local CLI run solely because valid exact-head CI validation already passed.
- Do not perform the Reviewer-owned semantic bidirectional PASS gate while authoring or revising OpenSpec artifacts.
- Do not treat actor identity, `human:approved`, `intake:approved`, or `human:notified` snapshots alone as sufficient Human authority.
- Scheduled roles MUST NOT add, remove, restore, or manufacture `human:approved` or `intake:approved`.
- The model worker does not directly persist durable result/routing/label mutations; request only bounded effects for repository-owned fresh reauthorization/application.
- A routing update is not a mutex/CAS; overlapping runtime executions must tolerate repeated observation and stop on stale/contradictory state.
