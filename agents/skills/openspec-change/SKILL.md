# OpenSpec Change Skill

Mapped actions: `Lead / propose-change`, `Lead / resolve-question`.

This skill operationalizes approved OpenSpec authoring and specification-question resolution. It does
not replace the repository OpenSpec proposal/specs/design/tasks lifecycle.

## Reconstruct before acting

Read from durable state:

- default-branch `agents/AGENTS.md`, `agents/roles/lead.md`, and this skill;
- coordination Issue routing and immutable `Change:` identity when set;
- current active OpenSpec proposal/specs/design/tasks and applicable canonical specs;
- applicable `README.md` and `openspec/config.yaml` governance;
- relevant durable Issue/review findings;
- exact current repository/branch revision and strict OpenSpec validation evidence.

If routing, change identity, or required evidence is contradictory, fail closed.

## `propose-change`

1. Confirm explicit Human/maintainer admission and valid `Lead / propose-change` routing.
2. If `Change:` is unset, choose/create one OpenSpec change id consistent with the authorized direction
   and persist it; after persistence the identity is immutable.
3. Author the minimum proposal, delta specs, design, and tasks needed by the approved direction. Keep the
   change single-purpose and preserve repository scope boundaries.
4. Any proposal/implementation PR associated with the persistent coordination Issue must use a
   non-closing reference to the coordination Issue (for example `Refs #N`). It must not establish Issue-closing linkage. Closing linkage is reserved for the final Archive PR lifecycle boundary.
5. Before handoff, verify required artifacts exist and perform both:
   - forward traceability `proposal → specs → design → tasks`;
   - reverse traceability `tasks → design → specs → proposal`.
6. Obtain strict OpenSpec validation for the exact handoff revision R. CI is sufficient only when
   durable validator evidence proves checkout `HEAD == R` before strict validation; `run.head_sha == R`
   alone is association metadata and is not checkout proof. If valid exact-head CI evidence is
   unavailable, use the repository-pinned local CLI directly against checkout R. Stale, missing,
   failed, revision-mismatched, or checkout-mismatched evidence fails closed.
7. Persist revision-aware readiness evidence before routing.

Legal outcomes:

- `READY_FOR_OPENSPEC_REVIEW` → hand off to `Reviewer / review-openspec`.
- `SPECIFICATION_BLOCKED` or invalid/stale evidence → retain Lead; do not hand off as ready.

## `resolve-question`

1. Reconstruct the finding/blocker and the exact currently governed OpenSpec state.
2. Decide whether the finding is accepted, rejected, or already resolved using approved scope and
   evidence. Explain the decision durably.
3. If accepted, revise only Lead-owned OpenSpec specification artifacts needed to resolve it; do not
   modify implementation code to make a gate pass.
4. If OpenSpec artifacts changed materially, repeat the same required-artifact, bidirectional
   traceability, and exact-revision strict-validation readiness checks used by `propose-change`.
5. If the same implementation or correction PR remains in use, keep its coordination-Issue reference
   non-closing; resolving a specification question never authorizes adding Issue-closing linkage to an
   implementation PR.
6. Persist the resolution and current revision before handoff.

Legal handoff depends on the gate/blocker being resolved:

- revised OpenSpec requiring independent review → `Reviewer / review-openspec`;
- implementation may continue under unchanged approved meaning → `Executor / implement-change`;
- lifecycle/archive question → return to the appropriate Lead finalize action only when the approved
  contract makes that legal;
- unresolved ambiguity or failed readiness evidence → retain Lead.

## Safety

- Do not infer missing specification meaning on behalf of Executor.
- Do not treat `run.head_sha` or a successful synthetic-merge validation for another checkout as
  exact-head proof for revision R.
- Do not require a duplicate local CLI run solely because valid exact-head CI validation already passed.
- Persist durable result/evidence before routing and fresh-read routing before the label mutation.
- A routing update is not a mutex/CAS; overlapping Lead runs must tolerate repeated observation and
  stop on stale/contradictory state.
