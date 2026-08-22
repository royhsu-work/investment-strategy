# Change: Enforce runtime dispatch preconditions

## Why

#105 / Change `enforce-dispatch-cardinality-preflight` correctly established WIP=1, complete repository-wide cardinality reconstruction, fail-closed dispatch, and pre-activation Explore/Propose guards. #133 then extracted that model into the production executable `src/investment_strategy/workflow_dispatch.py`, added explicit same-execution observation provenance, and made executable regressions consume the production implementation.

Reviewer implementation finding `issuecomment-5379837891` showed that the then-approved design still had no demonstrated runtime boundary that executed the classifier before the real Scheduled Agent performed substantive work. The later Transition-Gate correction moved routing mutation behind GitHub Actions, but Reviewer OpenSpec finding `issuecomment-5380345857` correctly identified that this was still too late: the first reconstructable #100/#130 violation was already #130 substantive `Lead / explore-change` while #100 occupied formal WIP. A post-action routing gate therefore cannot prevent the demonstrated recurrence class.

Further feasibility work established the required boundary more precisely: executable authorization must occur **before the model worker for a mapped action is invoked**. The current ChatGPT Scheduled Tasks surface has no demonstrated external webhook/pre-invocation hook that lets repository code decide whether a mapped action may start. Repository-hosted GitHub Actions can own scheduling and execute `workflow_dispatch.py` before any model request. The model worker can then operate inside an isolated runner/workspace without durable GitHub write authority, while repository-owned application code fresh-revalidates the same workflow state before committing any requested durable effect.

The corrected target is therefore a **machine-gated Scheduled Agent runtime**, not an Issue-comment transition gate and not a second workflow engine.

## What Changes

- Preserve `src/investment_strategy/workflow_dispatch.py` as the one repository-owned pure dispatch/cardinality/action-authorization implementation used by regressions and live runtime authorization.
- Add one repository-hosted Scheduled Agent runtime in GitHub Actions. Its scheduled/manual wake path checks out authoritative default-branch governance, reconstructs complete current GitHub workflow state, builds provenance-qualified classifier input, and executes the production classifier **before any mapped-action model invocation**.
- Preserve the three fixed role slots. Scheduled wakes for Lead, Reviewer, and Executor carry only the fixed slot role; the executable dispatcher selects the current Issue/routing from GitHub. A slot whose role does not match the selected current role exits without invoking a model.
- Permit an explicit GitHub Actions manual wake only when it is subject to the same pre-model dispatcher and fixed-role-match rule. Manual wake is an execution trigger, not workflow authorization or a target-selection override.
- Invoke an OpenAI Responses API model worker only after the dispatcher authorizes the exact coordination Issue, role, and action. The worker receives the mapped default-branch role/Skill context and repository/GitHub read capability needed by that action, plus local workspace tools where implementation work requires them.
- Do not use Codex as the worker runtime for this Change. The runtime integration is repository code calling the OpenAI Responses API; model choice/authentication is deployment configuration and does not become workflow state.
- Prevent the model worker from possessing durable GitHub write authority. Durable writes—including Issue/PR comments and labels, Change/routing mutation, branch/commit/PR changes, merge, close/reopen, and other workflow-owned GitHub effects—must pass through repository-owned apply code rather than a model-visible write credential.
- Represent worker-requested effects only as invocation-local output/transport. Such staged effects are not workflow state, are not an authorization token, and cannot authorize a later run.
- Before each effect batch is durably applied, fresh-reconstruct current GitHub state and re-run the production classifier. Application is allowed only while the exact source Issue/role/action remains authorized and any effect-specific repository preconditions still hold. A stale, incomplete, contradictory, multiple-active, or otherwise unprovable source fails closed without applying the staged effects.
- Keep `agents/workflow.md` as the single lifecycle-topology owner. Routing/successor effects must be validated against that authoritative topology without introducing a second normative DAG or hidden lifecycle registry.
- After an accepted effect batch, fresh-read the resulting durable state. Same-role continuation may run only after another executable dispatch from that new current state; cross-role continuation ends the fixed-role execution and waits for the matching role slot.
- Use one repository-wide runtime concurrency boundary so only one Scheduled Agent runtime execution applies workflow effects at a time. Concurrency is runner serialization only; it is not a lock/lease/heartbeat/claim or repository workflow state.
- Cover **all mapped actions**, including `explore-change` and `propose-change`, before this runtime becomes the sole scheduled execution path. A partial cutover that leaves an independent ChatGPT Scheduled Task able to start mapped work would not satisfy #133.
- Cut over without dual schedulers: legacy ChatGPT Scheduled Tasks must be disabled before/when the GitHub Actions runtime becomes authoritative for normal scheduled mapped actions. They are not retained as a fallback execution path.
- Require post-merge live evidence from normal #133 state: at least one scheduled role slot that does not match the current selected role must prove pre-model STOP/no model invocation, and the matching selected role slot must prove dispatcher authorization before the first real model invocation. No synthetic second formal workflow or special `Lead / resolve-question` state is required.

## Affected Capabilities

### Modified

- `scheduled-agent-workflow`
  - complete same-execution GitHub reconstruction and production classifier consumption become a pre-model runtime gate rather than an Agent-followed instruction;
  - fixed role scheduling remains, but repository-hosted GitHub Actions owns the wake/runtime boundary;
  - unauthorized/mismatched/incomplete dispatch exits before a mapped model action begins;
  - worker-requested durable effects are reauthorized from fresh current state before application;
  - same-role continuation is re-dispatched after applied durable state rather than inheriting an earlier authorization;
  - legacy ChatGPT Scheduled Tasks are not a parallel normal runtime after cutover.

## Scope

In scope:

- Existing pure production dispatch classifier and observation-provenance input contract.
- Repository-owned GitHub acquisition/normalization sufficient to build complete `DispatchPreflight` input in GitHub Actions.
- GitHub Actions scheduled/manual runtime wake with fixed Lead/Reviewer/Executor role slots and repository-wide execution serialization.
- A Responses API worker adapter that invokes a model only after exact Issue/role/action authorization.
- Model-worker isolation from durable GitHub write credentials.
- Invocation-local staged effect/result transport and repository-owned effect application after fresh classifier/action reauthorization.
- Effect-specific fresh guards, post-write verification, and stale-stop behavior.
- Same-role continuation only through fresh post-apply dispatch.
- Coverage of every mapped normal action, including pre-activation Explore and Propose, before runtime cutover.
- Removal/correction of prior governance/Skill wording that treated the current ChatGPT Scheduled Agent as the live executor/authorization owner.
- PR-stage runtime/adapter tests plus post-merge live default-branch canary evidence from ordinary #133 lifecycle state.

Out of scope:

- A generic workflow engine, second lifecycle DAG, hidden queue, durable authorization registry, lease, heartbeat, workflow claim, or model-derived priority system.
- Using Issue comments as transition commands or authorization tokens.
- Routing-event provenance as the primary #133 enforcement mechanism. Provenance remains useful audit/security evidence but does not substitute for pre-model authorization.
- Automatically repairing an already-created multiple-active repository state or selecting a winner from it.
- Changing Human authority semantics, Reviewer independence, role ownership, or the legal lifecycle topology.
- Moving workflow semantics into cron strings, model prompts, API-model configuration, or Actions artifacts.
- Codex-specific runtime integration.

## Skill maintenance traceability

The runtime boundary changes how durable effects are executed, not the semantic ownership of the ten mapped actions. Implementation MUST audit every mapped Skill against the new worker/apply split and modify only the Skills whose current procedure assumes direct model-owned GitHub mutation or Agent-owned executable authorization. At minimum, the two Skills already modified by #133 require correction:

- `agents/skills/openspec-explore/SKILL.md` — preserve Explore research/readiness ownership, but remove any claim that the model itself establishes executable dispatch authorization; substantive Explore is invoked only after the machine runtime authorizes its exact action.
- `agents/skills/openspec-change/SKILL.md` — preserve Propose/resolve-question semantic ownership, but remove the prior Issue-comment Transition Gate path and direct-worker durable transition assumption; its durable effects are applied through the shared runtime effect boundary.

Shared `agents/AGENTS.md` and message/result presentation must define the common pre-model authorization and staged-effect/apply semantics so action-local Skills do not each reimplement the dispatcher or effect gate. Any additional Skill changed during implementation MUST be listed with its concrete current-procedure reason before implementation is declared complete.

No new user-triggered Skill is introduced. The Scheduled Agent runtime is repository infrastructure.

## Traceability

- Source decision-complete Explore: #133 `issuecomment-5373937613`.
- Observation-provenance semantic correction: #133 `issuecomment-5377194503`.
- Prior implementation READY and production-classifier groundwork: #133 `issuecomment-5379787305`, PR #134 head `0727b030bb9c27d311a390e9d765d4421302abaa`.
- Reviewer implementation finding proving Agent-side executable consumption was absent: #133 `issuecomment-5379837891`.
- Executor capability blocker for the assumed Scheduled-Agent repository execution path: #133 `issuecomment-5379922085`.
- Reviewer OpenSpec finding rejecting the later Transition-Gate MVP: #133 `issuecomment-5380345857`.
- Prior semantic remediation: #105 / Change `enforce-dispatch-cardinality-preflight`.
- Existing canonical requirement: `Active-workflow cardinality and Issue-state coherence precede queue selection`.
- Added requirement in this correction: `Machine-gated runtime authorizes mapped work before model invocation and reauthorizes durable effects`.
- Capability delta: `specs/scheduled-agent-workflow/spec.md`.
- Design: `design.md`.
- Implementation slices: `tasks.md`.
