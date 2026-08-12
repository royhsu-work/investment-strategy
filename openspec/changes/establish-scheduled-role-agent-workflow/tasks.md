# Tasks — establish-scheduled-role-agent-workflow

## 1. Shared governance and role authority

- [ ] 1.1 RED — Add repository validation tests/checks proving `agents/AGENTS.md` exists and defines default-branch governance loading, untrusted-work-input boundaries, one-item-per-run behavior, state reconstruction, at-least-once recovery, routing tuple validity, durable handoff ordering, and no-op/no-noise behavior. Trace: `scheduled-agent-workflow` governance/recovery requirements; design Decisions 1, 3, 5–6, 11.
- [ ] 1.2 RED — Add validation tests/checks proving `agents/roles/lead.md`, `reviewer.md`, and `executor.md` exist and encode the artifact-authority separation without overlap: Lead specification/lifecycle authority, Reviewer independent gates, Executor implementation/authorized operational mutations, and repository automation normal archive mechanics. Trace: role-authority requirement; design Decision 2.
- [ ] 1.3 GREEN — Implement `agents/AGENTS.md` and the three role definitions with explicit responsibilities, prohibitions, escalation boundaries, and default-branch trust rules.
- [ ] 1.4 REFACTOR — Remove duplicated shared rules from role files where they belong in `agents/AGENTS.md`; keep role files focused on authority/judgment boundaries and avoid custom inheritance such as `roles/base.md`.
- [ ] 1.5 VERIFY — Run focused governance validation plus repository lint/type/test gates applicable to the implemented validation mechanism.

## 2. Reusable skills and nine-action contract mapping

- [ ] 2.1 RED — Add validation tests/checks proving the nine normal actions map to the correct legal role and to a reduced reusable set of skills, with no unmapped normal action and no illegal cross-role action. Trace: nine-action requirement; design Decisions 1, 4.
- [ ] 2.2 RED — Add validation tests/checks proving the skill set covers OpenSpec authoring/question resolution, OpenSpec review, implementation, implementation review, archive review, and revision-bound merge operation without creating one skill per trivial transition or a parallel proposal/spec/design/tasks DAG.
- [ ] 2.3 GREEN — Implement the reusable `agents/skills/*` procedures and action-to-skill mapping/documentation for `propose-change`, `resolve-question`, `finalize-change`, `finalize-archive`, `review-openspec`, `review-implementation`, `review-archive`, `implement-change`, and `merge-pr`.
- [ ] 2.4 REFACTOR — Consolidate materially identical procedures, especially merge behavior, while keeping distinct review/finalize contracts where inputs and gates differ.
- [ ] 2.5 VERIFY — Run action/skill mapping validation and inspect that each action documents required reconstructed inputs, legal outcomes, authority boundaries, and handoff behavior.

## 3. Routing, concurrency, revision-bound gates, and crash recovery

- [ ] 3.1 RED — Add routing contract tests/checks for exactly one logical `(agent:<role>, action:<action>)` tuple, fail-closed zero/multiple/conflicting labels, unrelated-label preservation, and illegal role/action combinations. Trace: routing requirement; design Decisions 3, 6.
- [ ] 3.2 RED — Add concurrency/recovery contract tests/checks proving governance never describes `fresh-read routing → update labels` as mutex/CAS/single-flight; require action precondition reconstruction, idempotency where practical, and fail-closed stale/contradictory evidence handling.
- [ ] 3.3 RED — Add review/authorization contract tests/checks proving PASS and merge authorization are revision-bound, Reviewer PASS alone cannot authorize merge, changed PR head invalidates authorization, and contradictory current evidence cannot satisfy the merge gate.
- [ ] 3.4 RED — Add crash-recovery contract tests/checks for interrupted work before handoff, merge-success-before-handoff, and another run changing routing before the current run's handoff mutation.
- [ ] 3.5 GREEN — Encode these routing/concurrency/revision/recovery invariants in shared governance and relevant skills; where repository helper scripts are introduced, implement only deterministic validation/support logic and not a central workflow engine.
- [ ] 3.6 REFACTOR — Keep canonical workflow metadata minimal; do not add leases, heartbeats, retry counters, sequence numbers, hidden event serialization, progress percentages, or `status:in-progress`.
- [ ] 3.7 VERIFY — Run focused routing/concurrency/revision/recovery validations and review all unsafe mutation procedures for explicit fail-closed preconditions.

## 4. Persistent Issue lifecycle, multi-PR continuation, archive boundary, and Human admission

- [ ] 4.1 RED — Add contract tests/checks proving one coordination Issue persists across the normal lifecycle, `Change:` may begin unset but becomes immutable after selection, and normal clarification/review-correction transitions do not require child workflow Issues. Trace: persistent-Issue requirement; design Decision 3.
- [ ] 4.2 RED — Add lifecycle contract tests/checks proving merged-but-incomplete OpenSpec state produces `MORE_IMPLEMENTATION_REQUIRED → Executor / implement-change`, while archive waiting starts only after merged default-branch state is Complete/eligible under the existing README archive contract.
- [ ] 4.3 RED — Add archive-boundary checks proving scheduled roles do not define a competing normal `archive-change` mutation and instead observe the existing repository archive automation and Archive PR state.
- [ ] 4.4 RED — Add Human-admission checks proving unrouted repository activity is ignored; idle advisory admission requires both an unambiguous selected direction and `intake:approved`; scheduled roles are explicitly forbidden from adding/removing/restoring/manufacturing the reserved marker.
- [ ] 4.5 RED — Add idle-advisory checks proving at most one open `advisory:idle` Issue is permitted, recommendations are limited to three, advisory Issues have no routing tuple, and an undecided open advisory causes later Lead runs to no-op rather than create duplicate noise.
- [ ] 4.6 GREEN — Encode persistent-Issue, multi-PR, existing-archive-automation, Human-admission, and idle-advisory contracts in governance/roles/skills and any deterministic validation support.
- [ ] 4.7 REFACTOR — Keep `intake:approved` explicitly described as a governance capability boundary rather than cryptographic provenance; do not introduce autonomous workflow admission or scheduled archive-repair actions.
- [ ] 4.8 VERIFY — Run lifecycle/admission/advisory contract validations and cross-check behavior against the repository's existing README archive classifier/recovery rules.

## 5. Durable final closure, README alignment, and OpenSpec readiness

- [ ] 5.1 RED — Add lifecycle validation proving a completion comment, PASS, or “may be closed” decision is insufficient; final workflow completion requires Lead `finalize-archive` to reconstruct canonical archived default-branch state, perform the GitHub Issue close mutation, and observe the Issue closed. Trace: durable closure requirement; design Decision 10.
- [ ] 5.2 RED — Add crash-recovery coverage/checks for the case where final archive state is complete but the run terminates before Issue closure; the next Lead run must be required to perform the missing close idempotently.
- [ ] 5.3 GREEN — Update README development lifecycle/responsibility documentation to describe `Lead / Reviewer / Executor`, independent Reviewer gates, Executor-authorized merge execution, existing deterministic archive automation, multi-PR continuation, scheduled routing, and durable final Issue closure without changing investment-analysis contracts.
- [ ] 5.4 GREEN — Add any required repository label/bootstrap documentation or deterministic setup helper needed for `agent:*`, `action:*`, `advisory:idle`, and reserved `intake:approved`, while preserving the Human-only mutation contract for the reserved marker.
- [ ] 5.5 REFACTOR — Verify the implementation adds no central workflow engine, exactly-once machinery, autonomous intake, scheduled normal archive mutation, or unrelated Strategy/market-data/Decision/Backtest behavior.
- [ ] 5.6 VERIFY — Run all project tests/checks plus any governance validation added by this change; verify the default branch remains the only governance authority in examples/tests.
- [ ] 5.7 VERIFY — Run `openspec validate --all --strict --json --no-interactive`; confirm proposal → spec → design → tasks forward traceability and tasks → design → spec → proposal reverse traceability before requesting Reviewer `review-openspec`.
