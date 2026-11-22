## ADDED Requirements

### Requirement: Implementation review findings stay within approved scope and stage-specific closure

For `Reviewer / review-implementation`, every blocking Finding SHALL identify (1) the violated Human-approved requirement or currently applicable invariant, (2) reproducible or inspectable evidence tied to the exact reviewed revision, (3) the delivery stage and gate whose current exit criterion is unsatisfied, and (4) an observable, testable closure condition. The Reviewer MUST separate a demonstrated defect from a suggested implementation mechanism and MUST evaluate an alternate implementation or valid counterevidence against the same original closure condition. A suggestion or advisory improvement MUST NOT become an additional binding requirement without an approved semantic/scope change.

For `Executor / implement-change`, a Reviewer Finding SHALL be independently checked against approved meaning, exact evidence and the applicable delivery stage before code or Skill changes. Executor SHALL correct only substantiated, in-scope defects with the smallest sufficient implementation and SHALL verify the original failure/counterexample or equivalent evidence. Executor MUST retain contradictory evidence or a demonstrated alternative in the existing review record for independent Reviewer adjudication and MUST NOT self-clear Reviewer PASS. If correction requires materially changing approved semantics, responsibility or scope, Executor MUST stop and follow the existing `SPEC_BLOCKER → Lead / resolve-question` route. Existing exact-head review, required downstream checks, non-idempotent no-replay, and mutation authorization remain in force.

#### Scenario: Accepted materialization preimage contradicts the requested write

- GIVEN the currently reviewed materialization requests a path whose accepted preimage does not match current observed content, as in PR #455
- WHEN Reviewer judges the relevant materialization/safety gate
- THEN the mismatched preimage is a substantiated `CONTRADICTORY` condition and the immutable accepted manifest is preserved
- AND zero unauthorized Git mutations are accepted as closure
- AND Reviewer does not require a preferred alternative mechanism if an independently proven correction satisfies the same invariant and closure condition

#### Scenario: RED-stage diagnostic is assessed at its own stage boundary

- GIVEN an approved RED-stage counterexample is under review, as in PR #453
- WHEN the observed failure is the intended failure caused by the missing target behavior
- THEN Reviewer evaluates that RED evidence against RED's exit criterion
- AND Reviewer MUST NOT block RED merely because later GREEN, regression, type-check or merge gates have not yet completed
- AND those later-stage gates remain mandatory at their own applicable boundaries

#### Scenario: Historical UNKNOWN does not grant replay or perpetual unrelated blockage

- GIVEN an earlier accepted non-idempotent Effect has an unresolved historical `UNKNOWN`, as in Issue #435
- AND a separately authorized correction is proposed without replaying that original Effect
- WHEN Reviewer considers whether the historical uncertainty blocks the correction
- THEN the original non-idempotent Effect remains subject to no-replay and no unfounded inference of completion or absence is made
- AND a blocking Finding identifies the concrete currently conflicting target/effect and observable release condition rather than relying only on hypothetical historical uncertainty
- AND Issue #435's own Recovery Exit and original gate remain unchanged

#### Scenario: Executor produces counterevidence or a valid alternative repair

- GIVEN Reviewer has recorded a blocking Finding with an approved invariant, exact revision, stage and observable closure condition
- AND Executor independently verifies the evidence and produces either an in-scope alternative fix or counterevidence
- WHEN implementation is submitted for independent re-review
- THEN the Reviewer adjudicates against the original closure condition, not a newly preferred mechanism
- AND Executor does not mark its own Finding resolved or expand the scope
- AND any material spec or approved-scope change is returned through the existing `SPEC_BLOCKER → Lead / resolve-question` boundary
