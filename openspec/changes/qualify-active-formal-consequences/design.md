# Design: Qualify active formal consequences

## Decision boundary

The parent outcome is repository-wide and remains small:

observable current evidence
+ explicit machine-decidable predicates
→ qualification by the existing executable owner of the consequence
→ consequence becomes eligible

Issue #229 is one concrete P0 proof case. The latest direct Human correction is issuecomment-5598442708. It removes workflow-specific mechanics from the generic rule, removes actor identity as a trust boundary, requires latest-applicable-transition binding including ABA, and requires no-delta dispositions before implementation.

Fresh evidence at main revision e4dcad8ad0326a6a38620998ee2f03ebcc060a19 is:

- Issue #229 open, Change qualify-active-formal-consequences, action:resolve-question.
- Existing PR #232 open on agent/qualify-active-formal-consequences at 2366bbfa853576b4d1f736c9833d7ed3b799822c.
- Prior review PASS issuecomment-5597482415 targets 2366bbfa853576b4d1f736c9833d7ed3b799822c, but predates the material Human correction and is not approval of this revised meaning.
- Application SPEC_BLOCKER issuecomment-5598786757 records the stale-review boundary.

The existing Change and PR are updated in place. No new Change, PR, state, or workflow is introduced.

## Ownership and subtraction

repository-governance owns one generic invariant: an existing canonical executable owner evaluates one affirmative qualification predicate before a machine-decidable repository consequence becomes eligible. It defines ownership and use of the result only. It does not define scheduled-agent routing, Change, ObservationProvenance, Action/Result, transport, carrier, terminal, or workflow-specific evidence.

scheduled-agent-workflow owns the concrete P0 predicate. Existing executable owners remain:

- scheduled_agent_runtime.py and workflow_dispatch.py for fresh current-state reconstruction and dispatch input;
- scheduled_agent_action_model.py for the finite Action/Role/Result vocabulary, legal transitions, and model-derived successor;
- scheduled_agent_effects.py and the application bridge for fresh application authorization and durable effect postconditions;
- existing GitHub event, comment, label, branch, PR, and commit surfaces for evidence; and
- the existing CarrierRequired plan for replaceable carrier execution.

No new protocol, state registry, ledger, cursor, lease, retry state, policy engine, carrier type, or competing authority is introduced.

## Concrete qualification predicate

For Change != unset, the existing scheduled-agent owner evaluates one predicate before dispatch or consequence:

1. Reconstruct the current Issue, routing, lifecycle, PR/ref, relevant comments, events, and default-branch revision from current GitHub evidence.
2. Identify the latest applicable repository-authorized transition for the same Issue and immutable Change. Its evidence contains the accepted Action/Result and binds current Action/Role identity, relevant source and default-branch revisions, and model-derived next_action when a successor exists.
3. Require the exact durable postcondition for that transition: current action label or terminal/close state, linked PR/ref/commit where applicable, or another existing application-owned postcondition.
4. Order candidates with existing durable lifecycle/event history and reject a candidate if a later relevant mutation supersedes it. Actor, connector, carrier, timestamp, or value equality alone never supplies the binding.
5. Mark the observation QUALIFIED only when one unique coherent binding remains. Otherwise mark it INDETERMINATE and let the existing complete-observation/dispatch boundary fail closed.

This is reconstruction-time judgment, not a persisted workflow state. The application still derives routing, successor, terminal, and success effects from the finite model and postconditions.

## Latest transition and ABA

The current value is not provenance identity:

- T1: repository-authorized transition A to B;
- T2: out-of-band mutation B to C;
- T3: out-of-band mutation C to B;
- fresh current state equals B.

T1 is not applicable to the current B. The owner must bind the fresh observation to the latest applicable qualified transition and show that no later relevant mutation superseded it. If that cannot be established, the current active-formal observation is INDETERMINATE.

## Evidence reuse and smallest fallback

First reuse existing evidence:

- Issue event identity and lifecycle ordering for label, close, reopen, and related mutations;
- existing formal Action/Result comments and exact revision fields;
- application authorization against current main;
- current finite transition derivation;
- branch, PR, commit, and exact postcondition observation; and
- existing CarrierRequired plan and later ref/PR postcondition.

Event history is ordering evidence, but actor and timestamp are not sufficient. If implementation proves these surfaces cannot uniquely establish causal binding, add only the smallest exact correlation identity required for that one binding. Do not add a registry, ledger, cursor, second protocol, or generic provenance framework.

## No-delta dispositions

| Boundary | Disposition |
| --- | --- |
| First Change materialization | Existing Lead / propose-change application path is sufficient; no delta. |
| Change: unset intake | Existing Explore/Propose pre-activation contract remains; no active-formal guard before Change persistence. |
| Carrier execution | Existing CarrierRequired boundary and immutable plan remain; carrier identity is not authority. |
| OpenSpec authoring guidance | Current openspec/config.yaml is sufficient; no delta. |
| #218 | Downstream boundary remains unchanged and out of scope. |
| Action/Role/Result model | Existing finite model remains sole executable owner; no new vocabulary. |

## Application and delivery boundary

The Lead correction changes only the semantic OpenSpec work product. Existing application materialization remains responsible for checking exact main authorization, current Issue/Action/Role and PR identity, resolving content-addressed blobs into one Change-branch commit, requiring the existing carrier plan for the branch/ref move, and validating the exact PR head before deriving a successor.

A carrier-required invocation persists only its exact plan and stops. A later fresh wake reconstructs current state and applies only still-missing effects. No successor is executed in the same wake.

## Verification boundary

The implementation must prove observable behavior:

- Change: unset legitimate intake remains eligible;
- qualified repository-authorized active route and terminal boundary are accepted;
- direct/out-of-band, structurally valid, equal-valued, actor/timestamp-only, missing, stale, ambiguous, contradictory, and superseded state fails closed;
- the ABA sequence does not inherit T1 qualification;
- an exact carrier plan followed by its observed postcondition qualifies only on a later fresh wake; and
- WIP, priority, finish-first, no-rewind, no-fallback, materialization, configuration, and downstream boundaries remain unchanged.

Final gates are focused tests, full Python tests, Ruff check and format check, mypy, and strict OpenSpec validation at the exact independently reviewed revision.
