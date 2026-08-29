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

#### Scenario: Lead selects a change id only after Propose entry

- GIVEN a coordination Issue has reached current `Lead / propose-change` routing
- AND `Change:` is not yet set
- AND the exact durable same-Issue Explore result is `PROPOSAL_READY`
- AND its still-applicable semantic evidence supports the current formalization direction
- WHEN Lead creates or selects the OpenSpec change id
- THEN Lead persists that change id on the coordination Issue
- AND later scheduled runs treat the persisted change id as immutable workflow identity
- AND no direct Human-to-Propose admission path is available as an alternative normal intake route

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

#### Scenario: Dynamic mode selects earliest pre-activation entry across Explore and Propose

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

#### Scenario: Older Explore prevents later direct-Propose activation

- GIVEN no active or terminal-pending workflow exists
- AND an older coherently routed `Lead / explore-change + Change: unset` Issue exists
- AND a newer coherently routed `Lead / propose-change + Change: unset` Issue exists
- WHEN dispatch selects pre-activation work after direct-Propose admission has been removed
- THEN the older Explore remains the deterministic combined-queue winner by creation order
- AND the newer Propose remains queued because current routing participates in the same FIFO, not because a direct-Propose Human-admission predicate exists

#### Scenario: Proposal-ready Explore keeps its queue position when Human authorizes Propose

- GIVEN an Explore Issue is the deterministic combined-queue winner
- AND Lead returns structured `PROPOSAL_READY` within the bounded current context
- AND no new Human-reserved decision is introduced
- WHEN repository-owned application routes the same Issue to `Lead / propose-change`
- THEN no Human authorization is required for that normal transition under the new contract
- AND the same Issue retains its original GitHub `created_at` and queue position
- AND Propose may persist the immutable Change identity only after re-checking queue ownership and its action-local semantic baseline

#### Scenario: Oldest eligible Propose activates after older Explore terminates

- GIVEN no active or terminal-pending workflow exists
- AND an older Explore has legally reached terminal `NO_CHANGE_REQUIRED` or `NO_GO` and left pre-activation routing
- AND at least one coherently routed `Lead / propose-change + Change: unset` Issue remains
- WHEN dispatch selects pre-activation work
- THEN the earliest remaining coherent candidate is selected by `created_at`, then Issue number
- AND Propose may activate only after its action-local semantic baseline and activation preconditions pass
- AND no Human direct-Propose admission predicate is evaluated

#### Scenario: Selected Propose with missing semantic evidence retains ownership

- GIVEN the FIFO-selected pre-activation candidate is current `Lead / propose-change + Change: unset`
- BUT the mapped Propose action cannot prove the required same-Issue Explore semantic baseline
- WHEN Propose evaluates activation
- THEN no Change identity is persisted
- AND the current Issue remains selected/owned for its legal fail-closed disposition
- AND a later candidate is not silently authorized as fallback

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

Current consumers of the general predicate SHALL use only these exact forms:

- Human-only advisory admission guarded by `intake:approved`: `issue:<issue-number>:advisory-admission`.
- A Human answer, authorization, or resume decision produced from canonical `HUMAN_DECISION_REQUIRED`: `issuecomment:<escalation-comment-id>`.

A later Human-reserved consumer MUST define its exact `decision_ref` form in canonical governance before using the predicate. Missing, inaccessible, ambiguous, contradictory, malformed, unorderable, or reference-mismatched evidence MUST fail closed rather than allowing model inference.

For a valid Human-reserved decision, the selected decision comment MUST be on the same coordination Issue, declare the exact expected reference, be authored by `royhsu-work`, and have raw creation provenance `performed_via_github_app == null`. `human:approved` MUST currently be present and a qualifying Human-only labeled event MUST have `actor.login == royhsu-work` plus `performed_via_github_app == null`. Event-first binding SHALL select the latest qualifying Human-created decision comment preceding each approval event by GitHub `created_at`, then numeric comment id; only after binding may the declared reference be compared with the current expected boundary. One approval event authorizes at most one bound comment/reference. A later replacement comment requires a later qualifying approval event, and `decision_comment.updated_at > approval_event.created_at` invalidates that earlier approval for the edited revision.

Where normalized connector reads omit `performed_via_github_app`, the workflow MUST inspect raw GitHub provenance or fail closed. `unlabeled` events MAY invalidate current label state but MUST NOT establish Human authority.

`intake:approved` remains the distinct Human-only advisory-admission capability marker. Its snapshot alone is insufficient authority. Scheduled roles MUST NOT add, remove, restore, or manufacture `human:approved` or `intake:approved`.

An Explore Issue, routing labels, creator identity, successful Explore execution, or current Propose routing MUST NOT be treated as Human authority for a later Human-reserved commitment. `human:notified` remains analytics-only metadata and MUST NOT grant authority, route work, create waiting semantics, participate in resume conditions, or prove that Human answered.

This authority rule SHALL remain prospective at its default-branch activation boundary; previously terminal workflows and Human authority already legally consumed under an earlier authoritative contract remain historical evidence.

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

- GIVEN the current Human-reserved consumer reconstructs one expected canonical `decision_ref`
- AND a qualifying Human-only `human:approved` event uniquely binds to one qualifying Human-created decision comment
- AND that comment declares the expected reference and has raw `performed_via_github_app == null`
- AND the comment has not been edited after the approval event
- WHEN the workflow evaluates the intended Human-reserved decision
- THEN the provenance-bound decision satisfies Human authority

#### Scenario: One approval event cannot authorize two decision references

- GIVEN Human-created comments for R1 and R2 both precede one qualifying Human-only approval event E
- AND R2 is later by `created_at`, then comment id
- WHEN E is evaluated
- THEN E binds only to R2 before boundary comparison
- AND E MUST NOT also authorize R1 by re-filtering candidates

#### Scenario: Multiple Human comments do not require model disambiguation

- GIVEN multiple qualifying Human-created decision comments precede approval event E
- WHEN E is evaluated
- THEN the latest qualifying comment is selected deterministically by `created_at`, then comment id
- AND model inference does not choose the intended comment

#### Scenario: Replacement decision for the same boundary requires reapproval

- GIVEN an earlier decision comment for R was approved
- AND a later Human-created replacement also declares R
- WHEN R is evaluated before any qualifying later approval event
- THEN the earlier event does not approve the replacement
- AND the workflow fails closed until the replacement is later approved

#### Scenario: Exact current admission anchors are deterministic

- GIVEN a workflow boundary is currently reserved to Human and consumes the general predicate
- WHEN its exact decision anchor is reconstructed
- THEN advisory admission uses exactly `issue:<N>:advisory-admission`
- AND an answer/resume from canonical `HUMAN_DECISION_REQUIRED` uses exactly `issuecomment:<C>`
- AND no direct-Propose Human-admission anchor exists under the new contract
- AND ordinary Explore/current pre-activation routing requires no Human-admission anchor

#### Scenario: Escalation answer anchor is deterministic

- GIVEN Lead persisted canonical `HUMAN_DECISION_REQUIRED` as comment id 12345
- WHEN a later Human answer/resume is evaluated
- THEN the expected reference is exactly `issuecomment:12345`
- AND no PR/revision or generic Issue reference substitutes for it

#### Scenario: Missing or unmapped decision reference fails closed

- GIVEN a Human-reserved consumer has no exact canonical reference mapping
- OR the available Human comment lacks or mismatches that reference
- WHEN Human authority is evaluated
- THEN the workflow does not invent an anchor or reinterpret prose
- AND Human authority fails closed

#### Scenario: Approved comment is edited afterward

- GIVEN a Human decision comment was approved
- AND it is later edited after the approval event
- WHEN prior approval is evaluated
- THEN prior approval is invalid for the edited revision
- AND a later qualifying approval event is required

#### Scenario: Normalized read lacks provenance

- GIVEN a normalized connector read identifies actor `royhsu-work` but omits `performed_via_github_app`
- WHEN Human authority is required
- THEN actor identity alone is insufficient
- AND raw provenance is obtained or evaluation fails closed

#### Scenario: Advisory intake marker remains distinct

- GIVEN advisory Issue N is being Human-admitted
- AND `intake:approved` is currently present
- WHEN Human authority is evaluated
- THEN the snapshot alone is insufficient
- AND the expected reference is exactly `issue:<N>:advisory-admission`
- AND the intended decision must satisfy the full provenance-bound contract

#### Scenario: Repository-authorized Explore does not impersonate Human admission

- GIVEN an Explore candidate was created from independently reconstructable repository-authorized evidence
- WHEN dispatch evaluates ordinary Explore execution
- THEN it may be queue-eligible without manufacturing Human evidence
- AND that repository evidence does not satisfy a later Human-reserved decision

#### Scenario: Human-created Formal Explore Issue is sufficient admission

- GIVEN Issue N was created directly by `royhsu-work`
- AND it is coherently routed `Change: unset + agent:lead + action:explore-change`
- WHEN dispatch evaluates ordinary Explore execution
- THEN the Issue may be queue-eligible without a separate Human admission predicate
- AND creation does not authorize a later Human-reserved commitment

#### Scenario: Connector-created Human-looking Issue is not Human admission

- GIVEN an Issue displays `user.login == royhsu-work`
- AND raw creation provenance identifies a GitHub App
- WHEN dispatch evaluates ordinary Explore/current routing and later Human-reserved boundaries
- THEN coherent routing may still be operationally queue-eligible
- AND connector/App provenance is not Human authority for a Human-reserved boundary

#### Scenario: Later connector routing can route but not authorize

- GIVEN repository tooling applies a structurally coherent workflow routing tuple to an open `Change: unset` Issue
- WHEN dispatch evaluates ordinary pre-activation execution
- THEN those labels may make the Issue queue-eligible under deterministic routing rules
- AND that mutation does not establish Human authority for advisory admission, escalation answer/resume, or another Human-reserved boundary

#### Scenario: Ambiguous or mutated creation declaration falls back to existing predicate

- GIVEN a legacy creation-time Explore admission declaration is absent, mutated, ambiguous, or unreconstructable
- WHEN dispatch evaluates ordinary Explore execution after activation
- THEN it does not use that declaration as an Explore authorization predicate
- AND coherent current routing controls ordinary Explore eligibility
- AND later Human-reserved decisions still use the provenance-bound predicate

#### Scenario: Routed Explore is not Human authority

- GIVEN an open Issue has coherent `Change: unset + agent:lead + action:explore-change` routing
- WHEN dispatch evaluates ordinary Explore execution
- THEN generic Human approval is not required solely to execute Explore
- AND the Issue/routing/execution is not Human authority for a later Human-reserved decision

#### Scenario: Historical completion is not retroactively invalidated

- GIVEN a workflow reached valid terminal completion before this authority contract became active
- WHEN later reconstruction evaluates history
- THEN the completed workflow remains historical terminal evidence
- AND it is not reopened solely because older Human evidence used the then-authoritative contract

#### Scenario: Pending pre-activation evidence is consumed after activation

- GIVEN a Human-reserved advisory or escalation decision was recorded before this contract became authoritative
- AND it has not yet been legally consumed
- WHEN workflow attempts to consume it after activation
- THEN the current applicable provenance rule applies
- AND insufficient evidence fails closed for fresh qualifying Human evidence

#### Scenario: Direct Propose keeps existing Human approval contract

- GIVEN direct Human-to-Propose admission existed under an earlier authoritative contract
- WHEN the new contract is active for normal intake
- THEN no new direct-Propose admission is accepted or reconstructed
- AND historical direct-Propose authority already legally consumed before activation remains historical evidence rather than being retroactively invalidated
- AND any current coherent Propose routing is selected only as operational state and still requires its action-local Explore semantic baseline before activation

## ADDED Requirements

### Requirement: Explore dispositions are structured bounded results with repository-derived effects

`Lead / explore-change` SHALL return exactly one structured bounded disposition from `PROPOSAL_READY`, `HUMAN_DECISION_REQUIRED`, `NO_CHANGE_REQUIRED`, or `NO_GO`. Lead remains responsible for the semantic judgment. Narrative result content MAY remain durable audit/traceability evidence, but repository application MUST consume the bounded disposition directly and MUST NOT re-extract machine control state from free-form Markdown, Issue comments, or another model call.

After fresh source-action reauthorization, repository-owned application SHALL derive the legal Explore effect from source `Lead / explore-change` plus the bounded result: `PROPOSAL_READY` derives same-Issue `Lead / propose-change` with `Change: unset`; `HUMAN_DECISION_REQUIRED` retains Explore and uses the existing Human escalation path; `NO_CHANGE_REQUIRED` and `NO_GO` derive the existing pre-Change terminal research close/routing-retirement behavior.

The worker MUST NOT independently choose an arbitrary successor routing tuple for Explore. Inconsistent/additional worker routing requests SHALL be rejected. Legal successor validation still consumes current default-branch `agents/workflow.md`. This bounded mapping MUST NOT become a second workflow DAG, generic workflow engine, OpenAI/model-call classifier, hidden result state, or generalized result-derived mechanism for unrelated actions.

#### Scenario: Structured proposal-ready result derives Propose routing

- GIVEN current machine dispatch authorizes `Lead / explore-change` for Issue N
- AND Lead returns structured `PROPOSAL_READY`
- AND application freshly reauthorizes the same source action
- WHEN the Explore effect is applied
- THEN application derives same-Issue `Lead / propose-change`
- AND `Change:` remains unset
- AND fresh redispatch consumes the new current routing directly

#### Scenario: Conflicting worker-chosen successor cannot override result

- GIVEN current machine dispatch authorizes `Lead / explore-change`
- AND the worker returns structured `PROPOSAL_READY`
- BUT also requests an inconsistent successor
- WHEN application validates effects
- THEN the worker-chosen successor is rejected
- AND only the result-derived legal Explore effect may be applied

#### Scenario: Human-decision result retains Explore ownership

- GIVEN current machine dispatch authorizes `Lead / explore-change`
- AND Lead returns structured `HUMAN_DECISION_REQUIRED`
- WHEN application consumes the result
- THEN routing remains `Lead / explore-change`
- AND the existing provenance-bound Human escalation/response contract remains authoritative

#### Scenario: Terminal research results derive terminal effects

- GIVEN current machine dispatch authorizes `Lead / explore-change`
- AND Lead returns structured `NO_CHANGE_REQUIRED` or `NO_GO`
- WHEN application consumes the result
- THEN it derives existing legal pre-Change terminal research close/routing retirement
- AND no fake Change identity is created

#### Scenario: Narrative Markdown cannot redefine the bounded result

- GIVEN the structured worker disposition is one legal Explore result
- AND narrative content contains another `Workflow:`, `Action:`, or `Result:`-looking field
- WHEN application determines the workflow effect
- THEN it uses only the validated structured disposition
- AND it does not parse narrative Markdown to reconstruct machine control state