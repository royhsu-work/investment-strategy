## MODIFIED Requirements

### Requirement: Lead idle advisory mode is bounded and non-routing

Lead SHALL keep idle advisory mode bounded and non-routing.

When no active or terminal-pending workflow requires work, no queued Human-admitted proposal is eligible for activation, and no unresolved orphan evidence requires diagnosis, Lead MAY create an idle advisory Issue containing at most three current recommendations only if no other open `advisory:idle` Issue exists.

When forming those bounded recommendations, Lead SHALL consider recent durable workflow evidence for Skill-maintenance opportunities such as repeated Agent mistakes or recoverable failures, missing or obsolete action guidance, unnecessary Skill complexity, and materially duplicated Skill guidance. A Skill-maintenance recommendation remains diagnostic/advisory only: it MUST NOT directly mutate governed Skill behavior, bypass Human admission, or create a second maintenance workflow.

An advisory Issue MUST NOT contain `agent:*` or `action:*` routing labels and is not itself a coordination workflow instance.

If an open advisory remains without valid Human admission, later Lead runs SHALL no-op rather than create duplicate advisory noise. Recommendation formation SHALL consider relevant Issues created or materially active during the preceding seven days.

#### Scenario: Existing idle advisory has no Human decision

- GIVEN one open `advisory:idle` Issue exists
- AND no valid Human admission has occurred
- WHEN Lead runs while workflow is otherwise idle
- THEN Lead does not create another advisory Issue
- AND does not repeat the same recommendations as new workflow noise

#### Scenario: Recent workflow evidence suggests a Skill improvement

- GIVEN workflow execution is otherwise idle
- AND recent durable evidence shows a repeated action mistake or missing/obsolete Skill guidance
- WHEN Lead forms an eligible bounded idle advisory
- THEN Lead may recommend the narrowest Skill-maintenance change supported by that evidence
- AND the recommendation does not itself modify the Skill or create a parallel maintenance workflow
- AND any governed behavior change still requires normal Human-admitted/OpenSpec lifecycle

## REMOVED Requirements

### Requirement: Workflow governance applies a simplicity and proportionality constraint

Repository workflow design SHALL add complexity only when justified by current approved requirements or demonstrated failure modes. Hypothetical future generality MUST NOT by itself justify a central workflow engine, multi-active arbitration platform, generic fault classifier, generic exception/retry platform, message bus/template engine, semantic-revision classifier service, generic context/event processor, or hidden runtime ownership state.

#### Scenario: A generalized dispatcher framework is proposed without current need

- GIVEN a proposed workflow change adds a generalized orchestration mechanism
- AND no current approved requirement or demonstrated failure mode requires that mechanism
- WHEN the change is evaluated
- THEN hypothetical future generality alone is insufficient justification
- AND the design prefers the smallest existing ownership layer that satisfies the approved contract
