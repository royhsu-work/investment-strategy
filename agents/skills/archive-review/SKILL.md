# Archive Review Skill

Mapped action: `Reviewer / review-archive`.

## Reconstruct before acting

Read default-branch governance and Reviewer role, the coordination Issue and immutable `Change:`, the
merged implementation/default-branch state, the existing archive automation result, the current Archive
PR and exact head revision, the active/archive/canonical OpenSpec state, and current validation evidence.

Reconstruct the action-specific accepted baseline B from the last valid independent `review-archive` gate that remains applicable to this archive stream, and the current target R as the exact current Archive PR head. Inspect all material unreviewed changes in `(B, R]` and evaluate the complete current state at R; the accepted baseline is a coverage boundary only and never authorizes a changed archive head.

This action is an exact-current-head gate. The semantic OpenSpec bookkeeping exception does not weaken this gate: even when a bookkeeping-only OpenSpec revision does not require another semantic `review-openspec`, Reviewer still evaluates the exact current Archive PR head R.

## Minimum gate

For the exact current Archive PR head R:

1. Verify the intended change is archived from the correct merged default-branch source state.
2. Verify resulting canonical specs preserve the approved contract.
3. Verify active change state is removed as intended and dated archive history is preserved.
4. Verify unrelated repository changes are absent.
5. Verify strict OpenSpec validation and any applicable repository validation evidence are current. If
   strict validation is claimed for R, durable validator evidence must prove checkout `HEAD == R`
   before the strict command; `run.head_sha == R` or a different synthetic merge checkout is not
   sufficient exact-head evidence.
6. Record actionable findings for any material deviation; otherwise record PASS.

## Legal results and handoff

- `PASS` → `Lead / finalize-archive`.
- `FINDINGS` → `Lead / resolve-question` or the repository-defined recovery decision required by the
  specific archive failure.

The result is bound to the exact archive PR head. A changed head invalidates the old gate for merge
authorization.

## Durable messages

Use `agents/templates/messages.md` for recurring durable presentation only when that presentation
contract is authoritative on the default branch. Once active, Archive gate outcomes use `REVIEW_RESULT`;
completed routing transfer uses canonical `HANDOFF` only after the routing mutation succeeds. Do not
duplicate shared template bodies in this skill.

## Boundary and safety

Reviewer does not repair archive/specification/implementation artifacts itself. This skill reviews the
Archive PR produced by existing repository archive mechanics; it does not introduce or execute a normal
scheduled `archive-change` mutation. Persist review evidence before routing and fresh-read routing before
handoff. Contradictory current evidence fails closed.
