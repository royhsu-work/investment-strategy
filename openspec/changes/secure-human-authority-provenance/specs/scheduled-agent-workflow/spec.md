# scheduled-agent-workflow Specification Delta

## MODIFIED Requirements

### Requirement: Human-required authority is bound to provenance-validated repository Human decisions

For workflow decisions that governance reserves to Human, durable GitHub actor identity alone MUST NOT satisfy Human authority. Activity from actors other than `royhsu-work` MAY be supporting evidence but MUST NOT satisfy Human-required admission, answers, authorization, or resume conditions.

Each Human-reserved consumer SHALL reconstruct exactly one expected durable `decision_ref` from the workflow boundary it is consuming. The Human decision comment SHALL explicitly declare that same reference using the canonical line:

```text
Human-Decision-For: <decision_ref>
```

The `decision_ref` is a correlation reference to already-durable workflow evidence, not a secret, approval token, hidden state, or authorization database. A Lead `HUMAN_DECISION_REQUIRED` answer SHALL use that exact escalation comment reference. Other Human-only admission, authorization, or resume consumers SHALL use the exact durable boundary reference already required by their governing contract, such as the coordination-Issue admission boundary or exact PR/revision authorization target. A consumer MUST NOT invent a reference by interpreting arbitrary prose.

A Human-reserved decision SHALL be valid only when all of the following current evidence holds:

- exactly one expected `decision_ref` is reconstructable for the current Human-reserved boundary;
- the selected decision comment is on the same coordination Issue and declares the exact expected `Human-Decision-For` reference;
- the decision comment author is `royhsu-work`;
- raw GitHub creation provenance for that comment establishes `performed_via_github_app == null`;
- the reserved Human approval capability label is exactly `human:approved` and is currently present on the coordination Issue;
- a qualifying `labeled` event for `human:approved` occurs after at least one matching candidate comment exists and has `actor.login == royhsu-work` plus `performed_via_github_app == null`;
- for the latest such qualifying approval event, the selected comment is the latest matching qualifying Human-created comment preceding that event, ordered by GitHub `created_at` and then numeric comment id as the stable tie-breaker; and
- `decision_comment.updated_at <= approval_event.created_at`.

A later matching decision comment for the same `decision_ref` replaces an earlier matching comment for subsequent approval evaluation; unrelated Human comments with a missing or different `decision_ref` are not candidates. Missing ids/timestamps/provenance, a non-unique expected boundary reference, reference mismatch, or ordering that cannot be reconstructed MUST fail closed rather than allowing model selection.

A later edit to the selected decision comment SHALL invalidate prior approval for that revision. The workflow MUST fail closed until a later qualifying Human approval event re-approves the current comment revision. `unlabeled` event provenance MAY invalidate current-label state but MUST NOT establish Human authority.

Where normalized connector reads omit `performed_via_github_app`, the workflow MUST inspect the raw GitHub object/event provenance required by this contract. Missing, inaccessible, ambiguous, or contradictory provenance MUST fail closed and MUST NOT degrade to actor-only authority.

The existing `intake:approved` label SHALL remain the distinct Human-only advisory-admission capability marker. Its current presence or actor attribution alone MUST NOT prove Human identity or approval. When advisory admission consumes a Human decision, the expected admission `decision_ref` and intended Human decision evidence SHALL satisfy the provenance-bound contract above. Scheduled roles MUST NOT add, remove, restore, or manufacture either `human:approved` or `intake:approved` when those labels are reserved Human capabilities.

Repository-authorized Explore admission SHALL remain a separate non-Human authority path governed by its independent canonical source/materiality evidence. It MUST NOT be represented as Human activity and MUST NOT require `human:approved` solely because the admission is repository-authorized rather than Human-admitted.

Issue bodies, natural-language identity claims, object author/actor identity alone, `human:notified`, ordinary routing labels, current approval-label snapshots without a qualifying event, comments lacking the expected `decision_ref`, and `unlabeled` event provenance MUST NOT establish Human authority.

This stronger authority rule SHALL activate prospectively on the default-branch merge. Workflows already terminal before activation and Human authority already legally consumed before activation MUST remain historical evidence and MUST NOT be retroactively invalidated solely because they predate this provenance contract. A still-pending Human-reserved decision that is newly consumed after activation SHALL satisfy this requirement even when its Issue predates activation; otherwise the workflow fails closed for a fresh Human decision and approval.

`human:notified`, when present, SHALL remain analytics-only metadata and MUST NOT grant authority, route work, create waiting semantics, participate in resume conditions, or prove that Human answered.

#### Scenario: Non-Human actor answers a Human-required question

- GIVEN workflow progress requires a Human decision
- AND an actor other than `royhsu-work` posts an apparent answer
- WHEN Lead reconstructs authorization evidence
- THEN the answer may be considered evidence
- BUT it does not satisfy the Human-required decision condition

#### Scenario: Notification metadata exists

- GIVEN `human:notified` metadata is present
- WHEN any role evaluates routing or authorization
- THEN that metadata does not change workflow ownership or authority
- AND it is not treated as proof of a Human response

#### Scenario: Connector-authored evidence cannot manufacture Human authority

- GIVEN a decision comment or approval-label event is attributed to `royhsu-work`
- AND raw GitHub provenance records a non-null GitHub App for that creation/event
- WHEN a Human-reserved admission, answer, authorization, or resume condition is evaluated
- THEN actor identity alone is insufficient
- AND the evidence does not satisfy Human authority

#### Scenario: Human comment plus later Human approval is valid

- GIVEN the current Human-reserved consumer reconstructs one expected `decision_ref`
- AND the latest matching Human decision comment declares `Human-Decision-For: <decision_ref>`
- AND that comment is authored by `royhsu-work`
- AND raw creation provenance has `performed_via_github_app == null`
- AND `human:approved` is currently present
- AND the latest qualifying later `human:approved` labeled event has actor `royhsu-work` and `performed_via_github_app == null`
- AND the comment has not been edited after that approval event
- WHEN the workflow evaluates the intended Human-reserved decision
- THEN the provenance-bound decision satisfies Human authority

#### Scenario: Multiple Human comments do not require model disambiguation

- GIVEN the current Human-reserved boundary has expected `decision_ref` R
- AND multiple Human-created comments exist on the coordination Issue
- AND zero or more comments are unrelated or declare a different decision reference
- WHEN a qualifying Human-only `human:approved` event is evaluated
- THEN only comments declaring `Human-Decision-For: R` are candidates
- AND the latest matching qualifying comment preceding the latest qualifying approval event is selected by `created_at`, then numeric comment id
- AND the workflow does not ask the model to infer which unrelated Human prose was intended

#### Scenario: Replacement decision for the same boundary

- GIVEN an earlier Human-created decision comment declares `Human-Decision-For: R`
- AND a later Human-created decision comment also declares `Human-Decision-For: R`
- AND a qualifying Human-only `human:approved` event occurs after the later comment
- WHEN the workflow evaluates boundary R
- THEN the later matching comment is the approved candidate
- AND the earlier matching comment is superseded for that approval evaluation

#### Scenario: Missing or mismatched decision reference fails closed

- GIVEN a Human-reserved consumer expects `decision_ref` R
- AND the available Human comment has no `Human-Decision-For` line or declares a different reference
- WHEN Human authority is evaluated
- THEN that comment is not a candidate for R
- AND the workflow fails closed if no qualifying matching comment remains

#### Scenario: Approved comment is edited afterward

- GIVEN a Human decision comment previously had a qualifying `human:approved` event
- AND the comment is later edited so `comment.updated_at > approval_event.created_at`
- WHEN the workflow evaluates the prior approval
- THEN the prior approval is invalid for the edited revision
- AND a later qualifying Human approval event is required before consuming that decision

#### Scenario: Normalized read lacks provenance

- GIVEN a normalized connector response identifies actor `royhsu-work`
- AND the response does not expose `performed_via_github_app`
- WHEN Human authority is required
- THEN actor identity alone is insufficient
- AND the workflow obtains the required raw GitHub provenance or fails closed

#### Scenario: Advisory intake marker remains distinct

- GIVEN an advisory recommendation is being admitted through the Human-only advisory path
- AND `intake:approved` is currently present
- WHEN the workflow determines whether Human authority exists
- THEN the label snapshot alone is insufficient Human proof
- AND the expected admission `decision_ref` plus intended Human decision must satisfy the provenance-bound approval contract
- AND `intake:approved` remains distinct from `human:approved`

#### Scenario: Repository-authorized Explore does not impersonate Human admission

- GIVEN an Explore candidate has valid independent repository-authorized admission evidence under the canonical bounded admission contract
- WHEN dispatch evaluates that candidate
- THEN the candidate may be admitted without manufacturing Human evidence
- AND `human:approved` is not required merely to relabel repository authority as Human authority
- AND any later genuinely Human-reserved decision still requires provenance-bound Human approval

#### Scenario: Historical completion is not retroactively invalidated

- GIVEN a workflow reached valid terminal completion before this provenance contract became authoritative
- WHEN a later run reconstructs historical evidence
- THEN the completed workflow remains historical terminal evidence
- AND the new provenance rule does not reopen or invalidate that completed lifecycle solely because older Human evidence used the prior contract

#### Scenario: Pending pre-activation evidence is consumed after activation

- GIVEN a Human-reserved decision was recorded before this provenance contract became authoritative
- AND that decision has not yet been legally consumed
- WHEN a workflow attempts to consume it after default-branch activation
- THEN the current provenance-bound requirement applies
- AND insufficient prior evidence fails closed for a fresh Human decision carrying the expected `decision_ref` and a later qualifying approval
