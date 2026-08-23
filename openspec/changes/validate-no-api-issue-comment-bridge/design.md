# Design: Validate no-API bridge and executable dispatch

## Context

The repository already has production dispatch code and regression coverage, but two runtime gaps remain coupled in #140:

1. the actual ChatGPT Scheduled Task environment has not proved a no-API round trip to repository-owned executable code; and
2. production dispatch still makes ordinary Issue selection depend on model-visible governance plus an acquisition path that performs closed-history/terminal/recovery forensics before it can select an otherwise unambiguous open formal workflow.

Primary source evidence:
- #140 Human Phase 1 refinement `issuecomment-5386416122`;
- #140 decision-complete Explore result `issuecomment-5386482159`;
- #140 scope correction `issuecomment-5387096717`;
- Reviewer finding `issuecomment-5387268115`;
- current default-branch `src/investment_strategy/workflow_dispatch.py`, `src/investment_strategy/scheduled_agent_runtime.py`, and `src/investment_strategy/human_authority.py`;
- current default-branch `agents/AGENTS.md` and `agents/workflow.md`;
- GitHub Actions documentation for the `issue_comment` `created` event and `GITHUB_TOKEN` recursion suppression semantics.

The Change keeps one purpose: make pre-model Scheduled-Agent selection executable through a no-API bridge while reducing selection to the smallest safe responsibility boundary. It does not add a second workflow DAG or move action/effect correctness into dispatch.

## Decision 1: Use the transport canary as a deployment prerequisite, not the lifecycle-completing scope

The first implementation slice still uses a dedicated `issue_comment: types: [created]` workflow to prove that ChatGPT Scheduled Task can synchronously exchange a request/result pair with bounded repository-owned GitHub Actions execution:

```text
Scheduled Task
  → exact GitHub Issue comment request
  → issue_comment Actions event
  → repository-owned handler
  → exact correlated result
  → same Scheduled Task reads that result
```

The transport result is deliberately non-authorizing and does not yet identify Issue/Role/Action. That preserves the original Phase 1 experiment and keeps transport failures isolated from workflow semantics.

However, transport success no longer completes the Change. After the transport path is deployed and proved, the same Change continues through the repository's existing multi-PR `MORE_IMPLEMENTATION_REQUIRED` lifecycle until production dispatch is simplified, deployed, and exercised through the bridge.

## Decision 2: The GitHub request comment ID is the sole bridge correlation identity

The Phase 1 request body remains exactly:

```text
DISPATCH_REQUEST
Requested-At: <timestamp>
```

After the comment write, the GitHub comment ID returned or freshly observed for that exact request is the sole correlation identity. No custom request UUID is generated.

The Phase 1 transport result remains:

```text
DISPATCH_RESULT
Request-Comment-ID: <exact GitHub request comment ID>
Default-Branch-Revision: <exact handler checkout revision>
Result: BRIDGE_OK
```

The Scheduled Task accepts only the result whose `Request-Comment-ID` equals its own exact request comment ID. Latest-comment selection, comment ordering, time proximity, or model inference are not correlation mechanisms.

## Decision 3: Check-in Issue selection is deployment configuration, not workflow authority

A Human creates the check-in Issue outside this Change. The bridge accepts a request only when the triggering comment belongs to the exact configured check-in Issue number.

That configured Issue number is deployment input, preferably an explicit repository variable. It is not a workflow-routing field and cannot identify the coordination Issue that production dispatch later selects.

If the configured Issue identity is absent, malformed, or mismatched, the bridge performs no valid request handling. This Change does not create, rotate, or close check-in Issues automatically.

## Decision 4: Strict parsing plus required request-scoped serialization bounds duplicate delivery

Before producing a bridge result, the repository-owned handler validates:

- the event is a newly created Issue comment;
- the event belongs to the configured check-in Issue;
- the body matches the exact bounded request contract;
- the event exposes a positive numeric request comment ID; and
- no valid correlated result already exists for that exact request comment ID.

The workflow MUST serialize handling for the same immutable request comment ID with a request-scoped GitHub Actions concurrency group and `cancel-in-progress: false`. After entering that serialized boundary, the handler freshly re-checks for an existing correlated result immediately before posting. An already-completed request becomes an idempotent no-op.

This is transient execution serialization, not a durable lock, lease, claim, retry registry, heartbeat, or hidden workflow state.

## Decision 5: Normal dispatch owns only current open-Issue selection

`src/investment_strategy/workflow_dispatch.py` remains the one pure production classifier shared by runtime and regression tests, but its normal-selection contract is narrowed.

Normal selection consumes only provenance-qualified current facts required to answer "what work, if any, is selected?":

- Issue number;
- current open state;
- persisted `Change:` identity;
- current routing tuple derived from labels;
- GitHub `created_at` ordering for the combined pre-activation queue; and
- enumeration/provenance completeness.

A direct-Propose candidate may participate only after the existing executable Human-authority surface in `src/investment_strategy/human_authority.py` has proved the canonical `propose_admission_ref(issue_number)` decision through `is_human_decision_approved(...)`. Runtime normalizes that result into candidate eligibility; `workflow_dispatch.py` does not parse Human comments/events itself, and the model does not interpret Human prose or reimplement that authority algorithm.

The model does not calculate formal cardinality, queue order, current routing, or Issue/Role/Action from governance prose. The production decision returns one structured disposition:

- `AUTHORIZE` with exact Issue/Role/Action;
- `NO_WORK`; or
- `FAIL_CLOSED`.

PR heads, CI runs, OpenSpec artifacts, review evidence, lifecycle-specific PR state, and effect-specific mutation guards are not normal-selection inputs.

## Decision 6: A sole open formal workflow bypasses closed-history forensics

The runtime first obtains a complete provenance-qualified snapshot of current open Issues and executes normal classification.

```text
complete current OPEN-Issue snapshot
        ↓
normal production classifier
        ├─ formal > 1 / invalid / incomplete → FAIL_CLOSED
        ├─ formal = 1 → AUTHORIZE exact Issue / Role / Action
        └─ formal = 0 → exceptional-recovery guard before queue or NO_WORK
```

When exactly one open routed non-`unset` formal workflow exists, that workflow wins immediately. The runtime MUST NOT require terminal comments, Human-retirement comments, archived legacy Change lookup, or closed-Issue re-observation merely to authorize that sole open formal workflow.

This changes cost and responsibility, not WIP=1 semantics: two open formal workflows still fail closed, and incomplete/unqualified open-Issue enumeration still cannot authorize work.

## Decision 7: Exceptional closed-history recovery is a formal-zero safety gate

Whenever no open formal workflow exists, the runtime performs a separate bounded executable recovery acquisition/classification before it may authorize pre-activation work or return `NO_WORK`. This prevents a prematurely closed unfinished workflow from being stranded merely because the open queue is empty, while avoiding historical forensics whenever a coherent open formal workflow already owns WIP.

At that boundary the runtime:

1. enumerates the current closed workflow-looking candidate set with observable completeness;
2. fetches detailed terminal/recovery evidence only for candidates that may affect recovery classification;
3. preserves existing terminal journal, direct-Human retirement, legacy archive, and current re-observation predicates as applicable;
4. classifies the result:
   - exactly one qualifying premature-close candidate → authorize `Lead / resolve-question` for that Issue;
   - multiple, unresolved, incomplete, or provenance-indeterminate recovery state → `FAIL_CLOSED`;
   - no blocking recovery candidate → allow deterministic open pre-activation selection or `NO_WORK`.

Therefore premature close still blocks new workflow admission and is recoverable even when there is no queued work, but the historical forensic path is no longer an unconditional prerequisite for every active-workflow wake.

This may be implemented as a focused recovery classifier/helper beside the normal classifier or as a narrowly factored runtime helper. It MUST NOT become a generic workflow engine, global fault registry, persistent recovery state machine, or hidden ownership store. Existing `workflow_recovery.py` is merge-recovery-specific and is not silently repurposed as proof that premature-close recovery already has the required abstraction.

## Decision 8: Action-specific correctness begins after selection

After machine selection identifies exact Issue/Role/Action, the mapped action reconstructs only the evidence its own contract requires.

Examples:
- `review-openspec` owns proposal/spec/design/tasks and exact semantic-review evidence;
- `implement-change` owns current implementation PR/task/test evidence;
- `merge-pr` owns exact PR head/review/merge preconditions;
- finalize actions own archive/lifecycle evidence;
- effect application owns mutation-time stale-state guards.

A fresh normal dispatch decision remains an action-entry identity precondition. It proves that the same exact Issue/routing is still selected; it does not make global dispatch load every action-specific resource.

`propose-change` retains immediate pre-write and fresh post-write activation checks. Its preactivation authorization also depends on executable direct-Propose admission and, whenever open formal cardinality is zero, the exceptional recovery guard having proved that no closed recovery candidate blocks admission.

## Decision 9: `agents/AGENTS.md` describes the authority boundary, not a duplicate classifier algorithm

The approved implementation will reduce the default-branch dispatch section to the durable rules that Humans and model workers need to know:

- dispatch mode and executable owner;
- authoritative current GitHub provenance/completeness requirements;
- the meaning of `AUTHORIZE`, `NO_WORK`, and `FAIL_CLOSED`;
- formal-work-first and WIP=1 safety;
- exceptional recovery must clear before pre-activation admission or `NO_WORK` when formal cardinality is zero;
- selected Issue/Role/Action comes only from executable output; and
- action/effect preconditions remain downstream responsibilities.

Detailed deterministic branching, candidate construction, admission evaluation, and ordering mechanics belong in executable production code and regression tests. `agents/workflow.md` continues to own lifecycle topology; this Change does not create a second topology representation.

## Decision 10: The deployed bridge returns the production machine decision after dispatch deployment

Phase 1 `DISPATCH_RESULT / BRIDGE_OK` remains transport-only. After the corrected production dispatch path is merged to the default branch, the deployed bridge gains a distinct machine-decision response:

```text
DISPATCH_DECISION
Request-Comment-ID: <exact GitHub request comment ID>
Default-Branch-Revision: <exact handler checkout revision>
Disposition: AUTHORIZE | NO_WORK | FAIL_CLOSED
Issue: <exact Issue number>       # AUTHORIZE only
Role: <lead|reviewer|executor>    # AUTHORIZE only
Action: <mapped action>           # AUTHORIZE only
```

The result is generated only from the same production normal-selection/recovery orchestration used by repository runtime and tests. `NO_WORK` and `FAIL_CLOSED` carry no Issue/Role/Action tuple.

`DISPATCH_DECISION` is authority only for which mapped model invocation may begin. It is not consequential-effect authorization and cannot authorize routing, Change mutation, review/merge acceptance, or another durable write by itself.

The Scheduled Task accepts only the decision correlated to its exact request comment ID and exact default-branch handler revision. It loads the selected default-branch Role and mapped Skill only after an `AUTHORIZE` decision. The model worker must not replace or override the returned tuple.

## Decision 11: Deployment requires staged multi-PR continuation inside the same Change

GitHub `issue_comment` workflows execute only when their workflow definition is already present on the default branch. Both transport proof and the later machine-decision proof therefore require deployment before real E2E acceptance.

The existing one-Change/multi-PR lifecycle is used in three deployment stages:

1. **Transport deployment.** Implement/review/merge the bounded bridge workflow/handler/tests to `main`. `finalize-change` sees approved work remaining and returns `MORE_IMPLEMENTATION_REQUIRED`.
2. **Executable dispatch deployment.** Prove the Phase 1 transport round trip, then implement/review/merge the normal-selection/recovery separation, executable direct-Propose admission consumption, governance simplification, bridge machine-decision extension, and deterministic tests to `main`. `finalize-change` again returns `MORE_IMPLEMENTATION_REQUIRED` because live machine-dispatch evidence remains.
3. **Live machine-dispatch proof.** A later real ChatGPT Scheduled Task invocation uses the deployed default-branch bridge and production classifier, obtains an exact correlated `DISPATCH_DECISION`, and consumes the machine-selected tuple without model-side selection. Evidence/task completion is recorded in the subsequent implementation revision/PR and passes the normal review/merge lifecycle.

No task is marked complete before its real deployment-dependent evidence exists. The sequence does not create a special merge bypass or second lifecycle DAG.

## Blast radius

Expected implementation surfaces:

- `.github/workflows/scheduled-agent-bridge-canary.yml` — no-API `issue_comment` entry point, request-scoped serialization, default-branch checkout, and later machine-decision response;
- `src/investment_strategy/scheduled_agent_bridge_canary.py` — bounded request/result parsing, correlation/idempotency, and dispatch-response rendering;
- `src/investment_strategy/workflow_dispatch.py` — pure normal open-Issue selection classifier and structured decision;
- `src/investment_strategy/scheduled_agent_runtime.py` — open-first acquisition/orchestration, executable admission consumption, and bounded exceptional-recovery acquisition;
- existing `src/investment_strategy/human_authority.py` as the canonical executable direct-Propose admission evaluator, modified only if integration proves a narrowly necessary reusable adapter is missing;
- a focused recovery helper only if needed to keep recovery classification independent and testable;
- `agents/AGENTS.md` — dispatch authority/result boundary simplified to consume executable decisions;
- focused bridge/dispatch/runtime regression tests;
- this OpenSpec Change.

No change is expected to `agents/workflow.md`, role definitions, mapped Skills, canonical message templates, or consequential effect application.

## Compatibility and rollout

- The existing Responses API runtime may remain during this Change; its presence is not the no-API proof.
- Phase 1 `BRIDGE_OK` remains non-authorizing and can coexist with the later `DISPATCH_DECISION` contract during staged deployment.
- Current WIP=1, deterministic pre-activation order, fail-closed multiple-active behavior, Human/maintainer administrative repair, executable Human authority, and bounded premature-close recovery semantics are preserved.
- Normal active-workflow selection no longer depends on repository-wide closed-history reconstruction.
- Exceptional recovery executes before any pre-activation work or `NO_WORK` result when open formal cardinality is zero.
- Action-specific gates remain independently authoritative after selection.
- The Human-created check-in Issue remains external deployment setup and is not workflow state.

## Rejected alternatives

### Keep transport-only scope and create another Change for dispatch

Rejected because #140's corrected scope requires the same immutable Change to prove the bridge and correct pre-model dispatch before lifecycle completion.

### Keep `state=all` forensic reconstruction on every wake

Rejected because closed terminal/recovery evidence is irrelevant to selection when one coherent open formal workflow already occupies WIP. Retaining that cost would preserve the demonstrated responsibility coupling without adding safety.

### Ignore closed Issues entirely

Rejected because a prematurely closed unfinished workflow must still be recovered or fail closed before pre-activation/idle classification. Exceptional recovery remains a required executable formal-zero gate.

### Reinterpret direct-Propose Human admission inside the dispatcher

Rejected because `human_authority.py` already owns the executable provenance-bound decision algorithm. Dispatch consumes its result rather than creating a second Human-authority implementation or asking the model to interpret comments/labels.

### Put PR/CI/OpenSpec/review evidence into the global classifier

Rejected because those facts determine whether a selected action may complete, not which Issue/Role/Action is globally selected. Loading them globally would expand dispatch responsibility and recreate model-like orchestration in code.

### Reuse the existing Responses API worker as the no-API proof

Rejected because the required product/runtime boundary starts from ChatGPT Scheduled Task without depending on an OpenAI API worker.

### Generate a custom request UUID or correlate by latest comment

Rejected because GitHub already supplies the exact immutable triggering comment identity.

### Rely on check-then-post without same-request serialization

Rejected because overlapping runs can both observe no existing result. Required request-scoped Actions serialization plus a fresh result re-check closes that race without durable coordination state.

### Add a lock, lease, heartbeat, global fault registry, or generic workflow engine

Rejected because the demonstrated semantics remain reconstructable from authoritative GitHub state with pure classifiers and bounded exceptional evidence acquisition.
