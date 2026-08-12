# OpenSpec Review Skill

Mapped action: `Reviewer / review-openspec`.

## Reconstruct before acting

Read default-branch governance, the coordination Issue, immutable `Change:` identity, current OpenSpec
revision, proposal/specs/design/tasks, applicable canonical specs, `README.md`, `openspec/config.yaml`,
and exact-revision strict-validation evidence.

Do not rely on a previous conversation or a prior PASS for another revision.

## Minimum gate

For the exact current OpenSpec revision:

1. Verify forward traceability `proposal → specs → design → tasks`.
2. Verify reverse traceability `tasks → design → specs → proposal`.
3. Verify scope and contract coherence.
4. Verify compatibility with applicable README and OpenSpec config governance.
5. Confirm strict OpenSpec validation evidence is current for the reviewed revision.
6. Convert each material problem into an actionable finding that identifies the violated contract and
   supporting evidence.
7. Confirm no task or implementation detail is being used as the sole source of normative governance
   that belongs upstream in proposal/spec/design.

## Legal results

- `PASS` — all minimum checks are satisfied for the exact reviewed revision.
- `FINDINGS` — one or more actionable material findings exist.

The result MUST identify the exact reviewed revision. A later revision invalidates the prior gate for
that later state.

## Handoff

- `PASS` → `Executor / implement-change`.
- `FINDINGS` → `Lead / resolve-question`.

Persist the review result before routing. Fresh-read current routing before handoff; if another run
already changed it, do not overwrite the newer tuple.

## Independence and concurrency

Reviewer does not edit specification artifacts to resolve its own findings. Multiple evidence records
may exist under overlapping runs; contradictory current evidence is not optimistically merged into a
PASS. `fresh-read routing → update labels` is not mutex/CAS/single-flight behavior.
