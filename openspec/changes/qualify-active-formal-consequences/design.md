# Design: Qualify active formal consequences

## Decision boundary

The exact durable same-Issue Explore result is issuecomment-5595057852 at main revision e4dcad8ad0326a6a38620998ee2f03ebcc060a19. Propose reverse-verified its material claims against current source and governance before authoring this Change. Human scope is carried by issuecomment-5594516745 and issuecomment-5594806867: Change: unset is pre-activation intake; Change != unset requires affirmative repository-owned qualification for active formal routing, successor, and terminal consequences; consequence authority belongs to the repository application and executable model; #227 hard-exit behavior and #218 sequencing are preserved.

The current defect is the gap between structural normalization and consequence authority. The runtime normalizes valid Issue fields into authoritative observations in scheduled_agent_runtime.py. The effect adapter has reusable Actions-authored evidence recognition and formal comment parsing, but _formal_transition_is_qualified currently accepts a matching observed route before it requires formal evidence. The repair keeps the existing finite model and moves the qualification boundary to the existing current-state and application checks.

## Ownership

- openspec/specs/repository-governance/spec.md owns the project-wide ownership invariant: an active formal machine-decidable consequence has one canonical owner and one affirmative qualification predicate. It does not define the scheduled workflow's concrete evidence shape.
- openspec/specs/scheduled-agent-workflow/spec.md owns the concrete active-formal predicate, including when current routing or terminal state may participate in dispatch and derived consequence. Its existing requirement is modified rather than duplicated.
- src/investment_strategy/scheduled_agent_action_model.py remains the sole owner of Action vocabulary, Role derivation, transition/result semantics, WIP, priority, and finish-first selection.
- scheduled_agent_runtime.py owns fresh GitHub Issue reconstruction and dispatch input construction; scheduled_agent_effects.py and the application bridge own fresh effect authorization, application-derived consequence, and durable postcondition checks.
- roles, skills, workflow presentation, and transport remain references or adapters. None receives a competing normative rule.

No new Action, Result kind, workflow state, registry, ledger, cursor, lease, heartbeat, retry state, mailbox, policy engine, carrier type, or carrier-result protocol is introduced.

## D1 — Qualify active state at current reconstruction and dispatch ingress

When a normalized Issue has Change != unset, current-state reconstruction must derive whether its active route or terminal boundary is qualified. The qualification result is the existing ObservationProvenance/current-state provenance consumed by dispatch; it is not a new persisted state.

The existing formal evidence detectors are reused. A qualifying observation must be fresh and repository-owned, and must bind the current workflow identity, immutable Change, current Action/Role, the source authorization/default-branch revision relationship, the accepted Action/Result, the model-derived next_action when a successor exists, and the exact observed durable route or terminal postcondition. The implementation may derive next_action from the existing Action/Result model rather than adding a message field. The exact predicate must reject evidence that is only structurally valid or only equal to the requested target.

The implementation should evaluate only evidence that the current repository application could have produced and whose durable postcondition is observed. Connector-authored EFFECT_REQUEST transport remains input to the application only. A connector comment, connector identity, or a worker claim cannot qualify a formal route, successor, terminal, or success consequence.

If no unique coherent proof can be reconstructed, or if any required source/revision/result/postcondition relationship is missing, stale, ambiguous, contradictory, incomplete, or unorderable, the observation is INDETERMINATE. Dispatch then fails closed through the existing complete-observation boundary. It must not select a later pre-activation Issue as semantic fallback.

Change: unset remains on the existing pre-activation path. Structural current routing may continue to select legitimate bounded Explore or Propose intake under the existing contract; the active-formal qualification predicate is not used to demand formal provenance before a Change is persisted.

## D2 — Reuse existing result and postcondition evidence

The implementation reuses:

- runtime recognition of GitHub Actions-authored comments;
- formal Action/Result marker and field parsing;
- current default-branch revision checks;
- application fresh reauthorization of the selected Issue/Action/Role;
- the existing finite model to derive the legal successor or terminal boundary; and
- exact durable postcondition observation.

The accepted evidence should be checked in the same direction as the consequence: identify the repository-owned authorization and result first, derive the only legal next action from the executable model, then require the observed Issue route or terminal state to match that result and its postcondition. A result comment without the corresponding route/postcondition, or a route without a matching result and authorization, is not sufficient. Multiple competing candidates are ambiguous and fail closed.

The evidence remains invocation-local or reconstructed from existing repository records. It is not written to a new registry or converted into a second protocol.

## D3 — Remove the equality-only acceptance shortcut

After D1 owns the qualification decision, _formal_transition_is_qualified must no longer treat current routing equal to a requested target as sufficient formal authority. The effect layer must consume the existing qualified evidence decision or the exact invocation-local evidence created by the same repository-owned application batch. There must be one qualification owner and one acceptance path.

This change applies to both derived routing transitions and terminal/close boundaries after Change is set. A terminal close with no qualifying repository-owned evidence remains INDETERMINATE; a repository-owned terminal transition with fresh authorization and observed postcondition remains QUALIFIED. The application must not auto-rewind, auto-accept, or launder an out-of-band mutation through idempotent reconciliation.

## D4 — Preserve carrier and later-wake semantics

CarrierRequired remains the existing hard invocation-exit boundary. When a carrier is needed, the current wake emits only the exact application-authorized CarrierPlan and exits. It does not create an active formal consequence. After the carrier executes, a later fresh repository-owned wake reconstructs the branch/PR/ref and exact postcondition, reauthorizes against current main, and then applies only still-missing effects.

An exact carrier plan and its observed postcondition may supply the repository-owned evidence required for a later formal state, but the carrier does not choose routing, successor, retry, terminal, or success. The qualification predicate remains tied to the application authorization and observed postcondition, not to a carrier assertion.

## D5 — Regression matrix and quality boundary

Focused tests cover:

- Change: unset Human-requested, idle-discovery, scope-split, and Propose compatibility;
- repository-owned qualified active routing and terminal transitions;
- direct/out-of-band syntactically valid active routing;
- equality-only current state without formal evidence;
- connector-authored, missing, stale, ambiguous, contradictory, and incomplete evidence;
- exact carrier postcondition followed by a later fresh qualified wake;
- formal priority, WIP, finish-first, no-rewind, and no-fallback behavior; and
- preservation of the existing finite Action/Result vocabulary and application/carrier boundary.

The implementation is accepted only when focused tests, the full Python suite, Ruff, mypy, and strict OpenSpec validation pass at the exact reviewed revision. Lifecycle review, merge, archive, and terminal actions remain repository-derived later Actions and are not performed in this Change.
