## ADDED Requirements

### Requirement: Machine-decidable consequence qualification has one canonical owner

When eligibility for a repository-owned consequence can be decided from observable repository evidence and explicit deterministic predicates, the existing canonical executable owner SHALL evaluate one affirmative qualification predicate before the consequence becomes eligible. Consumers SHALL use that owner's qualification result and MUST NOT add a competing acceptance shortcut or infer eligibility from a structurally matching value alone.

If observable evidence does not establish the predicate for the current consequence, that consequence remains unqualified for that evaluation. This requirement defines ownership only; concrete evidence shape, workflow state, transport, and actor or carrier mechanics remain with the affected capability.

#### Scenario: The existing owner qualifies a machine-decidable consequence

- GIVEN a repository-owned consequence has eligibility expressible as observable evidence and explicit deterministic predicates
- AND the affected capability has one existing canonical executable owner
- WHEN that owner evaluates the affirmative qualification predicate
- THEN the consequence becomes eligible only when the predicate is satisfied
- AND consuming surfaces use that qualification rather than creating a second acceptance path

#### Scenario: A structurally matching value is not owner qualification

- GIVEN a consequence target value is present and structurally valid
- WHEN the canonical owner has not qualified the evidence and predicates for the current consequence
- THEN the target value does not make the consequence eligible
- AND another surface does not infer qualification from that value alone
