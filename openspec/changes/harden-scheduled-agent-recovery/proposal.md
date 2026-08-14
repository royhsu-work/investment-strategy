# Change: Harden scheduled-agent recovery under constrained execution

## Why

Issue #28 records several failures observed while #25 was executed under constrained GitHub tooling and scheduled wakes. The existing workflow already has at-least-once reconstruction, work-conserving execution, canonical exception evidence, and bounded Lead diagnosis, but the incidents exposed remaining gaps at the boundaries between those contracts:

- an Executor may encounter a recoverable branch-integration problem yet lack ordinary local git merge/rebase tooling;
- a catchable denied/unsupported mutation can leave the action with no legal same-role path unless the failure is explicitly dispositioned and handed to Lead;
- repeated retries of an unchanged rejected mutation can waste a wake without changing durable state;
- a later wake can incorrectly reuse stale `in_progress`/waiting evidence instead of fresh-reading the specific awaited Actions/PR resource;
- implementation lifecycle can reach review/finalization while the PR is still Draft;
- a durable Human escalation can exist without the analytics-only `human:notified` observability marker even though governance defines how that marker must not be interpreted.

These are one resilience problem: scheduled actions must converge from current durable reality after constrained execution failures without weakening revision-bound gates or inventing hidden workflow state.

## What Changes

- Require every wake resuming an external asynchronous wait to fresh-read the specific awaited durable resource before concluding that the wait still exists. Historical waiting/progress evidence cannot by itself justify another yield.
- Tighten catchable failure disposition so an unchanged denied/unsupported mutation is not retried repeatedly without a materially changed precondition or a different repository-governed operation path; otherwise the action preserves evidence and hands bounded unresolved diagnosis to Lead.
- Define minimum durable recovery evidence for partial workflow-operation failure using the existing canonical `EXECUTION_EXCEPTION` / action result / handoff surfaces. If no repository surface is writable, the run must not pretend durable workflow state changed; later wakes reconstruct from actual repository state.
- Define constrained Executor branch-integration recovery as a non-force, precondition-checked implementation correction that preserves the approved implementation tree/semantics and exact-head gate model. If no legal repository mutation surface can perform the correction, Executor must stop retrying and hand bounded diagnosis to Lead rather than weakening review or merge gates.
- Make PR Ready state part of the implementation-to-review boundary: before `Executor / implement-change` hands implementation to `Reviewer / review-implementation`, the current implementation PR must be non-Draft; inability to perform that transition is handled as an execution failure rather than allowing later merge authorization to contradict PR presentation state.
- After durable `HUMAN_DECISION_REQUIRED` evidence is recorded, require Lead to idempotently ensure the analytics-only `human:notified` label. The label remains historical observability metadata only and never becomes routing, waiting, authorization, resume, or Human-response state.

## Affected Capabilities

- `scheduled-agent-workflow`: MODIFY existing reconstruction / exception disposition / implementation-review lifecycle behavior and ADD explicit async-wait resume, constrained branch-integration, PR Ready, and Human-escalation observability requirements.

## Scope Boundaries

This change does **not** add a retry engine, retry counter, backoff state machine, lock/lease/heartbeat, hidden waiting state, generic fault classifier, new workflow action, global supervisor, or second workflow DAG. It does not relax Reviewer independence, exact-revision validation, exact-head merge authorization, or the single-active workflow boundary.

The external Scheduled Task conversation/result remains non-authoritative product output. If repository evidence cannot be persisted, later workflow correctness still comes only from durable repository reconstruction.

## Relationship

- Persistent coordination Issue: #28.
- Source incidents/evidence: #25 / PR #26 / Archive PR #33 and the additional Human-authored #28 incident comments.
- Follow-up Issue #29 may later reorganize documentation ownership/SSOT; this change only places each new rule at the current narrowest correct governance/action layer and does not perform that broader documentation refactor.
