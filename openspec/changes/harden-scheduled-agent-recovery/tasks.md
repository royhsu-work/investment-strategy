# Tasks: Harden scheduled-agent recovery

## 1. Fresh reconstruction after external asynchronous waits

Trace: proposal `external wait stale evidence` → spec `External asynchronous waits are revalidated from the awaited resource` + modified `Scheduled execution is at-least-once and state reconstructable` → Design Decision 1.

- [ ] 1.1 RED: add contract tests proving a resumed wake must fresh-read the specifically awaited Actions/PR resource and cannot reuse an older `in_progress` coordination comment as current status.
- [ ] 1.2 GREEN: implement the minimum shared governance/role-skill wording needed to require awaited-resource fresh reads before another async-wait yield.
- [ ] 1.3 VERIFY: run focused tests, full regression suite, Ruff lint/format, mypy, and strict OpenSpec validation; confirm no polling/heartbeat/hidden waiting state was introduced.

## 2. Evidence-based retry and minimum durable fallback

Trace: proposal `unchanged rejected mutation + minimum durable evidence` → modified `Catchable execution exceptions are dispositioned before normal invocation exit` + modified `Scheduled execution is at-least-once and state reconstructable` → Design Decisions 2 and 4.

- [ ] 2.1 RED: add contract tests for unchanged denied/unsupported mutations, changed-precondition retry eligibility, different legal operation paths, and no-repository-write-surface reconstruction semantics.
- [ ] 2.2 GREEN: update shared governance/exception contracts so identical retries require materially changed fresh-read preconditions or a different legal repository operation; preserve canonical evidence when writable and never treat Scheduled Task output as durable workflow state.
- [ ] 2.3 VERIFY: run focused and full quality gates plus strict OpenSpec validation; confirm no retry counter/backoff/fault-state machine was introduced.

## 3. Constrained Executor branch integration recovery

Trace: proposal `restricted branch integration` → spec `Constrained branch integration preserves reviewed semantics and fail-closed gates` → Design Decision 3.

- [ ] 3.1 RED: add Executor contract tests for non-force reconciliation using fresh implementation/default-branch heads, tree/semantic preservation, new-head gate invalidation, and no-legal-mutation-path escalation.
- [ ] 3.2 GREEN: update Executor role/implementation procedure with the minimum constrained integration recovery sequence; keep semantics-changing conflicts outside Executor authority and route unresolved tool/authority boundaries to Lead diagnosis.
- [ ] 3.3 VERIFY: run focused and full quality gates plus strict OpenSpec validation; verify exact-head review/merge gates are unchanged and no force-update path is authorized.

## 4. PR Ready boundary before implementation review

Trace: proposal `Draft/Ready lifecycle mismatch` → spec `Implementation PR is Ready before implementation review handoff` → Design Decision 5.

- [ ] 4.1 RED: add contract tests proving `implement-change` cannot hand off a Draft PR to `review-implementation`, and that a failed Ready mutation follows exception/finalization handling.
- [ ] 4.2 GREEN: make Executor own the Draft-to-Ready transition immediately before implementation-review handoff; require fresh-read non-Draft state at the same current PR head.
- [ ] 4.3 VERIFY: run focused/full quality gates and strict OpenSpec validation; confirm no new routing/status label or workflow action was introduced.

## 5. Human escalation observability producer

Trace: #28 Human escalation observability addition → spec `Human escalation creates analytics-only notified observability` → Design Decision 6.

- [ ] 5.1 RED: add contract tests for idempotent `human:notified` ensure after durable `HUMAN_DECISION_REQUIRED`, label persistence after Human response, label-only non-wait semantics, and label-mutation failure handling.
- [ ] 5.2 GREEN: update Lead/shared Human-escalation governance so Lead ensures the analytics label after durable escalation without making it routing/waiting/authorization/resume state.
- [ ] 5.3 VERIFY: run focused/full quality gates and strict OpenSpec validation; confirm the label remains analytics-only and does not become a workflow-state dependency.

## 6. Final coherence and review readiness

Trace: proposal full intent → all scheduled-agent-workflow delta requirements → Design Decisions 1–6; engineering/governance verification also follows `openspec/config.yaml`.

- [ ] 6.1 Re-check required trace declarations/references across proposal, spec, design, and tasks; confirm #28 source incidents are covered without expanding into #29 documentation/SSOT scope.
- [ ] 6.2 Run repository-pinned strict OpenSpec validation for the exact final handoff revision and retain checkout-identity evidence satisfying the default-branch exact-revision contract.
- [ ] 6.3 Confirm the change remains single-purpose: constrained recovery/reconstruction only; no retry engine, lock/lease/heartbeat, hidden state, global supervisor, new normal action, Reviewer-independence change, or gate weakening.
