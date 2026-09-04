# Design: Workflow-dynamic scheduled dispatch

## Context

The repository already has durable coordination Issues, one legal routing tuple, role/action skills, revision-bound evidence, and at-least-once reconstruction. The missing piece is dispatch: external Scheduled Tasks currently wake a fixed role and then perform role-local discovery. #23 accepted a workflow-first mode where the repository's active workflow selects the role while preserving the same lifecycle.

Implementation history also exposed coordination observability gaps. #21 consistently mirrored verified Executor slices into the persistent coordination Issue, while #25 demonstrated that task markers and PR commits alone can leave the coordination Issue looking unchanged even though implementation progressed. #21 also showed that native Archive PR closing can close the Issue while routing still says `Executor / merge-pr`, making the documented `Lead / finalize-archive` terminal reconstruction unreachable under an open-Issue-only dispatcher.

During #25 implementation, another gap became concrete: the generic governance did not distinguish crash/recovery wording from a healthy invocation's voluntary termination. `Executor / implement-change` could legally retain routing and defer clear failed-VERIFY corrections or remaining approved work to a later wake even though the selected action still had immediately actionable work. The same ambiguity could affect Lead authoring/finalization actions if fixed independently in each skill.

The analysis of that defect also exposed a Lead-role behavior gap. Lead initially treated the Executor stop as a local implementation-workflow issue and only broadened the analysis to sibling actions after Human explicitly asked whether the same defect existed elsewhere. A Lead responsible for specification/lifecycle coherence needs a bounded systemic view: when evidence plausibly points to a shared contract problem, Lead should proactively test the directly related blast radius before choosing a local abstraction.

The coordination history across #18, #21, and #25 also shows the same workflow events being reported in several incompatible free-form shapes. #18 commonly used explicit Role/Action/Change/Revision/Result/Next headers, #21 converged on checkpoint/READY/PASS/MERGE/BLOCKED event families, and #25 added Slice and lifecycle journals but still emitted ad-hoc single-line checkpoints. Most importantly, #25 reached `Executor / implement-change` READY while the routing labels still remained on Executor, demonstrating that a durable action result and a completed ownership handoff are distinct boundaries that must not be conflated by message prose.

A later Executor wake then exposed a generic execution-finalization gap. The selected action had approved Section 9 work and the external GitHub file mutation returned a catchable safety/policy denial. The Scheduled Task could surface a prose summary externally, but the repository retained only the prior Reviewer handoff: no raw exception evidence, no durable disposition, and no defined path for later Lead diagnosis. Because the same failure shape can occur while Lead, Reviewer, or Executor is calling a tool, the correction belongs in shared execution governance rather than the implementation skill alone.

The latest #25 review sequence exposed a more general context-continuity gap. #23 had already accepted work-conserving multi-slice Executor behavior, and #25 carried direct references to the authoritative #23 Lead consolidation and Reviewer PASS, yet the first #25 OpenSpec revision omitted that normative requirement. Later in #25, `ea8aaa6...` added material exception/finalization semantics and was handed to Reviewer but never independently reviewed before `a225dbf...` added a second material clarification. Treating only the latest handoff or latest delta as the next review scope would therefore erase still-unreviewed obligations. Cross-Issue provenance and intra-workflow unresolved evidence need the same reconstructive rule.

After Section 12 implementation completed, #25 exposed an over-correction in that review-continuity design. `OpenSpec Validate` correctly ran again for the final PR head because `tasks.md` completion markers changed under `openspec/**`; the workflow then treated that newer exact SHA as if it automatically made the already accepted semantic OpenSpec meaning stale. That produced an unnecessary `implementation complete → review-openspec → review-implementation` sequence even though only task-completion bookkeeping had advanced. The design therefore must distinguish an exact-revision mechanical validation target from a semantic OpenSpec review target and applicability boundary.

The same run exposed a second bootstrap problem. The feature branch already contained `agents/templates/messages.md` and role/skill references to canonical messages, but the Reviewer invocation correctly derives execution authority from the default branch, where those rules are not merged yet. The resulting free-form Reviewer response is not evidence that feature-branch governance should self-authorize its own review; it is evidence that the template activation boundary must be explicit and tested.

## Goals

- Make dispatch mode explicit and default-branch governed.
- Reuse existing routing and skills rather than build a scheduler/orchestrator subsystem.
- Enforce one active persisted Change while allowing queued Human-admitted proposals.
- Keep overlapping wakes safe without hidden ownership state.
- Make the selected action work-conserving under one shared termination/yield contract rather than duplicating generic continuation semantics across role/action skills.
- Preserve authoritative durable context across comments, revisions, handoffs, and Issue/workflow boundaries until an explicit approved consumption event removes it from current obligations.
- Make cross-Issue authoritative source decisions/gates reconstructable by dereferencing declared provenance rather than trusting copied summaries as replacement authority.
- Make Reviewer cumulative coverage gate-specific: semantic OpenSpec coverage follows material semantic change, while implementation/archive review remain exact-current-head gates.
- Keep exact-revision mechanical OpenSpec validation separate from semantic `review-openspec` applicability so task-marker/checkpoint bookkeeping does not create a redundant semantic gate.
- Make catchable tool/runtime/execution exceptions reconstructable by preserving the platform-observable raw error before interpretation or disposition.
- Make normal invocation exit converge to a reconstructable durable outcome, with local recovery continuing in the same action and non-local recovery completing the required legal result/handoff.
- Give Lead a bounded systemic-coherence responsibility for cross-cutting workflow/specification defects without turning Lead into a supervisor or central orchestrator.
- Make Human authority and escalation reconstructable from durable GitHub evidence.
- Keep Scheduled Task prompts thin and product-independent.
- Make `review-openspec` inspection order deterministic without changing its bidirectional correctness gate.
- Make each verified Executor slice reconstructable from the persistent coordination Issue as well as PR/task evidence, with one completion-boundary checkpoint rather than per-mutation logging.
- Standardize recurring durable workflow messages through one shared canonical Markdown template source without creating a message-processing subsystem, and make that presentation contract authoritative only after it is merged to the default branch.
- Keep action/review result evidence distinct from completed routing handoff, with crash-safe recovery of a missing handoff only.
- Make ordinary Scheduled Agent runs Human-silent; only an unresolved Lead-owned Human decision is delivery-eligible.
- Make material workflow lifecycle ownership/state transitions reconstructable from bounded coordination journals.
- Preserve native Archive PR closing while keeping `Lead / finalize-archive` reachable as the terminal owner and preserving meaningful terminal routing history.

## Non-goals

- Continuous Lead supervision, progress polling, or intervention into another role's valid routed action.
- Unrelated repository-wide audits or speculative generalized frameworks under the banner of systemic coherence.
- Per-action copies of the generic work-conserving, authoritative-context, exception-capture, or invocation-finalization contracts.
- A generic event-sourcing engine, message queue, hidden context cache, sequence label, pending-review state machine, persistent consumption tracker, semantic-revision classifier service, or hidden review-applicability marker.
- Per-role/per-action copies of shared message template bodies.
- Per-commit, per-file, or per-mutation Issue logging inside an implementation slice.
- A template engine, template-version negotiation/state machine, JSON/YAML runtime message schema, parser-dependent message bus, notification state machine, or generic messaging framework.
- A generic exception/fault classifier, retry engine, automatic remediation platform, or persistent failure-state machine.
- Normalizing free-form RED/GREEN/test-trigger/compatibility-correction progress, Lead progress polling, or `No Human action is required` noise into supported workflow message types.
- Multi-active workflow arbitration or dependency/conflict graphing.
- Global cross-role/action priority scoring.
- Locks, claims, leases, heartbeat, retry/progress state, or exactly-once execution.
- A generic repository fault classifier or Human wait-state machine.
- New lifecycle actions, completion/status labels, independent Reviewer authority changes, implementation/archive exact-current-head PASS changes, merge-authority changes, or replacement of repository-owned archive automation.

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

Reviewer inspection order is deterministic for each material semantic OpenSpec target: inspect `tasks → design → specs → proposal` first, then inspect `proposal → specs → design → tasks`. PASS still requires both directions to be complete for the same exact semantic target revision. Decision 21 defines when a later repository SHA actually creates a new semantic target.

Trace: proposal reverse-first review requirement → spec `OpenSpec review uses reverse-first inspection while retaining the bidirectional gate` → implementation slice 7 and semantic-review corrections in slice 13.

## Decision 10: Verified slices journal exactly one bounded coordination checkpoint

After a vertical implementation slice reaches successful `VERIFY`, Executor must persist the satisfied task markers and exactly one bounded comment on the persistent coordination Issue before beginning another slice or handing off. The comment records completed slice/task IDs, verified/checkpoint revision, required gate result, and remaining work or handoff.

The Issue comment is not a second source of truth for code or task completion. PR commits and task markers remain the detailed implementation evidence. RED/GREEN/refactor/test-trigger/compatibility-correction commits and ordinary artifact/task edits inside the same not-yet-complete slice do not independently require Issue comments. If markers are durable but the Slice checkpoint was interrupted, a later Executor run repairs only the missing checkpoint from durable evidence before continuing.

Trace: proposal verified-slice checkpoint requirement → spec `Verified implementation slices persist a bounded coordination-Issue checkpoint` → implementation slice 4.

## Decision 11: Journal material lifecycle transitions, not every mutation

Coordination-Issue journaling has a separate lifecycle boundary. A Scheduled Agent records one bounded journal entry when it completes a material workflow lifecycle transition that changes durable workflow ownership/state: routing handoff, PR merge, Archive native close/post-merge terminal handoff, Lead `LIFECYCLE_COMPLETE`, or Human escalation/specification-resolution boundary.

Related low-level writes within one legal lifecycle transition are summarized by that one journal entry. Ordinary implementation mutations remain in Git/PR/task evidence and are surfaced to the coordination Issue only by Decision 10 after successful Slice VERIFY. This prevents the Issue from becoming a duplicate commit/activity log while preserving reconstructable ownership transitions.

When the canonical typed-message contract introduced by Decision 15 is active under Decision 22 and a typed message represents the covered boundary, that typed message is the required lifecycle journal for the boundary. There is no additional generic `LIFECYCLE_JOURNAL` message and no duplicate meta-comment solely to restate the same transition.

If a lifecycle transition succeeds but its journal write is interrupted, a later eligible run reconstructs the durable transition and repairs only the missing journal before a later lifecycle transition or handoff; it does not replay a completed unsafe mutation.

Trace: proposal lifecycle-transition journal requirement → spec `Material workflow lifecycle transitions are journaled on the coordination Issue` → implementation slices 5, 9, and activation correction slice 13.

## Decision 12: Native Archive close hands off to Lead on the closed Issue

The final Archive PR keeps repository-approved `Closes #N` linkage. Executor still owns only the authorized merge mutation. After merge succeeds, Executor fresh-reads the PR and coordination Issue. When the Archive PR is durably merged and the Issue is observed natively closed, Executor replaces the consumed `Executor / merge-pr` labels with `Lead / finalize-archive` even though the Issue is closed, then records the bounded merge/native-close/handoff lifecycle journal. Invocation role remains Executor and ends after that handoff.

The dispatcher admits exactly one closed-Issue exception: `closed + agent:lead + action:finalize-archive` with a matching authorized merged Archive PR and no durable Lead `LIFECYCLE_COMPLETE` result for that merge. Lead reconstructs canonical archived default-branch state, confirms expected native closure and exact archive evidence, and records one bounded `LIFECYCLE_COMPLETE` result comment. After that result exists, later wakes treat the tuple as completed terminal history.

If merge succeeded and native close happened but Executor was interrupted before relabel/comment, later reconstruction repairs only the missing post-merge terminal handoff/journal after proving exact authorized archive merge and native closure; it must not re-merge.

Trace: proposal native-close terminal handoff → specs modified `Actionable workflow routing is one logical role/action tuple`, `Native Archive close hands off to terminal Lead reconstruction`, and modified work-selection/active-workflow requirements → implementation slice 5.

## Decision 13: Work-conserving selected-action semantics are shared governance

Once dispatch selects a legal role/action, the action continues all immediately actionable work in the same invocation while routing, revision/base preconditions, authority, and execution context remain current. Checkpoints are durable recovery boundaries, not automatic yield points. A recoverable same-role failure or failed-but-actionable validation is also not a voluntary yield point: if correction is inside the selected authority and approved contract, correct it and rerun the relevant gate in the same invocation.

The shared contract enumerates the bounded reasons an invocation may end early: completed handoff/terminal result, another role or Human authority boundary, a genuine external asynchronous wait, ambiguity/contradictory unsafe state, stale/concurrency loss, or actual tool/hard-runtime interruption. A catchable execution failure does not bypass Decisions 18-19: if the invocation still has execution opportunity, it captures the raw failure, attempts legal local recovery when available, and otherwise finalizes a durable disposition before normal exit. Only a genuinely uncatchable hard termination may prevent current-run finalization.

This design keeps termination semantics coherent across `implement-change`, Lead authoring/finalization actions, Reviewer gates, and merge actions without adding an execution state machine. It also keeps the Scheduled Task prompt thin because the external wake only selects and loads governance; it does not restate yield policy.

Trace: proposal shared work-conserving contract → spec `Selected Scheduled Agent actions are work-conserving within an invocation` and repository-artifact requirement → implementation slice 6.

## Decision 14: Systemic coherence is a bounded Lead role responsibility

Lead owns specification meaning and lifecycle authorization, so it also owns checking whether a material defect is actually local before choosing the abstraction level of a fix. When a material finding, Human clarification, workflow failure, or specification defect plausibly indicates a cross-cutting pattern, Lead performs a bounded blast-radius analysis over the directly related sibling actions, role contracts, lifecycle invariants, and governance surfaces. The analysis identifies the root cause, checks whether sibling contracts can fail for the same reason, and selects the narrowest correct ownership layer.

This responsibility is implemented once in `agents/roles/lead.md`. It is not copied into `agents/AGENTS.md` or each Lead skill. It does not grant Lead supervisory authority over Reviewer/Executor, does not justify progress polling or intervention while another role owns valid routing, and does not require unrelated repository-wide audits. Simplicity/proportionality still constrains the scan to the plausible blast radius of the observed evidence.

This is an Engineering/Governance role-artifact responsibility rather than a new generic scheduled-agent capability requirement. Its trace runs proposal role responsibility → this design decision → implementation slice 7 → `agents/roles/lead.md`, under the existing `openspec/config.yaml` allowance for governance tasks.

## Decision 15: Recurring workflow messages use eight canonical Markdown templates

The repository will add one shared presentation artifact at `agents/templates/messages.md`. It defines a common envelope and exactly eight currently supported recurring message types derived from the concrete history in #18, #21, and #25 plus the newly demonstrated catchable execution-failure evidence:

- `ACTION_RESULT` for non-review action outcomes and lifecycle results such as OpenSpec readiness, resolution, archive readiness, or terminal completion;
- `REVIEW_RESULT` for `review-openspec`, `review-implementation`, and `review-archive` PASS/FINDINGS results;
- `SLICE_CHECKPOINT` for the verified Executor Slice completion boundary;
- `MERGE_AUTHORIZATION` for Lead exact-revision merge authorization;
- `MERGE_RESULT` for Executor merge success or merge blocker results;
- `HANDOFF` for a completed routing ownership transfer after the routing mutation succeeds;
- `HUMAN_DECISION_REQUIRED` for the bounded Lead-only Human escalation; and
- `EXECUTION_EXCEPTION` for a catchable tool/runtime/execution failure, preserving the raw platform-observable error before separate interpretation/disposition.

The templates define presentation and required evidence fields, not workflow meaning. The common envelope carries the durable workflow identity/context that is broadly useful (`Workflow`, `Change`, `Action`, `Result`, and an exact revision when applicable); individual message types then require only the fields justified by that event. `SLICE_CHECKPOINT` carries Slice/task IDs, verified and marker/checkpoint revisions where distinct, required gate evidence, remaining work, and current/expected routing. `EXECUTION_EXCEPTION` carries the selected role/action, attempted operation/tool, relevant revision, whether any durable mutation completed before failure, unfinished work boundary, raw observable error text, and separate classification/disposition fields where known.

Roles/skills choose when an event is legal under the capability/governance contract and reference this one template source after Decision 22 activates it from the default branch. They do not copy the full template body into every skill. The artifact is Markdown for Human/agent readability; no parser, message bus, code-generation layer, JSON/YAML runtime schema, global exception taxonomy, or hidden workflow state is introduced.

Free-form Lead progress polling, RED/GREEN/test-trigger/compatibility-correction progress, and `No Human action is required` status messages are intentionally not template types. They are noise or intermediate activity rather than durable workflow boundaries once the canonical contract is active.

Trace: proposal canonical message contract → specs `Recurring workflow messages use canonical shared templates` and `Canonical workflow message templates activate only from default-branch governance` → implementation slices 9 and 13.

## Decision 16: Result evidence and routing handoff are separate durable boundaries

A legal action/review result may need to be persisted before ownership changes so the next owner can reconstruct the gate that authorizes the handoff. Therefore an action/review result can be valid durable evidence while the source routing tuple is still current. It does not, by itself, prove the handoff happened.

When the action's legal outcome requires a new owner, normal completion is:

```text
persist result + revision-aware evidence
→ fresh-read source routing
→ mutate routing to the target tuple
→ observe successful routing mutation
→ persist required handoff journal using the currently authoritative presentation contract
→ end the current invocation
```

This makes the #25 failure mode explicit: `Executor / implement-change` may have a durable `READY` result for revision R, but if labels still say `Executor / implement-change`, ownership has not transferred to Reviewer. Under at-least-once recovery, a later eligible Executor reconstructs the already-complete result and performs only the missing routing mutation/handoff journal; it does not repeat completed Slices or fabricate another READY result.

After Decision 22 activates canonical messages, `HANDOFF` is the lifecycle-journal presentation for the routing boundary. It records From/To, the triggering result/revision evidence, fresh-read source routing, successful routing mutation, and observed target routing. Before activation, the then-authoritative default-branch journal presentation remains valid. The canonical routing tuple remains workflow state; the message is reconstructable evidence only.

The pre-change canonical requirement identity `Routing handoff persists evidence before ownership transfer` is retained as a `MODIFIED` requirement, but its ordering is now precise: action/review result and revision-aware evidence remain durable before ownership transfer, while the handoff journal is written only after the routing mutation succeeds and target ownership is observed. The separate added handoff-ordering requirement is removed so the canonical requirement remains the single normative source for this transition ordering.

Trace: proposal result-vs-handoff contract → modified spec `Routing handoff persists evidence before ownership transfer` plus lifecycle-journal and template-activation requirements → implementation slices 9 and 13.

## Decision 17: Human-facing scheduled delivery is Lead-only and decision-required

Repository workflow evidence and Human delivery are separate channels. Reviewer and Executor continue to write the GitHub evidence needed by later agents, but their ordinary review results, Slice checkpoints, merge results, handoffs, and execution exceptions are not Human-facing Scheduled Task delivery. Ordinary Lead action results, merge authorization, handoff, execution-exception evidence, finalize progress, and successful self-resolved clarification are also repository-durable only.

Only Lead may emit `HUMAN_DECISION_REQUIRED` once the canonical contract is active, and only after Lead has reconstructed current durable evidence, applied its own specification/lifecycle authority and bounded systemic-coherence responsibility, and established that workflow progress genuinely requires Human authority or intent that Lead cannot legally resolve. Before activation, equivalent decision-ready escalation semantics remain governed by current default-branch rules. The decision-ready shape remains no more than three options, material impact/risk/trade-off, Lead recommendation, and an explicit requested Human response.

If that condition is absent, the Scheduled Agent wake is Human-silent even though repository work and durable GitHub evidence may have been produced. This is the same product pattern as a scheduled market task that runs but emits no user decision card when its delivery condition is false.

The repository defines delivery eligibility; the external Scheduled Task product configuration owns actual notification/associated-conversation surfacing. The three retained wake slots should be configured so ordinary workflow outcomes do not notify Human, while a genuine Lead-owned unresolved Human decision is the only workflow result eligible for Human delivery. Product UI behavior is not a repository routing, waiting, or authorization predicate.

Trace: proposal Human-delivery boundary → specs `Human-facing scheduled delivery is Lead-only and decision-required`, repository-artifact requirement, and Scheduled Task migration → implementation slice 9 plus external migration configuration, with activation semantics in slice 13.

## Decision 18: Catchable execution exceptions preserve raw observable evidence before classification

All Scheduled Agent engineering actions share one exception-capture contract. When a tool/runtime/execution operation returns a catchable failure and the invocation still has the ability to persist repository evidence, the current role records one bounded execution-exception record before relying on a summarized interpretation; once Decision 22 is active, this uses canonical `EXECUTION_EXCEPTION`.

The raw field is the error text actually observable to the Agent after the platform's existing safety redaction. The workflow neither attempts to recover hidden/withheld data nor unredacts credentials. The record also captures factual context required for later reconstruction: selected role/action, attempted operation/tool, relevant revision/base when applicable, whether any durable mutation is known to have completed before the failure, and the current unfinished work boundary.

Raw observation and interpretation are separate. The Agent may add a classification such as a known transient/recoverable condition when the evidence supports it, but an unfamiliar failure may remain `UNCLASSIFIED_EXECUTION_EXCEPTION`. The raw message must not be replaced by a paraphrase such as `GitHub mutation failed`, because Lead and later runs need the original observable evidence to determine whether a stable recovery path should be added.

The exception record is evidence, not a new lifecycle action/result and not automatically a lifecycle-transition journal. It does not itself change routing or authorize a retry. Repeated exception handling remains bounded by normal reconstruction and work-conserving/finalization rules rather than a retry counter or fault state machine.

Trace: proposal shared exception capture → spec `Catchable execution exceptions preserve raw observable evidence before disposition` → implementation slice 10 and message-template/activation slices 9 and 13.

## Decision 19: Invocation finalization converges catchable failures to reconstructable durable outcomes

After exception evidence is captured, the current role/action first asks whether the failure can be legally recovered within the same selected authority while routing and preconditions remain current. If yes, it performs that recovery and continues immediately under Decision 13; recording an exception does not create a voluntary yield point.

If the catchable failure cannot be resolved within the current role/action, the invocation must not normally disappear with only an external Scheduled Task reply. While the execution context still permits finalization, it persists the action-defined legal blocked/disposition result or routes to the contract-defined diagnosis owner, fresh-reads routing, completes any required ownership transfer under Decision 16, and persists the corresponding handoff journal when a handoff is required.

This shared rule does not invent one universal `EXECUTION_BLOCKED` result or force every failure to Lead. Action-specific contracts remain responsible for normal result enums and any known local recovery. For a newly observed failure with no existing legal disposition, bounded Lead diagnosis is the fallback specification/authority path; the durable raw exception evidence is what allows Lead to classify the root cause without relying on conversation memory.

A truly uncatchable hard termination—such as the execution environment ending before the Agent can persist anything—cannot be required to run a conceptual `finally` block. A later wake uses the existing at-least-once reconstruction rules over partial durable state. Thus the contract distinguishes `catchable failure with execution opportunity` from `hard termination with no persistence opportunity` without pretending exactly-once finalization is possible.

Trace: proposal invocation-finalization contract → spec `Catchable execution exceptions are dispositioned before normal invocation exit` plus work-conserving and modified handoff requirements → implementation slice 10.

## Decision 20: Authoritative context continuity is shared reconstruction; Reviewer gates specialize cumulative coverage

The workflow distinguishes current snapshots from durable obligations. Current routing labels, Issue state, and PR head describe the latest observable state. Requirements, Human clarifications, findings, review results, exceptions, blockers, authorizations, and declared source decisions are durable evidence whose applicability is determined by workflow meaning rather than comment recency. A newer message, handoff, validation result, routing change, or revision does not implicitly supersede earlier unresolved evidence.

Evidence leaves the selected action's required reconstruction context only through an explicit contract-defined consumption event: an authoritative supersession, a durable resolution that addresses the evidence, an applicable independent gate acceptance, completion of the lifecycle boundary the evidence authorized, or another action-specific event that clearly consumes it. The workflow does not add a persistent consumed flag; later invocations infer consumption from the existing durable events and current state.

Cross-Issue provenance follows the same rule. If a coordination workflow names an authoritative upstream source decision/gate, as #25 does for #23, Lead authoring must dereference the source authority rather than relying only on the copied Issue summary. `Reviewer / review-openspec` independently verifies that the current OpenSpec preserves the applicable upstream accepted/rejected boundaries and later authoritative Human clarifications. The summary remains useful orientation but is not a new canonical requirement set. If the source cannot be fetched or its authority/supersession is ambiguous, the action fails closed rather than inventing a replacement summary.

Reviewer coverage is gate-specific. `review-openspec` reconstructs the last valid applicable semantic PASS baseline B and every still-unreviewed material semantic OpenSpec change through the current semantic target R; Decision 21 defines why non-semantic bookkeeping revisions do not create a new semantic target. `review-implementation` and `review-archive` continue to reconstruct the last valid independent baseline and the exact current PR head R, cover all material unreviewed changes through R, and evaluate the complete current state. A Lead/Executor readiness result, routing handoff, mechanical validation PASS, or intermediate revision without the applicable independent Reviewer PASS does not independently advance the accepted baseline.

This design does not require replaying every historical comment. Authoritative source references, valid independent gate results, explicit resolution/supersession evidence, commit ancestry, current artifacts, and the persistent coordination Issue bound the relevant reconstruction set. It also does not add a queue, sequence number, pending-review label, context cache, semantic-revision classifier, event processor, or hidden state machine.

Trace: proposal authoritative-context/provenance continuity → specs `Scheduled Agent reconstruction preserves authoritative context continuity` and `Revision-bound Reviewer gates preserve cumulative unreviewed coverage` → implementation slice 12, refined by slice 13.

## Decision 21: Mechanical OpenSpec validation and semantic OpenSpec review have different invalidation boundaries

The repository's `OpenSpec Validate` workflow is intentionally broad. Any revision that changes `openspec/**` may trigger strict validation, including a revision that only flips completed task markers. That run is a mechanical statement about one exact checkout revision H: its validity depends on proving validator `HEAD == H` and running the pinned strict command. It says nothing by itself about whether Human/Lead intent and the semantic OpenSpec contract were independently reviewed.

`Reviewer / review-openspec` is different. Its PASS is recorded against the exact semantic target revision S that Reviewer actually inspected, but applicability follows OpenSpec meaning rather than raw SHA recency. If later revisions only persist completion/checkpoint bookkeeping and proposal/spec/design/traceability/scope/normative task intent are unchanged, S remains the accepted semantic baseline; a new mechanical CI run at H neither invalidates S nor creates another semantic gate.

A material semantic change creates a new semantic target. Examples include changed proposal intent, capability requirement/scenario, design decision, traceability, scope boundary, or normative task meaning. If implementation discovers such a defect, Executor cannot decide the new meaning: the legal exceptional path is `implement-change → Lead / resolve-question → review-openspec → implement-change`. Only after the corrected semantic target receives a fresh independent PASS may Executor resume implementation. By contrast, when implementation finishes with no semantic OpenSpec change after its approved baseline, the normal path is `review-openspec PASS → implement-change → review-implementation`.

The workflow does not persist a semantic revision ID, classifier result, applicability flag, or new status label. Lead/Reviewer/Executor reconstruct applicability from actual artifact changes and durable Human/Lead/Reviewer evidence. If that reconstruction is ambiguous, the relevant action fails closed rather than guessing.

This decision leaves `review-implementation` and `review-archive` unchanged as exact-current-head gates. Their current target is the implementation/archive PR head because the gate evaluates the current executable/archive content rather than a semantic contract that can survive bookkeeping-only SHA changes.

Trace: authoritative Human correction on #25 → spec `Mechanical OpenSpec validation and semantic OpenSpec review have separate invalidation boundaries` + refined `Revision-bound Reviewer gates preserve cumulative unreviewed coverage` → implementation slice 13.

## Decision 22: Canonical message templates activate only when default-branch governance contains them

Default-branch governance remains the only Scheduled Agent execution authority. Therefore the same feature PR that introduces `agents/templates/messages.md` cannot require its Reviewer invocation to execute under those unmerged rules. During review of that governance PR, feature-branch roles/skills/templates are governed artifacts under inspection, not bootstrap authority.

The activation boundary is the merge to the default branch. Once the change is present there, later Scheduled Agent invocations load the now-authoritative shared template source through default-branch `agents/AGENTS.md`, roles, and skills; covered durable events must use the canonical presentation. Earlier pre-activation free-form/legacy messages remain valid historical evidence when they complied with the then-authoritative default-branch contract. They are not retroactively findings solely because the new template later became active.

This boundary is deliberately static and requires no template-version state, migration daemon, runtime negotiation, branch override, or self-hosted bootstrap. Tests distinguish the two states by the location of authority: feature branch only means pre-activation; default branch means post-merge enforcement.

Decision 22 also applies to typed lifecycle journaling. Before activation, the evidence fields and lifecycle boundary still matter under the current default-branch contract, but canonical type names are not self-authorizing. After activation, the canonical typed message itself satisfies the lifecycle journal where specified.

Trace: authoritative Human correction on #25 → spec `Canonical workflow message templates activate only from default-branch governance` + refined message/lifecycle requirements → implementation slice 13.

## Scheduled Task migration

The three existing external wake slots remain. Their prompts should converge on the same bootstrap contract: read `README.md` and `agents/AGENTS.md` from the default branch, determine the declared mode, use the legacy assigned role only in `fixed-role`, and in `workflow-dynamic` derive role/action from durable workflow state. Once an invocation selects a role, it never switches role in that run.

Prompt configuration itself is external product state. Repository tests/docs can define the required bootstrap and Human-delivery eligibility contract but cannot make Scheduled Task conversation/result surfacing part of GitHub workflow state. The prompt also does not duplicate the shared work-conserving, context-continuity, semantic-review applicability, exception-capture, invocation-finalization, or canonical message bodies; those remain repository governance/templates loaded after bootstrap.

Message-template authority follows the same bootstrap rule. A wake processing an unmerged governance PR does not load that PR's template as its own authority. After the governance change merges, a subsequent wake obtains the canonical message contract naturally from the default branch; no external prompt rewrite or template-version switch is required solely for activation.

The retained external wake configuration must treat ordinary workflow execution as silent. Reviewer/Executor results, execution-exception evidence, and ordinary Lead results are still persisted to GitHub for reconstruction, but only a Lead-owned unresolved Human decision is eligible to surface to Human. If product UI still exposes associated task-conversation history, that surfacing remains external history rather than workflow state and does not change the repository delivery-eligibility contract.

## Validation strategy

Behavioral tests should exercise mode parsing, fixed-role compatibility, active-workflow selection, queued proposal activation ordering, invalid/multiple active fail-closed behavior, immutable invocation role, work-conserving continuation after recoverable same-role or failed-but-actionable validation, legal external-wait/stale/handoff termination, authoritative-context continuity across newer comments/handoffs/revisions, explicit supersession/resolution consumption, cross-Issue authoritative-source dereference with summary-not-authority semantics, cumulative gate-specific Reviewer baseline coverage, semantic `review-openspec` applicability surviving checkbox/task-checkpoint-only SHA changes, material semantic correction forcing `Lead / resolve-question → review-openspec → implement-change`, normal completed implementation routing directly to `review-implementation` when semantic meaning is unchanged, broad exact-head mechanical OpenSpec validation remaining independent of semantic PASS, catchable exception capture before disposition, local recovery continuation after captured exception, non-local catchable failure finalization to a legal durable outcome/handoff, uncatchable-hard-termination reconstruction, absence of duplicated weaker per-skill execution/context policy, stale competing activation, actor-bound Human evidence, duplicate escalation suppression, seven-day advisory evidence, analytics-only notification metadata, reverse-first `review-openspec` inspection with unchanged semantic bidirectional PASS semantics, Lead-role systemic-coherence contract wording and its non-supervisory/bounded scope, verified-Slice checkpoint persistence/recovery with no per-mutation implementation logging, lifecycle-transition journal recovery, native Archive close followed by closed-Issue `Lead / finalize-archive` handoff, terminal candidate selection before Lead completion evidence, and terminal exclusion after bounded `LIFECYCLE_COMPLETE` evidence.

Message-contract tests should additionally prove one shared `agents/templates/messages.md` source contains the eight approved types and common envelope without per-role copies; the unmerged feature template cannot govern the invocation reviewing that same PR; pre-activation messages are evaluated against current default-branch governance rather than future template rules; after merge/default-branch activation, later applicable roles/skills must reference and use the canonical source; execution-exception evidence preserves the raw platform-observable message plus bounded factual context and keeps interpretation/classification separate; unknown classification is allowed; `SLICE_CHECKPOINT` preserves the verified-Slice required fields after activation; canonical typed lifecycle-boundary messages satisfy the journal boundary without a duplicate generic meta-journal after activation; the modified canonical handoff requirement keeps result/revision evidence before transfer while requiring the applicable handoff journal after successful routing mutation; a persisted READY/PASS result with unchanged source routing is not treated as completed handoff; interrupted result-before-handoff recovery performs only the missing routing transition/journal; Reviewer/Executor exception/results and ordinary Lead exception/results are not Human-delivery eligible; and only a Lead-owned unresolved Human decision carries the bounded decision-ready Human shape. Repository quality checks and strict OpenSpec validation remain required.
