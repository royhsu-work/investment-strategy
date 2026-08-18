# Design: Consolidate PR merge lifecycle

## Context

Current `main` uses independent Reviewer exact-head PASS followed by a Lead `MERGE_AUTHORIZED(R)` hop and then `Executor / merge-pr`. The implementation path contains no independent Lead-owned judgment in that post-review hop: Lead rechecks current head/gates, while Executor must repeat those checks immediately before mutation. The Archive path does contain Lead-owned lifecycle judgment, but that judgment concerns whether the final Archive target is ready to be reviewed/closed, not whether a previously reviewed exact revision needs a second acceptance token.

#58 also changed the normal deployed Archive boundary: repository automation now succeeds at validated `agent/archive-<change>` branch readiness and Lead creates/reuses the final Archive PR as ordinary lifecycle continuation. The ordinary archive branch is therefore a normal lifecycle artifact. Explicit `openspec-archive-recovery`, manual `workflow_dispatch`, and separately provenance-owned correction/recovery branches remain exceptional paths.

This design removes the duplicate normal authorization token without moving specification/lifecycle judgment into Executor or weakening exact-head fail-closed behavior.

## Requirement traceability

| Requirement | Design decisions |
| --- | --- |
| `Review and finalize actions have Lead-owned minimum gate contracts` | D1, D2, D5 |
| `Executor merges only an explicitly authorized unchanged revision` | D1, D3, D4 |
| `Normal OpenSpec archive mechanics remain owned by repository automation` | D2, D4, D5 |
| `Final Archive native-close occurs only after known terminal cleanup obligations are cleared` | D2, D3, D4 |

## D1 — Reviewer PASS is the normal acceptance authority; Executor owns operational merge safety

For both implementation and final Archive PRs, an independent Reviewer PASS is bound to exact revision `R`. Once PASS(R) is durable, routing goes directly to `Executor / merge-pr`.

The removed Lead hop is not replaced with another token. Executor fresh-reads immediately before mutation and requires:

- target PR head still equals `R`;
- the applicable Reviewer PASS(R) is current, unambiguous, and not contradicted by later findings;
- required CI/validation checks remain valid;
- implementation PRs retain only non-closing coordination linkage;
- final Archive PRs retain the exact repository-approved closing linkage;
- path-specific lifecycle preparation and cleanup preconditions remain satisfied.

Any changed head requires a new exact-head review. A changed/contradictory gate, linkage, or lifecycle precondition fails closed to the legal correction owner. This preserves the current safety property while removing duplicate Lead acceptance evidence.

### Why this is sufficient

`MERGE_AUTHORIZED(R)` currently does not carry additional implementation semantics: Lead verifies the same PASS/head/check state that Executor must independently reconstruct before the irreversible mutation. The durable independent PASS plus fresh mutation-time preconditions is therefore the smaller sufficient contract.

## D2 — Archive lifecycle judgment moves to the pre-review preparation boundary

Archive differs from implementation because final native close can make lifecycle obligations unreachable. Lead retains authority for those judgments, but performs them before handing the final Archive PR to `Reviewer / review-archive`.

`Lead / finalize-change`, after validated archive-branch readiness and final Archive PR creation/reuse, reconstructs:

1. every still-applicable approved required separate-follow-up obligation and its durable tracker;
2. any separately workflow-owned temporary correction/recovery branch identified by explicit durable provenance;
3. whether such a branch is safely deletable before native close, intentionally retained with a legal durable disposition, or ambiguous/unsafe.

If this Lead-owned preparation is missing, ambiguous, or contradictory, the Archive PR is not review-ready. Lead does not postpone the judgment until after Reviewer PASS.

Reviewer then evaluates the exact Archive revision together with the applicable durable preparation evidence. PASS means the target is independently accepted and lifecycle-prepared for operational merge, subject to mutation-time fresh reads.

### Preparation evidence after PASS

No hidden preparation token is introduced. Durable Issue/PR/recovery/tracker evidence remains the source of truth.

- Expected fulfillment of an already reviewed obligation, such as Executor deleting the exact predeclared safely deletable temporary branch immediately before merge, does not stale PASS.
- Discovery of a new required obligation, a changed retention/cleanup classification, contradictory tracker state, or other material preparation change after PASS fails closed. Executor does not reinterpret it; control returns to Lead and the Archive target requires renewed independent review when the reviewed preparation meaning materially changed.

## D3 — Executor keeps only operational cleanup mutation authority

Executor does not decide whether an arbitrary branch is temporary or whether lifecycle policy permits discarding it. Lead identifies/classifies any temporary correction/recovery obligation from durable provenance before Archive review.

Immediately before final Archive merge, Executor fresh-reads only those explicitly identified branches and may delete one only when current evidence proves:

- it is the same workflow-owned temporary correction/recovery branch;
- it is not an open PR head/base;
- it is not active correction/recovery input;
- it has no unique commits outside canonical `main` or an explicitly retained successor;
- the Lead-reviewed disposition still requires safe deletion.

Denied, unavailable, stale, ambiguous, or unsafe deletion blocks merge while the coordination Issue remains open. There is no broad `agent/*` garbage collection.

## D4 — Normal archive branches and genuine recovery branches are distinct

`agent/archive-<change>` produced by repository automation is always the normal validated archive lifecycle artifact. Its name alone can never satisfy temporary-branch identity or deletion authority.

Genuine recovery remains exceptional and explicitly entered, including:

- `openspec-archive-recovery` recovery mode for eligible already-merged Complete changes;
- manual `workflow_dispatch` recovery/migration fallback;
- a separately provenance-owned temporary correction/integration branch created or adopted by the governed recovery/integration contract.

Historical Issues may retain their historical wording. Current authoritative governance, Skills, specs, and tests should use recovery terminology only for those actual exceptional paths.

## D5 — Post-merge lifecycle ownership and existing Ready semantics remain unchanged

This change removes only the redundant acceptance-to-merge Lead hop.

Implementation remains:

```text
Executor / implement-change
→ Reviewer / review-implementation
→ PASS(R)
→ Executor / merge-pr
→ Lead / finalize-change
```

Archive remains:

```text
Lead / finalize-change
→ create/reuse + prepare Archive PR
→ Reviewer / review-archive
→ PASS(R)
→ Executor / merge-pr
→ Lead / finalize-archive
→ LIFECYCLE_COMPLETE
```

`Lead / finalize-change` remains necessary after implementation merge to reconstruct multi-PR completion and archive automation state. `Lead / finalize-archive` remains necessary after Archive merge/native close for terminal canonical reconstruction.

Implementation Draft-to-Ready remains Executor-owned before `review-implementation`. Moving Ready after review would change presentation/review semantics without being necessary to remove `MERGE_AUTHORIZED` and is therefore out of scope.

## Alternatives considered

### Keep `MERGE_AUTHORIZED` for both paths

Rejected. It preserves duplicate implementation judgment and forces the Archive-specific preparation problem to remain after independent review instead of placing it at the natural preparation boundary.

### Remove Lead authorization only for implementation

Rejected. It would create two acceptance-to-merge contracts solely because Archive has pre-close preparation. Moving that preparation before archive review permits one smaller shared merge contract without moving Lead judgment into Executor.

### Move Archive lifecycle judgment into Executor

Rejected. Required deferred-follow-up applicability and temporary-branch lifecycle classification are Lead-owned specification/lifecycle judgments. Executor only performs the already-governed operational fresh-read/deletion/merge mutations.

### Delete all temporary correction/recovery cleanup semantics

Rejected. Current governance still supports constrained integration/recovery branches. The correct simplification is provenance-scoped cleanup and explicit exclusion of normal archive branches, not deleting a safety contract that still has a supported producer class.

### Move Draft → Ready after Reviewer PASS

Rejected as unnecessary scope expansion. Current pre-review Ready semantics are coherent and independently governed.

## Risks and mitigations

- **Risk: PASS is mistaken for permission to merge stale state.** Mitigation: PASS remains exact-head; Executor requires current head/checks/linkage/preconditions and fails closed on any mismatch.
- **Risk: Archive obligation appears after review.** Mitigation: new/materially changed preparation evidence blocks merge and returns to Lead; renewed review is required when reviewed meaning changed.
- **Risk: normal archive branch is deleted as recovery cleanup.** Mitigation: explicit normative exclusion plus tests; temporary identity requires separate durable provenance, never a branch-name pattern.
- **Risk: removal of token reduces reconstruction clarity.** Mitigation: durable Reviewer PASS, routing, current PR state, checks, Lead preparation evidence, and merge result remain reconstructable; no extra token is necessary to recover the accepted revision.

## Deferred / related work

- #80 may later extract end-to-end workflow topology into `agents/workflow.md`; it should use the lifecycle resulting from this Change rather than duplicating the pre-change topology.
- Broader scheduler/deployment liveness and new merge-queue abstractions remain out of scope.
