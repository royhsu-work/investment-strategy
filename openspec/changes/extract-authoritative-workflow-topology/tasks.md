# Tasks

Traceability baseline: Explore `issuecomment-5363202052` → proposal → `scheduled-agent-workflow` requirement → design decisions → slices below.

## Slice 1 — Establish authoritative topology surface

- [ ] RED: add focused tests proving current end-to-end topology has one expected owner and that `agents/workflow.md` must represent the existing legal action progression, correction loops, pre-Change Explore outcomes, and post-#115 terminal path.
- [ ] GREEN: add `agents/workflow.md` with the minimum authoritative normal-flow representation plus bounded correction/Explore-terminal/formal-terminal sections, preserving current behavior.
- [ ] REFACTOR: remove or convert duplicated global topology text in `agents/AGENTS.md` to references while retaining shared execution/cardinality/Human-authority/invocation/reconstruction invariants there.
- [ ] VERIFY: run focused tests, full regression suite, type checks, lint/format checks, and strict OpenSpec validation; persist the verified Slice checkpoint.

## Slice 2 — Normalize role, Skill, and README references

- [ ] RED: add regressions that detect competing normative global topology restatements in README, role files, and mapped Skills while allowing necessary action-local predecessor/successor references.
- [ ] GREEN: update README orientation and directly affected role/Skill references so they point to `agents/workflow.md` for global topology and retain only their independently owned local meaning.
- [ ] REFACTOR: remove synchronization-by-convention wording/copies without deleting role authority or action-local executable procedure.
- [ ] VERIFY: run focused tests, full regression suite, type checks, lint/format checks, and strict OpenSpec validation; persist the verified Slice checkpoint.

## Slice 3 — Prove behavioral equivalence and ownership boundaries

- [ ] RED: add executable/structural regressions covering current legal transitions, same-role versus cross-role boundaries, correction loops, independent review/merge separation, and the Archive merge → open `Lead / finalize-archive` → `LIFECYCLE_COMPLETE` → close/re-observe terminal path.
- [ ] GREEN: make only the minimum governance/reference corrections required for all ownership and behavioral-equivalence regressions to pass.
- [ ] REFACTOR: ensure canonical OpenSpec remains requirement/acceptance authority and `agents/workflow.md` remains runtime topology authority without introducing a generated registry, hidden state, or second workflow engine.
- [ ] VERIFY: run focused tests, full regression suite, type checks, lint/format checks, and strict OpenSpec validation; persist the verified Slice checkpoint.

## Completion

- [ ] Confirm every material boundary in Explore `issuecomment-5363202052` is represented and no new Human-reserved commitment was introduced.
- [ ] Confirm no role/action, dispatch/cardinality rule, queue ordering, Human-authority predicate, review/merge gate, Invocation Exit rule, archive mechanic, or terminal ordering changed unintentionally.
- [ ] Confirm all applicable required separate-follow-up obligations have durable trackers; none are introduced by this Change.
- [ ] Run final Python quality gates and exact-head strict OpenSpec validation before `READY`.