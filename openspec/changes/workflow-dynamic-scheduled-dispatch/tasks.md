# Tasks

## 1. Dispatch mode and workflow-first role selection

- [ ] 1.1 RED: add behavioral tests for the authoritative `Scheduled-Dispatch-Mode` marker, fixed-role compatibility, workflow-dynamic active-workflow selection, invalid/multiple-active fail-closed behavior, and immutable invocation role; verify failures are caused by missing target behavior.
- [ ] 1.2 GREEN: implement the minimum default-branch governance/dispatcher behavior that parses the single marker and derives role/action/skill from the one active workflow without global urgency scoring or a second DAG.
- [ ] 1.3 REFACTOR/VERIFY: keep bootstrap logic thin; run slice tests, full regression suite, type checks, and lint checks.

Trace: proposal dispatch mode + thin dispatcher → specs `Default-branch governance declares the scheduled dispatch mode`, `Workflow-dynamic dispatch derives one fixed invocation role`, modified `Each scheduled run processes...` → design Decisions 1-2.

## 2. Single-active activation and concurrent wake safety

- [ ] 2.1 RED: add tests for `Change: unset` queued proposals, persisted Change activation, oldest-created/lower-number activation order, refusal to activate while another Change is active, and overlapping/stale activation attempts; verify target-behavior RED failures.
- [ ] 2.2 GREEN: implement the minimum single-active admission/activation behavior using durable reconstruction and first-valid-write-wins/precondition checks where applicable, without lock/claim/lease/heartbeat/in-progress state.
- [ ] 2.3 REFACTOR/VERIFY: confirm existing at-least-once action safety remains intact; run slice tests, full regression suite, type checks, and lint checks.

Trace: proposal activation/concurrency → specs `Persisted Change identity defines...`, `Dynamic dispatch tolerates...`, modified Human admission → design Decisions 3-4.

## 3. Orphan guard and Human authority/escalation

- [ ] 3.1 RED: add tests for unexplained durable workflow evidence blocking new activation, Human-required evidence accepted only from `royhsu-work`, non-Human evidence remaining non-authoritative, `human:notified` having no routing/authorization effect, and duplicate unanswered escalation suppression.
- [ ] 3.2 GREEN: implement the minimum Lead diagnosis/escalation and actor-bound Human evidence checks required by the specs; do not add a generic fault classifier or Human waiting state machine.
- [ ] 3.3 REFACTOR/VERIFY: ensure Human-facing escalation is decision-ready with at most three options, impact/trade-off, and recommendation; run slice tests, full regression suite, type checks, and lint checks.

Trace: proposal orphan/Human contract → specs `Unexplained durable workflow evidence...`, `Human-required authority...`, `Lead Human-facing escalation...` → design Decisions 5-6.

## 4. Idle advisory, documentation, and migration contract

- [ ] 4.1 RED: add tests/contract checks for the seven-day relevant-Issue advisory lens, bounded/no-duplicate advisory behavior, bootstrap-only Scheduled Task contract, and simplicity/proportionality constraints where mechanically testable.
- [ ] 4.2 GREEN: update repository governance/docs/role-skill guidance needed for workflow-dynamic mode and switch the canonical dispatch marker only with the completed compatible behavior; preserve the three external wake slots and document the external prompt migration contract without treating product conversation/result state as repository state.
- [ ] 4.3 REFACTOR/VERIFY: confirm no new lifecycle action, global priority table, multi-active arbitration, fault platform, lock/lease/claim state, or duplicate OpenSpec DAG was introduced; run slice tests, full regression suite, type checks, and lint checks.

Trace: proposal idle/product/simplicity boundaries → specs idle, repository artifacts, and proportionality requirements → design Decisions 7-8 and Scheduled Task migration.

## 5. OpenSpec completion gate

- [ ] 5.1 Verify forward traceability `proposal → specs → design → tasks` and reverse traceability `tasks → design → specs → proposal`; resolve any orphan requirement/task.
- [ ] 5.2 Run repository-pinned `openspec validate --all --strict --json --no-interactive` against the exact final change revision and preserve exact-checkout validation evidence.
- [ ] 5.3 Confirm proposal/spec/design/tasks remain single-purpose and consistent with `README.md`, `openspec/config.yaml`, and the accepted #23 scope before requesting independent OpenSpec review.
