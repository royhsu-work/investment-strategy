---
name: archive-review
description: Review the exact current final Archive PR and its Lead-prepared lifecycle evidence for Reviewer / review-archive without changing archive artifacts or workflow authority.
---

# Archive Review Skill

Mapped action: `Reviewer / review-archive`.

## Reconstruct before acting

Read default-branch governance and Reviewer role, the coordination Issue and immutable `Change:`, the
merged implementation/default-branch state, the existing archive automation result, the current Archive
PR and exact head revision, the active/archive/canonical OpenSpec state, current validation evidence, and
the Lead preparation evidence that made this final Archive PR review-ready.

Lead preparation evidence is the applicable durable Issue/PR/recovery/tracker evidence reconstructed by
`Lead / finalize-change` before `Reviewer / review-archive`; it is not a replacement authorization token.
It must establish that every still-applicable approved required separate-follow-up obligation has a durable
tracker and that every explicitly provenance-owned temporary correction/recovery branch has a
reconstructable pre-close disposition: safely deletable, intentionally retained with a legal durable
reason/owner, or absent. Missing, ambiguous, contradictory, or materially changed preparation evidence
fails closed.

Reconstruct the action-specific accepted baseline B from the last valid independent `review-archive` gate
that remains applicable to this archive stream, and the current target R as the exact current Archive PR
head. Inspect all material unreviewed changes in `(B, R]` and evaluate the complete current state at R;
the accepted baseline is a coverage boundary only and never authorizes a changed archive head.

This action is an exact-current-head gate. The semantic OpenSpec bookkeeping exception does not weaken this
gate: even when a bookkeeping-only OpenSpec revision does not require another semantic `review-openspec`,
Reviewer still evaluates the exact current Archive PR head R.

## Minimum gate

For the exact current Archive PR head R:

1. Verify the intended change is archived from the correct merged default-branch source state.
2. Verify resulting canonical specs preserve the approved contract.
3. Verify active change state is removed as intended and dated archive history is preserved.
4. Verify unrelated repository changes are absent.
5. Verify strict OpenSpec validation and any applicable repository validation evidence are current. If
   strict validation is claimed for R, durable validator evidence must prove checkout `HEAD == R` before
   the strict command; `run.head_sha == R` or a different synthetic merge checkout is not sufficient
   exact-head evidence.
6. Verify the applicable Lead preparation evidence is complete and consistent with the current Archive
   target and durable lifecycle state. Reviewer independently inspects the evidence but does not recreate
   Lead's lifecycle judgment or mutate trackers/branches.
7. Record actionable findings for any material deviation; otherwise record PASS bound to R and the
   reviewed preparation meaning.

## Legal results and handoff

- `PASS` → `Executor / merge-pr`.
- `FINDINGS` → `Lead / resolve-question` or the repository-defined recovery decision required by the
  specific archive failure.

The result is bound to the exact archive PR head and the materially reviewed preparation meaning. A changed
head invalidates the old gate. Discovery of a new required obligation, changed cleanup/retention
classification, contradictory tracker state, or another material preparation change after PASS also fails
closed to Lead and requires renewed independent review when the reviewed meaning changes. Expected
fulfillment of an already reviewed disposition, such as Executor deleting the exact predeclared safely
deletable temporary branch immediately before merge, does not itself stale PASS.

## Durable messages

Use `agents/templates/messages.md` for recurring durable presentation only when that presentation contract
is authoritative on the default branch. Once active, Archive gate outcomes use `REVIEW_RESULT`; completed
routing transfer uses canonical `HANDOFF` only after the routing mutation succeeds. Do not duplicate shared
template bodies in this skill.

## Boundary and safety

Reviewer does not repair archive/specification/implementation artifacts itself. This skill reviews the
Archive PR produced by existing repository archive mechanics and its applicable Lead preparation evidence;
it does not introduce or execute a normal scheduled `archive-change` mutation. Persist review evidence
before routing and fresh-read routing before handoff. Contradictory current evidence fails closed.
