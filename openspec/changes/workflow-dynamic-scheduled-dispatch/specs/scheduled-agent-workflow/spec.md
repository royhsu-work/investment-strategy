# scheduled-agent-workflow Delta Specification

## ADDED Requirements

### Requirement: Default-branch governance declares the scheduled dispatch mode

The repository SHALL declare exactly one authoritative `Scheduled-Dispatch-Mode` marker in default-branch `agents/AGENTS.md`, with value `fixed-role` or `workflow-dynamic`.

A Scheduled Task MUST determine dispatch mode from that marker after loading default-branch governance and MUST NOT infer the mode from task names, conversation memory, Issues, PRs, or feature branches.

#### Scenario: Workflow-dynamic mode is declared

- GIVEN default-branch `agents/AGENTS.md` declares `Scheduled-Dispatch-Mode: workflow-dynamic`
- WHEN any Scheduled Task wakes
- THEN it uses workflow-dynamic dispatch
- AND its legacy externally assigned role does not override the repository-selected role

#### Scenario: Fixed-role mode is declared

- GIVEN default-branch `agents/AGENTS.md` declares `Scheduled-Dispatch-Mode: fixed-role`
- WHEN a legacy role Scheduled Task wakes
- THEN it uses its externally assigned legacy role
- AND follows the existing role-local deterministic discovery contract

### Requirement: Workflow-dynamic dispatch derives one fixed invocation role from durable workflow state

In `workflow-dynamic` mode, a wake SHALL reconstruct current durable workflow state before selecting a role. If exactly one active workflow exists, its valid routing tuple SHALL determine the invocation role/action and mapped skill.

Once selected, the invocation role MUST remain fixed for the remainder of that run. A routing handoff MAY persist a different next role/action, but the current invocation MUST end rather than redispatch to the new role.

The dispatcher MUST NOT introduce model-derived global urgency, cross-role priority scoring, or a second workflow DAG.

#### Scenario: Active workflow routes to Reviewer

- GIVEN dispatch mode is `workflow-dynamic`
- AND the single active workflow has valid routing `agent:reviewer + action:review-openspec`
- WHEN a Scheduled Task dispatches the run
- THEN Reviewer is selected for that invocation
- AND the `review-openspec` skill is loaded
- AND any legacy external Lead/Reviewer/Executor assignment is ignored for role selection

#### Scenario: Handoff changes the next owner

- GIVEN the current invocation was dispatched as Lead
- AND Lead durably completes its action and legally hands off to Reviewer
- WHEN the routing tuple is changed to Reviewer
- THEN the current invocation ends as Lead
- AND it does not execute Reviewer work in the same invocation

### Requirement: Selected Scheduled Agent actions are work-conserving within an invocation

After a Scheduled Agent invocation selects one legal role/action, that selected action SHALL continue all immediately actionable work within the same invocation while the routing still matches the selected action, required revision/preconditions and authority remain current, and no legal blocking condition exists.

A durable checkpoint, remaining approved local work, a recoverable same-role failure, or a failed-but-actionable validation MUST NOT by itself be treated as a voluntary yield point. When the correction is within the selected role/action authority and approved contract, the invocation SHALL perform that correction and continue the action instead of deferring it solely to a later wake.

A selected action MAY end before its normal completion only when at least one of these conditions applies:

- the action has completed a legal handoff or terminal result;
- continuing requires a different role or authoritative Human decision;
- progress genuinely depends on external asynchronous evidence that is not yet available;
- approved contract/state is genuinely ambiguous, contradictory, or unsafe to continue under the selected authority;
- stale or competing durable state invalidates the invocation's revision/base/preconditions; or
- an actual tool failure, hard runtime limit, or other execution interruption prevents continuation.

The generic continuation/termination contract SHALL be owned once by shared governance in `agents/AGENTS.md`. Role and skill documents MUST NOT duplicate or weaken this shared rule; they MAY define only action-specific results, authority boundaries, waits, blockers, and handoffs.

#### Scenario: Failed validation is locally actionable

- GIVEN a selected action still owns the current routing
- AND its validation fails for a clear correction inside that same action's approved authority
- AND the execution revision/preconditions remain current
- WHEN the invocation evaluates whether to stop
- THEN the validation failure is not a voluntary yield point
- AND the invocation corrects the failure and reruns the required validation in the same invocation

#### Scenario: Verified implementation checkpoint has more approved work

- GIVEN Executor is selected for `implement-change`
- AND one approved Slice reaches successful VERIFY and its required checkpoint is persisted
- AND another approved Slice is immediately actionable under the same current routing and approved contract
- WHEN Executor completes the checkpoint boundary
- THEN the checkpoint is a durable recovery boundary rather than a scheduled-run termination boundary
- AND Executor continues the next approved Slice in the same invocation

#### Scenario: External asynchronous evidence is genuinely pending

- GIVEN Lead is selected for a finalize action
- AND the action has completed all immediately actionable Lead work
- AND legal continuation depends on repository automation that is still running and whose result is not yet available
- WHEN Lead evaluates continuation
- THEN retaining the current routing and ending the invocation is a legal external-wait outcome

#### Scenario: Competing durable state invalidates the execution base

- GIVEN an invocation selected a role/action from durable revision R
- AND another run wins a competing durable mutation so the required base/preconditions are no longer current
- WHEN the first invocation rechecks its preconditions
- THEN it stops as stale rather than rebasing or continuing speculative work inside the same invocation

### Requirement: Persisted Change identity defines the single active workflow boundary

An open coordination Issue with a valid routing tuple and a persisted non-`unset` `Change:` identity SHALL be an active workflow. The repository MUST allow at most one such active workflow at a time.

A closed coordination Issue SHALL also remain terminal-pending active workflow work only when all of the following hold:

- it has a persisted non-`unset` `Change:` identity;
- its routing tuple is exactly `agent:lead + action:finalize-archive`;
- the repository-approved Archive PR for that Change is durably merged and the Issue is natively closed by the approved closing linkage; and
- no durable Lead `LIFECYCLE_COMPLETE` result bound to that archive merge exists yet.

Once Lead records valid `LIFECYCLE_COMPLETE` evidence after terminal reconstruction, that closed tuple SHALL be terminal history, MUST NOT be selected as active work, and MUST NOT block later workflow admission.

An open Human-admitted `Lead / propose-change` coordination Issue with `Change: unset` SHALL be queued pre-activation work and MUST NOT count as an active workflow until Lead persists its immutable Change identity.

Lead MUST NOT activate a queued proposal while another active or terminal-pending workflow exists. If no active or terminal-pending workflow exists, deterministic admission among queued `propose-change` candidates SHALL use earliest GitHub `created_at`, then lower Issue number.

#### Scenario: Queued proposal exists while another workflow is active

- GIVEN Change A is an active workflow
- AND Change B is an open `Lead / propose-change` Issue with `Change: unset`
- WHEN workflow-dynamic dispatch reconstructs work
- THEN Change A remains the only active workflow
- AND Change B is not activated or globally arbitrated against Change A

#### Scenario: Closed terminal handoff still blocks new activation

- GIVEN Change A has an authorized merged Archive PR and its coordination Issue is natively closed
- AND that Issue is routed `Lead / finalize-archive`
- AND no valid Lead `LIFECYCLE_COMPLETE` evidence exists for the archive merge
- AND Change B is queued with `Change: unset`
- WHEN workflow-dynamic dispatch reconstructs work
- THEN Change A is selected as terminal-pending workflow work
- AND Change B is not activated

#### Scenario: Oldest queued proposal activates after terminal completion

- GIVEN no open active workflow exists
- AND no closed terminal-pending workflow exists because any prior closed terminal tuple has valid Lead `LIFECYCLE_COMPLETE` evidence
- AND two valid Human-admitted `Lead / propose-change` Issues have `Change: unset`
- WHEN Lead selects pre-activation work
- THEN the earlier `created_at` Issue is selected
- AND lower Issue number breaks an equal-time tie
- AND persisting its Change identity activates that workflow

### Requirement: Dynamic dispatch tolerates overlapping wakes without hidden ownership state

Workflow-dynamic dispatch SHALL remain at-least-once and MUST NOT rely on Scheduled Tasks to provide mutual exclusion.

Overlapping wakes SHALL remain safe through durable reconstruction, idempotency where practical, revision/precondition-aware unsafe mutations, first-valid-write-wins where applicable, and stale-run termination. The workflow MUST NOT add lock, claim, lease, heartbeat, retry counter, hidden sequence, or `status:in-progress` state solely to serialize dispatcher runs.

#### Scenario: Two wakes observe the same active tuple

- GIVEN two wakes reconstruct the same active workflow and routing tuple concurrently
- WHEN both dispatch the same role/action
- THEN neither assumes single-flight execution
- AND each action re-evaluates durable preconditions before unsafe mutation
- AND a run that becomes stale stops rather than overwriting newer durable state

### Requirement: Unexplained durable workflow evidence fails closed to Lead diagnosis

If dispatch finds no active workflow but durable repository evidence indicates an unresolved workflow-related state that cannot be safely classified under the normal lifecycle, it MUST NOT activate queued proposal work merely by ignoring that evidence.

The repository SHALL use bounded Lead diagnosis and, when Human input is required, a decision-ready escalation rather than a repository-wide fault classifier or persistent fault state machine.

#### Scenario: Orphan evidence blocks new activation

- GIVEN no active coordination Issue with a persisted Change is found
- AND durable PR/OpenSpec evidence appears to belong to unresolved workflow work
- WHEN dispatch evaluates whether to activate a queued proposal
- THEN activation fails closed
- AND Lead diagnoses the evidence or escalates a bounded decision to Human
- AND the dispatcher does not invent a global fault status taxonomy

### Requirement: Human-required authority is bound to the repository Human actor

For workflow decisions that governance reserves to Human, only durable GitHub activity attributable to actor `royhsu-work` SHALL satisfy the Human authority condition.

Activity from other actors MAY be used as evidence but MUST NOT satisfy Human-required admission, answers, authorization, or resume conditions.

`human:notified`, when present, SHALL be analytics-only metadata and MUST NOT grant authority, route work, create waiting semantics, or prove that Human answered.

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

### Requirement: Lead Human-facing escalation is bounded and decision-ready

When Lead requires Human input, it SHALL present at most three actionable proposals and SHALL include the material impact, risk/trade-off, and Lead recommendation needed to make the decision.

Lead MUST NOT repeat materially equivalent unanswered notifications while the durable question and available evidence remain unchanged.

#### Scenario: Lead needs a Human decision

- GIVEN Lead cannot legally continue without Human input
- WHEN Lead records the escalation
- THEN it presents no more than three actionable options
- AND states material impact and trade-offs
- AND identifies a recommended option

#### Scenario: Human has not answered

- GIVEN Lead already recorded a decision-ready escalation
- AND no authoritative Human answer or material evidence change exists
- WHEN a later wake reconstructs the same blocked state
- THEN Lead does not post a duplicate unanswered notification

### Requirement: Human-facing scheduled delivery is Lead-only and decision-required

Repository workflow evidence and Human-facing Scheduled Task delivery SHALL be treated as separate channels.

Ordinary Reviewer and Executor workflow results, checkpoints, merge results, and handoffs MUST remain repository-durable evidence only and MUST NOT be marked as Human-facing scheduled delivery. Ordinary Lead action results, merge authorization, resolved clarification, finalize progress, and handoff evidence MUST likewise remain repository-durable only.

Only Lead MAY emit the canonical `HUMAN_DECISION_REQUIRED` workflow message, and Lead SHALL do so only when current approved contract and durable evidence are insufficient for Lead to legally resolve a decision that genuinely requires Human authority or intent. When no such unresolved Lead-owned Human decision exists, the Scheduled Agent wake SHALL be Human-silent even though repository work or durable GitHub evidence may have been produced.

The repository SHALL define Human-delivery eligibility, while actual Scheduled Task notification or associated-conversation surfacing remains external product configuration and MUST NOT become workflow routing, waiting, authorization, or completion state.

#### Scenario: Reviewer records PASS and hands off

- GIVEN Reviewer completes an independent gate with `PASS`
- WHEN Reviewer persists the review evidence and legal handoff
- THEN the `REVIEW_RESULT` and `HANDOFF` remain repository-durable workflow evidence
- AND no Human-facing scheduled delivery is required

#### Scenario: Lead can resolve a workflow problem itself

- GIVEN a finding or workflow problem routes to Lead
- AND Lead can resolve it within current specification/lifecycle authority from durable approved evidence
- WHEN Lead records the resolution and next handoff
- THEN the Lead result remains repository-durable only
- AND no Human-facing scheduled delivery is required

#### Scenario: Lead genuinely requires Human authority

- GIVEN Lead has exhausted its authorized resolution path
- AND workflow progress requires Human authority or intent not derivable from approved contract and durable evidence
- WHEN Lead escalates
- THEN Lead uses `HUMAN_DECISION_REQUIRED`
- AND that message is the only workflow result eligible for Human-facing scheduled delivery

### Requirement: OpenSpec review uses reverse-first inspection while retaining the bidirectional gate

For `Reviewer / review-openspec`, Reviewer MUST inspect reverse traceability first in the order `tasks → design → specs → proposal`, and MUST then inspect forward traceability in the order `proposal → specs → design → tasks`.

The inspection order MUST NOT weaken or replace the correctness gate. A `PASS` still requires both traceability directions to be complete against the same exact revision under review.

#### Scenario: Reviewer performs OpenSpec traceability inspection

- GIVEN Reviewer is executing `review-openspec` for exact revision R
- WHEN Reviewer evaluates proposal/spec/design/task traceability
- THEN Reviewer first verifies `tasks → design → specs → proposal`
- AND then verifies `proposal → specs → design → tasks`
- AND Reviewer may record `PASS` only if both directions are complete for revision R

### Requirement: Recurring workflow messages use canonical shared templates

The repository SHALL define one shared Markdown presentation contract for recurring durable workflow messages and SHALL support the following seven canonical message types: `ACTION_RESULT`, `REVIEW_RESULT`, `SLICE_CHECKPOINT`, `MERGE_AUTHORIZATION`, `MERGE_RESULT`, `HANDOFF`, and `HUMAN_DECISION_REQUIRED`.

The shared template artifact SHALL define a common workflow envelope and the event-specific evidence fields required by each type. Templates MUST define presentation/evidence shape only and MUST NOT redefine routing, authorization, termination, review, merge, lifecycle, or result-enum semantics owned by governance and role/action skills.

Roles and skills SHALL reference the shared template source rather than duplicate full template bodies per role/action. The message contract MUST NOT require a parser-dependent message bus, JSON/YAML runtime schema, template engine, notification state machine, or hidden workflow state.

Free-form RED/GREEN/refactor/test-trigger/compatibility-correction progress, Lead progress polling, and `No Human action is required` status noise MUST NOT become additional supported workflow message types.

When a canonical typed message directly represents a lifecycle-journal boundary, that typed message SHALL satisfy the one required journal record for that boundary and MUST NOT require an additional duplicate generic `LIFECYCLE_JOURNAL` or recursive meta-comment.

#### Scenario: Verified Slice uses the shared checkpoint template

- GIVEN Executor completes a verified implementation Slice
- WHEN the required coordination checkpoint is persisted
- THEN it uses the canonical `SLICE_CHECKPOINT` shape
- AND identifies the Slice/tasks, durable verified/checkpoint evidence, required gates, and remaining work or handoff

#### Scenario: Reviewer gate uses the shared review template

- GIVEN Reviewer records a revision-bound PASS or finding
- WHEN the durable review result is persisted
- THEN it uses `REVIEW_RESULT`
- AND preserves the exact reviewed revision, gate evidence, findings when present, and expected next owner

#### Scenario: Typed transition message is already the lifecycle journal

- GIVEN a PR merge boundary is durably represented by canonical `MERGE_RESULT`
- WHEN lifecycle-journal compliance is evaluated for that same merge boundary
- THEN that typed message is the required bounded journal record
- AND no second generic lifecycle-journal comment is required solely to restate the merge

### Requirement: Verified implementation slices persist a bounded coordination-Issue checkpoint

For `Executor / implement-change`, after an approved vertical slice reaches successful `VERIFY`, Executor MUST persist all satisfied task markers for that slice and MUST persist exactly one bounded checkpoint comment on the persistent coordination Issue before beginning the next slice or handing off.

The checkpoint comment MUST use the canonical `SLICE_CHECKPOINT` presentation contract and MUST identify the completed slice or task IDs, the durable checkpoint or verified revision, the required VERIFY/gate result, and the remaining approved work or handoff target. The comment SHALL summarize the completion boundary and MUST NOT replace the PR/commit, task markers, or CI evidence as their respective sources of truth.

RED/GREEN/refactor/test-trigger/compatibility-correction commits and ordinary governed artifact or task-marker edits inside the same not-yet-complete slice MUST NOT independently require coordination-Issue progress comments. This requirement is completion-boundary observability only and MUST NOT introduce periodic heartbeat, progress percentage, `status:in-progress`, lock, claim, lease, retry counter, hidden ownership state, or other live execution machinery.

#### Scenario: Verified slice completes before another slice begins

- GIVEN Executor completes an approved vertical slice
- AND the slice's required VERIFY and repository gates succeed
- WHEN Executor prepares to continue implementation
- THEN all satisfied task markers for that slice are durably persisted
- AND exactly one canonical `SLICE_CHECKPOINT` is durably recorded on the persistent coordination Issue
- AND the checkpoint identifies the completed work, durable revision, gate result, and remaining work
- AND only then may Executor begin the next approved slice

#### Scenario: Work continues inside an unverified slice

- GIVEN Executor is performing RED, GREEN, refactor, test-trigger, compatibility correction, or ordinary artifact/task edits inside one approved slice
- AND that slice has not yet reached successful VERIFY
- WHEN those intermediate mutations are persisted
- THEN Git/PR/task evidence remains the detailed source of truth
- AND no additional implementation-progress Issue comment is required solely for those mutations

#### Scenario: Task markers persisted but checkpoint write was interrupted

- GIVEN a prior Executor run successfully verified a slice and durably persisted its satisfied task markers
- BUT the run ended before the required coordination-Issue checkpoint was persisted
- WHEN a later Executor run reconstructs the active implementation state
- THEN it does not rerun or clear the already verified slice merely to recreate progress
- AND it persists the missing canonical `SLICE_CHECKPOINT` from current durable evidence before beginning another slice or handing off

### Requirement: Material workflow lifecycle transitions are journaled on the coordination Issue

A Scheduled Agent MUST persist one bounded coordination-Issue journal entry when it completes a material workflow lifecycle transition that changes durable workflow ownership or lifecycle state. Covered boundaries include routing handoff, PR merge, Archive native close/post-merge terminal handoff, Lead `LIFECYCLE_COMPLETE`, and Human escalation/specification-resolution boundaries.

When an approved canonical typed message represents the covered transition, that typed message SHALL be the required journal entry for the boundary: routing ownership transfer uses `HANDOFF`; PR merge uses `MERGE_RESULT`; Lead terminal or other non-review lifecycle result uses `ACTION_RESULT`; and Human escalation uses `HUMAN_DECISION_REQUIRED`. The workflow MUST NOT add a duplicate generic `LIFECYCLE_JOURNAL` message solely to restate a boundary already represented by its canonical typed event.

Related low-level writes that together implement one legal lifecycle transition MAY be represented by the single boundary journal. Ordinary implementation mutations inside an unverified slice are governed by the verified-Slice checkpoint requirement above and MUST NOT become per-commit, per-file, or per-mutation Issue logging. The journal comment itself SHALL NOT recursively require another meta-comment.

If a lifecycle transition succeeds but its required journal write is interrupted, a later eligible run MUST reconstruct the already durable transition and persist the missing bounded canonical journal message before performing a later lifecycle transition or handoff; it MUST NOT replay the completed unsafe mutation merely to recreate journal evidence.

#### Scenario: Routing handoff is durably changed

- GIVEN a Scheduled Agent legally completes an action and changes the coordination Issue routing tuple
- WHEN the routing handoff succeeds
- THEN the Agent records one canonical `HANDOFF` comment describing the completed boundary, resulting durable state/evidence, and next role/action
- AND no recursive meta-comment is required for that journal write

#### Scenario: Intermediate implementation commit is persisted

- GIVEN Executor is inside an approved slice that has not reached successful VERIFY
- WHEN a RED, GREEN, refactor, test-trigger, compatibility-correction, artifact, or task-edit mutation is persisted
- THEN that mutation does not independently require a lifecycle journal comment
- AND the eventual successful Slice VERIFY is journaled exactly once under the verified-Slice checkpoint requirement

#### Scenario: Lifecycle transition succeeds but journal write is interrupted

- GIVEN a Scheduled Agent completed a material lifecycle transition
- BUT the run ended before its required bounded canonical journal message was persisted
- WHEN a later eligible run reconstructs that state
- THEN it preserves the already durable transition
- AND writes only the missing canonical journal record before a later lifecycle transition or handoff

### Requirement: Native Archive close hands off to terminal Lead reconstruction

The final Archive PR SHALL retain the repository-approved GitHub closing linkage to the persistent coordination Issue.

After Executor successfully merges the authorized Archive PR, Executor MUST fresh-read the Archive PR and coordination Issue. If the PR is durably merged and the coordination Issue is observed natively `closed`, Executor MUST replace the consumed routing tuple with exactly `agent:lead + action:finalize-archive` on that closed Issue and MUST record a bounded canonical `HANDOFF` message whose evidence includes the merge/native-close boundary. Executor MUST NOT execute Lead finalization in the same invocation.

A closed coordination Issue with exactly `agent:lead + action:finalize-archive` SHALL be eligible only as the narrow terminal-reconstruction candidate defined by the active-workflow requirement above. Lead `finalize-archive` MUST reconstruct the authorized Archive PR merge, canonical archived default-branch state, and observed native Issue closure. On successful reconstruction Lead MUST record one bounded canonical `ACTION_RESULT` carrying `LIFECYCLE_COMPLETE` bound to the Archive PR exact head and merge commit; the normal native-close path MUST NOT reopen or redundantly close the Issue.

After valid Lead `LIFECYCLE_COMPLETE` evidence exists for the current archive merge, the closed tuple MUST remain terminal history but MUST NOT be selected again and MUST NOT block later workflow admission.

#### Scenario: Archive merge native-closes the Issue

- GIVEN Reviewer archive PASS and Lead merge authorization bind to exact Archive PR revision R
- AND Executor confirms unchanged current head R and all merge preconditions
- WHEN Executor merges the Archive PR and GitHub natively closes the coordination Issue through the approved closing linkage
- THEN Executor fresh-reads and confirms the merged PR and closed Issue
- AND replaces routing with `agent:lead + action:finalize-archive` on the closed Issue
- AND records the canonical `HANDOFF` evidence for the merge/native-close/terminal ownership boundary
- AND ends the invocation without executing Lead work

#### Scenario: Lead completes terminal reconstruction on the closed Issue

- GIVEN the Issue is closed and routed `Lead / finalize-archive`
- AND the matching authorized Archive PR is merged
- AND no valid Lead `LIFECYCLE_COMPLETE` evidence exists yet
- WHEN Lead is dispatched for terminal reconstruction
- THEN Lead verifies canonical archived default-branch state and native closure
- AND records canonical `ACTION_RESULT` with `LIFECYCLE_COMPLETE` evidence bound to the Archive PR exact head and merge commit
- AND does not reopen or redundantly close the Issue
- AND later dispatch excludes that closed tuple from active work

#### Scenario: Merge succeeded but post-merge handoff was interrupted

- GIVEN the authorized Archive PR is already merged and the Issue is natively closed
- AND routing still contains the consumed pre-merge tuple because Executor stopped before terminal handoff
- WHEN a later run reconstructs exact authorized merge and native-close evidence
- THEN it MUST NOT re-merge
- AND MAY repair only the missing `Lead / finalize-archive` terminal routing and canonical `HANDOFF` evidence according to the merge recovery contract

### Requirement: Idle exploration considers recent relevant Issue activity

Lead idle advisory SHALL remain available only when no active workflow requires work and no unresolved advisory already prevents duplicate advisory creation.

When forming bounded idle recommendations, Lead SHALL consider relevant repository Issues created or materially active during the preceding seven days in addition to current default-branch repository state.

#### Scenario: Recent Issue changes recommendation context

- GIVEN workflow execution is idle
- AND a relevant Issue was created or materially active within the preceding seven days
- WHEN Lead forms an idle advisory
- THEN that Issue is considered as current exploration evidence
- AND the advisory remains bounded to at most three recommendations

### Requirement: Workflow governance applies a simplicity and proportionality constraint

Repository workflow design SHALL add complexity only when justified by current approved requirements or demonstrated failure modes. Hypothetical future generality MUST NOT by itself justify a central workflow engine, multi-active arbitration platform, generic fault classifier, message bus/template engine, or hidden runtime ownership state.

#### Scenario: A generalized dispatcher framework is proposed without current need

- GIVEN current workflow requirements are satisfied by the thin workflow-first dispatcher and shared Markdown message contract
- AND no demonstrated failure requires a generalized orchestration or messaging subsystem
- WHEN an implementation or later proposal considers such machinery
- THEN the additional machinery is out of scope
- AND a new approved OpenSpec change with concrete evidence is required before adding it

## MODIFIED Requirements

### Requirement: Actionable workflow routing is one logical role/action tuple

A coordination Issue SHALL be actionable by scheduled roles only when it contains exactly one valid `agent:<role>` label and exactly one valid `action:<action>` label forming a legal routing tuple for that role, and either:

- the Issue is open; or
- the Issue is the one narrow terminal-pending exception: it is closed, has persisted non-`unset` `Change:` identity, is routed exactly `agent:lead + action:finalize-archive`, is backed by the repository-approved authorized merged Archive PR/native close for that Change, and does not yet have valid Lead `LIFECYCLE_COMPLETE` evidence for that archive merge.

Zero, multiple, contradictory, or illegal routing labels MUST fail closed and MUST NOT be resolved by model inference.

Unrelated Issue labels MUST be preserved during routing changes.

#### Scenario: Open coordination Issue has valid routing

- GIVEN an open coordination Issue has exactly one `agent:reviewer` label
- AND exactly one `action:review-openspec` label
- WHEN Reviewer discovers eligible work
- THEN the Issue is eligible for the Reviewer `review-openspec` action

#### Scenario: Closed terminal-pending Issue has the one legal exception

- GIVEN a coordination Issue is closed by the authorized final Archive PR linkage
- AND its persisted routing is exactly `agent:lead + action:finalize-archive`
- AND matching authorized merged-archive/native-close evidence exists
- AND no valid Lead `LIFECYCLE_COMPLETE` evidence exists for that archive merge
- WHEN scheduled work discovery evaluates routing eligibility
- THEN the closed Issue remains eligible only for terminal Lead reconstruction

#### Scenario: Coordination Issue has conflicting role labels

- GIVEN an open coordination Issue has both `agent:lead` and `agent:reviewer`
- WHEN a scheduled role evaluates eligibility
- THEN the routing is invalid
- AND no role proceeds by guessing which role owns the work

### Requirement: Routing handoff persists evidence before ownership transfer

A scheduled role SHALL persist the required action/review result, governed artifact state, and revision-aware evidence before changing the logical routing tuple. The result evidence MAY therefore exist while the source routing tuple is still current and MUST NOT by itself be treated as proof that ownership transferred.

Before the routing mutation, the role SHALL fresh-read current Issue routing. If routing no longer matches the source action being completed, the role MUST NOT overwrite the newer routing and MUST stop as stale/contradictory rather than manufacture a handoff.

If the source tuple still matches and the handoff remains legal, the role SHALL replace the routing tuple with the target owner/action and observe the successful routing mutation. The canonical `HANDOFF` lifecycle-journal evidence SHALL then be persisted after the routing mutation succeeds and SHALL describe the resulting target ownership. A required normal handoff is durably complete only when both the target routing mutation and its canonical `HANDOFF` evidence are durable.

The workflow MUST NOT intentionally expose an intermediate state with two role owners or two action owners during a normal handoff. Routing labels remain canonical workflow ownership; `HANDOFF` is reconstructable evidence of the completed transition rather than a substitute for routing state.

If an actual interruption occurs after result evidence is durable but before routing mutation or `HANDOFF` persistence completes, a later eligible run SHALL preserve the completed result and perform only the missing legal handoff work. If the routing mutation already succeeded but the `HANDOFF` write was interrupted, recovery SHALL preserve the target routing and repair only the missing `HANDOFF` evidence; it MUST NOT replay the completed source action merely to recreate the journal.

#### Scenario: Result is durable before ownership transfer

- GIVEN a role has durably persisted the action/review result and required revision-aware evidence
- AND the coordination Issue still carries the matching source routing tuple
- WHEN the role performs the required handoff
- THEN it fresh-reads the source routing
- AND changes routing to the legal target tuple
- AND observes the successful routing mutation
- AND only then persists canonical `HANDOFF` evidence describing the target ownership

#### Scenario: Another run has already changed routing

- GIVEN a role has completed work and persisted its result/revision evidence
- AND a fresh read shows that another run has already changed the Issue routing tuple
- WHEN the first run reaches its handoff step
- THEN it does not overwrite the newer routing
- AND it does not persist a false `HANDOFF` claiming a transition it did not perform
- AND it stops for later reconstruction under the current durable owner/action

#### Scenario: Routing changed but HANDOFF write was interrupted

- GIVEN a legal handoff already changed routing to the target tuple
- BUT the run ended before canonical `HANDOFF` evidence was persisted
- WHEN a later eligible run reconstructs the durable state
- THEN it preserves the already changed routing
- AND repairs only the missing canonical `HANDOFF` evidence before a later lifecycle transition
- AND it does not replay the completed source action

### Requirement: Each scheduled run processes at most one actionable work item using a fixed stable order

A scheduled invocation SHALL process at most one eligible actionable coordination Issue per run.

In `fixed-role` mode, selection SHALL retain the existing role-local action priority:

- Lead: `resolve-question` > `finalize-archive` > `finalize-change` > `propose-change`;
- Reviewer: `review-archive` > `review-implementation` > `review-openspec`;
- Executor: `merge-pr` > `implement-change`.

Within the same fixed-role role/action priority, selection SHALL choose earliest GitHub `created_at`, then lower Issue number.

In `workflow-dynamic` mode, the single active workflow SHALL be selected before role/action selection; its valid routing tuple determines the role/action. The only closed-Issue exception is a terminal-pending `closed + agent:lead + action:finalize-archive` workflow with matching authorized merged Archive PR/native close and no valid Lead `LIFECYCLE_COMPLETE` evidence. If no active or terminal-pending workflow exists, only valid queued `Lead / propose-change` admission or bounded Lead idle/orphan diagnosis may proceed according to the requirements above.

The model MUST NOT substitute its own urgency or preference for either mode's deterministic selection rules.

#### Scenario: Fixed-role mode retains role-local priority

- GIVEN dispatch mode is `fixed-role`
- AND Lead has one eligible `propose-change` Issue and one eligible `resolve-question` Issue
- WHEN Lead selects work for the run
- THEN Lead selects `resolve-question`
- AND processes at most that one Issue

#### Scenario: Dynamic mode follows the active workflow

- GIVEN dispatch mode is `workflow-dynamic`
- AND exactly one active workflow routes to `Executor / implement-change`
- AND a queued `Lead / propose-change` Issue also exists
- WHEN a Scheduled Task selects work
- THEN the active workflow is selected
- AND Executor is the fixed invocation role
- AND the queued proposal remains pre-activation

#### Scenario: Dynamic mode selects terminal reconstruction before queued work

- GIVEN dispatch mode is `workflow-dynamic`
- AND a closed coordination Issue is terminal-pending under `Lead / finalize-archive`
- AND a queued `Lead / propose-change` Issue exists
- WHEN a Scheduled Task selects work
- THEN the closed terminal-pending workflow is selected
- AND Lead is the fixed invocation role
- AND the queued proposal remains pre-activation

### Requirement: Workflow admission is explicitly Human-controlled

Scheduled agents MUST NOT autonomously admit arbitrary Issues, PRs, repository activity, discussions, or discovered requirements into workflow work.

An initial coordination Issue is Human-admitted only through explicit routing established by actor `royhsu-work`; other actors cannot satisfy this Human-required admission condition.

A Human-admitted `Lead / propose-change` Issue MAY remain queued with `Change: unset`; in workflow-dynamic mode it becomes active only when no other active or terminal-pending workflow exists and Lead durably persists its immutable Change identity.

Lead idle advisory admission additionally requires both an unambiguous selected direction from actor `royhsu-work` and the reserved Human capability marker `intake:approved` applied by that Human actor.

Scheduled Lead, Reviewer, and Executor MUST NEVER add, remove, restore, or otherwise manufacture `intake:approved`; they MAY only consume valid Human-authored evidence.

#### Scenario: Human directly admits a queued proposal

- GIVEN actor `royhsu-work` creates or explicitly routes a coordination Issue to `Lead / propose-change`
- AND `Change:` is unset
- WHEN scheduled workflow reconstructs admission
- THEN the Issue is valid queued pre-activation work
- AND it does not become active while another persisted Change or terminal-pending workflow exists

#### Scenario: Non-Human routing is insufficient

- GIVEN an actor other than `royhsu-work` applies apparently valid initial routing
- WHEN scheduled workflow evaluates Human admission
- THEN that routing does not satisfy Human-required admission
- AND scheduled roles fail closed rather than treating it as authorized workflow entry

### Requirement: Lead idle advisory mode is bounded and non-routing

Lead SHALL keep idle advisory mode bounded and non-routing.

When no active or terminal-pending workflow requires work, no queued Human-admitted proposal is eligible for activation, and no unresolved orphan evidence requires diagnosis, Lead MAY create an idle advisory Issue containing at most three current recommendations only if no other open `advisory:idle` Issue exists.

An advisory Issue MUST NOT contain `agent:*` or `action:*` routing labels and is not itself a coordination workflow instance.

If an open advisory remains without valid Human admission, later Lead runs SHALL no-op rather than create duplicate advisory noise. Recommendation formation SHALL consider relevant Issues created or materially active during the preceding seven days.

#### Scenario: Existing idle advisory has no Human decision

- GIVEN one open `advisory:idle` Issue exists
- AND no valid Human admission has occurred
- WHEN Lead runs while workflow is otherwise idle
- THEN Lead does not create another advisory Issue
- AND does not repeat the same recommendations as new workflow noise

### Requirement: Repository agent artifacts expose the governance contract

Implementation SHALL provide:

- `agents/AGENTS.md` for shared execution protocol, the single authoritative `Scheduled-Dispatch-Mode` marker, the shared work-conserving selected-action termination/yield contract, and the shared result-vs-handoff completion rule;
- role definitions for Lead, Reviewer, and Executor under `agents/roles/`;
- a reduced reusable set of procedural skills under `agents/skills/` covering the nine action contracts without one skill per trivial action and without duplicating or weakening shared termination/handoff semantics;
- one shared `agents/templates/messages.md` Markdown presentation contract containing the common envelope and the seven canonical workflow message types without per-role/per-action template copies or a template/message runtime engine;
- repository documentation describing fixed-role compatibility, workflow-dynamic dispatch, the single-active activation boundary, shared work-conserving invocation semantics, canonical workflow messages, result-vs-handoff completion, verified-slice coordination checkpoints, lifecycle-transition journaling, Lead-only decision-required Human delivery eligibility, native-close terminal handoff/reconstruction, and the relationship to existing OpenSpec/archive automation.

Scheduled Task prompts SHALL remain bootstrap-only: they may require loading default-branch governance and selecting dispatch mode, but MUST NOT duplicate repository execution, concurrency, handoff, stale-state, Human-escalation, termination/yield, canonical message bodies, checkpoint-journal, lifecycle-journal, terminal-reconstruction, or idle semantics.

Associated Scheduled Task conversation/result surfacing SHALL be treated as an external product boundary and MUST NOT become repository workflow state. The external migration configuration SHALL treat ordinary workflow outcomes as Human-silent and SHALL reserve Human-facing workflow delivery eligibility for Lead `HUMAN_DECISION_REQUIRED` only, subject to actual product delivery capabilities.

#### Scenario: Dynamic Scheduled Task bootstraps from repository governance

- GIVEN a Scheduled Task wakes
- WHEN it loads default-branch shared governance
- THEN it determines dispatch mode from `Scheduled-Dispatch-Mode`
- AND in `workflow-dynamic` mode reconstructs the active or terminal-pending workflow to derive role/action and mapped skill
- AND repository governance/templates remain sufficient without embedding a duplicate workflow or message protocol in the Scheduled Task prompt
