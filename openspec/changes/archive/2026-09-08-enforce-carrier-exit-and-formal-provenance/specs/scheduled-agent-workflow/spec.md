## Decision-boundary traceability (non-normative)

This section records the Human decision boundary and source evidence carried by #227. It is context and traceability only; it is not an additional OpenSpec requirement and does not create a second normative owner.

Source evidence:
- #221 rejection and root-cause record: https://github.com/royhsu-work/investment-strategy/issues/221#issuecomment-5575078000
- #221 latest Human-approved minimal repair direction: https://github.com/royhsu-work/investment-strategy/issues/221#issuecomment-5578787305
- #221 deterministic implementation decision record: https://github.com/royhsu-work/investment-strategy/issues/221#issuecomment-5585904208
- #227 current Explore evidence: https://github.com/royhsu-work/investment-strategy/issues/227#issuecomment-5581185977
- The prior #227 review evidence at issuecomment-5582134734 is historical and was invalidated by later material changes.

The preserved parent outcome is: verified slice, durable checkpoint, interruption, reconstruction from current truth without replay, and continuation at the first incomplete slice. The source records describe a fail-open execution boundary: formal durable state had a repository-owned Actions/application path and an LLM or direct-connector path, and the latter could still be treated as formal progress when the repository-owned path was unavailable or unverifiable. The defect is therefore the execution and provenance boundary, not checkpoint syntax.

This delta keeps active formal routing and terminal provenance under the requirement below. The existing canonical scheduled-agent-workflow requirements remain the normative owner of verified-slice, checkpoint, interruption-recovery, no-replay, and first-incomplete-slice semantics. The shared CarrierRequired hard-exit contract is owned by repository-governance; this context refers to that owner without restating its normative text here. #221 remains historical and is not reopened, rewritten, or treated as Human accepted by this Change; #218 remains blocked.

The approved boundary retains repository-owned Actions/application authorization and observed postconditions for formal progress, bounded untrusted EFFECT_REQUEST connector ingress, the existing application/carrier separation, one bounded implementation slice, task equality, and merge reconciliation from historical exact head plus fresh current main.

Excluded from this correction are new Action or Result types, a checkpoint/progress registry, cursor, lease, heartbeat, retry state, mailbox, second DAG, new carrier type or result protocol, generic provenance/recovery framework, dedicated GitHub App or token infrastructure, a GITHUB_TOKEN-only carrier replacement, ruleset redesign, and #218/#207/#180 scope.

## ADDED Requirements

### Requirement: Active formal transitions require repository-owned provenance

When a coordination Issue has `Change != unset`, the current formal
`action:*` routing transition and terminal/close boundary SHALL be accepted
only when fresh evidence qualifies the transition as the result of a
repository-owned GitHub Actions/application execution. The evidence MUST bind
the transition to the application's fresh authorization and observed durable
postcondition; syntactically valid Issue fields, labels, timestamps, or
connector-authored comments alone are insufficient.

A connector-authored or other out-of-band direct formal routing or
terminal/close mutation, and any transition whose repository-owned provenance
is missing, incomplete, stale, ambiguous, contradictory, or unverified, SHALL
be classified as `INDETERMINATE` and fail closed. The application MUST NOT
auto-accept it, auto-rewind it, or launder it through idempotent
reconciliation. A qualified repository-owned Actions/application transition
continues to use the existing finite Action/Result vocabulary and transition
model.

Connector ingress remains limited to the bounded untrusted
`EFFECT_REQUEST` transport needed by the current application bridge. Ingress
does not grant routing, successor, retry, merge, terminal, or success
authority; those effects remain application-derived and postcondition-bound.

Existing pre-activation behavior for `Change: unset` SHALL remain
compatible: Explore/Propose selection may use the current pre-activation
contract and does not require the active-formal provenance guard until a
Change is set.

#### Scenario: Connector-authored active routing fails closed

- GIVEN a coordination Issue has `Change != unset` and a connector-authored
  direct comment or label mutation makes a syntactically valid `action:*`
  route current
- WHEN the application freshly observes the active formal state
- THEN the transition is classified `INDETERMINATE`
- AND the application fails closed without accepting the route or deriving a
  successor
- AND it does not auto-rewind or launder the mutation through reconciliation

#### Scenario: Connector-authored premature close fails closed

- GIVEN a coordination Issue has `Change != unset` and a connector-authored
  direct mutation closes the Issue or presents terminal evidence
- WHEN the application freshly reconstructs the formal lifecycle
- THEN the close or terminal boundary is classified `INDETERMINATE`
- AND no terminal/success effect is accepted or derived
- AND the next legal handling remains governed by fresh repository-owned
  evidence rather than the connector mutation

#### Scenario: Repository-owned formal transition remains qualified

- GIVEN a coordination Issue has `Change != unset` and a repository-owned
  Actions/application run has fresh authorization, emits the formal transition,
  and its durable postcondition is observed
- WHEN the application reconstructs the current formal lifecycle
- THEN the `action:*` route or terminal/close boundary is classified
  `QUALIFIED`
- AND the existing executable Action/Role/transition model may proceed
- AND no new Action, Result kind, or routing state is introduced

#### Scenario: Change-unset pre-activation remains compatible

- GIVEN a coordination Issue still has `Change: unset` and is selected by the
  existing pre-activation Explore/Propose dispatch
- WHEN the application reconstructs the current pre-activation state
- THEN the existing compatibility contract remains applicable
- AND the active-formal provenance guard is not used to require a Change
  before the approved Propose transition
