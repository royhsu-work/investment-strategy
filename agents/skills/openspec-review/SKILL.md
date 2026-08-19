# OpenSpec Review Skill

Mapped action: `Reviewer / review-openspec`.

## Repository Skill composition

When the reviewed OpenSpec target materially concerns repository Skills, load the default-branch `agents/skills/skill-creator/SKILL.md` and `agents/skills/skill-creator/references/repository-governance.md` before reviewing those Skill artifacts and their integration contract. They are reusable semantic/procedural input only; this mapped action plus current default-branch governance and the Reviewer role retain independent review authority, traceability, exact-revision validation, findings, and routing semantics. Do not load this composition for unrelated OpenSpec review.

## Spec-driven semantic adapter

When default-branch `openspec/config.yaml` declares `schema: spec-driven`, load
`agents/skills/openspec-semantic-adapter.md` independently as part of this gate. Verify the reviewed
artifact set against its dependency/readiness, applicable config/context, complete delta-authoring,
canonicalization-readiness, Apply-context, and provenance/fail-closed semantics. The adapter is semantic
input only and does not replace reverse-first/forward traceability, exact-revision validation, or
Reviewer independence. A configured schema or material baseline mismatch is a finding/fail-closed
condition; do not substitute model memory or mutable upstream `main`.

## Reconstruct before acting

Read default-branch governance, the coordination Issue, immutable `Change:` identity, current OpenSpec
proposal/specs/design/tasks, applicable canonical specs, `README.md`, `openspec/config.yaml`, declared
semantic-review provenance, and exact-revision strict-validation evidence for the current checkout when
that mechanical evidence is required.

If the coordination Issue or current OpenSpec artifacts contain declared upstream authoritative decision/gate references, Reviewer MUST dereference those sources before deciding the gate. A cross-Issue summary is orientation only and is not replacement authority for the declared source evidence.

For continuity terminology, the action-specific accepted baseline B is the last independently accepted
semantic OpenSpec state that remains applicable, and the current target R is the exact semantic target
that now requires review. Reviewer covers material unreviewed changes in `(B, R]` as material semantic
changes and evaluates the complete current state at R. These established baseline/target names remain
part of the generic Reviewer coverage contract even though `review-openspec` applicability is semantic
rather than raw-SHA-global.

Reconstruct the applicable semantic OpenSpec baseline B from the last valid independent `review-openspec`
gate whose accepted meaning has not been materially superseded. Determine the semantic target R from the
latest material OpenSpec meaning that requires review. Cover all material semantic changes in `(B, R]`
and evaluate the complete semantic state at R; the semantic OpenSpec baseline B is a coverage boundary,
not authority for changed meaning.

A bookkeeping-only revision does not advance or invalidate the semantic baseline. Task-marker/checkpoint
updates, newer implementation commits, or a newer mechanical validation SHA do not by themselves create
a new semantic target when proposal intent, capability requirements/scenarios, design decisions,
traceability, scope boundaries, and normative task meaning are unchanged. Successful mechanical OpenSpec
validation is not semantic PASS evidence.

A material semantic change to those sources creates a new semantic target and invalidates the prior PASS
for the changed meaning. The correction must come through Lead specification authority before this gate.
If semantic applicability cannot be reconstructed unambiguously from durable artifacts/evidence, fail
closed rather than guessing or inventing a revision classifier.

Do not rely on a previous conversation or a prior PASS for materially changed OpenSpec meaning.

## Minimum gate

For the exact semantic target R, inspection is reverse-first and PASS still requires both directions on
that same target revision:

1. Verify reverse traceability `tasks → design → specs → proposal`.
2. Verify forward traceability `proposal → specs → design → tasks`.
3. Verify scope and contract coherence.
4. Verify compatibility with applicable README and OpenSpec config governance.
5. Under `spec-driven`, independently verify the loaded semantic adapter contract. In particular: NEW capability deltas have exactly one non-empty canonicalization-ready `## Purpose`; ADDED identifiers are genuinely new; MODIFIED targets use the exact canonical header and preserve every still-applicable scenario/content in the complete future block; REMOVED targets exist and carry required rationale/migration treatment; RENAMED uses exact FROM/TO and rename-plus-behavior-change also carries a complete MODIFIED block under the new identifier. Missing, duplicate, ambiguous, unsupported, or baseline-mismatched semantics are findings even when strict validation passes.
6. Confirm required strict OpenSpec validation evidence is mechanically current for the checkout used as evidence and proves validator `HEAD == validation target` before strict validation. Mechanical exact-revision validation does not by itself determine semantic target applicability.
7. Reconstruct every approved decision that explicitly classifies work as a required deferred follow-up. Require a durable linked tracker that identifies the source coordination Issue/Change and exact defer decision/reference. Missing required tracker linkage is a finding. Ordinary out-of-scope, non-goal, optional future work, or work merely not selected now is not a tracking obligation and MUST NOT be promoted into one by Reviewer inference.
8. Convert each material problem into an actionable finding that identifies the violated contract and supporting evidence.
9. Confirm no task or implementation detail is being used as the sole source of normative governance that belongs upstream in proposal/spec/design.
10. Confirm the approved Apply context is closed and reconstructable for Executor: proposal, applicable delta specs, design, tasks, canonical specs needed to interpret modified behavior, and materially applicable default-branch config context/rules. If required context is absent, contradictory, materially ambiguous, or unsupported by the represented baseline, the change cannot PASS to implementation.

Reverse-first is an inspection order only. It does not replace bidirectional traceability; both directions must be complete before PASS.

## Legal results

- `PASS` — all minimum semantic checks are satisfied for the exact reviewed revision, which is the exact
  semantic target actually inspected.
- `FINDINGS` — one or more actionable material findings exist.

The result MUST identify the exact reviewed revision and semantic target. A later material semantic
OpenSpec change requires a new gate; a bookkeeping-only OpenSpec revision does not stale an applicable
semantic PASS merely because its SHA is newer.

## Handoff

- `PASS` → `Executor / implement-change`.
- `FINDINGS` → `Lead / resolve-question`.

Persist the review result before routing. Fresh-read current routing before handoff; if another run
already changed it, do not overwrite the newer tuple.

## Durable messages and handoff recovery

Use `agents/templates/messages.md` for recurring durable presentation only when the shared presentation
contract is authoritative on the default branch. An unmerged governance PR containing that file is review
target/input, not execution authority, and must not govern its own current invocation.

Once active, the independent gate result uses `REVIEW_RESULT`, and completed routing transfer uses
canonical `HANDOFF` only after the routing mutation succeeds.

If an already-durable result exists but source routing still matches `Reviewer / review-openspec`,
preserve the review evidence, fresh-read the source tuple, perform only the missing routing mutation to
the action-defined target, observe the target routing, and persist canonical `HANDOFF` when that template
contract is active. Do not repeat the independent review or fabricate another review result merely to
recover the missing handoff.

## Independence and concurrency

Reviewer does not edit specification artifacts to resolve its own findings. Multiple evidence records
may exist under overlapping runs; contradictory current evidence is not optimistically merged into a
PASS. `fresh-read routing → update labels` is not mutex/CAS/single-flight behavior.
