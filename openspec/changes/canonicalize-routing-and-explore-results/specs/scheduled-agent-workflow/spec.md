## MODIFIED Requirements

### Requirement: One persistent coordination Issue represents the normal OpenSpec workflow lifecycle

The workflow SHALL use one persistent coordination Issue for one routed work item through any optional pre-Propose Explore and, when a formal Change is authorized, through proposal, review, implementation, merge, archive review, archive merge, and final closure.

Before the change id exists, `explore-change` and `propose-change` MAY operate with `Change: unset`. `explore-change` MUST keep `Change: unset` and MUST NOT create a formal OpenSpec change solely to represent research. The normal route into Propose SHALL be a same-Issue `Lead / explore-change` result of `PROPOSAL_READY` followed by the repository-owned routing effect to `Lead / propose-change`. Once Lead persists a change id during `propose-change`, that identity MUST remain immutable for that Issue.

A coherently routed `Lead / propose-change + Change: unset` Issue MAY be selected operationally from current routing, including after an out-of-band routing mutation, but selection alone MUST NOT satisfy Propose's action-local semantic preconditions. Before persisting a Change identity, Propose MUST dereference the exact durable same-Issue Explore `ACTION_RESULT(PROPOSAL_READY)` and verify that its still-applicable scope, constraints, exclusions, feasibility evidence, and selected direction support formalization. Missing, ambiguous, stale, or contradictory semantic evidence MUST retain/fail that selected Propose action and MUST NOT cause dispatch to skip to another pre-activation Issue.

Normal clarification and review-correction transitions SHALL remain in the same coordination Issue unless a later repository contract explicitly introduces child workflow items.

A terminal Explore result that concludes `NO_CHANGE_REQUIRED` or `NO_GO` MAY complete and close the coordination/research Issue without creating or archiving a fake OpenSpec Change.

#### Scenario: Explore remains pre-Change

- GIVEN an open coordination Issue is coherently routed to `Lead / explore-change`
- AND `Change:` is unset
- WHEN Lead investigates the problem
- THEN the Issue remains `Change: unset`
- AND no `openspec/changes/<id>/` artifact set is created by Explore
- AND generic Human admission is not required solely to execute that bounded research action

#### Scenario: Lead selects a change id only after proposal-ready Explore evidence

- GIVEN a coordination Issue has reached current `Lead / propose-change` routing
- AND `Change:` is not yet set
- AND the exact durable same-Issue Explore result is `PROPOSAL_READY`
- AND its still-applicable semantic evidence supports the current formalization direction
- WHEN Lead creates or selects the OpenSpec change id
- THEN Lead persists that change id on the coordination Issue
- AND later scheduled runs treat the persisted change id as immutable workflow identity
- AND no direct Human-to-Propose admission path is required or available as an alternative normal intake route

#### Scenario: Routed Propose without semantic baseline does not fall through

- GIVEN an open coordination Issue is coherently routed to `Lead / propose-change + Change: unset`
- AND dispatch selects it from current operational routing
- BUT Propose cannot dereference an unambiguous applicable same-Issue `PROPOSAL_READY` Explore baseline
- WHEN Lead evaluates formal activation
- THEN no Change identity is persisted
- AND the same Issue retains current Propose ownership for fail-closed diagnosis or legal correction
- AND dispatch does not authorize a later queued Issue merely because this action-local evidence is missing

#### Scenario: Explore concludes without a repository change

- GIVEN Lead has reached a decision-complete `NO_CHANGE_REQUIRED` or `NO_GO` Explore conclusion
- AND no formal Change identity was created
- WHEN Lead persists the bounded terminal research evidence
- THEN Lead may close the coordination/research Issue as completed
- AND the workflow does not create a fake OpenSpec Change only to obtain archive semantics

### Requirement: Each scheduled run processes at most one actionable work item using a fixed stable order

A scheduled invocation SHALL process at most one eligible actionable coordination Issue per run.

In `fixed-role` mode, role-local lifecycle/blocker priority SHALL remain deterministic:

- Lead: `resolve-question` > `finalize-archive` > `finalize-change` > pre-activation intake;
- Reviewer: `review-archive` > `review-implementation` > `review-openspec`;
- Executor: `merge-pr` > `implement-change`.

For Reviewer, Executor, and the three higher-priority Lead actions above, selection within the same fixed-role role/action priority SHALL choose earliest GitHub `created_at`, then lower Issue number.

If fixed-role Lead has no eligible `resolve-question`, `finalize-archive`, or `finalize-change` work, every coherently routed open `Lead / explore-change + Change: unset` entry and every coherently routed open `Lead / propose-change + Change: unset` entry SHALL form one combined pre-activation intake queue ordered by earliest GitHub `created_at`, then lower Issue number. Dispatcher queue eligibility SHALL use current structural Issue/routing facts and MUST NOT depend on origin, Human admission, prior `ACTION_RESULT` prose, or action-local semantic readiness. The selected Issue's current routing determines whether Lead executes Explore or Propose. Fixed-role mode MUST NOT apply an `explore-change > propose-change` priority inside this combined intake queue.

In `workflow-dynamic` mode, a formal active workflow or terminal-pending workflow SHALL be selected before pre-activation work; its valid routing tuple determines the role/action. The only closed-Issue active exception remains a terminal-pending `closed + agent:lead + action:finalize-archive` workflow with matching authorized merged Archive PR/native close and no valid Lead `LIFECYCLE_COMPLETE` evidence.

If no formal active or terminal-pending workflow exists, every coherently routed open `Lead / explore-change + Change: unset` entry and every coherently routed open `Lead / propose-change + Change: unset` entry SHALL form the same deterministic pre-activation queue ordered by earliest GitHub `created_at`, then lower Issue number. Only that winner may proceed. Current routing SHALL remain operational truth for queue selection; dispatch MUST NOT re-read Issue comments/events to re-prove why a coherent Propose tuple exists. Action-local semantic evidence is reconstructed only after the mapped action is selected.

The model MUST NOT substitute its own urgency or preference for either mode's deterministic selection rules.

#### Scenario: Dynamic mode follows the formal active workflow

- GIVEN dispatch mode is `workflow-dynamic`
- AND exactly one formal active workflow routes to `Executor / implement-change`
- AND queued Explore and Propose Issues also exist
- WHEN a Scheduled Task selects work
- THEN the formal active workflow is selected
- AND Executor is the fixed invocation role
- AND the queued pre-activation work remains queued

#### Scenario: Dynamic mode selects earliest pre-activation entry across current Explore and Propose routing

- GIVEN dispatch mode is `workflow-dynamic`
- AND no formal active or terminal-pending workflow exists
- AND an older coherently routed `Lead / propose-change + Change: unset` Issue exists
- AND a newer coherently routed `Lead / explore-change + Change: unset` Issue exists
- WHEN Scheduled workflow selects pre-activation work
- THEN the older Propose Issue is selected by GitHub creation order
- AND the newer Explore Issue remains queued
- AND dispatch does not read prior `ACTION_RESULT` prose or Human-admission evidence to decide whether the older current routing may participate

#### Scenario: Irrelevant result prose cannot alter pre-activation selection

- GIVEN the deterministic pre-activation winner is a coherently routed `Lead / propose-change + Change: unset` Issue
- AND an earlier Issue comment contains additional prose fields such as another bullet beginning `- Workflow:`
- WHEN dispatch reconstructs the current pre-activation queue
- THEN that comment is not parsed for queue eligibility
- AND the current Propose routing remains in the queue
- AND FIFO selection is unchanged by the prose shape

#### Scenario: Fixed-role Lead uses the same combined pre-activation winner

- GIVEN dispatch mode is `fixed-role`
- AND the scheduled role is Lead
- AND no eligible `resolve-question`, `finalize-archive`, or `finalize-change` work exists
- AND an older coherently routed Propose Issue and a newer coherently routed Explore Issue are both valid with `Change: unset`
- WHEN Lead selects pre-activation intake
- THEN the older Propose Issue is selected
- AND the newer Explore Issue remains queued
- AND action type does not override the combined queue's creation-order winner

#### Scenario: Open Explore remains selected without an in-progress marker

- GIVEN the oldest valid pre-activation entry is an open `Lead / explore-change` Issue
- AND it has not reached a terminal result or transitioned to Propose
- WHEN a later wake reconstructs the same queue
- THEN that same Issue remains the deterministic winner by stable creation order
- AND no `status:exploring`, lease, heartbeat, approval token, or hidden ownership state is required

#### Scenario: Dynamic mode selects terminal reconstruction before queued work

- GIVEN dispatch mode is `workflow-dynamic`
- AND a closed coordination Issue is terminal-pending under `Lead / finalize-archive`
- AND queued Explore or Propose work exists
- WHEN a Scheduled Task selects work
- THEN the closed terminal-pending workflow is selected
- AND Lead is the fixed invocation role
- AND queued pre-activation work remains queued

### Requirement: Persisted Change identity defines the single active workflow boundary

An open coordination Issue with a valid routing tuple and a persisted non-`unset` `Change:` identity SHALL be an active workflow. The repository MUST allow at most one such active workflow at a time.

A closed coordination Issue SHALL also remain terminal-pending active workflow work only when all of the following hold:

- it has a persisted non-`unset` `Change:` identity;
- its routing tuple is exactly `agent:lead + action:finalize-archive`;
- the repository-approved Archive PR for that Change is durably merged and the Issue is natively closed by the approved closing linkage; and
- no durable Lead `LIFECYCLE_COMPLETE` result bound to that archive merge exists yet.

Once Lead records valid `LIFECYCLE_COMPLETE` evidence after terminal reconstruction, that closed tuple SHALL be terminal history, MUST NOT be selected as active work, and MUST NOT block later workflow admission.

Open coherently routed `Lead / explore-change + Change: unset` and `Lead / propose-change + Change: unset` coordination Issues SHALL be queued pre-activation work based on current structural routing. Neither form counts as an active workflow before Propose persists an immutable Change identity. Dispatcher selection MUST NOT distinguish an unset Propose by origin, Human admission, comment provenance, or reconstructed semantic readiness.

Lead MUST NOT activate a queued proposal while another active or terminal-pending workflow exists. If no active or terminal-pending workflow exists, deterministic pre-activation selection SHALL be evaluated across the single combined set of coherently routed open `Lead / explore-change + Change: unset` and `Lead / propose-change + Change: unset` candidates using earliest GitHub `created_at`, then lower Issue number. Only that combined-queue winner may proceed. A `propose-change` runner MUST re-check that its Issue is still that same winner immediately before persisting a non-`unset` Change identity.

A proposal-ready Explore remains pre-activation until repository-owned application legally routes that same Issue to `Lead / propose-change`. The transition SHALL NOT require a generic Human proceed confirmation when the proposal-ready direction remains inside the bounded researched/canonical evidence and introduces no Human-reserved decision. After routing, the same Issue retains its original queue position. Propose SHALL reconstruct the exact durable same-Issue `PROPOSAL_READY` semantic baseline before activation; an absent/invalid baseline blocks that selected action rather than changing dispatcher eligibility. If formalization would introduce a new Human-reserved product/project direction, material externally observable behavior or scope trade-off, explicit risk acceptance, or materially different security/privacy/cost/operational commitment, Lead MUST use the existing `HUMAN_DECISION_REQUIRED` boundary instead of treating routing or Explore execution as Human authority.

#### Scenario: Queued pre-activation work exists while another workflow is active

- GIVEN Change A is an active workflow
- AND Issue B is an open routed `Lead / explore-change` or `Lead / propose-change` Issue with `Change: unset`
- WHEN workflow-dynamic dispatch reconstructs work
- THEN Change A remains the only active workflow
- AND Issue B is not activated or globally arbitrated against Change A

#### Scenario: Closed terminal handoff still blocks new activation

- GIVEN Change A has an authorized merged Archive PR and its coordination Issue is natively closed
- AND that Issue is routed `Lead / finalize-archive`
- AND no valid Lead `LIFECYCLE_COMPLETE` evidence exists for the archive merge
- AND queued Explore or Propose work exists with `Change: unset`
- WHEN workflow-dynamic dispatch reconstructs work
- THEN Change A is selected as terminal-pending workflow work
- AND the queued pre-activation work is not activated

#### Scenario: Older current Propose routing prevents later Explore activation

- GIVEN no open active workflow exists
- AND no closed terminal-pending workflow exists
- AND an older coherently routed `Lead / propose-change + Change: unset` Issue exists
- AND a newer coherently routed `Lead / explore-change + Change: unset` Issue exists
- WHEN Lead evaluates pre-activation work
- THEN the older Propose Issue is the deterministic combined-queue winner
- AND the newer Explore Issue remains queued
- AND dispatch does not omit the older Issue because of missing or malformed historical semantic prose

#### Scenario: Proposal-ready Explore keeps its queue position through deterministic routing

- GIVEN an Explore Issue is the deterministic combined-queue winner
- AND Lead returns structured `PROPOSAL_READY` within the bounded current context
- AND no new Human-reserved decision is introduced
- WHEN repository-owned application derives and applies `Lead / propose-change` routing while `Change:` remains unset
- THEN no generic second Human approval is required for that transition
- AND the same Issue retains its original GitHub `created_at` and queue position
- AND Propose may persist the immutable Change identity only after re-checking that this Issue remains the combined-queue winner and its action-local semantic baseline is valid

#### Scenario: Selected Propose with missing semantic evidence retains ownership

- GIVEN no active or terminal-pending workflow exists
- AND the FIFO-selected pre-activation candidate is current `Lead / propose-change + Change: unset`
- BUT the mapped Propose action cannot prove the required same-Issue Explore semantic baseline
- WHEN Propose evaluates activation
- THEN no Change identity is persisted
- AND the current Issue remains selected/owned for its legal fail-closed disposition
- AND a later Explore or Propose candidate is not silently authorized as fallback

#### Scenario: Out-of-band coherent Propose routing is operational but not semantic authority

- GIVEN an administrator or connector writes a structurally coherent `Lead / propose-change + Change: unset` tuple
- WHEN dispatch reconstructs current pre-activation state
- THEN the Issue participates in deterministic selection from current routing without label-writer provenance reconstruction
- AND that routing does not manufacture the required Explore semantic baseline
- AND consequential Propose activation still fails closed unless its action-local semantic preconditions are satisfied

### Requirement: Human-required authority is bound to the repository Human actor

For workflow decisions that governance reserves to Human, durable GitHub actor identity alone MUST NOT satisfy Human authority. Activity from actors other than `royhsu-work` MAY be supporting evidence but MUST NOT satisfy Human-required answers, authorization, or resume conditions. Formal Explore execution and ordinary current pre-activation routing are not Human-reserved decisions and therefore do not consume this Human-authority predicate.

Each Human-reserved consumer that uses the general provenance-bound decision predicate SHALL reconstruct exactly one expected durable `decision_ref` from the workflow boundary it is consuming. The Human decision comment SHALL explicitly declare that same reference using the canonical line:

```text
Human-Decision-For: <decision_ref>
```

The `decision_ref` is a correlation reference to already-durable workflow evidence, not a secret, approval token, hidden state, or authorization database. Current consumers of the general predicate SHALL use only these exact forms:

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

The existing `intake:approved` label SHALL remain the distinct Human-only advisory-admission capability marker. Its current presence or actor attribution alone MUST NOT prove Human identity or approval. When advisory admission consumes a Human decision, the expected reference is exactly `issue:<issue-number>:advisory-admission` and the intended Human decision evidence SHALL satisfy the provenance-bound contract above. Scheduled roles MUST NOT add, remove, restore, or manufacture either `human:approved` or `intake:approved` when those labels are reserved Human capabilities.

An Explore Issue, its routing labels, its creator identity, its successful execution, or a current Propose routing tuple MUST NOT be treated as Human authority for a later Human-reserved commitment. Connector/App activity remains non-Human for every boundary that still requires Human authority.

Issue bodies or natural-language identity claims, object author/actor identity alone, `human:notified`, ordinary routing labels, current approval-label snapshots without a qualifying event, comments lacking the expected `decision_ref`, and `unlabeled` event provenance MUST NOT establish Human authority.

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

- GIVEN a decision comment or approval-label event is attributed to `royhsu-work`
- AND raw GitHub provenance records a non-null GitHub App for that creation/event
- WHEN a Human-reserved answer, authorization, or resume condition is evaluated
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

#### Scenario: Exact current Human decision anchors are deterministic

- GIVEN a workflow boundary is currently reserved to Human and consumes the general provenance-bound predicate
- WHEN its exact decision anchor is reconstructed
- THEN advisory admission uses exactly `issue:<N>:advisory-admission`
- AND an answer or resume from canonical `HUMAN_DECISION_REQUIRED` uses exactly `issuecomment:<C>`
- AND ordinary `Lead / explore-change` and current pre-activation routing require no Human-admission anchor

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

- GIVEN an Explore candidate was created from independently reconstructable repository-authorized evidence
- WHEN dispatch evaluates ordinary Formal Explore execution
- THEN the candidate may be queue-eligible without manufacturing Human evidence
- AND `human:approved` is not required merely to relabel repository authority as Human authority
- AND that repository evidence does not satisfy any later Human-reserved decision

#### Scenario: Human-created Formal Explore Issue is sufficient routing input after coherent routing exists

- GIVEN Issue N was created directly by `royhsu-work`
- AND it is coherently routed as `Change: unset + agent:lead + action:explore-change`
- WHEN dispatch evaluates ordinary Formal Explore execution
- THEN the Issue may be queue-eligible without a separate Human admission predicate
- AND Human creation provenance or a legacy `Admission: Lead / explore-change` declaration is not required solely for Explore execution
- AND Issue creation does not authorize a later Human-reserved commitment

#### Scenario: Connector-created Human-looking Issue is not Human authority

- GIVEN an Issue displays `user.login == royhsu-work`
- AND raw Issue creation provenance identifies a GitHub App
- WHEN dispatch evaluates ordinary Formal Explore execution and later Human-reserved boundaries
- THEN coherent Explore routing may still make the Issue queue-eligible under the normal deterministic Explore rules
- AND connector/App provenance is not Human authority for any boundary that remains Human-reserved

#### Scenario: Later connector routing can route but not authorize Human decisions

- GIVEN repository tooling applies a structurally coherent workflow routing tuple to an open `Change: unset` Issue
- WHEN dispatch evaluates ordinary pre-activation execution
- THEN those routing labels may make the Issue queue-eligible under the deterministic pre-activation rules
- AND the label mutation itself does not establish Human authority for advisory admission, escalation answer/resume, or another Human-reserved boundary

#### Scenario: Ambiguous or mutated creation declaration does not control Explore execution

- GIVEN a legacy creation-time Explore admission declaration is absent, mutated, ambiguous, or cannot be reconstructed
- WHEN dispatch evaluates ordinary Formal Explore execution after this contract activates
- THEN dispatch does not use that declaration as an Explore authorization predicate
- AND coherent routing and deterministic queue rules govern ordinary Explore eligibility
- AND any later Human-reserved decision still requires the existing full provenance-bound Human decision predicate

#### Scenario: Routed Explore is not Human authority

- GIVEN an open Issue has coherent `Change: unset + agent:lead + action:explore-change` routing
- WHEN dispatch evaluates ordinary Formal Explore execution
- THEN generic Human approval is not required solely to execute Explore
- AND the Issue/routing/execution is not treated as Human authority for any later Human-reserved decision

#### Scenario: Historical completion is not retroactively invalidated

- GIVEN a workflow reached valid terminal completion before this provenance contract became authoritative
- WHEN a later run reconstructs historical evidence
- THEN the completed workflow remains historical terminal evidence
- AND the new provenance rule does not reopen or invalidate that completed lifecycle solely because older Human evidence used the prior contract

#### Scenario: Pending Human-reserved evidence is consumed under current authority rules

- GIVEN a Human-reserved decision was recorded before this contract became authoritative
- AND that decision has not yet been legally consumed
- WHEN a workflow attempts to consume it after default-branch activation
- THEN the current applicable provenance requirement applies
- AND insufficient prior evidence fails closed for fresh qualifying Human evidence under the applicable boundary

## ADDED Requirements

### Requirement: Explore dispositions are structured bounded results with repository-derived effects

`Lead / explore-change` SHALL return exactly one structured bounded disposition from this finite vocabulary:

- `PROPOSAL_READY`;
- `HUMAN_DECISION_REQUIRED`;
- `NO_CHANGE_REQUIRED`; or
- `NO_GO`.

The Lead worker SHALL remain responsible for the semantic judgment that the selected disposition is warranted. The same worker result MAY also carry narrative evidence/content for durable audit presentation, but repository application MUST consume the bounded disposition directly and MUST NOT re-extract the machine disposition from free-form Markdown, Issue comments, or another model call.

After fresh source-action reauthorization, repository-owned application SHALL derive the legal Explore effect from the authorized source `Lead / explore-change` plus the bounded disposition:

- `PROPOSAL_READY` derives same-Issue routing to `Lead / propose-change` while `Change:` remains unset;
- `HUMAN_DECISION_REQUIRED` retains `Lead / explore-change` and uses the existing governed Human escalation path;
- `NO_CHANGE_REQUIRED` derives the existing terminal pre-Change research close/routing-retirement effect; and
- `NO_GO` derives the existing terminal pre-Change research close/routing-retirement effect.

The Explore worker MUST NOT independently choose an arbitrary successor routing tuple as control state. If a worker request contains a routing successor inconsistent with, unnecessary for, or additional to the repository-derived effect, repository application SHALL reject that worker-chosen transition rather than allow the worker to redefine workflow topology. Legal successor validation SHALL still use current default-branch `agents/workflow.md`; this bounded derivation MUST NOT create a second workflow DAG or generic workflow engine.

The implementation MUST NOT introduce OpenAI API/model-call fallback classification, a prose parser as a control-state authority, hidden result state, a lock/lease/heartbeat, or generalized result-derived transitions for unrelated actions merely because Explore now uses a bounded structured result.

#### Scenario: Structured proposal-ready result derives Propose routing

- GIVEN current machine dispatch authorizes `Lead / explore-change` for Issue N
- AND the Lead worker returns structured result `PROPOSAL_READY`
- AND repository application freshly reauthorizes that same source action
- WHEN the Explore effect is applied
- THEN repository application derives `Lead / propose-change` for the same Issue
- AND `Change:` remains unset
- AND the worker does not need to supply a target routing tuple
- AND fresh redispatch consumes the new current routing directly

#### Scenario: Conflicting worker-chosen successor cannot override result

- GIVEN current machine dispatch authorizes `Lead / explore-change`
- AND the worker returns structured `PROPOSAL_READY`
- BUT the worker also requests routing to an unrelated or inconsistent successor
- WHEN repository application validates effects
- THEN the worker-chosen successor is rejected
- AND only the result-derived legal Explore effect may be applied
- AND model preference cannot choose another workflow successor

#### Scenario: Human-decision result retains Explore ownership

- GIVEN current machine dispatch authorizes `Lead / explore-change`
- AND Lead's semantic judgment returns structured `HUMAN_DECISION_REQUIRED`
- WHEN repository application consumes the result
- THEN routing remains `Lead / explore-change`
- AND the existing provenance-bound Human escalation/response contract remains authoritative
- AND no direct-Propose admission mechanism is introduced

#### Scenario: Terminal research results derive terminal effects

- GIVEN current machine dispatch authorizes `Lead / explore-change`
- AND Lead returns structured `NO_CHANGE_REQUIRED` or `NO_GO`
- WHEN repository application consumes the result
- THEN it derives the existing legal pre-Change terminal research close/routing-retirement behavior
- AND no fake Change identity is created

#### Scenario: Narrative Markdown cannot redefine the bounded result

- GIVEN the structured worker disposition is one legal Explore result
- AND narrative result content contains text that looks like another `Workflow:`, `Action:`, or `Result:` field
- WHEN repository application determines the workflow effect
- THEN it uses only the validated structured disposition
- AND it does not parse the narrative Markdown to reconstruct machine control state