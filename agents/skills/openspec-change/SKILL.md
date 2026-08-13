# OpenSpec Change Skill

Mapped actions: `Lead / propose-change`, `Lead / resolve-question`.

This skill operationalizes approved OpenSpec authoring and specification-question resolution. It does
not replace the repository OpenSpec proposal/specs/design/tasks lifecycle.

## Reconstruct before acting

Read from durable state:

- default-branch `agents/AGENTS.md`, `agents/roles/lead.md`, and this skill;
- coordination Issue routing and immutable `Change:` identity when set;
- current active OpenSpec proposal/specs/design/tasks and applicable canonical specs;
- applicable `README.md` and `openspec/config.yaml` governance;
- relevant durable Issue/review findings;
- exact current repository/branch revision and strict OpenSpec validation evidence.

If the coordination Issue or current OpenSpec artifacts contain declared upstream authoritative decision/gate references, Lead MUST dereference those sources during `propose-change` and any materially revised `resolve-question`. A cross-Issue summary is orientation only and is not replacement authority for the declared source evidence.

If routing, change identity, active-workflow identity, or required evidence is contradictory, fail closed.

## `propose-change`

1. Confirm explicit Human/maintainer admission and valid `Lead / propose-change` routing.
2. If `Change:` is unset, reconstruct active workflow state before persisting an unset Change identity.
   - If another persisted Change workflow is active, keep this Issue queued and perform no activation.
   - If multiple active workflows or contradictory durable identity evidence exist, fail closed.
   - If no active workflow exists, choose among valid Human-admitted queued proposals by earliest GitHub
     `created_at`, then lower Issue number; only the selected Issue may attempt activation.
   - Persist the selected immutable Change identity as the activation write. Overlapping attempts use
     first-valid-write-wins semantics rather than a lock/claim/lease/heartbeat.
   - Immediately re-read durable state after the write. Only the first valid activation continues; a
     competing run that observes a different/newer durable result must stop as stale.
3. Author the minimum proposal, delta specs, design, and tasks needed by the approved direction. Keep the
   change single-purpose and preserve repository scope boundaries.
4. Any proposal/implementation PR associated with the persistent coordination Issue must use a
   non-closing reference to the coordination Issue (for example `Refs #N`). It must not establish Issue-closing linkage. Closing linkage is reserved for the final Archive PR lifecycle boundary.
5. Before handoff, verify required artifacts exist and author/maintain the required trace declarations/references across proposal, specs, design, and tasks. These authoring references must be present and mechanically consistent enough to hand to independent review, but the semantic bidirectional PASS gate belongs to `Reviewer / review-openspec`; Lead MUST NOT execute or claim that independent PASS gate.
6. Obtain strict OpenSpec validation for the exact handoff revision R. CI is sufficient only when
   durable validator evidence proves checkout `HEAD == R` before strict validation; `run.head_sha == R`
   alone is association metadata and is not checkout proof. If valid exact-head CI evidence is
   unavailable, use the repository-pinned local CLI directly against checkout R. Stale, missing,
   failed, revision-mismatched, or checkout-mismatched evidence fails closed.
7. Persist revision-aware readiness evidence before routing to `Reviewer / review-openspec` for the semantic bidirectional gate.

Legal outcomes:

- `READY_FOR_OPENSPEC_REVIEW` → hand off to `Reviewer / review-openspec`.
- queued behind another active workflow → retain `Lead / propose-change` without activation noise.
- `SPECIFICATION_BLOCKED` or invalid/stale evidence → retain Lead; do not hand off as ready.

## `resolve-question`

1. Reconstruct the finding/blocker and the exact currently governed OpenSpec state.
2. Decide whether the finding is accepted, rejected, or already resolved using approved scope and
   evidence. Explain the decision durably.
3. If accepted, revise only Lead-owned OpenSpec specification artifacts needed to resolve it; do not
   modify implementation code to make a gate pass.
4. If OpenSpec artifacts changed materially, repeat the same required-artifact, required trace declarations/references authoring, and exact-revision strict-validation readiness checks used by `propose-change`. The semantic bidirectional PASS gate remains independent Reviewer work.
5. If the same implementation or correction PR remains in use, keep its coordination-Issue reference
   non-closing; resolving a specification question never authorizes adding Issue-closing linkage to an
   implementation PR.
6. Persist the resolution and current revision before handoff.

Legal handoff depends on the gate/blocker being resolved:

- revised OpenSpec requiring independent review → `Reviewer / review-openspec`;
- implementation may continue under unchanged approved meaning → `Executor / implement-change`;
- lifecycle/archive question → return to the appropriate Lead finalize action only when the approved
  contract makes that legal;
- unresolved ambiguity or failed readiness evidence → retain Lead.

## Durable messages

Use `agents/templates/messages.md` for recurring durable presentation. Lead readiness/resolution outcomes
use the applicable `ACTION_RESULT`; a genuine unresolved Human authority/intent decision uses Lead-only
`HUMAN_DECISION_REQUIRED`; and a completed ownership transfer uses canonical `HANDOFF` only after the
routing mutation succeeds. Do not copy private template bodies into this skill.

## Safety

- Do not infer missing specification meaning on behalf of Executor.
- Do not treat `run.head_sha` or a successful synthetic-merge validation for another checkout as
  exact-head proof for revision R.
- Do not require a duplicate local CLI run solely because valid exact-head CI validation already passed.
- Do not perform the Reviewer-owned semantic bidirectional PASS gate while authoring or revising OpenSpec artifacts.
- Persist durable result/evidence before routing and fresh-read routing before the label mutation.
- A routing update is not a mutex/CAS; overlapping Lead runs must tolerate repeated observation and
  stop on stale/contradictory state.
