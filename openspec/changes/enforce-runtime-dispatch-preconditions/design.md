# Design: Enforce runtime dispatch preconditions

## Context

#105 corrected the workflow semantics but intentionally stopped at prose-governed runtime behavior plus a test-only classifier. That design was reasonable for the then-observed incident, but the later #100/#130 recurrence demonstrates that the live Scheduled-Agent path can still bypass or misapply the prose precondition while the parallel fixture model remains green.

The exact durable timeline matters:

```text
2026-08-21T15:33:08Z  #100 -> Lead / finalize-change (formal-active)
2026-08-21T15:48:15Z  #130 Lead / explore-change -> PROPOSAL_READY
2026-08-21T15:50:29Z  #130 Lead / propose-change -> formal activation
```

The first proven illegal mapped action is therefore `explore-change`, not a near-simultaneous activation race. The repository needs an executable decision surface at action entry. The design must not pretend that GitHub Issue mutation APIs expose a cross-Issue atomic compare-and-swap primitive when the current connector does not.

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

EnumerationEvidence
- observed open-Issue count
- source-reported total count when available
- incomplete/truncated indicator
- pagination/exhaustion proof supplied by the acquisition adapter

DispatchPreflight
- snapshot collection
- enumeration evidence
- optional selected/candidate Issue expected by the caller
```

It returns a structured immutable decision, for example:

```text
DispatchDecision
- completeness: COMPLETE | INDETERMINATE
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
- The runtime can fail closed when the function cannot execute rather than silently falling back to model interpretation.

## Decision 2 — Runtime execution must consume, not paraphrase, the executable result

Update shared governance so workflow-dynamic dispatch and action-entry checks require executing the default-branch classifier against the fresh complete snapshot.

A Scheduled/manual Agent MAY obtain the raw GitHub state through the connector/tool surface, but it MUST NOT replace the executable decision with its own candidate-local or prose-derived classification. If the runtime cannot execute the default-branch helper byte-for-byte/equivalently, cannot supply complete enumeration evidence, or cannot normalize the required fields without ambiguity, disposition is fail closed.

The external Scheduled Task prompt stays bootstrap-only. It continues to say “load default-branch governance”; the repository tells the selected runtime how to load/execute the helper.

## Decision 3 — `explore-change` consumes executable action-entry authorization

Before substantive pre-activation Explore research, `openspec-explore` requires a fresh executable decision proving:

- enumeration is complete;
- formal active cardinality is zero;
- no bounded recovery candidate blocks intake;
- the current Issue is the deterministic combined pre-activation winner; and
- selected routing is still `Lead / explore-change`.

If any predicate fails, Explore does not begin substantive research and the Agent reconstructs/fails closed according to shared governance.

This directly rejects the #100/#130 recurrence: a snapshot containing formal-active #100 cannot authorize queued #130 Explore.

## Decision 4 — Propose consumes the same executable gate before and after activation

`openspec-change` keeps formal activation ownership but replaces prose-only reconstruction decisions with the same executable precondition:

1. **Immediate pre-write:** fresh complete snapshot must authorize this `Lead / propose-change` Issue as the legal pre-activation winner with no formal active workflow.
2. **Activation write:** persist the immutable non-`unset` Change identity.
3. **Immediate post-write:** fresh complete snapshot is classified again. Activation is accepted only when exactly one formal active workflow exists and it is this Issue with the expected routing/Change identity.

If post-write state contains another formal workflow, is incomplete, or contradicts the expected identity, the current invocation fails closed/stops stale. It does not choose a winner or automatically rewrite another Issue.

### Overlapping activation limitation

The current GitHub connector's Issue update surface exposes no cross-Issue atomic compare/precondition parameter. Therefore this Change does not claim that a pure read/classify/write sequence can make two simultaneous writes physically impossible. Instead, “accepted activation” remains post-write validated: two competing durable writes cannot both be accepted as legal continuations because the shared post-write classifier returns multiple-active and blocks normal action progression.

The demonstrated #100/#130 recurrence was not such a tight race—#100 had been formal-active for about fifteen minutes—so a lock/lease/durable claim is not justified by the incident. If future evidence requires physical prevention of transient double persistence, that is a separate mutation-primitive/serialization decision rather than something to conceal inside this classifier.

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
- Propose pre-write blocks a second activation when formal work already exists;
- post-write competing activation yields no accepted activation and no normal successor;
- Human/maintainer administrative repair remains external and a later decision uses only fresh state.

Tests that only assert governance phrases may remain as structural SSOT checks, but they are not substitutes for executable behavior tests.

## Decision 6 — Canonical action results expose the same decision evidence

Do not introduce a second dispatch state store or a debug-only message bus. Extend the existing canonical `ACTION_RESULT` presentation for the two pre-activation boundaries:

### `Lead / explore-change`

When an Explore result is persisted after substantive research, include the executable action-entry evidence actually consumed:

- enumeration completeness;
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
- post-write completeness/disposition;
- whether activation was accepted.

These fields are audit/debug evidence only. `Change + agent + action` remains canonical workflow state, and the comment MUST NOT be used as a replacement authorization token on a later wake.

When the runtime supplies a stable wake/invocation-source identifier, the message MAY preserve it for correlation. If the runtime does not expose one, the Agent MUST NOT fabricate scheduler identity or infer a task/slot from timing.

## Decision 7 — No new Skill; two existing Skills get minimal consumption changes

The executable classifier is shared runtime infrastructure, not a user-triggered Skill. Do not create a `dispatch-preflight` Skill merely to wrap one deterministic function.

Modify only:

- `agents/skills/openspec-explore/SKILL.md`: before substantive research, execute/consume the shared helper and retain its result for the later `ACTION_RESULT` evidence.
- `agents/skills/openspec-change/SKILL.md`: execute/consume it immediately before and after formal activation and retain those exact results for readiness evidence.

Both Skills reference shared governance/helper ownership rather than duplicating classifier rules. This follows `skill-creator` progressive-disclosure and SSOT guidance.

## Decision 8 — External Scheduled Task configuration remains unchanged

No slot count, cadence, title, legacy role, or prompt execution semantics change is required. Current bootstrap prompts already load default-branch governance dynamically. The fix belongs in the repository-owned execution surface.

This also means #133 does not attempt to identify historical external Scheduled Task run IDs that GitHub durable state never recorded. New optional correlation evidence is prospective only.

## Traceability

- Source Explore: #133 `issuecomment-5373937613`.
- Incident: #100 formal-active handoff and #130 Explore/Propose action results.
- Prior semantics: #105 / `enforce-dispatch-cardinality-preflight`.
- Modified canonical requirement: `Active-workflow cardinality and Issue-state coherence precede queue selection`.
- Decisions 1–5 -> executable classifier + runtime/test consumption.
- Decision 6 -> canonical `ACTION_RESULT` observability.
- Decision 7 -> minimal Skill changes with Skill maintenance traceability.
- Decision 8 -> Scheduled Task bootstrap negative scope.

## Risks and mitigations

### Risk: Executable helper becomes a second workflow authority

Mitigation: keep topology, authority, queue semantics, and Human rules in their existing owners. The helper implements only the approved dispatch-precondition decision and exposes structured evidence.

### Risk: Runtime cannot execute repository code

Mitigation: fail closed explicitly. Do not silently fall back to prose/model classification at a consequential dispatch boundary. The implementation must document and test the supported execution adapter used by the current Scheduled-Agent environment.

### Risk: Structured evidence becomes workflow state

Mitigation: canonical comments are audit evidence only. Every later invocation fresh-reconstructs repository Issue state and reruns the executable classifier.

### Risk: Physical overlapping writes remain possible

Mitigation: distinguish **accepted activation** from raw write completion. The immediate post-write executable check blocks both competing states from normal continuation. Do not introduce a hidden mutex without concrete evidence that a stronger mutation primitive is required.
