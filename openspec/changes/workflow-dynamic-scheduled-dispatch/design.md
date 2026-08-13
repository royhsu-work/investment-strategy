# Design: Workflow-dynamic scheduled dispatch

## Context

The repository already has durable coordination Issues, one legal routing tuple, role/action skills, revision-bound evidence, and at-least-once reconstruction. The missing piece is dispatch: external Scheduled Tasks currently wake a fixed role and then perform role-local discovery. #23 accepted a workflow-first mode where the repository's active workflow selects the role while preserving the same lifecycle.

Implementation history also exposed coordination observability gaps. #21 consistently mirrored verified Executor slices into the persistent coordination Issue, while #25 demonstrated that task markers and PR commits alone can leave the coordination Issue looking unchanged even though implementation progressed. #21 also showed that native Archive PR closing can close the Issue while routing still says `Executor / merge-pr`, making the documented `Lead / finalize-archive` terminal reconstruction unreachable under an open-Issue-only dispatcher.

During #25 implementation, another gap became concrete: the generic governance did not distinguish crash/recovery wording from a healthy invocation's voluntary termination. `Executor / implement-change` could legally retain routing and defer clear failed-VERIFY corrections or remaining approved work to a later wake even though the selected action still had immediately actionable work. The same ambiguity could affect Lead authoring/finalization actions if fixed independently in each skill.

The analysis of that defect also exposed a Lead-role behavior gap. Lead initially treated the Executor stop as a local implementation-workflow issue and only broadened the analysis to sibling actions after Human explicitly asked whether the same defect existed elsewhere. A Lead responsible for specification/lifecycle coherence needs a bounded systemic view: when evidence plausibly points to a shared contract problem, Lead should proactively test the directly related blast radius before choosing a local abstraction.

The coordination history across #18, #21, and #25 also shows the same workflow events being reported in several incompatible free-form shapes. #18 commonly used explicit Role/Action/Change/Revision/Result/Next headers, #21 converged on checkpoint/READY/PASS/MERGE/BLOCKED event families, and #25 added Slice and lifecycle journals but still emitted ad-hoc single-line checkpoints. Most importantly, #25 reached `Executor / implement-change` READY while the routing labels still remained on Executor, demonstrating that a durable action result and a completed ownership handoff are distinct boundaries that must not be conflated by message prose.

## Goals

- Make dispatch mode explicit and default-branch governed.
- Reuse existing routing and skills rather than build a scheduler/orchestrator subsystem.
- Enforce one active persisted Change while allowing queued Human-admitted proposals.
- Keep overlapping wakes safe without hidden ownership state.
- Make the selected action work-conserving under one shared termination/yield contract rather than duplicating generic continuation semantics across role/action skills.
- Give Lead a bounded systemic-coherence responsibility for cross-cutting workflow/specification defects without turning Lead into a supervisor or central orchestrator.
- Make Human authority and escalation reconstructable from durable GitHub evidence.
- Keep Scheduled Task prompts thin and product-independent.
- Make `review-openspec` inspection order deterministic without changing its bidirectional correctness gate.
- Make each verified Executor slice reconstructable from the persistent coordination Issue as well as PR/task evidence, with one completion-boundary checkpoint rather than per-mutation logging.
- Standardize recurring durable workflow messages through one shared canonical Markdown template source without creating a message-processing subsystem.
- Keep action/review result evidence distinct from completed routing handoff, with crash-safe recovery of a missing handoff only.
- Make ordinary Scheduled Agent runs Human-silent; only an unresolved Lead-owned Human decision is delivery-eligible.
- Make material workflow lifecycle ownership/state transitions reconstructable from bounded coordination journals.
- Preserve native Archive PR closing while keeping `Lead / finalize-archive` reachable as the terminal owner and preserving meaningful terminal routing history.

## Non-goals

- Continuous Lead supervision, progress polling, or intervention into another role's valid routed action.
- Unrelated repository-wide audits or speculative generalized frameworks under the banner of systemic coherence.
- Per-action copies of the generic work-conserving/termination contract.
- Per-role/per-action copies of shared message template bodies.
- Per-commit, per-file, or per-mutation Issue logging inside an implementation slice.
- A template engine, JSON/YAML runtime message schema, parser-dependent message bus, notification state machine, or generic messaging framework.
- Normalizing free-form RED/GREEN/test-trigger/compatibility-correction progress, Lead progress polling, or `No Human action is required` noise into supported workflow message types.
- Multi-active workflow arbitration or dependency/conflict graphing.
- Global cross-role/action priority scoring.
- Locks, claims, leases, heartbeat, retry/progress state, or exactly-once execution.
- A generic repository fault classifier or Human wait-state machine.
- New lifecycle actions, completion/status labels, independent Reviewer authority changes, exact-revision PASS changes, merge-authority changes, or replacement of repository-owned archive automation.

## Decision 1: One explicit dispatch marker

`agents/AGENTS.md` owns a single marker: `Scheduled-Dispatch-Mode: fixed-role | workflow-dynamic`. The implementation change will switch the canonical marker to `workflow-dynamic` only when the rest of the contract is implemented and tested. No separate config file is introduced because one enum-valued governance decision does not justify a configuration subsystem.

Trace: proposal dispatch-mode change → spec `Default-branch governance declares the scheduled dispatch mode` → implementation slice 1.

## Decision 2: Thin workflow-first dispatch

A dynamic wake performs only enough bootstrap to load default-branch governance, determine mode, reconstruct active workflow identity/routing, and select one role/action/skill. It then executes that role normally. The invocation role is immutable after selection.

This avoids a second DAG: the dispatcher does not understand proposal/review/implementation semantics beyond the existing legal routing tuple and the narrow terminal reconstruction exception defined below. Handoff persists the next tuple and ends the invocation.

Trace: proposal thin dispatcher → specs `Workflow-dynamic dispatch derives one fixed invocation role` and modified selection requirement → slice 1.

## Decision 3: `Change:` persistence is activation, with one closed terminal-pending exception

The normal single-active invariant is defined over open coordination Issues with a valid routing tuple and persisted non-`unset` Change identity. Human-admitted `Lead / propose-change` Issues may queue with `Change: unset`. When no active workflow exists, oldest `created_at`, then lower Issue number selects the next proposal for Lead to activate.

One narrow exception preserves terminal reconstruction after native Archive PR close: a closed coordination Issue with persisted Change identity, routing exactly `agent:lead + action:finalize-archive`, an authorized merged Archive PR/native close, and no durable Lead `LIFECYCLE_COMPLETE` evidence for that archive merge remains terminal-pending workflow work. It blocks activation of queued proposals until Lead performs the existing `finalize-archive` reconstruction and records completion evidence. After that bounded Lead completion record exists, the closed tuple is terminal history, is not eligible work, and does not block later admission.

Trace: proposal activation boundary + native-close terminal handoff → specs `Persisted Change identity defines the single active workflow boundary`, modified `Actionable workflow routing is one logical role/action tuple`, and `Native Archive close hands off to terminal Lead reconstruction` → slices 2 and 5.

## Decision 4: At-least-once overlap remains the concurrency model

Dynamic wake cadence can cause two invocations to see the same tuple. Scheduled Tasks are not assumed to serialize. Existing reconstruction/idempotency/revision-precondition semantics remain authoritative. Activation and other competing durable writes use first-valid-write-wins behavior where the backing mutation permits it; after any competing write, stale runs re-read and terminate rather than manufacture a second owner.

No lock/lease/claim state is introduced. If future evidence demonstrates these primitives are insufficient, that is a separate OpenSpec change.

Trace: proposal overlap policy → spec `Dynamic dispatch tolerates overlapping wakes without hidden ownership state` → slices 1-2 and regression validation.

## Decision 5: Minimal orphan guard, not fault orchestration

Before activating queued work, dynamic dispatch checks for durable evidence that indicates unresolved workflow work despite no active coordination Issue. The implementation should use the smallest repository-specific evidence set needed to prevent obvious unsafe activation, then route diagnosis to Lead. If classification requires Human judgment, Lead posts one bounded decision-ready escalation.

Trace: proposal orphan handling → spec `Unexplained durable workflow evidence fails closed to Lead diagnosis` → slice 3.

## Decision 6: Human authority is actor-bound

The repository's Human authority is GitHub actor `royhsu-work`. Human-required admission, answers, authorization, and resume decisions must be attributable to that actor. Other actors' comments/reactions/labels may be evidence but cannot cross a Human capability boundary. `human:notified` may be analytics metadata but is never a workflow predicate.

Trace: proposal Human boundary → specs `Human-required authority...` and `Lead Human-facing escalation...` → slice 3.

## Decision 7: Idle advisory adds a seven-day Issue lens

Idle advisory remains Lead-only and bounded. Its research context expands to relevant Issues created or materially active in the preceding seven days. This is an evidence window, not a new queue or routing source.

Trace: proposal idle exploration → spec idle requirements → slice 7.

## Decision 8: Simplicity/proportionality is a governance constraint

Implementation and future workflow changes must justify complexity with current approved requirements or demonstrated failures. Generalized orchestration machinery is explicitly deferred.

Trace: proposal scope boundary → spec proportionality requirement → slice 7 and final review.

## Decision 9: `review-openspec` is reverse-first, while PASS stays bidirectional

Reviewer inspection order is now deterministic: for each exact revision under `review-openspec`, inspect `tasks → design → specs → proposal` first, then inspect `proposal → specs → design → tasks`. PASS still requires both directions to be complete for the same exact revision.

Trace: proposal reverse-first review requirement → spec `OpenSpec review uses reverse-first inspection while retaining the bidirectional gate` → implementation slice 7 and OpenSpec completion gate.

## Decision 10: Verified slices journal exactly one bounded coordination checkpoint

After a vertical implementation slice reaches successful `VERIFY`, Executor must persist the satisfied task markers and exactly one bounded comment on the persistent coordination Issue before beginning another slice or handing off. The comment records completed slice/task IDs, verified/checkpoint revision, required gate result, and remaining work or handoff.

The Issue comment is not a second source of truth for code or task completion. PR commits and task markers remain the detailed implementation evidence. RED/GREEN/refactor/test-trigger/compatibility-correction commits and ordinary artifact/task edits inside the same not-yet-complete slice do not independently require Issue comments. If markers are durable but the Slice checkpoint was interrupted, a later Executor run repairs only the missing checkpoint from durable evidence before continuing.

Trace: proposal verified-slice checkpoint requirement → spec `Verified implementation slices persist a bounded coordination-Issue checkpoint` → implementation slice 4.

## Decision 11: Journal material lifecycle transitions, not every mutation

Coordination-Issue journaling has a separate lifecycle boundary. A Scheduled Agent records one bounded journal entry when it completes a material workflow lifecycle transition that changes durable workflow ownership/state: routing handoff, PR merge, Archive native close/post-merge terminal handoff, Lead `LIFECYCLE_COMPLETE`, or Human escalation/specification-resolution boundary.

Related low-level writes within one legal lifecycle transition are summarized by that one journal entry. Ordinary implementation mutations remain in Git/PR/task evidence and are surfaced to the coordination Issue only by Decision 10 after successful Slice VERIFY. This prevents the Issue from becoming a duplicate commit/activity log while preserving reconstructable ownership transitions.

When a canonical typed message introduced by Decision 15 represents the covered boundary, that typed message is the required lifecycle journal for the boundary. There is no eighth generic `LIFECYCLE_JOURNAL` message and no duplicate meta-comment solely to restate the same transition.

If a lifecycle transition succeeds but its journal write is interrupted, a later eligible run reconstructs the durable transition and repairs only the missing journal before a later lifecycle transition or handoff; it does not replay a completed unsafe mutation.

Trace: proposal lifecycle-transition journal requirement → spec `Material workflow lifecycle transitions are journaled on the coordination Issue` → implementation slices 5 and 9.

## Decision 12: Native Archive close hands off to Lead on the closed Issue

The final Archive PR keeps repository-approved `Closes #N` linkage. Executor still owns only the authorized merge mutation. After merge succeeds, Executor fresh-reads the PR and coordination Issue. When the Archive PR is durably merged and the Issue is observed natively closed, Executor replaces the consumed `Executor / merge-pr` labels with `Lead / finalize-archive` even though the Issue is closed, then records the bounded merge/native-close/handoff lifecycle journal. Invocation role remains Executor and ends after that handoff.

The dispatcher admits exactly one closed-Issue exception: `closed + agent:lead + action:finalize-archive` with a matching authorized merged Archive PR and no durable Lead `LIFECYCLE_COMPLETE` result for that merge. Lead reconstructs canonical archived default-branch state, confirms expected native closure and exact archive evidence, and records one bounded `LIFECYCLE_COMPLETE` result comment. After that result exists, later wakes treat the tuple as completed terminal history.

If merge succeeded and native close happened but Executor was interrupted before relabel/comment, later reconstruction repairs only the missing post-merge terminal handoff/journal after proving exact authorized archive merge and native closure; it must not re-merge.

Trace: proposal native-close terminal handoff → specs modified `Actionable workflow routing is one logical role/action tuple`, `Native Archive close hands off to terminal Lead reconstruction`, and modified work-selection/active-workflow requirements → implementation slice 5.

## Decision 13: Work-conserving selected-action semantics are shared governance

Once dispatch selects a legal role/action, the action continues all immediately actionable work in the same invocation while routing, revision/base preconditions, authority, and execution context remain current. Checkpoints are durable recovery boundaries, not automatic yield points. A recoverable same-role failure or failed-but-actionable validation is also not a voluntary yield point: if correction is inside the selected authority and approved contract, correct it and rerun the relevant gate in the same invocation.

The shared contract enumerates the bounded reasons an invocation may end early: completed handoff/terminal result, another role or Human authority boundary, a genuine external asynchronous wait, ambiguity/contradictory unsafe state, stale/concurrency loss, or actual tool/hard-runtime interruption. This is intentionally not copied into every skill. Skills express only action-specific outcomes and blockers; generic crash-recovery language must not be interpreted as permission for a healthy invocation to stop.

This design keeps termination semantics coherent across `implement-change`, Lead authoring/finalization actions, Reviewer gates, and merge actions without adding an execution state machine. It also keeps the Scheduled Task prompt thin because the external wake only selects and loads governance; it does not restate yield policy.

Trace: proposal shared work-conserving contract → spec `Selected Scheduled Agent actions are work-conserving within an invocation` and repository-artifact requirement → implementation slice 6.

## Decision 14: Systemic coherence is a bounded Lead role responsibility

Lead owns specification meaning and lifecycle authorization, so it also owns checking whether a material defect is actually local before choosing the abstraction level of a fix. When a material finding, Human clarification, workflow failure, or specification defect plausibly indicates a cross-cutting pattern, Lead performs a bounded blast-radius analysis over the directly related sibling actions, role contracts, lifecycle invariants, and governance surfaces. The analysis identifies the root cause, checks whether sibling contracts can fail for the same reason, and selects the narrowest correct ownership layer.

This responsibility is implemented once in `agents/roles/lead.md`. It is not copied into `agents/AGENTS.md` or each Lead skill. It does not grant Lead supervisory authority over Reviewer/Executor, does not justify progress polling or intervention while another role owns valid routing, and does not require unrelated repository-wide audits. Simplicity/proportionality still constrains the scan to the plausible blast radius of the observed evidence.

This is an Engineering/Governance role-artifact responsibility rather than a new generic scheduled-agent capability requirement. Its trace runs proposal role responsibility → this design decision → implementation slice 7 → `agents/roles/lead.md`, under the existing `openspec/config.yaml` allowance for governance tasks.

## Decision 15: Recurring workflow messages use seven canonical Markdown templates

The repository will add one shared presentation artifact at `agents/templates/messages.md`. It defines a common envelope and exactly seven currently supported recurring message types derived from the concrete history in #18, #21, and #25:

- `ACTION_RESULT` for non-review action outcomes and lifecycle results such as OpenSpec readiness, resolution, archive readiness, or terminal completion;
- `REVIEW_RESULT` for `review-openspec`, `review-implementation`, and `review-archive` PASS/FINDINGS results;
- `SLICE_CHECKPOINT` for the verified Executor Slice completion boundary;
- `MERGE_AUTHORIZATION` for Lead exact-revision merge authorization;
- `MERGE_RESULT` for Executor merge success or merge blocker results;
- `HANDOFF` for a completed routing ownership transfer after the routing mutation succeeds; and
- `HUMAN_DECISION_REQUIRED` for the bounded Lead-only Human escalation.

The templates define presentation and required evidence fields, not workflow meaning. The common envelope carries the durable workflow identity/context that is broadly useful (`Workflow`, `Change`, `Action`, `Result`, and an exact revision when applicable); individual message types then require only the fields justified by that event. `SLICE_CHECKPOINT` carries Slice/task IDs, verified and marker/checkpoint revisions where distinct, required gate evidence, remaining work, and current/expected routing. Review, merge, authorization, handoff, and Human-decision templates carry their corresponding revision/evidence fields.

Roles/skills choose when an event is legal under the capability/governance contract and reference this one template source. They do not copy the full template body into every skill. The artifact is Markdown for Human/agent readability; no parser, message bus, code-generation layer, JSON/YAML runtime schema, or hidden workflow state is introduced.

Free-form Lead progress polling, RED/GREEN/test-trigger/compatibility-correction progress, and `No Human action is required` status messages are intentionally not template types. They are noise or intermediate activity rather than durable workflow boundaries.

Trace: proposal canonical message contract → spec `Recurring workflow messages use canonical shared templates` → implementation slice 9.

## Decision 16: Result evidence and routing handoff are separate durable boundaries

A legal action/review result may need to be persisted before ownership changes so the next owner can reconstruct the gate that authorizes the handoff. Therefore an `ACTION_RESULT` or `REVIEW_RESULT` can be valid durable evidence while the source routing tuple is still current. It does not, by itself, prove the handoff happened.

When the action's legal outcome requires a new owner, normal completion is:

```text
persist result + revision-aware evidence
→ fresh-read source routing
→ mutate routing to the target tuple
→ observe successful routing mutation
→ persist HANDOFF
→ end the current invocation
```

This makes the #25 failure mode explicit: `Executor / implement-change` may have a durable `READY` result for revision R, but if labels still say `Executor / implement-change`, ownership has not transferred to Reviewer. Under at-least-once recovery, a later eligible Executor reconstructs the already-complete result and performs only the missing routing mutation/HANDOFF; it does not repeat completed Slices or fabricate another READY result.

`HANDOFF` is the lifecycle-journal message for the routing boundary. It records From/To, the triggering result/revision evidence, fresh-read source routing, successful routing mutation, and observed target routing. The canonical routing tuple remains workflow state; the message is reconstructable evidence only.

The pre-change canonical requirement identity `Routing handoff persists evidence before ownership transfer` is retained as a `MODIFIED` requirement, but its ordering is now precise: action/review result and revision-aware evidence remain durable before ownership transfer, while canonical `HANDOFF` journal evidence is written only after the routing mutation succeeds and target ownership is observed. The separate added handoff-ordering requirement is removed so the canonical requirement remains the single normative source for this transition ordering.

Trace: proposal result-vs-handoff contract → modified spec `Routing handoff persists evidence before ownership transfer` plus lifecycle-journal requirement → implementation slice 9.

## Decision 17: Human-facing scheduled delivery is Lead-only and decision-required

Repository workflow evidence and Human delivery are separate channels. Reviewer and Executor continue to write the GitHub evidence needed by later agents, but their ordinary `REVIEW_RESULT`, `SLICE_CHECKPOINT`, `MERGE_RESULT`, and `HANDOFF` messages are not Human-facing Scheduled Task delivery. Ordinary Lead `ACTION_RESULT`, `MERGE_AUTHORIZATION`, handoff, finalize progress, and successful self-resolved clarification are also repository-durable only.

Only Lead may emit `HUMAN_DECISION_REQUIRED`, and only after Lead has reconstructed current durable evidence, applied its own specification/lifecycle authority and bounded systemic-coherence responsibility, and established that workflow progress genuinely requires Human authority or intent that Lead cannot legally resolve. That message uses the existing bounded escalation shape: no more than three options, material impact/risk/trade-off, Lead recommendation, and an explicit requested Human response.

If that condition is absent, the Scheduled Agent wake is Human-silent even though repository work and durable GitHub evidence may have been produced. This is the same product pattern as a scheduled market task that runs but emits no user decision card when its delivery condition is false.

The repository defines delivery eligibility; the external Scheduled Task product configuration owns actual notification/associated-conversation surfacing. The three retained wake slots should be configured so ordinary workflow outcomes do not notify Human, while a genuine Lead `HUMAN_DECISION_REQUIRED` result is the only workflow result eligible for Human delivery. Product UI behavior is not a repository routing, waiting, or authorization predicate.

Trace: proposal Human-delivery boundary → specs `Human-facing scheduled delivery is Lead-only and decision-required`, repository-artifact requirement, and Scheduled Task migration → implementation slice 9 plus external migration configuration.

## Scheduled Task migration

The three existing external wake slots remain. Their prompts should converge on the same bootstrap contract: read `README.md` and `agents/AGENTS.md`, determine the declared mode, use the legacy assigned role only in `fixed-role`, and in `workflow-dynamic` derive role/action from durable workflow state. Once an invocation selects a role, it never switches role in that run.

Prompt configuration itself is external product state. Repository tests/docs can define the required bootstrap and Human-delivery eligibility contract but cannot make Scheduled Task conversation/result surfacing part of GitHub workflow state. The prompt also does not duplicate the shared work-conserving termination/yield semantics or canonical message bodies; those remain repository governance/templates loaded after bootstrap.

The retained external wake configuration must treat ordinary workflow execution as silent. Reviewer/Executor results and ordinary Lead results are still persisted to GitHub for reconstruction, but only a Lead-owned unresolved `HUMAN_DECISION_REQUIRED` condition is eligible to surface to Human. If product UI still exposes associated task-conversation history, that surfacing remains external history rather than workflow state and does not change the repository delivery-eligibility contract.

## Validation strategy

Behavioral tests should exercise mode parsing, fixed-role compatibility, active-workflow selection, queued proposal activation ordering, invalid/multiple active fail-closed behavior, immutable invocation role, work-conserving continuation after recoverable same-role or failed-but-actionable validation, legal external-wait/stale/handoff termination, absence of duplicated weaker per-skill yield wording, stale competing activation, actor-bound Human evidence, duplicate escalation suppression, seven-day advisory evidence, analytics-only notification metadata, reverse-first `review-openspec` inspection with unchanged exact-revision bidirectional PASS semantics, Lead-role systemic-coherence contract wording and its non-supervisory/bounded scope, verified-Slice checkpoint persistence/recovery with no per-mutation implementation logging, lifecycle-transition journal recovery, native Archive close followed by closed-Issue `Lead / finalize-archive` handoff, terminal candidate selection before Lead completion evidence, and terminal exclusion after bounded `LIFECYCLE_COMPLETE` evidence.

Message-contract tests should additionally prove one shared `agents/templates/messages.md` source contains the seven approved types and common envelope without per-role copies; each recurring event references the applicable type; `SLICE_CHECKPOINT` preserves the verified-Slice required fields; canonical typed lifecycle-boundary messages satisfy the journal boundary without a duplicate generic meta-journal; the modified canonical handoff requirement keeps result/revision evidence before transfer while requiring `HANDOFF` after successful routing mutation; a persisted READY/PASS result with unchanged source routing is not treated as completed handoff; interrupted result-before-handoff recovery performs only the missing routing transition and `HANDOFF`; Reviewer/Executor and ordinary Lead results are not Human-delivery eligible; and only Lead `HUMAN_DECISION_REQUIRED` carries the bounded decision-ready Human shape. Repository quality checks and strict OpenSpec validation remain required.
