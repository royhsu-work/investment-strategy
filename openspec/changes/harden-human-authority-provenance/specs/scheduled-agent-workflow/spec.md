# scheduled-agent-workflow Specification Delta

## MODIFIED Requirements

### Requirement: Human-required authority is bound to the repository Human actor

For new workflow decisions that governance reserves to Human after this change becomes authoritative, durable GitHub actor identity alone MUST NOT satisfy Human authority. The repository SHALL validate a provenance-bound Human decision using a mutable decision comment plus a later reserved approval-label event.

A Human decision is valid only when all of the following hold for the intended decision comment and qualifying approval event:

- the decision comment author is `royhsu-work`;
- raw GitHub provenance for comment creation establishes `performed_via_github_app == null`;
- the reserved Human approval label is currently present on the coordination Issue;
- the qualifying approval `labeled` event has `actor.login == royhsu-work` and `performed_via_github_app == null`;
- the approval event occurs after the intended decision comment exists; and
- `decision_comment.updated_at <= approval_event.created_at`.

The qualifying approval event MUST deterministically bind to the intended decision comment using current durable Issue/comment/event evidence rather than hidden state. A later edit to the approved comment invalidates that approval; the workflow MUST fail closed until a later qualifying Human approval event re-approves the current comment revision.

Issue bodies, natural-language identity claims, current actor identity alone, `human:notified`, ordinary routing labels, and `unlabeled` event provenance MUST NOT establish Human authority. Activity from other actors MAY be supporting evidence but MUST NOT satisfy Human-required admission, answers, authorization, or resume conditions.

Where normalized connector reads omit `performed_via_github_app`, the workflow MUST inspect the raw GitHub object/event provenance required by this contract rather than silently degrading to actor-only authority. Missing, inaccessible, ambiguous, or contradictory provenance MUST fail closed.

This stronger authority rule SHALL apply prospectively to Human-reserved decisions that are newly created or newly consumed after the default-branch activation boundary. Already completed historical workflows and already-consumed Human authority evidence before activation MUST remain historical evidence and MUST NOT be retroactively invalidated solely because they predate this provenance contract.

`human:notified`, when present, SHALL remain analytics-only metadata and MUST NOT grant authority, route work, create waiting semantics, participate in resume conditions, or prove that Human answered.

#### Scenario: Connector-authored approval cannot satisfy Human authority

- GIVEN an Agent creates or mutates GitHub evidence through a connector
- AND GitHub attributes the activity to `royhsu-work`
- AND raw provenance records a non-null GitHub App for the decision comment creation or approval `labeled` event
- WHEN a Human-reserved admission, answer, authorization, or resume condition is evaluated
- THEN the evidence does not satisfy Human authority
- AND the workflow fails closed without treating actor identity alone as approval

#### Scenario: Human comment plus later Human approval is valid

- GIVEN a decision comment is authored by `royhsu-work`
- AND raw creation provenance has `performed_via_github_app == null`
- AND a later approval `labeled` event has actor `royhsu-work` and `performed_via_github_app == null`
- AND the reserved approval label is currently present
- AND the comment has not been edited after that approval event
- WHEN a Human-reserved workflow boundary evaluates that intended decision
- THEN the provenance-bound decision satisfies Human authority

#### Scenario: Approved comment is edited afterward

- GIVEN a Human decision comment previously had a qualifying approval event
- AND the comment is later edited so `comment.updated_at > approval_event.created_at`
- WHEN the workflow evaluates the prior approval
- THEN the prior approval is invalid for the edited revision
- AND the workflow requires a later qualifying Human approval event before consuming the decision

#### Scenario: Normalized read lacks provenance

- GIVEN a normalized connector response identifies actor `royhsu-work`
- AND the response does not expose `performed_via_github_app`
- WHEN Human authority is required
- THEN actor identity alone is insufficient
- AND the workflow obtains the required raw GitHub provenance or fails closed

#### Scenario: Historical completion is not retroactively invalidated

- GIVEN a workflow reached valid terminal completion before this provenance contract became authoritative
- WHEN a later run reconstructs historical evidence
- THEN the completed workflow remains historical terminal evidence
- AND the new provenance rule does not retroactively reopen or invalidate that completed lifecycle solely because the old Human evidence used the prior contract
