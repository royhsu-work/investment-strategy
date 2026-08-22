# Design: Enforce runtime dispatch preconditions

## Context

#105 corrected the workflow semantics but intentionally stopped at prose-governed runtime behavior plus a test-only classifier. That design was reasonable for the then-observed incident, but the later #100/#130 recurrence demonstrates that the live Scheduled-Agent path can still bypass or misapply the prose precondition while the parallel fixture model remains green.

The first proven illegal mapped action in the original recurrence was `explore-change`, not a near-simultaneous activation race. The repository therefore needs an executable decision surface at action entry. The design must not pretend that GitHub Issue mutation APIs expose a cross-Issue atomic compare-and-swap primitive when the current connector does not.

Reviewer finding `issuecomment-5377194503` exposed a second, distinct trust boundary that the initial formal target omitted: a correct classifier can still return the wrong current authorization result when its normalized input was synthesized from stale conversation/prior-run/cache/history instead of authoritative GitHub observations from the current invocation. The correction below treats **decision correctness** and **input authority** as separate required layers. It does not retroactively claim that this later observation-provenance failure mode was established at the original Explore handoff.

## Decision 1 — One pure executable dispatch-precondition module

Add one repository-owned production module, `src/investment_strategy/workflow_dispatch.py`, containing the deterministic workflow-dynamic classifier/precondition logic that is currently duplicated as a test-local model.

The module accepts explicit normalized inputs rather than reading GitHub itself:

```text
RepositoryIssueSnapshot
- issue_number
- created_at
- open/closed state
- Change identity
- routing role/action
- only the bounded lifecycle/recovery fields required by shared governance
- current-observation provenance for authorization-bearing fields

EnumerationEvidence
- observed open-Issue count
- source-reported total count when available
- incomplete/truncated indicator
- pagination/exhaustion proof supplied by the acquisition adapter
- authoritative GitHub observation identity/surface for this invocation

DispatchPreflight
- snapshot collection
- enumeration evidence
- optional selected/candidate Issue expected by the caller
```

It returns a structured immutable decision, for example:

```text
DispatchDecision
- completeness: COMPLETE | INDETERMINATE
- observation_provenance: QUALIFIED | INDETERMINATE
- formal_issue_ids
- recovery_candidate_ids
- preactivation_candidate_ids
- selected_issue_id | None
- selected_role/action | None
- disposition: AUTHORIZE | FAIL_CLOSED | NO_WORK
- reason
```

The exact names are implementation detail; the required property is one deterministic executable result carrying enough structured evidence for both authorization and durable presentation.

The module does **not** own GitHub acquisition, routing mutation, lifecycle topology, or Human authority. `agents/AGENTS.md` remains the semantic owner and the production function is its executable adapter.

### Why a pure module

- Tests can call the same code as runtime authorization.
- The classifier remains stateless and has no hidden repository state.
- Acquisition completeness and classification are explicit instead of inferred from a candidate-local query.
- Observation provenance is explicit, so stale model-constructed inputs cannot masquerade as current authoritative repository state.
- The runtime can fail closed when the function cannot execute or when current-source provenance cannot be established rather than silently falling back to model interpretation.

## Decision 1A — Current-state input authority is part of the executable contract

The acquisition layer remains outside `workflow_dispatch.py`, but the production decision surface accepts authorization-bearing snapshots only when their current-state fields are provenance-qualified as authoritative GitHub observations from the same invocation.

For current dispatch predicates, the acquisition adapter/procedure must establish at minimum:

- current Issue open/closed state;
- current routing labels/tuple;
- current persisted `Change:` identity;
- repository-wide enumeration completeness sufficient for the governed classifier;
- enough source metadata to prove that these values came from the current invocation's GitHub reads rather than conversation history, prior invocation output, cache, copied Issue summaries, or historical body/comment routing.

Historical durable evidence remains valid for genuinely historical/lifecycle predicates, but it never fills a missing current routing/state field. A previously routed Issue with current routing labels removed is therefore normalized as currently unrouted even if old HANDOFF/body/comment text still describes the former tuple.

If the runtime cannot obtain or prove a required current field from same-invocation authoritative GitHub evidence, it constructs an indeterminate provenance/completeness result and the executable precondition fails closed. It does not substitute the last known value.

This keeps acquisition replaceable while preventing the classifier boundary from accepting an unqualified model-built snapshot as if it were current repository fact.

## Decision 2 — Runtime execution must consume, not paraphrase, the executable result

Update shared governance so workflow-dynamic dispatch and action-entry checks require executing the default-branch classifier against the fresh complete, provenance-qualified snapshot.

A Scheduled/manual Agent MAY obtain the raw GitHub state through the connector/tool surface, but it MUST NOT replace the executable decision with its own candidate-local or prose-derived classification. It also MUST NOT populate current routing/state/Change fields from conversation history, previous Scheduled output, model memory/cache, or historical Issue text. If the runtime cannot execute the default-branch helper byte-for-byte/equivalently, cannot supply complete enumeration evidence, cannot establish same-invocation authoritative observation provenance, or cannot normalize the required fields without ambiguity, disposition is fail closed.

The external Scheduled Task prompt stays bootstrap-only. It continues to say “load default-branch governance”; the repository tells the selected runtime how to load/execute the helper and qualify its input.

## Decision 3 — `explore-change` consumes executable action-entry authorization

Before substantive pre-activation Explore research, `openspec-explore` requires a fresh executable decision proving:

- enumeration is complete;
- authorization-bearing current fields came from same-invocation authoritative GitHub observations;
- formal active cardinality is zero;
- no bounded recovery candidate blocks intake;
- the current Issue is the deterministic combined pre-activation winner; and
- selected routing is still `Lead / explore-change`.

If any predicate fails, Explore does not begin substantive research and the Agent reconstructs/fails closed according to shared governance.

This directly rejects both demonstrated safety shapes: a snapshot containing formal-active #100 cannot authorize queued #130 Explore, and historical #130 routing text cannot make #130 current-active when current GitHub routing labels are absent.

## Decision 4 — Propose consumes the same executable gate before and after activation

`openspec-change` keeps formal activation ownership but replaces prose-only reconstruction decisions with the same executable precondition:

1. **Immediate pre-write:** fresh complete, provenance-qualified snapshot must authorize this `Lead / propose-change` Issue as the legal pre-activation winner with no formal active workflow.
2. **Activation write:** persist the immutable non-`unset` Change identity.
3. **Immediate post-write:** fresh complete, provenance-qualified snapshot is classified again. Activation is accepted only when exactly one formal active workflow exists and it is this Issue with the expected routing/Change identity.

If post-write state contains another formal workflow, is incomplete, lacks same-invocation current-state provenance, or contradicts the expected identity, the current invocation fails closed/stops stale. It does not choose a winner, reuse the pre-write snapshot, or automatically rewrite another Issue.

### Overlapping activation limitation

The current GitHub connector's Issue update surface exposes no cross-Issue atomic compare/precondition parameter. Therefore this Change does not claim that a pure read/classify/write sequence can make two simultaneous writes physically impossible. Instead, “accepted activation” remains post-write validated: two competing durable writes cannot both be accepted as legal continuations because the shared post-write classifier returns multiple-active and blocks normal action progression.

The demonstrated original #100/#130 recurrence was not a tight activation race, so a lock/lease/durable claim is not justified by the incident. If future evidence requires physical prevention of transient double persistence, that is a separate mutation-primitive/serialization decision rather than something to conceal inside this classifier.

## Decision 5 — Regression tests import the production classifier

Refactor `tests/test_dispatch_cardinality_preflight.py` so it imports the production decision types/function instead of defining local `WorkflowIssue`, `Snapshot`, `classify`, `action_entry_allowed`, `activate`, and `activation_still_valid` logic.

Keep fixture-driven tests, but make them evidence for the actual executable authorization surface. Required regressions include:

- zero formal WIP selects the deterministic pre-activation winner;
- one formal active blocks queued Explore and Propose;
- incomplete/partial enumeration returns indeterminate/fail closed;
- candidate-local or role-local input cannot establish completeness;
- two formal active workflows authorize no mapped action;
- stale action-entry snapshot is rejected by a fresh invocation;
- the exact #100/#130 recurrence shape rejects #130 Explore;
- an Issue with historical routing evidence but current routing labels absent is not classified active from history;
- prior invocation output/cache cannot satisfy current state/routing/Change predicates;
- inability to obtain same-invocation authoritative current routing/state produces indeterminate rather than fallback-to-history;
- Propose pre-write blocks a second activation when formal work already exists;
- post-write competing activation yields no accepted activation and no normal successor;
- Human/maintainer administrative repair remains external and a later decision uses only fresh authoritative current state.

Tests that only assert governance phrases may remain as structural SSOT checks, but they are not substitutes for executable behavior tests.

## Decision 6 — Canonical action results expose the same decision evidence

Do not introduce a second dispatch state store or a debug-only message bus. Extend the existing canonical `ACTION_RESULT` presentation for the two pre-activation boundaries:

### `Lead / explore-change`

When an Explore result is persisted after substantive research, include the executable action-entry evidence actually consumed:

- enumeration completeness;
- observation provenance sufficient to identify the authoritative current GitHub read surface/result consumed;
- formal-active Issue IDs;
- bounded recovery candidate IDs when any were considered;
- combined pre-activation candidate Issue IDs;
- selected Issue ID;
- executable disposition/reason sufficient to prove authorization.

### `Lead / propose-change`

Include:

- the pre-write executable decision fields above;
- the activation write's expected Change identity;
- post-write formal-active Issue IDs;
- post-write completeness/provenance/disposition;
- whether activation was accepted.

These fields are audit/debug evidence only. `Change + agent + action` remains canonical workflow state, and the comment MUST NOT be used as a replacement authorization token on a later wake.

When the runtime supplies a stable wake/invocation-source identifier, the message MAY preserve it for correlation. If the runtime does not expose one, the Agent MUST NOT fabricate scheduler identity or infer a task/slot from timing. Observation provenance does not require such a scheduler identifier; it requires proof that the authorization-bearing repository fields came from authoritative GitHub reads in the current invocation.

## Decision 7 — No new Skill; two existing Skills get minimal consumption changes

The executable classifier is shared runtime infrastructure, not a user-triggered Skill. Do not create a `dispatch-preflight` Skill merely to wrap one deterministic function.

Modify only:

- `agents/skills/openspec-explore/SKILL.md`: before substantive research, execute/consume the shared helper using same-invocation authoritative current-state evidence and retain its result for the later `ACTION_RESULT` evidence.
- `agents/skills/openspec-change/SKILL.md`: execute/consume it immediately before and after formal activation using fresh same-invocation authoritative current-state evidence and retain those exact results for readiness evidence.

Both Skills reference shared governance/helper ownership rather than duplicating classifier or provenance rules. This follows `skill-creator` progressive-disclosure and SSOT guidance.

## Decision 8 — External Scheduled Task configuration remains unchanged

No slot count, cadence, title, legacy role, or prompt execution semantics change is required. Current bootstrap prompts already load default-branch governance dynamically. The fix belongs in the repository-owned execution surface.

This also means #133 does not attempt to identify historical external Scheduled Task run IDs that GitHub durable state never recorded. New optional correlation evidence is prospective only.

## Traceability

- Source Explore: #133 `issuecomment-5373937613`.
- Post-handoff Reviewer correction: #133 `issuecomment-5377194503`.
- Evidence-discipline clarification: #133 `issuecomment-5377184598`; later evidence is not projected backward into the original Explore timeline.
- Original incident: #100 formal-active durable evidence and #130 Explore/Propose action results.
- Current-state provenance regression: current GitHub routing/state observations control current classification; historical Issue routing/body/comment evidence is audit context only.
- Prior semantics: #105 / `enforce-dispatch-cardinality-preflight`.
- Modified canonical requirement: `Active-workflow cardinality and Issue-state coherence precede queue selection`.
- Decisions 1–5 -> executable classifier + input-authority/runtime/test consumption.
- Decision 6 -> canonical `ACTION_RESULT` observability.
- Decision 7 -> minimal Skill changes with Skill maintenance traceability.
- Decision 8 -> Scheduled Task bootstrap negative scope.

## Risks and mitigations

### Risk: Executable helper becomes a second workflow authority

Mitigation: keep topology, authority, queue semantics, and Human rules in their existing owners. The helper implements only the approved dispatch-precondition decision and exposes structured evidence.

### Risk: Correct classifier receives stale or model-constructed input

Mitigation: make same-invocation authoritative GitHub observation provenance part of the executable input contract. Unqualified current-state fields cannot authorize work; missing provenance yields indeterminate/fail closed rather than last-known-state fallback.

### Risk: Runtime cannot execute repository code or qualify current observations

Mitigation: fail closed explicitly. Do not silently fall back to prose/model classification or historical context at a consequential dispatch boundary. The implementation must document and test the supported execution/acquisition adapter used by the current Scheduled-Agent environment.

### Risk: Structured evidence becomes workflow state

Mitigation: canonical comments are audit evidence only. Every later invocation fresh-reconstructs repository Issue state from authoritative GitHub observations and reruns the executable classifier.

### Risk: Physical overlapping writes remain possible

Mitigation: distinguish **accepted activation** from raw write completion. The immediate post-write executable check blocks both competing states from normal continuation. Do not introduce a hidden mutex without concrete evidence that a stronger mutation primitive is required.
