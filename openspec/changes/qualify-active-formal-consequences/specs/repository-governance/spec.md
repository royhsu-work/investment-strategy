## ADDED Requirements

### Requirement: Active formal consequence qualification has one canonical owner

When a repository-owned machine-decidable consequence relies on an active formal workflow state, exactly one canonical capability surface SHALL own an affirmative qualification predicate for that consequence. The predicate SHALL be evaluated from fresh repository-owned evidence; structural validity or equality with a requested state is not itself qualification. Other surfaces MUST reference that owner and MUST NOT manufacture a competing acceptance shortcut.

If evidence for the owned predicate is missing, stale, ambiguous, contradictory, incomplete, connector-authored, or merely structural, the consequence SHALL be classified as INDETERMINATE and fail closed. The implementation MUST NOT auto-accept or launder the state through idempotent reconciliation. This ownership rule reuses current ObservationProvenance, Action/Result, application authorization, carrier, and durable-postcondition primitives and does not create a new workflow state, registry, or generic provenance framework.

The existing pre-activation Change: unset intake and dispatch contract remains compatible. This requirement does not require formal-state provenance before legitimate bounded Explore or Propose intake can follow that existing contract.

#### Scenario: Equality alone cannot authorize an active formal consequence

- GIVEN an active formal Issue currently has a syntactically valid route or terminal shape
- AND that shape equals the requested target
- BUT no fresh affirmative repository-owned qualification exists
- WHEN a machine-decidable consequence is evaluated
- THEN the consequence is classified INDETERMINATE
- AND no competing surface may accept it merely from equality

#### Scenario: The affected capability owns the concrete predicate

- GIVEN a repository capability has an active formal consequence
- AND its canonical owner defines a fresh repository-owned qualification predicate
- WHEN another repository surface needs to consume that consequence
- THEN it consumes the owner's qualification result
- AND it does not create a second normative predicate or acceptance shortcut

#### Scenario: Change-unset intake remains compatible

- GIVEN an Issue has Change: unset
- AND its existing bounded Explore or Propose intake is structurally and operationally eligible
- WHEN current pre-activation dispatch is evaluated
- THEN the existing intake contract remains applicable
- AND this active-formal ownership rule does not require a persisted Change before that intake can proceed
