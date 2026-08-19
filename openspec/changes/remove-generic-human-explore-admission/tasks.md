# Tasks

## Slice 1 — Routed Formal Explore is queue-eligible without generic Human approval

Trace: proposal `What Changes` items 1–2; design Decisions 1 and 5; `scheduled-agent-workflow` queue/active-workflow requirements.

- [ ] **RED:** Add dispatcher/governance regressions proving an open `Change: unset + agent:lead + action:explore-change` Issue is pre-activation eligible without `human:approved`, for both connector-created and directly Human-created intake, while active/terminal-pending work still wins and `created_at` then Issue number remains deterministic.
- [ ] Run the focused RED tests and verify failures are caused by the current Human-admission eligibility requirement rather than fixture/setup errors.
- [ ] **GREEN:** Update shared governance, Lead/Explore procedure wording, and any workflow reconstruction helpers so ordinary routed Explore eligibility no longer consumes Human admission/origin classification; keep direct Propose Human admission and WIP/order semantics unchanged.
- [ ] **REFACTOR:** Remove duplicated origin-specific dispatcher wording while retaining producer/source provenance where it constrains creation/scope.
- [ ] **VERIFY:** Run focused workflow tests, full regression suite, Ruff, Mypy, and strict OpenSpec validation; persist satisfied Slice 1 task markers only after VERIFY succeeds.

## Slice 2 — Remove obsolete Explore-only Human authority machinery

Trace: proposal `What Changes` items 4–6; design Decision 3; `scheduled-agent-workflow` Human-authority requirement.

- [ ] **RED:** Add/update Human-authority regressions proving Explore admission no longer needs an Explore decision ref or creation-bound Issue shortcut, while direct Propose, advisory admission, and canonical `HUMAN_DECISION_REQUIRED` responses still require provenance-bound Human approval and reject GitHub-App/Connector provenance.
- [ ] Run the focused RED tests and verify failures specifically expose the obsolete Explore-admission API/contracts.
- [ ] **GREEN:** Remove Explore-only Human decision boundary/mapping, creation-bound Explore constants/adapters/predicates/composition, and unused README Human-created Explore ceremony; preserve the general raw comment/event provenance evaluator and all remaining Human-only consumers.
- [ ] **REFACTOR:** Remove dead imports/tests/helpers created solely for #88 and keep the remaining Human-authority API minimal and explicit.
- [ ] **VERIFY:** Run focused Human-authority tests, full regression suite, Ruff, Mypy, and strict OpenSpec validation; persist satisfied Slice 2 task markers only after VERIFY succeeds.

## Slice 3 — Preserve bounded creation and Human commitment boundaries through Explore→Propose

Trace: proposal `What Changes` items 3, 5, 7; design Decisions 2 and 4; `scheduled-agent-workflow` workflow-admission requirement.

- [ ] **RED:** Add governance/flow regressions proving Scheduled Agents still cannot create arbitrary routed Explore work; idle discovery and required-separate-follow-up producers remain independently bounded/deduplicated; a valid in-scope `PROPOSAL_READY` continues automatically; and a new Human-reserved product/scope/risk/security/privacy/cost/operational commitment still stops with `HUMAN_DECISION_REQUIRED`.
- [ ] Run the focused RED tests and verify failures correspond to the changed admission/continuation semantics.
- [ ] **GREEN:** Update governance/role/skill/spec wording so creation authority remains producer-owned while dispatcher Explore eligibility is origin-neutral; preserve direct-Propose authority and Human escalation/resume semantics.
- [ ] **REFACTOR:** Remove stale #88 compatibility wording and any redundant Explore-origin taxonomy that no longer controls execution eligibility, without deleting source-linkage/materiality rules still needed by producers.
- [ ] **VERIFY:** Run focused flow/governance tests, full regression suite, Ruff, Mypy, and strict OpenSpec validation; persist satisfied Slice 3 task markers only after VERIFY succeeds.

## Completion

- [ ] Confirm proposal → specs → design → tasks trace declarations are mechanically consistent and reverse traceability is reconstructable.
- [ ] Confirm no implementation/PR uses Issue-closing linkage before the final Archive PR.
- [ ] Obtain strict OpenSpec validation for the exact proposal handoff revision and record the checkout identity evidence.
- [ ] Hand the exact semantic revision to `Reviewer / review-openspec`; do not claim the independent semantic PASS as Lead.
