# Canonical Workflow Messages

This file is the single shared Markdown presentation contract for recurring durable Scheduled Agent workflow messages. It defines presentation/evidence shape only and does not redefine routing, authorization, termination, review, merge, lifecycle, result-enum, or exception semantics owned by `agents/AGENTS.md`, role files, and action skills.

## Activation boundary

Repository execution authority comes only from the default branch. The default-branch merge is the activation boundary for this canonical presentation contract. While an unmerged governance PR introduces or edits this file and its role/skill references, those feature-branch artifacts are review target/input and must not govern its own current invocation. The invocation continues to use the then-authoritative default-branch governance.

After the governance/template change is merged to the default branch, later covered workflow events use this single shared template source. Pre-activation free-form/legacy messages that complied with then-authoritative default-branch governance remain valid historical evidence; their older presentation is not a retroactive template finding.

This activation rule does not add template-version state, migration state, a parser-dependent runtime, branch-authority override, or hidden workflow state.

## Machine-gated worker/application boundary

After machine-gated runtime cutover, a mapped model worker does not make a canonical durable message authoritative by directly writing GitHub. The worker returns its action result and any requested durable effects as invocation-local output. Repository-owned application code fresh-reauthorizes the exact source Issue/role/action, validates effect-specific preconditions and topology, applies only the authorized effects, and fresh-reads the resulting durable state.

A canonical message below exists as durable workflow evidence only after the repository-owned application boundary has successfully persisted it and any required postcondition is observed. Worker output or an Actions artifact is staged transport only: it is not a durable message, routing state, authorization token, or proof that a requested mutation succeeded.

When an applied result changes routing, continuation always re-enters executable dispatch from the resulting current GitHub state. Every selected successor uses a fresh mapped model invocation and reconstructs current durable evidence. A same-role successor may continue in the same scheduled wake after fresh dispatch. A cross-role successor is wake-terminal for the current scheduled wake: its durable routing and machine selection are preserved, but that successor role is not invoked until a later scheduled wake performs fresh reconstruction and executable dispatch. The boundary does not wait for a dedicated fixed-role schedule slot, and no prior worker context or requested effect authorizes any continuation.

The common workflow envelope is used whenever a field is applicable to the event:

- `Workflow`: persistent coordination Issue identity.
- `Change`: immutable OpenSpec Change identity.
- `Action`: selected repository action.
- `Result`: action/review/merge/lifecycle result defined by the owning action contract.
- `Revision`: exact revision/base relevant to the event when applicable.

Event-specific fields below add only the durable evidence required for that boundary. Roles and skills reference this file instead of copying private template bodies. This contract does not require a parser-dependent message bus, JSON/YAML runtime schema, template engine, notification state machine, generic exception engine, or hidden workflow state.

## `ACTION_RESULT`

Use for non-review action outcomes and lifecycle results.

Required evidence when applicable:

- common workflow envelope including `Result` and exact `Revision`;
- bounded result evidence supporting the action-defined result;
- next action, expected owner, wait condition, or terminal state.

For applicable pre-activation `Lead / explore-change`, the `ACTION_RESULT` MUST preserve the exact executable decision actually consumed at action entry, including enumeration completeness, observation provenance, formal-active/terminal-pending Issue identities, recovery candidate identities, pre-activation candidate identities, selected Issue, and disposition. The repository runtime renders those fields from the consumed machine decision/evidence envelope rather than reconstructing a second model-derived Issue list.

For applicable `Lead / propose-change`, the `ACTION_RESULT` MUST additionally preserve the immediate pre-write executable decision, expected Change identity, post-write formal-active/terminal-pending Issue identities, post-write completeness, post-write observation provenance, post-write disposition, and whether activation accepted. The pre-write and post-write fields reflect the exact executable decisions consumed by repository-owned dispatch/application at those boundaries rather than a later model summary.

These preflight/activation fields are audit/diagnostic evidence only and MUST NOT authorize a later invocation. A later dispatch MUST fresh-reconstruct the required current state from authoritative GitHub observations and re-execute the executable dispatch precondition; prior invocation output, durable comments, cached observations, and historical routing remain audit/context only. Optional wake/invocation-source correlation MAY be recorded only when the execution environment actually exposes it, MUST NOT be fabricated, and MUST NOT be used as routing or authorization state.

`ACTION_RESULT` does not create result enums; the owning action contract defines them.

## `REVIEW_RESULT`

Use for `review-openspec`, `review-implementation`, and `review-archive`.

Required evidence:

- common workflow envelope;
- exact reviewed revision;
- gate evidence used for the independent review;
- `PASS` or action-defined findings, with findings identified when present;
- expected next owner or correction owner.

For `review-openspec`, the exact reviewed revision is the semantic target actually inspected; later bookkeeping-only SHAs do not retroactively rewrite that semantic review record. Implementation and archive review records remain bound to their exact current PR heads.

## `SLICE_CHECKPOINT`

Use exactly once after an approved Executor Slice reaches successful VERIFY.

Required evidence:

- completed Slice/task IDs;
- verified revision;
- task-marker/checkpoint revision when distinct from the verified revision;
- required VERIFY/gate evidence and result;
- remaining work or handoff target;
- current/expected routing.

This is completion-boundary observability, not RED/GREEN/refactor/test-trigger/compatibility-correction progress or live progress state.

## `MERGE_RESULT`

Use for Executor merge success or action-defined merge blocker result.

Required evidence:

- common workflow envelope;
- PR identity;
- exact head revision evaluated for merge;
- merge commit when a merge succeeded;
- merge result and bounded gate/precondition evidence;
- resulting durable state and next action/owner.

When `MERGE_RESULT` directly represents the covered PR-merge lifecycle boundary, it is also the required lifecycle journal record for that same boundary.

## `HANDOFF`

Use only after a cross-role routing ownership transfer succeeds and the target routing is observed.

Required evidence:

- `From`: source role/action;
- `To`: target role/action;
- triggering result and revision evidence already persisted before ownership transfer;
- fresh-read source routing immediately before the routing mutation;
- routing mutation outcome;
- observed target routing after successful mutation;
- next owner/action.

A result message alone is not a handoff. `HANDOFF` is reconstructable evidence for the completed cross-role ownership boundary; the routing tuple remains canonical workflow state. Under the machine-gated worker/application split, the repository application boundary—not the model worker—owns the routing mutation, target observation, and durable `HANDOFF` write after fresh reauthorization. The completed cross-role handoff is wake-terminal for the source scheduled wake; the observed target routing remains current for a later scheduled wake to reconstruct and dispatch.

Same-role action transitions MUST NOT emit a synthetic `HANDOFF` or a new action-transition message. The source `ACTION_RESULT` or other action-defined result evidence, successful repository-owned routing mutation on the same coordination Issue, and subsequent fresh executable dispatch are sufficient durable evidence for that same-role boundary. If the resulting dispatch selects another same-role action immediately, it receives a fresh mapped model invocation in the same scheduled wake rather than continuing the prior worker context.

## `HUMAN_DECISION_REQUIRED`

Lead-only durable escalation for a decision that genuinely requires Human authority or intent and cannot be resolved from current approved contract and durable evidence.

Required evidence:

- common workflow envelope;
- the unresolved decision/question;
- at most three actionable options;
- material impact for each material option;
- risk/trade-off;
- Lead recommendation;
- explicit requested Human response and what workflow boundary it resolves.

This is the only canonical workflow message eligible for Human-facing scheduled delivery. Actual notification/associated-conversation surfacing remains external product configuration.

## `EXECUTION_EXCEPTION`

Use for a catchable tool/runtime/execution failure while the current invocation still has execution opportunity to persist durable evidence.

Required evidence:

- common workflow envelope;
- selected role/action;
- attempted operation/tool;
- relevant revision/base when applicable;
- whether any durable mutation is known to have completed before the failure;
- unfinished work boundary needed for reconstruction;
- raw observable error exactly as returned to the Agent after existing platform safety redaction;
- separate classification when evidence supports one, otherwise `UNCLASSIFIED_EXECUTION_EXCEPTION` is allowed;
- separate disposition/current recovery decision when known.

The raw observable error must not be replaced by a paraphrase or classification-only summary. This message is durable evidence, not an action result, routing transition, retry authorization, or lifecycle transition by default.

Canonical typed messages that directly represent a covered lifecycle boundary satisfy that boundary's one required journal record. Do not add a second generic lifecycle journal or recursive meta-comment merely to restate the same event.
