## MODIFIED Requirements

### Requirement: Human-required authority is bound to the repository Human actor

For workflow decisions that governance reserves to Human, durable GitHub actor identity alone MUST NOT satisfy Human authority. Activity from actors other than `royhsu-work` MAY be supporting evidence but MUST NOT satisfy Human-required admission, answers, authorization, or resume conditions.

Each Human-reserved consumer that uses the general provenance-bound decision predicate SHALL reconstruct exactly one expected durable `decision_ref` from the workflow boundary it is consuming. The Human decision comment SHALL explicitly declare that same reference using the canonical line:

```text
Human-Decision-For: <decision_ref>
```

The `decision_ref` is a correlation reference to already-durable workflow evidence, not a secret, approval token, hidden state, or authorization database. Current consumers of the general predicate SHALL use only these exact forms:

- Human admission of a coordination Issue directly to Explore through the general decision path: `issue:<issue-number>:admission:lead:explore-change`.
- Human admission of a coordination Issue directly to Propose: `issue:<issue-number>:admission:lead:propose-change`.
- Human-only advisory admission guarded by `intake:approved`: `issue:<issue-number>:advisory-admission`.
- A Human answer, authorization, or resume decision produced from canonical `HUMAN_DECISION_REQUIRED`: `issuecomment:<escalation-comment-id>`, where the id is the exact durable escalation comment being answered.

A later Human-reserved consumer MUST define its exact `decision_ref` form in its canonical governing requirement before it may use the general predicate. If a current boundary cannot map to exactly one form above, or a future boundary lacks an explicit canonical mapping, evaluation MUST fail closed. The shared evaluator MUST NOT invent a reference by interpreting arbitrary prose, PR descriptions, routing history, or model inference.

A Human-reserved decision evaluated through the general predicate SHALL be valid only when all of the following current evidence holds:

- exactly one expected `decision_ref` is reconstructable for the current Human-reserved boundary;
- the selected decision comment is on the same coordination Issue and declares the exact expected `Human-Decision-For` reference;
- the decision comment author is `royhsu-work`;
- raw GitHub creation provenance for that comment establishes `performed_via_github_app == null`;
- the reserved Human approval capability label is exactly `human:approved` and is currently present on the coordination Issue;
- a qualifying `labeled` event for `human:approved` has `actor.login == royhsu-work` plus `performed_via_github_app == null`;
- that approval event binds to exactly one qualifying Human decision comment across all decision references: the latest qualifying Human-created comment on the same coordination Issue that precedes the event and contains exactly one syntactically valid `Human-Decision-For:` line, ordered by GitHub `created_at` and then numeric comment id as the stable tie-breaker;
- the single comment bound to that event declares the exact expected `decision_ref`; and
- `decision_comment.updated_at <= approval_event.created_at`.

Boundary evaluation through the general predicate MUST first derive the event→comment binding without filtering by the boundary's expected `decision_ref`; only after one comment is bound to the event may the workflow compare that comment's declared reference with the expected boundary reference. Therefore one qualifying `human:approved` labeled event can authorize at most one decision comment and at most one `decision_ref`. The same event MUST NOT be independently reused to authorize R1 and R2 by filtering the candidate set differently for each boundary.

When multiple qualifying Human-only approval events exist, evaluate them from newest to oldest and use the newest event whose uniquely bound comment is current and whose declared reference equals the expected `decision_ref`. An event bound to another reference is not authority for the current boundary. A later matching decision comment for the same `decision_ref` requires a later qualifying approval event to approve that replacement comment; an older event MUST NOT float forward to the replacement. Missing ids/timestamps/provenance, malformed or multiple `Human-Decision-For` lines in the bound comment, a non-unique expected boundary reference, reference mismatch, or ordering that cannot be reconstructed MUST fail closed rather than allowing model selection.

A later edit to the selected decision comment SHALL invalidate prior approval for that revision. The workflow MUST fail closed until a later qualifying Human approval event re-approves the current comment revision. `unlabeled` event provenance MAY invalidate current-label state but MUST NOT establish Human authority.

Where normalized connector reads omit `performed_via_github_app`, the workflow MUST inspect the raw GitHub object/event provenance required by this contract. Missing, inaccessible, ambiguous, or contradictory provenance MUST fail closed and MUST NOT degrade to actor-only authority.

Initial Formal Explore admission SHALL additionally permit exactly one creation-bound Human alternative instead of the general decision/approval ceremony when all of the following are reconstructable from raw GitHub evidence:

- the coordination Issue was created by `royhsu-work`;
- raw Issue creation provenance has `performed_via_github_app == null`;
- the Issue creation-time body contains exactly one repository-defined declaration `Admission: Lead / explore-change` and declares `Change: unset`;
- current routing is exactly `agent:lead + action:explore-change`; and
- no durable evidence makes the creation-time declaration ambiguous, replaced, or inapplicable.

For this creation-bound alternative, the Human Issue creation event itself SHALL be the admission decision. A second `Human-Decision-For: issue:<N>:admission:lead:explore-change` comment and later `human:approved` event SHALL NOT be required solely to repeat that same initial Explore admission. Routing labels remain routing state rather than Human authority: connector- or Agent-applied routing MAY make an already qualifying Human-created Explore Issue actionable, but MUST NOT make an app-created or provenance-ambiguous Issue Human-admitted.

If required raw Issue creation provenance or creation-time declaration history cannot be reconstructed unambiguously, the creation-bound alternative MUST fail closed. Failure of this alternative MUST NOT weaken the existing general Human-decision path; an Explore Issue may still be Human-admitted when the full provenance-bound `issue:<N>:admission:lead:explore-change` decision predicate succeeds.

The creation-bound alternative SHALL apply only to initial `Lead / explore-change` admission. Human direct-Propose admission, Human-only advisory admission, canonical `HUMAN_DECISION_REQUIRED` answers/authorization/resume, and all other Human-reserved boundaries MUST continue to use their existing exact `decision_ref` mappings and general provenance-bound decision/approval predicate unless a later canonical requirement explicitly changes them.

The existing `intake:approved` label SHALL remain the distinct Human-only advisory-admission capability marker. Its current presence or actor attribution alone MUST NOT prove Human identity or approval. When advisory admission consumes a Human decision, the expected reference is exactly `issue:<issue-number>:advisory-admission` and the intended Human decision evidence SHALL satisfy the provenance-bound contract above. Scheduled roles MUST NOT add, remove, restore, or manufacture either `human:approved` or `intake:approved` when those labels are reserved Human capabilities.

Repository-authorized Explore admission SHALL remain a separate non-Human authority path governed by its independent canonical source/materiality evidence. It MUST NOT be represented as Human activity and MUST NOT require `human:approved` solely because the admission is repository-authorized rather than Human-admitted.

Issue bodies or natural-language identity claims without the exact creation-bound predicate, object author/actor identity alone, `human:notified`, ordinary routing labels, current approval-label snapshots without a qualifying event, comments lacking the expected `decision_ref`, and `unlabeled` event provenance MUST NOT establish Human authority.

This stronger authority rule SHALL activate prospectively on the default-branch merge. Workflows already terminal before activation and Human authority already legally consumed before activation MUST remain historical evidence and MUST NOT be retroactively invalidated solely because they predate this provenance contract. A still-pending Human-reserved decision that is newly consumed after activation SHALL satisfy the current applicable requirement even when its Issue predates activation; otherwise the workflow fails closed for fresh qualifying Human evidence.

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

- GIVEN a decision comment, approval-label event, or Issue creation is attributed to `royhsu-work`
- AND raw GitHub provenance records a non-null GitHub App for that creation/event
- WHEN a Human-reserved admission, answer, authorization, or resume condition is evaluated
- THEN actor identity alone is insufficient
- AND the evidence does not satisfy Human authority

#### Scenario: Human comment plus later Human approval is valid

- GIVEN the current Human-reserved consumer uses the general predicate and reconstructs one expected `decision_ref` using the exact canonical mapping
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

- GIVEN Issue 47 is Human-admitted directly to `Lead / explore-change` through the general decision path rather than the creation-bound alternative
- WHEN the Human admission decision is evaluated
- THEN the expected reference is exactly `issue:47:admission:lead:explore-change`
- AND a comment or approval event for any other reference cannot satisfy that general admission path

#### Scenario: Escalation answer anchor is deterministic

- GIVEN Lead persisted canonical `HUMAN_DECISION_REQUIRED` as issue comment id 12345
- WHEN a later Human answer or resume decision is evaluated for that escalation
- THEN the expected reference is exactly `issuecomment:12345`
- AND no PR/revision or generic Issue reference may substitute for that anchor

#### Scenario: Missing or unmapped decision reference fails closed

- GIVEN a Human-reserved consumer using the general predicate has no exact canonical `decision_ref` mapping
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

- GIVEN a Human-reserved decision was recorded before this contract became authoritative
- AND that decision has not yet been legally consumed
- WHEN a workflow attempts to consume it after default-branch activation
- THEN the current applicable provenance requirement applies
- AND insufficient prior evidence fails closed for fresh qualifying Human evidence under the applicable boundary

#### Scenario: Human-created Formal Explore Issue is sufficient admission

- GIVEN Issue N was created directly by `royhsu-work`
- AND raw Issue creation provenance shows `performed_via_github_app == null`
- AND the creation-time body contains exactly one `Admission: Lead / explore-change` declaration and `Change: unset`
- AND current routing is exactly `agent:lead + action:explore-change`
- AND the creation-time declaration remains reconstructable and unambiguous
- WHEN dispatch evaluates initial Formal Explore admission
- THEN Issue creation itself satisfies the Human Explore admission boundary
- AND no second Human decision comment or `human:approved` event is required solely for that same admission

#### Scenario: Connector-created Human-looking Issue is not Human admission

- GIVEN an Issue displays `user.login == royhsu-work`
- AND raw Issue creation provenance identifies a GitHub App
- WHEN dispatch evaluates creation-bound Explore admission
- THEN the creation-bound alternative fails
- AND later connector-applied routing labels do not manufacture Human authority

#### Scenario: Later connector routing can route but not authorize

- GIVEN a Human-created Issue already satisfies the creation-bound Explore admission predicate
- AND repository tooling later applies `agent:lead + action:explore-change`
- WHEN dispatch evaluates the routed Issue
- THEN those labels may make the already-admitted Issue actionable
- AND the label mutation itself is not treated as the Human admission event

#### Scenario: Ambiguous or mutated creation declaration falls back to existing predicate

- GIVEN creation-time Explore admission meaning cannot be reconstructed unambiguously because required raw provenance or declaration history is unavailable or contradictory
- WHEN dispatch evaluates the creation-bound alternative
- THEN that alternative fails closed
- AND the Issue may proceed only if another independently legal admission path, including the existing full provenance-bound Human decision predicate, is satisfied

#### Scenario: Direct Propose keeps existing Human approval contract

- GIVEN a Human wants to admit a coordination Issue directly to `Lead / propose-change`
- WHEN dispatch evaluates Human authority
- THEN the creation-bound Explore alternative does not apply
- AND the existing exact `issue:<N>:admission:lead:propose-change` provenance-bound decision/approval predicate remains required

### Requirement: Workflow admission is explicitly authority-controlled

Scheduled agents MUST NOT autonomously admit arbitrary Issues, PRs, repository activity, discussions, discovered requirements, or Agent-authored recommendations into workflow work.

Human admission remains valid through the repository Human-authority contract. Initial Formal Explore admission MAY use either the canonical general provenance-bound Human decision/approval predicate or the narrowly defined Human-created Issue alternative in the `Human-required authority is bound to the repository Human actor` requirement. Current `agent:lead + action:explore-change` routing makes a legally admitted Issue actionable but routing labels alone MUST NOT establish creation-bound Human authority. Direct-Propose and other Human-reserved boundaries do not inherit the creation-bound shortcut.

In addition, Lead MAY autonomously materialize one bounded `Lead / explore-change` coordination Issue with `Change: unset` only from the idle-discovery boundary when the admission is independently justified by one of the following:

- an applicable default-branch canonical MUST/SHALL requirement with a concrete material gap;
- an approved required-deferred obligation with reconstructable source linkage;
- an explicitly governed README project-direction commitment that is prospective, scoped, affirmative, non-contradictory with canonical specs, and not merely descriptive/current-state/non-goal/example/deferred-uncommitted text; or
- concrete material behavior-preserving maintenance/friction evidence with a bounded ownership surface and no new Human-reserved product/scope/risk decision.

An autonomous admission MUST contain reconstructable evidence identifying the admission kind, exact observed default-branch revision where applicable, exact authority/evidence source, bounded problem statement, and why no Human-reserved decision is being made. Later reconstruction MUST validate that evidence and MUST fail closed when the cited source is absent, stale, contradictory, merely descriptive, insufficiently material, or otherwise does not authorize the bounded problem.

Agent-authored advisory text, Explore conclusions, and prior Agent-created tickets MUST NOT recursively serve as sufficient authority for another autonomous admission by themselves. Every autonomous admission SHALL trace to an independent default-branch authority source or current concrete repository/friction evidence.

Autonomous admission MUST NOT add, remove, restore, or manufacture `intake:approved`, MUST NOT persist a formal Change identity, and MUST NOT bypass Propose, Reviewer, implementation, merge, archive, or lifecycle gates.

A Human-admitted or valid repository-authorized `Lead / explore-change` Issue with `Change: unset` is queued pre-Change research. A Human-admitted `Lead / propose-change` Issue MAY remain queued with `Change: unset` as direct-to-Propose work. In workflow-dynamic mode, neither may bypass a formal active or terminal-pending workflow, and both participate in the deterministic pre-activation queue defined by the capability.

Explore admission establishes a bounded authority envelope for the admitted problem. When Explore reaches `PROPOSAL_READY`, Lead MAY route the same Issue to `Lead / propose-change` without a second generic Human proceed decision only when the proposal-ready direction remains within that envelope and introduces no new Human-reserved decision. A new project/product direction, material externally observable behavior choice, material scope trade-off, explicit risk acceptance, materially different security/privacy/cost/operational commitment, contradictory authority evidence, or materially changed governing evidence SHALL require `HUMAN_DECISION_REQUIRED` before Propose.

Lead idle advisory admission, where still used, continues to require both an unambiguous selected direction from actor `royhsu-work` and the reserved Human capability marker `intake:approved` applied by that Human actor. Scheduled Lead, Reviewer, and Executor MUST NEVER add, remove, restore, or otherwise manufacture Human-only `intake:approved`; they MAY only consume valid Human-authored evidence where that capability remains applicable.

#### Scenario: Human directly admits fuzzy work to Explore

- GIVEN a coordination Issue with `Change: unset` satisfies either the creation-bound Human Explore admission predicate or the existing full provenance-bound Human Explore decision predicate
- AND current routing is exactly `Lead / explore-change`
- WHEN scheduled workflow reconstructs admission
- THEN the Issue is valid queued pre-Change research
- AND Explore does not create a formal Change until an applicable `PROPOSAL_READY` result is authorized within its admitted authority envelope

#### Scenario: Human directly admits concrete work to Propose

- GIVEN Human admission satisfies the existing full provenance-bound direct-Propose predicate for `Lead / propose-change`
- AND `Change:` is unset
- WHEN scheduled workflow reconstructs admission
- THEN the Issue is valid queued pre-activation work
- AND Explore is not mandatory for that Issue
- AND the creation-bound Explore alternative does not satisfy direct-Propose admission

#### Scenario: Canonical requirement authorizes bounded Explore

- GIVEN no active/terminal-pending workflow or already eligible pre-activation work should be advanced first
- AND default-branch canonical requirement R contains an applicable MUST/SHALL obligation
- AND Lead observes a concrete material gap against R that introduces no new Human-reserved decision
- WHEN Lead performs bounded idle discovery
- THEN Lead may materialize at most one `Change: unset + Lead / explore-change` Issue
- AND the Issue records reconstructable admission evidence that cites R and the observed default-branch revision
- AND no `intake:approved` or formal Change identity is created

#### Scenario: Arbitrary README prose cannot authorize admission

- GIVEN README contains descriptive/current-state text, an example, a non-goal, or work marked merely deferred/uncommitted
- WHEN Lead evaluates autonomous Explore admission
- THEN that text alone is insufficient admission authority
- AND Lead does not infer roadmap permission from arbitrary prose

#### Scenario: Explicit README commitment can authorize bounded Explore

- GIVEN README contains an explicitly governed prospective project-direction commitment
- AND the commitment is scoped, affirmative, non-contradictory with canonical specs, and not merely deferred/uncommitted
- AND a concrete material gap remains within that direction without introducing a Human-reserved decision
- WHEN Lead evaluates bounded idle discovery
- THEN that commitment may serve as admission authority for one bounded Explore candidate
- AND runtime routing semantics remain governed by `agents/AGENTS.md` rather than README prose

#### Scenario: Recurring material workflow friction authorizes bounded maintenance Explore

- GIVEN current repository evidence demonstrates a behavior-preserving recurring workflow failure or equivalent material structural friction
- AND the problem has a bounded ownership surface
- AND resolving the problem does not choose new product scope or require Human risk acceptance
- WHEN Lead reaches the idle-discovery boundary
- THEN Lead may autonomously materialize one bounded Formal Explore candidate
- AND style preference or speculative cleanup alone would not satisfy the same threshold

#### Scenario: Agent-created ticket cannot self-feed another admission

- GIVEN an earlier Agent-created advisory or Explore Issue recommends additional work
- AND no independent default-branch authority source or current concrete material friction evidence supports that additional work
- WHEN Lead evaluates another autonomous admission
- THEN the earlier Agent-authored artifact alone is insufficient authority
- AND no recursive workflow ticket is materialized

#### Scenario: Proposal-ready Explore proceeds inside admitted authority

- GIVEN a Human-admitted or valid repository-authorized Explore has a decision-complete `PROPOSAL_READY`
- AND the proposed direction remains inside the admitted authority envelope
- AND no new Human-reserved decision is required
- WHEN Lead completes Explore
- THEN Lead may route the same Issue to `Lead / propose-change` without a second generic Human proceed decision
- AND same-role continuation follows the existing reconstruction contract

#### Scenario: Proposal-ready Explore exposes a new Human decision

- GIVEN Explore discovers a material new product direction, scope/behavior trade-off, risk acceptance, or materially different security/privacy/cost/operational commitment
- WHEN Lead evaluates the next disposition
- THEN Lead records `HUMAN_DECISION_REQUIRED`
- AND does not route to Propose until valid Human authority is reconstructed

#### Scenario: Non-Human routing is insufficient

- GIVEN an Issue has apparently valid initial `Lead / explore-change` routing
- AND the Issue does not satisfy the Human-created raw-provenance predicate or the full provenance-bound Human decision predicate
- AND no independently valid repository-authorized admission evidence satisfies the bounded autonomous Explore contract
- WHEN scheduled workflow evaluates admission
- THEN that routing does not satisfy Human-required admission
- AND scheduled roles fail closed rather than treating routing alone as authorized workflow entry
