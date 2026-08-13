# Change: Workflow-dynamic scheduled dispatch

## Why

The current Scheduled Tasks are externally assigned fixed roles, so handoff latency and wake ownership are coupled to three independent role schedules even though the repository already persists the legal role/action tuple. Exploration in #23 established that the repository can make durable workflow state authoritative for dispatch without adding a workflow engine, lock, lease, or new lifecycle.

Implementation experience on #21 and #25 also demonstrated an observability boundary: task markers and PR commits can prove a slice was completed, but without a bounded checkpoint on the persistent coordination Issue the workflow's progress is not reconstructable from its coordination journal alone.

## What Changes

- Add one default-branch `Scheduled-Dispatch-Mode` governance marker with `fixed-role` and `workflow-dynamic` values.
- In `workflow-dynamic` mode, make each wake reconstruct repository workflow state first and derive the invocation role/action from the single active workflow; the externally assigned legacy role becomes compatibility fallback only.
- Define `Change:` persistence as the activation boundary. At most one open coordination Issue with a persisted active Change may exist; additional `Lead / propose-change` Issues with `Change: unset` remain queued pre-activation work.
- Preserve one-role-per-invocation semantics: once dispatch selects a role, handoff does not redispatch inside that invocation.
- Preserve at-least-once safety through reconstruction, idempotency where practical, revision/precondition checks, first-valid-write-wins where applicable, and stale-run termination rather than mutex/claim/lease state.
- Add minimal orphan/unexplained durable-state handling through Lead diagnosis and decision-ready Human escalation.
- Bind Human-required workflow authority to GitHub actor `royhsu-work`; other actors remain evidence-only for Human-required decisions.
- Tighten Lead Human notifications and idle exploration: at most three decision-ready proposals, no repeated unanswered notification, and idle exploration considers relevant Issues created or materially active in the preceding 7 days.
- Define `human:notified` as analytics-only metadata and keep Scheduled Task conversation/result surfacing outside repository workflow state.
- Require `review-openspec` to inspect reverse traceability first (`tasks → design → specs → proposal`), then forward traceability (`proposal → specs → design → tasks`), while keeping PASS dependent on both directions against the same exact revision.
- Require each successfully verified implementation slice to persist both satisfied task markers and one bounded checkpoint comment on the persistent coordination Issue before the next slice or handoff, so completion boundaries remain reconstructable without introducing live progress state.
- Add a simplicity/proportionality constraint so hypothetical generality cannot justify a central dispatcher platform or fault state machine.

## Affected Capabilities

- `scheduled-agent-workflow` — modifies scheduled dispatch, workflow activation/admission, work selection, Reviewer OpenSpec inspection order, Executor verified-slice checkpoint observability, Human authority/notification, idle advisory, and repository governance exposure.

## Scope Boundaries

This change does not alter the nine OpenSpec lifecycle actions, role artifact authority, Reviewer independence, exact-revision gates, merge authorization, the meaning of task checkboxes as verified completion evidence, or repository-owned normal archive automation. It extends verified-slice persistence by requiring a bounded coordination-Issue checkpoint after successful VERIFY. That checkpoint is a completion-boundary journal, not heartbeat, progress percentage, `status:in-progress`, lock/claim/lease, retry counter, or other live runtime ownership state.

Reverse-first changes only the required `review-openspec` inspection order; it does not weaken or replace exact-revision bidirectional traceability. This change does not add multi-active workflow arbitration, global urgency scoring, locks/leases/heartbeats/claims, hidden in-progress state, a Human waiting state machine, or a separate dispatcher configuration subsystem.

External Scheduled Task cadence and associated-conversation/result UI are product configuration boundaries; repository behavior only defines the bootstrap contract those tasks consume.
