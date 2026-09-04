## Why

Recent Scheduled-Agent repairs have repeatedly changed routing reconstruction, history parsing, worker/application boundaries, wake continuation, and transport behavior because one logical workflow state machine is independently represented across GitHub labels, `Change:`, prose governance, runtime classifiers, effect parsers, worker schemas, transport comments, and Scheduled Task instructions. Fixing each recurrence with another parser or compatibility predicate has increased the number of control-state representations instead of reducing them.

#138's decision-complete Explore establishes a smaller target that fits the actual execution environment: ChatGPT Scheduled Tasks are the only normal model wake; GitHub Actions may execute deterministic repository code but must not host or call a model; one wake executes exactly one machine-authorized semantic action; repository code owns state/dispatch/result validation/transition/effect application; transport is replaceable and is never workflow authority.

The formal baseline is #138 `ACTION_RESULT(PROPOSAL_READY)` comment `5470121673`, produced from current-default-branch revision `4e3241d7d84a64012bf3b6218442128a4cb48d7a`. Its material claims are supported by current default-branch governance/runtime observations plus the linked production evidence from #133, #140, #155, #158, #161, #164, #168, and #175. Propose independently rechecked that evidence against current `main`; no new Human-reserved requirement, scope/risk acceptance, or architecture commitment is required.

## What Changes

- Reduce canonical live workflow routing to exactly one `action:<action>` label on an open coordination Issue. Role becomes a deterministic projection of Action from the executable topology; persistent `agent:*` labels are removed from normal state and retired at migration cutover.
- Keep `Change:` as immutable formal workflow identity once Propose activates it and keep Issue open/closed as lifecycle state. Results, reviews, Human decisions, HANDOFF/messages, PR/CI evidence, and transport comments remain durable evidence/audit surfaces, not current routing state.
- Replace the ambiguous generic `merge-pr` action with explicit `merge-implementation-pr` and `merge-archive-pr` action identities so the two merge lifecycle positions do not require phase inference from surrounding prose/history.
- Establish one small executable workflow topology/kernel as the only production authority for Action vocabulary, Action→Role derivation, legal typed results/transitions, deterministic dispatch ordering/cardinality, effect capabilities, fresh source reauthorization, stale/replay rejection, and postcondition validation. Production dispatch/application/tests consume that same executable authority.
- Make `agents/workflow.md` a generated or mechanically verified Human-readable projection of the executable topology instead of an independently maintained second DAG. Governance/Skills continue to own semantic role procedure but must not duplicate machine-decidable topology predicates as parallel authority.
- Generalize the bounded structured-result pattern already proven at the Explore boundary: a semantic worker returns an exact machine-authorized Issue/Action-bound typed control result plus narrative/source evidence; repository application derives the only legal transition/effects. Control outcomes are never re-extracted from arbitrary Markdown.
- Adopt one-action-per-wake as the normal Scheduled-Agent execution contract: fresh dispatch → exactly one mapped semantic action → deterministic result application/transition → invocation exit. The next Scheduled Task wake fresh-dispatches from current canonical state. Same-role continuation, cross-role wake-barrier orchestration, fresh-worker same-wake chaining, continuation-required flags, and wake-role state are removed from correctness-critical semantics.
- Preserve work-conserving behavior inside the one selected action: immediately actionable RED→GREEN→VERIFY work, correction of actionable validation failures, and bounded consumption of an exact just-triggered external resource remain inside that action until its own result or a genuine Human/external/stale/hard boundary is reached. Finishing one action never authorizes a second action in the same wake.
- Keep ChatGPT/GitHub connector comments and GitHub Actions as replaceable transport adapters only. Current no-API transport must correlate exact request → exact Actions run/job/result and exact application request/result; later transport replacement must not change topology or kernel semantics. No OpenAI API, Responses API, GitHub-hosted model worker, generic daemon, second scheduler, lock/lease/heartbeat/retry-state framework, or broker is introduced.
- Perform a bounded shadow/canonicalization/cutover migration: inventory all live/routed Issues from complete authoritative GitHub observations; classify terminal/current/ambiguous state; compare old and new deterministic decisions without mutation; migrate live state to Action-only routing; explicitly escalate only genuine ambiguity; cut production dispatch/application to the kernel; then delete obsolete Role-label, history-parser, Markdown-topology/effect-parser, old worker-host, continuation, response-mailbox, and compatibility hot paths.
- Preserve WIP=1 / finish-first, authoritative enumeration/completeness/provenance, Human-reserved authority, exact-revision review/merge gates, role separation, action-local semantic evidence, stale/concurrency fail-closed behavior, and deterministic OpenSpec archive automation.

## Capabilities

### Modified Capabilities

- `scheduled-agent-workflow`: reduce canonical routing/state, introduce explicit merge action identities and typed executable topology/application semantics, enforce exactly one mapped action per Scheduled Task wake, and define bounded migration/cutover/deletion while preserving semantic role judgment and lifecycle gates.
- `repository-governance`: make the executable workflow topology/kernel the single authoritative workflow-semantics surface for machine-decidable state/transition rules, with Human-readable workflow documentation mechanically derived or verified rather than independently normative.

## Skill maintenance traceability

Source/change reference for every entry below: #138 Explore result `5470121673` and Change `simplify-scheduled-agent-control-plane`.

- **Modified — mapped OpenSpec Skills (`openspec-explore`, `openspec-change`, `openspec-review`)**
  - Responsibility before: combine semantic procedure with several routing/continuation/application facts expressed in prose.
  - Responsibility after: retain semantic research/formalization/review ownership and evidence obligations, but consume machine authorization and typed result/application contracts from the executable kernel; do not duplicate Action→Role mapping, legal successor tables, or same-wake continuation logic.
  - Rationale: preserve semantic judgment while removing parallel machine-control authority from procedural prose.
  - Replacement/supersession: no semantic Skill is replaced; only duplicated deterministic control-plane material is removed or shortened.

- **Modified — mapped implementation/merge/lifecycle/archive Skills**
  - Responsibility before: encode action-local semantic/verification work plus references to generic `merge-pr`, routing tuples, cross-role HANDOFF/wake behavior, and shared continuation predicates.
  - Responsibility after: retain role-specific implementation/review/finalize/merge gates; use explicit `merge-implementation-pr` / `merge-archive-pr` identities and the shared typed application boundary; end the wake after one mapped action result is applied.
  - Rationale: make phase identity executable and remove workflow-engine behavior from Skills without weakening exact-head review/merge or lifecycle preparation.
  - Replacement/supersession: generic merge-action wording is superseded by two explicit action identities; no semantic role authority moves to deterministic code.

No new repository Skill is introduced. `skill-creator` is composition guidance for keeping the modified Skills concise and preserving the default-branch authority hierarchy; it is not itself a modification target.

## Impact

Expected final implementation surfaces include shared governance, `agents/workflow.md`, mapped role/Skill references, message presentation guidance where routing/continuation wording changes, the canonical `scheduled-agent-workflow` and `repository-governance` specs, and the current dispatcher/runtime/worker/effect/transport modules plus their production-boundary tests. The implementation MAY rename/consolidate those modules, but the approved end state must have one executable topology/kernel owner rather than a new fourth classifier left beside the old ones.

Migration must be staged so old/new decisions can be compared before mutation cutover. Dual control paths are permitted only inside that bounded migration window. After cutover acceptance, compatibility/history/topology parsing that is no longer required by live canonical state must be deleted from the production hot path; historical artifacts remain audit evidence.

The physical connector currently exposes direct GitHub write capabilities, so this Change does not claim token-level impossibility of bypass by the external model host. The governed normal path nevertheless requires consequential workflow application through fresh kernel authorization and postcondition verification. Stronger credential/tool scoping may be added later without altering workflow semantics.

This Change intentionally does not redesign semantic Explore/Propose/Reviewer meaning established by #175, deterministic archive ownership, Human authority provenance, or WIP=1. It changes the control-plane representation and execution boundary that carry those semantics.