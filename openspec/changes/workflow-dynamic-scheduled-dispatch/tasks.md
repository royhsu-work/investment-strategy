# Tasks

## 1. Dispatch mode and workflow-first role selection

- [x] 1.1 RED: add behavioral tests for the authoritative `Scheduled-Dispatch-Mode` marker, fixed-role compatibility, workflow-dynamic active-workflow selection, invalid/multiple-active fail-closed behavior, and immutable invocation role; verify failures are caused by missing target behavior.
- [x] 1.2 GREEN: implement the minimum default-branch governance/dispatcher behavior that parses the single marker and derives role/action/skill from the one active workflow without global urgency scoring or a second DAG.
- [x] 1.3 REFACTOR/VERIFY: keep bootstrap logic thin; run slice tests, full regression suite, type checks, and lint checks.

Trace: proposal dispatch mode + thin dispatcher → specs `Default-branch governance declares the scheduled dispatch mode`, `Workflow-dynamic dispatch derives one fixed invocation role`, modified `Each scheduled run processes...` → design Decisions 1-2.

## 2. Single-active activation and concurrent wake safety

- [x] 2.1 RED: add tests for `Change: unset` queued proposals, persisted Change activation, oldest-created/lower-number activation order, refusal to activate while another Change is active, and overlapping/stale activation attempts; verify target-behavior RED failures.
- [x] 2.2 GREEN: implement the minimum single-active admission/activation behavior using durable reconstruction and first-valid-write-wins/precondition checks where applicable, without lock/claim/lease/heartbeat/in-progress state.
- [x] 2.3 REFACTOR/VERIFY: confirm existing at-least-once action safety remains intact; run slice tests, full regression suite, type checks, and lint checks.

Trace: proposal activation/concurrency → specs `Persisted Change identity defines...`, `Dynamic dispatch tolerates...`, modified Human admission → design Decisions 3-4.

## 3. Orphan guard and Human authority/escalation

- [x] 3.1 RED: add tests for unexplained durable workflow evidence blocking new activation, Human-required evidence accepted only from `royhsu-work`, non-Human evidence remaining non-authoritative, `human:notified` having no routing/authorization effect, and duplicate unanswered escalation suppression.
- [x] 3.2 GREEN: implement the minimum Lead diagnosis/escalation and actor-bound Human evidence checks required by the specs; do not add a generic fault classifier or Human waiting state machine.
- [x] 3.3 REFACTOR/VERIFY: ensure Human-facing escalation is decision-ready with at most three options, impact/trade-off, and recommendation; run slice tests, full regression suite, type checks, and lint checks.

Trace: proposal orphan/Human contract → specs `Unexplained durable workflow evidence...`, `Human-required authority...`, `Lead Human-facing escalation...` → design Decisions 5-6.

## 4. Verified-slice coordination checkpoint

- [ ] 4.1 RED: add contract/regression coverage proving a successfully verified Executor slice requires both satisfied task markers and one bounded persistent-coordination-Issue checkpoint before another slice or handoff; cover reconstruction where markers are durable but the checkpoint write was interrupted.
- [ ] 4.2 GREEN: update shared governance and `Executor / implement-change` skill guidance so each verified slice checkpoint records completed slice/task IDs, durable checkpoint or verified revision, VERIFY/gate result, and remaining work or handoff; preserve PR/CI/task evidence as their own sources of truth.
- [ ] 4.3 REFACTOR/VERIFY: confirm checkpoint journaling occurs only at verified completion boundaries and introduces no heartbeat, progress percentage, `status:in-progress`, lock/claim/lease, retry counter, or other live runtime state; run slice tests, full regression suite, type checks, and lint checks.

Trace: proposal verified-slice observability → spec `Verified implementation slices persist a bounded coordination-Issue checkpoint` and repository-artifact bootstrap boundary → design Decision 10.

## 5. Durable mutation journal and native-close terminal handoff

- [ ] 5.1 RED: add contract/regression coverage proving substantive Scheduled Agent durable mutations require one bounded persistent-coordination-Issue journal record; cover mutation-success/journal-interruption recovery without repeating the mutation, and prove the journal comment itself does not recursively require a meta-comment.
- [ ] 5.2 RED: add lifecycle/dispatcher coverage for final Archive PR native close: after authorized archive merge, Executor observes the closed Issue, replaces consumed routing with `agent:lead + action:finalize-archive`, journals the merge/native-close/handoff, and ends without role switching; cover interrupted post-merge handoff recovery without duplicate merge.
- [ ] 5.3 RED: add selection/finalization coverage proving `closed + Lead / finalize-archive` is eligible only while matching authorized merged-archive/native-close evidence exists and no valid Lead `LIFECYCLE_COMPLETE` result exists; prove terminal-pending work blocks queued activation and completed terminal history does not.
- [ ] 5.4 GREEN: update shared governance, dispatcher/action skills, and lifecycle documentation to implement the bounded mutation journal, closed terminal-reconstruction exception, Executor post-merge terminal handoff, and Lead bounded `LIFECYCLE_COMPLETE` evidence without adding a completion/status label or reopening normally natively closed Issues.
- [ ] 5.5 REFACTOR/VERIFY: confirm canonical completion still requires authorized Archive PR merge + correct archived default-branch state + observed closed Issue, while the Lead result comment is durable execution evidence only; confirm no new lifecycle action, heartbeat/progress/in-progress state, lock/claim/lease, or generic terminal state machine was introduced; run slice tests, full regression suite, type checks, and lint checks.

Trace: proposal mutation journal + native-close terminal ownership → specs `Substantive durable workflow mutations are journaled...`, `Native Archive close hands off to terminal Lead reconstruction`, modified active-workflow/work-selection requirements → design Decisions 3, 11-12.

## 6. Idle advisory, Reviewer order, documentation, and migration contract

- [ ] 6.1 RED: add tests/contract checks for the seven-day relevant-Issue advisory lens, bounded/no-duplicate advisory behavior, required reverse-first `review-openspec` inspection followed by forward inspection with unchanged exact-revision bidirectional PASS semantics, bootstrap-only Scheduled Task contract, and simplicity/proportionality constraints where mechanically testable.
- [ ] 6.2 GREEN: update repository governance/docs/role-skill guidance needed for workflow-dynamic mode and for Reviewer reverse-first `review-openspec` inspection; switch the canonical dispatch marker only with the completed compatible behavior; document the external migration plan retaining the existing three wake slots while keeping exact slot count/topology/cadence outside repository capability/runtime state, and document the common external bootstrap-prompt contract.
- [ ] 6.3 REFACTOR/VERIFY: confirm reverse-first changes inspection order only and does not weaken bidirectional traceability; confirm the retained three-slot topology remains an external migration/product-configuration constraint rather than repository workflow state; confirm no global priority table, multi-active arbitration, fault platform, lock/lease/claim state, or duplicate OpenSpec DAG was introduced; run slice tests, full regression suite, type checks, and lint checks.

Trace: behavior/product portions of section 6 trace from proposal idle/reviewer-order/simplicity intent → specs idle, `OpenSpec review uses reverse-first inspection while retaining the bidirectional gate`, repository artifacts, and proportionality requirements → design Decisions 7-9. The exact three-wake-slot preservation is a migration/governance verification traced to proposal scope + design `Scheduled Task migration` + the `openspec/config.yaml` allowance for Engineering/Governance tasks; it is intentionally not a repository capability requirement.

## 7. OpenSpec completion gate

- [ ] 7.1 Verify reverse traceability first `tasks → design → specs → proposal`, then verify forward traceability `proposal → specs → design → tasks`; resolve any orphan requirement/task. This inspection order does not replace the requirement that both directions pass for the same exact revision.
- [ ] 7.2 Run repository-pinned `openspec validate --all --strict --json --no-interactive` against the exact final change revision and preserve exact-checkout validation evidence.
- [ ] 7.3 Confirm proposal/spec/design/tasks remain single-purpose and consistent with `README.md`, `openspec/config.yaml`, the authoritative Human updates on #25, and the accepted #23 scope before requesting independent OpenSpec review.
