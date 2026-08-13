# Canonical Workflow Messages

This file is the single shared Markdown presentation contract for recurring durable Scheduled Agent workflow messages. It defines presentation/evidence shape only and does not redefine routing, authorization, termination, review, merge, lifecycle, result-enum, or exception semantics owned by `agents/AGENTS.md`, role files, and action skills.

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

`ACTION_RESULT` does not create result enums; the owning action contract defines them.

## `REVIEW_RESULT`

Use for `review-openspec`, `review-implementation`, and `review-archive`.

Required evidence:

- common workflow envelope;
- exact reviewed revision;
- gate evidence used for the independent review;
- `PASS` or action-defined findings, with findings identified when present;
- expected next owner or correction owner.

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

## `MERGE_AUTHORIZATION`

Use for Lead exact-revision merge authorization.

Required evidence:

- common workflow envelope;
- PR identity and authorized revision;
- applicable Reviewer/gate evidence;
- merge preconditions that must remain current;
- authorization scope and expected Executor owner.

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

Use only after a routing ownership transfer succeeds and the target routing is observed.

Required evidence:

- `From`: source role/action;
- `To`: target role/action;
- triggering result and revision evidence already persisted before ownership transfer;
- fresh-read source routing immediately before the routing mutation;
- routing mutation outcome;
- observed target routing after successful mutation;
- next owner/action.

A result message alone is not a handoff. `HANDOFF` is reconstructable evidence for the completed routing boundary; the routing tuple remains canonical workflow state.

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
