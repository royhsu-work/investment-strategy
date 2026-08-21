# Tasks

## Slice 1 — Shared/canonical async-wait proof rejects observation-count sufficiency

- [ ] 1.1 RED: add executable regression cases showing that first and repeated absent/queued/in-progress observations cannot authorize async-wait Exit while another legal same-resource observation remains executable, including a PR #129-style short-run terminal-success/failure sequence.
- [ ] 1.2 GREEN: update the shared Invocation Exit/exact-resource implementation contract and canonical `scheduled-agent-workflow` behavior so ordinary async-wait Exit requires independent current execution-opportunity exhaustion rather than observation count or absence of unrelated work.
- [ ] 1.3 REFACTOR: keep async-wait, stale/precondition, and hard execution-boundary classification distinct; remove superseded #124 sufficiency wording without adding a timer/counter/waiter abstraction.
- [ ] 1.4 VERIFY: run focused Invocation Exit regressions plus full repository Python quality and strict OpenSpec validation for the exact revision.

Trace: proposal `Why`/`What changes` → modified `Selected actions are work-conserving within the fixed invocation role` scenarios → design Decisions 1–4/6.

## Slice 2 — Trigger-and-consume Skills consume the corrected shared proof boundary

- [ ] 2.1 RED: add structural/executable regression coverage that fails while `implementation/SKILL.md` or `openspec-change/SKILL.md` treats a later nonterminal observation as sufficient async-wait proof.
- [ ] 2.2 GREEN: modify `agents/skills/implementation/SKILL.md` exact required-run observation procedure to continue bounded same-resource observation while another legal observation remains executable and to defer decisive Exit classification to shared positive-proof semantics.
- [ ] 2.3 GREEN: modify `agents/skills/openspec-change/SKILL.md` exact validation-run observation procedure with the same responsibility-preserving correction.
- [ ] 2.4 REFACTOR: keep both Skills action-local and concise; do not duplicate the shared Exit taxonomy or introduce a new reusable abstraction without demonstrated reuse beyond the existing shared owner.
- [ ] 2.5 VERIFY: run Skill/governance regressions, full repository Python quality, and strict OpenSpec validation for the exact revision; confirm the approved Skill maintenance traceability declaration remains accurate.

Trace: proposal `Skill maintenance traceability`/scope → modified requirement exact-resource scenarios → design Decision 5.

## Final verification

- [ ] 3.1 Verify repeated nonterminal observations followed by terminal success and terminal actionable failure are consumed in the same invocation when another legal observation remained executable.
- [ ] 3.2 Verify explicit invocation-local inability to perform another legal same-resource observation can prove ordinary async-wait Exit while current routing/revision/preconditions remain valid.
- [ ] 3.3 Verify stale/precondition and hard execution-boundary cases still use their existing distinct Exit classes.
- [ ] 3.4 Verify no durable timer, observation/polling/retry counter, heartbeat, lease, hidden waiter, scheduler state, new workflow action, or second DAG was introduced.
- [ ] 3.5 Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src tests`, and strict `openspec validate --all --strict --json --no-interactive` through repository-supported exact-revision validation surfaces.

Trace: `openspec/config.yaml` task/validation rules + design Decisions 1–6.
