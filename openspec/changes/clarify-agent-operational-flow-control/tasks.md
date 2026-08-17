# Tasks

## Slice 1 — Active WIP and execution-eligibility reconstruction

- [x] RED: add focused regressions proving a formal active workflow remains the winner while its next action waits for required durable evidence, and proving incomplete active-workflow enumeration cannot fall through to pre-activation queue work. Trace: proposal `What Changes`; requirements `Operational execution eligibility remains orthogonal to lifecycle state` and `Active-workflow cardinality and Issue-state coherence precede queue selection`; design Decisions 1–3.
- [x] GREEN: make the minimum shared-governance/dispatcher contract changes needed to express formal WIP=1, finish-first scheduling, blocker-as-derived evidence, and cardinality-before-queue reconstruction without a global blocked state/label/result. Trace: design Decisions 1–3.
- [x] REFACTOR/VERIFY: keep Human/async/execution-exception reasons owned by their existing contracts; run focused tests, full pytest, Ruff, mypy, and strict OpenSpec validation. Trace: `openspec/config.yaml` task rules.

## Slice 2 — Issue-state coherence and bounded premature-close recovery

- [x] RED: add regression coverage for the #40 failure class where a closed coordination Issue carries nonterminal formal routing. Prove the stale routed action is not executable while closed; the existing terminal-pending `Lead / finalize-archive` closed shape remains the only normal closed actionable shape; one unambiguous unfinished premature-close candidate blocks pre-activation and selects bounded `Lead / resolve-question` recovery; and ambiguous/Human-terminated/multiple-candidate cases remain fail closed. Trace: requirement `Active-workflow cardinality and Issue-state coherence precede queue selection`; design Decision 3.
- [x] GREEN: implement the smallest reconstruction/recovery contract that (a) recognizes only the demonstrated closed-nonterminal formal-workflow predicate, (b) assigns its bounded diagnosis/reopen owner to `Lead / resolve-question`, (c) reopens only when durable unfinished-lifecycle, nonterminal routing, no-terminal-completion, no qualifying Human termination, and repository-wide uniqueness/cardinality preconditions all hold, and (d) preserves Change/routing then forces a fresh reconstruction before any later wake resumes the normal routed action. Do not add a generic workflow fault/recovery state. Trace: design Decision 3.
- [x] REFACTOR/VERIFY: reuse existing routing, Human-authority, terminal-pending, diagnosis, and same-Issue lifecycle evidence rather than adding recovery registries/tokens; prove the recovery invocation itself does not execute the preserved stale normal action; run focused/full quality gates plus strict OpenSpec validation. Trace: `openspec/config.yaml` task rules.

## Slice 3 — Required deferred follow-up becomes runnable pre-activation work

- [x] RED: add regressions proving an explicit approved required-separate defer decision creates/reuses one source-linked `Change: unset + Lead / explore-change` tracker, while optional/non-goal/deferred prose does not create workflow admission. Trace: requirement `Required separate follow-up is directly queueable for fresh Explore revalidation`; design Decision 4.
- [x] GREEN: update the Lead-owned defer-tracking path to materialize/reuse and route the required tracker idempotently into the existing combined pre-activation queue; do not create another backlog/status vocabulary. Trace: design Decision 4.
- [x] REFACTOR/VERIFY: deduplicate the later idle-discovery/re-admission handling that becomes unnecessary for newly created required trackers while preserving reconstruction of historical trackers; run focused/full quality gates and strict OpenSpec validation. Trace: `openspec/config.yaml` task rules.

## Slice 4 — Pre-activation Propose fallback to Explore

- [x] RED: add regressions for valid `Change: unset + Lead / propose-change` intake that is not proposal-ready, proving same-Issue fallback to Explore is legal without a second Human admission and proving a non-`unset` Change cannot take that backward path. Trace: requirement `Pre-activation Propose may conservatively fall back to Explore`; design Decision 5.
- [x] GREEN: implement the minimum Lead/Propose/Explore contract changes for `propose-change → explore-change → PROPOSAL_READY → propose-change` inside one authority envelope, using existing same-role continuation and no synthetic `HANDOFF`. Trace: design Decision 5.
- [x] REFACTOR/VERIFY: prevent ordinary loops and keep formal post-activation ambiguity on `resolve-question`; run focused/full quality gates and strict OpenSpec validation. Trace: `openspec/config.yaml` task rules.

## Slice 5 — Derived flow visualization boundary

- [x] RED: add or extend a governance regression proving Project/Kanban status cannot substitute for repository routing/identity/gate authority. Trace: requirement `Flow visualization is derived and non-authoritative`; design Decision 6.
- [x] GREEN: add only the minimum non-normative orientation needed to make the projection boundary explicit; do not create Project-backed dispatch state or KPI machinery. Trace: design Decision 6.
- [x] REFACTOR/VERIFY: confirm no new lifecycle state, blocker enum, priority engine, lease/heartbeat, hidden backlog, generic recovery state, or merge-authorization redesign entered the Change; run focused/full quality gates and strict OpenSpec validation. Trace: `openspec/config.yaml` task rules.

## Final verification

- [ ] Verify proposal/spec/design/task traces are mechanically consistent and every approved requirement has an implementation slice.
- [ ] Run strict OpenSpec validation and repository quality gates on the exact implementation revision before completion handoff.
