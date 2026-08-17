# Tasks: Consolidate PR merge lifecycle

## Slice 1 — Implementation PASS routes directly to merge

Trace: proposal `What Changes` direct PASS-to-merge; requirement `Executor merges only an explicitly authorized unchanged revision`; design D1/D5.

- [ ] 1.1 RED: add focused governance regression coverage proving `review-implementation` PASS routes directly to `Executor / merge-pr`, while a stale head, contradictory gate/check state, or implementation closing linkage still fails closed.
- [ ] 1.2 GREEN: update shared governance, directly affected role/skill contracts, and recurring message presentation so normal implementation merge consumes exact-head Reviewer PASS without Lead `MERGE_AUTHORIZED` or a replacement token.
- [ ] 1.3 REFACTOR: remove duplicate implementation authorization wording while keeping post-merge `Lead / finalize-change`, current Draft-to-Ready-before-review semantics, and cross-role handoff reconstruction coherent.
- [ ] 1.4 VERIFY: run focused Slice 1 tests, full regression suite, Ruff lint/format, mypy, and strict OpenSpec validation; persist verified slice completion before continuing.

## Slice 2 — Archive lifecycle preparation moves before review

Trace: proposal Archive preparation boundary; requirement `Review and finalize actions have Lead-owned minimum gate contracts`; design D2/D3/D5.

- [ ] 2.1 RED: add focused regression coverage proving final Archive PR review handoff is blocked until required separate-follow-up tracker state and any explicitly provenance-owned temporary correction/recovery disposition are reconstructable.
- [ ] 2.2 GREEN: move those Lead-owned judgments into `finalize-change` Archive-PR preparation, teach `review-archive` to inspect applicable preparation evidence, and route archive PASS directly to `Executor / merge-pr`.
- [ ] 2.3 REFACTOR: reduce `finalize-archive` to post-merge/native-close terminal reconstruction plus genuine close recovery, without retaining a hidden pre-merge authorization phase.
- [ ] 2.4 VERIFY: run focused Slice 2 tests, full regression suite, Ruff lint/format, mypy, and strict OpenSpec validation; persist verified slice completion before continuing.

## Slice 3 — Executor enforces one shared fresh-read merge contract

Trace: requirement `Executor merges only an explicitly authorized unchanged revision`; design D1/D3.

- [ ] 3.1 RED: add regression coverage for implementation and Archive merge showing current head, applicable PASS, required checks, correct linkage, and path-specific lifecycle preparation are all required immediately before mutation without a Lead authorization token.
- [ ] 3.2 GREEN: update `merge-pr` and directly related Executor/shared governance contracts to consume Reviewer PASS as normal merge authority and return stale/changed lifecycle evidence to the legal correction owner.
- [ ] 3.3 REFACTOR: consolidate common implementation/Archive merge checks while keeping Archive-only closing-linkage and pre-close cleanup preconditions explicit rather than creating a second merge action.
- [ ] 3.4 VERIFY: run focused Slice 3 tests, full regression suite, Ruff lint/format, mypy, and strict OpenSpec validation; persist verified slice completion before continuing.

## Slice 4 — Normalize normal Archive versus genuine recovery semantics

Trace: requirements `Normal OpenSpec archive mechanics remain owned by repository automation` and `Final Archive native-close occurs only after known terminal cleanup obligations are cleared`; design D4.

- [ ] 4.1 RED: add regression coverage proving normal `agent/archive-<change>` is never inferred to be a temporary cleanup branch and that cleanup authority requires separate durable correction/recovery provenance.
- [ ] 4.2 GREEN: update current authoritative governance/skills/spec-facing documentation to describe validated archive branch + Lead-created final Archive PR as normal lifecycle, while preserving explicit recovery/manual fallback semantics where they are actually supported.
- [ ] 4.3 REFACTOR: remove obsolete recovery wording or generic branch-discovery language that could classify ordinary archive branches as temporary, without rewriting historical Issue/PR evidence.
- [ ] 4.4 VERIFY: run focused Slice 4 tests, full regression suite, Ruff lint/format, mypy, and strict OpenSpec validation; persist verified slice completion before continuing.

## Slice 5 — Completion and SSOT-safe handoff

Trace: proposal scope/relationship to #80; design D1–D5; `openspec/config.yaml` governance.

- [ ] 5.1 RED: add/adjust repository governance regression coverage that detects a remaining normal dependency on `MERGE_AUTHORIZED` or duplicate current merge/recovery semantics in directly governed runtime surfaces.
- [ ] 5.2 GREEN: update only necessary README/orientation, canonical message/template references, and directly affected role/skill traces so one current contract remains authoritative; do not pre-implement #80 `agents/workflow.md` extraction.
- [ ] 5.3 REFACTOR: verify the Change introduces no replacement authorization token, second workflow DAG, hidden state, broad branch cleanup rule, or duplicate lifecycle owner.
- [ ] 5.4 VERIFY: run all project tests, Ruff lint/format, mypy, exact-head OpenSpec validation, and confirm proposal/spec/design/task traceability and all approved task markers are complete before implementation-review handoff.
