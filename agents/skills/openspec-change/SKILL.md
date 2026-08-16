# OpenSpec Change Skill

Mapped actions: `Lead / propose-change`, `Lead / resolve-question`.

This skill operationalizes approved OpenSpec authoring and specification-question resolution. It does
not replace the repository OpenSpec proposal/specs/design/tasks lifecycle.

## Spec-driven semantic adapter

When default-branch `openspec/config.yaml` declares `schema: spec-driven`, load
`agents/skills/openspec-semantic-adapter.md` before authoring or materially revising OpenSpec artifacts.
Consume its artifact-readiness, applicable config/context, delta-authoring, canonicalization-readiness,
and provenance contracts together with applicable canonical specs. If the configured schema or material
represented baseline is unsupported/mismatched, fail closed rather than substituting model memory,
mutable upstream `main`, or an inferred rule. The adapter is semantic input only; it does not change
runtime routing or Lead authority.

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

1. Confirm valid `Lead / propose-change` routing and the admission authority that legally produced it. Human direct-to-Propose admission MUST satisfy the provenance-bound Human-decision predicate for exactly `issue:<issue-number>:admission:lead:propose-change`. A same-Issue transition from a valid already-admitted Explore may instead rely on that Explore authority envelope when current governance authorizes direct continuation; do not manufacture a second Human admission requirement. Direct-to-Propose remains valid for Human direction that is already concrete/buildable; Explore is not a prerequisite.
2. If `Change:` is unset, reconstruct formal active/terminal-pending workflow state and the shared combined pre-activation queue before persisting any Change identity. The procedure must reconstruct active workflow state before persisting an unset Change identity.
   - If a formal active/terminal-pending workflow exists, keep this Issue queued and perform no activation.
   - If multiple formal active workflows or contradictory durable identity evidence exist, fail closed.
   - If no formal active/terminal-pending workflow exists, combine valid Human-admitted open `Lead / explore-change + Change: unset`, valid repository-authorized open `Lead / explore-change + Change: unset`, and valid Human-admitted `Lead / propose-change + Change: unset` entries, then choose the winner by earliest GitHub `created_at`, then lower Issue number.
   - A later direct-Propose Issue MUST NOT activate while an older eligible Explore is the deterministic combined pre-activation winner.
   - Immediately before the activation write, re-read durable state and require this Issue to remain the combined pre-activation winner; only the first valid activation may continue.
   - Persist the selected immutable Change identity as the activation write. Overlapping attempts use first-valid-write-wins semantics rather than a lock/claim/lease/heartbeat.
   - Immediately re-read durable state after the write. Only the first valid activation continues; a competing run that observes a different/newer durable result must stop as stale.
3. Author the minimum proposal, delta specs, design, and tasks needed by the approved direction. Keep the change single-purpose and preserve repository scope boundaries. Under `spec-driven`, satisfy the loaded semantic adapter's dependency/readiness and applicable config/context rules; for delta specs, apply its complete ADDED/MODIFIED/REMOVED/RENAMED and canonicalization-readiness contract rather than relying on strict validation alone.
4. Any proposal/implementation PR associated with the persistent coordination Issue must use a non-closing reference to the coordination Issue (for example `Refs #N`). It must not establish Issue-closing linkage. Closing linkage is reserved for the final Archive PR lifecycle boundary.
5. Before handoff, verify required artifacts exist and author/maintain the required trace declarations/references across proposal, specs, design, and tasks. These authoring references must be present and mechanically consistent enough to hand to independent review, but the semantic bidirectional PASS gate belongs to `Reviewer / review-openspec`; Lead MUST NOT execute or claim that independent PASS gate. For a NEW capability, require exactly one non-empty canonicalization-ready `## Purpose`; for existing capabilities, verify delta targets against canonical requirement identities and preserve all still-applicable MODIFIED scenarios/content.
6. Obtain strict OpenSpec validation for the exact handoff revision R. CI is sufficient only when durable validator evidence proves checkout `HEAD == R` before strict validation; `run.head_sha == R` alone is association metadata and is not checkout proof. If valid exact-head CI evidence is unavailable, use the repository-pinned local CLI directly against checkout R. Stale, missing, failed, revision-mismatched, or checkout-mismatched evidence fails closed.
7. Persist revision-aware readiness evidence before routing to `Reviewer / review-openspec` for the semantic bidirectional gate.

Legal outcomes:

- `READY_FOR_OPENSPEC_REVIEW` → hand off to `Reviewer / review-openspec`.
- queued behind a formal active/terminal-pending workflow or an older combined pre-activation winner → retain `Lead / propose-change` without activation noise.
- `SPECIFICATION_BLOCKED` or invalid/stale evidence → retain Lead; do not hand off as ready.

## `resolve-question`

1. Reconstruct the finding/blocker and the exact currently governed OpenSpec state.
2. Decide whether the finding is accepted, rejected, or already resolved using approved scope and evidence. Explain the decision durably.
3. If the unresolved blocker is explicitly Human-reserved, only a valid provenance-bound Human decision may resolve it. For a canonical `HUMAN_DECISION_REQUIRED` escalation comment C, the exact expected reference is `issuecomment:<C>`; the qualifying Human-created answer comment must declare exactly `Human-Decision-For: issuecomment:<C>` and be bound by a later qualifying Human-only `human:approved` label event while that label is currently present. Actor identity, `human:notified`, or label snapshot alone does not resume the workflow.
4. If accepted, revise only Lead-owned OpenSpec specification artifacts needed to resolve it; do not modify implementation code to make a gate pass. Under `spec-driven`, materially revised artifacts must continue to satisfy the loaded adapter contract; do not let a correction drop surviving canonical scenarios/content or other canonicalization-ready information.
5. If OpenSpec artifacts changed materially, repeat the same required-artifact, required trace declarations/references authoring, and exact-revision strict-validation readiness checks used by `propose-change`. The semantic bidirectional PASS gate remains independent Reviewer work.
6. If the same implementation or correction PR remains in use, keep its coordination-Issue reference non-closing; resolving a specification question never authorizes adding Issue-closing linkage to an implementation PR.
7. Persist the resolution and current revision before routing.

Legal target action depends on the gate/blocker being resolved:

- revised OpenSpec requiring independent review → `Reviewer / review-openspec`;
- implementation may continue under unchanged approved meaning → `Executor / implement-change`;
- lifecycle/archive question → route to the appropriate Lead finalize action only when the approved contract makes that legal;
- unresolved ambiguity or failed readiness evidence → retain Lead.

When the legal target is another Lead action on the same coordination Issue, perform the source `ACTION_RESULT`, fresh-read and replace the action routing, observe the target tuple, then reconstruct that target action using its mapped default-branch skill. If it is immediately actionable, continue in the same invocation under the shared fixed-role contract without `HANDOFF`. Cross-role targets still use canonical `HANDOFF` and end the invocation.

## Exact validation run observation

When `propose-change` or a materially revised `resolve-question` has just caused a just-triggered exact required run for OpenSpec validation, the first observation of that run as `queued` or `in_progress` is not by itself a reason to yield. While bounded execution opportunity remains and no different authority boundary is required, observe only the same exact run using bounded same-invocation observation. If the same exact run becomes terminal, consume its terminal result and continue immediately with the current action's next legal step. If it remains nonterminal when bounded execution opportunity is exhausted, that is a real external asynchronous wait.

A later wake does not trust the earlier nonterminal observation. It must fresh-read that exact run before deciding that waiting still applies. This specialization adds no timer, sleep policy, polling counter, heartbeat, retry counter, background service, or hidden waiter; the shared asynchronous-resource contract remains authoritative in `agents/AGENTS.md`.

## Human escalation producer

A genuine unresolved Human authority/intent decision uses canonical `HUMAN_DECISION_REQUIRED`. Lead first
persists the durable escalation evidence. The exact persisted escalation comment id C defines the current
Human-response anchor `issuecomment:<C>`. A later response does not satisfy the boundary until the Human-created
decision comment declares exactly `Human-Decision-For: issuecomment:<C>` and the provenance-bound approval
predicate succeeds with a later qualifying Human-only `human:approved` event and current label presence.
After the escalation write succeeds, Lead MUST idempotently ensure the `human:notified` label. The label is
historical analytics-only observability: it does not participate in routing, waiting, authorization, resume
conditions, or proof of Human response, and ordinary resolution does not remove it.

If `human:notified` is already present, the ensure is a no-op. If the label mutation fails while the
escalation evidence is already durable, capture the observable failure through the shared exception
contract and disposition it from current evidence; do not repeat an identical denied mutation unless a
fresh-read material precondition changed or a different legal repository operation path is available.
The already-durable escalation remains authoritative even when label production fails.

## Durable messages

Use `agents/templates/messages.md` for recurring durable presentation. Lead readiness/resolution outcomes
use the applicable `ACTION_RESULT`; a genuine unresolved Human authority/intent decision uses Lead-only
`HUMAN_DECISION_REQUIRED`; a cross-role completed ownership transfer uses canonical `HANDOFF` only after
the routing mutation succeeds. Same-role action transitions continue from the source result and routing
mutation without `HANDOFF`; do not add an action-transition message type.

## Safety

- Do not infer missing specification meaning on behalf of Executor.
- Do not treat `run.head_sha` or a successful synthetic-merge validation for another checkout as
  exact-head proof for revision R.
- Do not require a duplicate local CLI run solely because valid exact-head CI validation already passed.
- Do not perform the Reviewer-owned semantic bidirectional PASS gate while authoring or revising OpenSpec artifacts.
- Do not treat actor identity, `human:approved`, `intake:approved`, or `human:notified` snapshots alone as sufficient Human authority.
- Scheduled roles MUST NOT add, remove, restore, or manufacture `human:approved` or `intake:approved`.
- Persist durable result/evidence before routing and fresh-read routing before the label mutation.
- A routing update is not a mutex/CAS; overlapping Lead runs must tolerate repeated observation and stop on stale/contradictory state.
