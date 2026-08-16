# scheduled-agent-workflow Specification Delta

## MODIFIED Requirements

### Requirement: Human-required authority is bound to the repository Human actor

For workflow decisions that governance reserves to Human, durable GitHub actor identity alone MUST NOT satisfy Human authority. Activity from actors other than `royhsu-work` MAY be supporting evidence but MUST NOT satisfy Human-required admission, answers, authorization, or resume conditions.

Each Human-reserved consumer SHALL reconstruct exactly one expected durable `decision_ref` from the workflow boundary it is consuming. The Human decision comment SHALL explicitly declare that same reference using the canonical line:

```text
Human-Decision-For: <decision_ref>
```

The `decision_ref` is a correlation reference to already-durable workflow evidence, not a secret, approval token, hidden state, or authorization database. Current consumers SHALL use only these exact forms:

- Human admission of a coordination Issue directly to Explore: `issue:<issue-number>:admission:lead:explore-change`.
- Human admission of a coordination Issue directly to Propose: `issue:<issue-number>:admission:lead:propose-change`.
- Human-only advisory admission guarded by `intake:approved`: `issue:<issue-number>:advisory-admission`.
- A Human answer, authorization, or resume decision produced from canonical `HUMAN_DECISION_REQUIRED`: `issuecomment:<escalation-comment-id>`, where the id is the exact durable escalation comment being answered.

A later Human-reserved consumer MUST define its exact `decision_ref` form in its canonical governing requirement before it may use this predicate. If a current boundary cannot map to exactly one form above, or a future boundary lacks an explicit canonical mapping, evaluation MUST fail closed. The shared evaluator MUST NOT invent a reference by interpreting arbitrary prose, PR descriptions, routing history, or model inference.

A Human-reserved decision SHALL be valid only when all of the following current evidence holds:

- exactly one expected `decision_ref` is reconstructable for the current Human-reserved boundary;
- the selected decision comment is on the same coordination Issue and declares the exact expected `Human-Decision-For` reference;
- the decision comment author is `royhsu-work`;
- raw GitHub creation provenance for that comment establishes `performed_via_github_app == null`;
- the reserved Human approval capability label is exactly `human:approved` and is currently present on the coordination Issue;
- a qualifying `labeled` event for `human:approved` has `actor.login == royhsu-work` plus `performed_via_github_app == null`;
- that approval event binds to exactly one qualifying Human decision comment across all decision references: the latest qualifying Human-created comment on the same coordination Issue that precedes the event and contains exactly one syntactically valid `Human-Decision-For:` line, ordered by GitHub `created_at` and then numeric comment id as the stable tie-breaker;
- the single comment bound to that event declares the exact expected `decision_ref`; and
- `decision_comment.updated_at <= approval_event.created_at`.

Boundary evaluation MUST first derive the event→comment binding without filtering by the boundary's expected `decision_ref`; only after one comment is bound to the event may the workflow compare that comment's declared reference with the expected boundary reference. Therefore one qualifying `human:approved` labeled event can authorize at most one decision comment and at most one `decision_ref`. The same event MUST NOT be independently reused to authorize R1 and R2 by filtering the candidate set differently for each boundary.

When multiple qualifying Human-only approval events exist, evaluate them from newest to oldest and use the newest event whose uniquely bound comment is current and whose declared reference equals the expected `decision_ref`. An event bound to another reference is not authority for the current boundary. A later matching decision comment for the same `decision_ref` requires a later qualifying approval event to approve that replacement comment; an older event MUST NOT float forward to the replacement. Missing ids/timestamps/provenance, malformed or multiple `Human-Decision-For` lines in the bound comment, a non-unique expected boundary reference, reference mismatch, or ordering that cannot be reconstructed MUST fail closed rather than allowing model selection.

A later edit to the selected decision comment SHALL invalidate prior approval for that revision. The workflow MUST fail closed until a later qualifying Human approval event re-approves the current comment revision. `unlabeled` event provenance MAY invalidate current-label state but MUST NOT establish Human authority.

Where normalized connector reads omit `performed_via_github_app`, the workflow MUST inspect the raw GitHub object/event provenance required by this contract. Missing, inaccessible, ambiguous, or contradictory provenance MUST fail closed and MUST NOT degrade to actor-only authority.

The existing `intake:approved` label SHALL remain the distinct Human-only advisory-admission capability marker. Its current presence or actor attribution alone MUST NOT prove Human identity or approval. When advisory admission consumes a Human decision, the expected reference is exactly `issue:<issue-number>:advisory-admission` and the intended Human decision evidence SHALL satisfy the provenance-bound contract above. Scheduled roles MUST NOT add, remove, restore, or manufacture either `human:approved` or `intake:approved` when those labels are reserved Human capabilities.

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

- GIVEN the current Human-reserved consumer reconstructs one expected `decision_ref` using the exact canonical mapping
- AND a qualifying Human-only `human:approved` labeled event uniquely binds to one qualifying Human-created decision comment
- AND that bound comment declares the expected `Human-Decision-For: <decision_ref>`
- AND raw creation provenance has `performed_via_github_app == null`
- AND `human:approved` is currently present
- AND the comment has not been edited after that approval event
- WHEN the workflow evaluates the intended Human-reserved decision
- THEN the provenance-bound decision satisfies Human authority

#### Scenario: One approval event cannot authorize two decision references

- GIVEN Human-created comments for R1 and R2 both precede one qualifying Human-only `human:approved` labeled event E
- AND the R2 comment is later than the R1 comment by `created_at`, then numeric comment id
- WHEN the workflow derives E's approval target
- THEN E binds only to the R2 comment
- AND E may satisfy boundary R2 when all other evidence is valid
- AND E MUST NOT also satisfy boundary R1 by re-filtering candidates for R1

#### Scenario: Multiple Human comments do not require model disambiguation

- GIVEN multiple qualifying Human-created decision comments precede approval event E
- WHEN E is evaluated
- THEN the latest qualifying comment across all decision references is selected by `created_at`, then numeric comment id
- AND E binds to that one comment before any boundary reference comparison
- AND the workflow does not ask the model to infer which Human prose was intended

#### Scenario: Replacement decision for the same boundary requires reapproval

- GIVEN an earlier Human-created decision comment for R was approved by event E1
- AND a later Human-created decision comment also declares `Human-Decision-For: R`
- WHEN boundary R is evaluated before any qualifying approval event after the later comment
- THEN E1 does not approve the replacement comment
- AND the workflow fails closed until a later qualifying Human-only approval event binds to the replacement comment

#### Scenario: Exact current admission anchors are deterministic

- GIVEN Issue 47 is Human-admitted directly to `Lead / explore-change`
- WHEN the Human admission decision is evaluated
- THEN the expected reference is exactly `issue:47:admission:lead:explore-change`
- AND a comment or approval event for any other reference cannot satisfy that admission

#### Scenario: Escalation answer anchor is deterministic

- GIVEN Lead persisted canonical `HUMAN_DECISION_REQUIRED` as issue comment id 12345
- WHEN a later Human answer or resume decision is evaluated for that escalation
- THEN the expected reference is exactly `issuecomment:12345`
- AND no PR/revision or generic Issue reference may substitute for that anchor

#### Scenario: Missing or unmapped decision reference fails closed

- GIVEN a Human-reserved consumer has no exact canonical `decision_ref` mapping
- OR the available Human comment has no valid `Human-Decision-For` line or declares a different reference
- WHEN Human authority is evaluated
- THEN the workflow does not invent an anchor or reinterpret prose
- AND the Human authority condition fails closed

#### Scenario: Approved comment is edited afterward

- GIVEN a Human decision comment previously had a qualifying `human:approved` event bound to it
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

- GIVEN an advisory recommendation on Issue N is being admitted through the Human-only advisory path
- AND `intake:approved` is currently present
- WHEN the workflow determines whether Human authority exists
- THEN the label snapshot alone is insufficient Human proof
- AND the expected reference is exactly `issue:<N>:advisory-admission`
- AND the intended Human decision must satisfy the provenance-bound approval contract
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
- AND insufficient prior evidence fails closed for a fresh Human decision carrying the exact expected `decision_ref` and a later qualifying approval
