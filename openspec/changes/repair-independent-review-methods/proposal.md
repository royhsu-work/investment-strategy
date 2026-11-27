# Repair independent Reviewer methods

## Why

Independent review must discover material defects, not merely confirm the author's evidence or the internal consistency of artifacts. The exact historical semantic review of #491 accepted a proposal and delta containing implementation details that belonged in Design or Tasks. Existing review procedures contain valuable safeguards, but do not reliably direct the Reviewer to reconstruct the expected result, inspect the responsible surface and actively challenge the candidate. The Implementation Review procedure and Reviewer Role also disagree with the executable model on legal result categories.

The Human has prioritized this repair before #491 and #478. The outcome is a concise, repeatable review method that independently detects material problems and distinguishes valid work from harmless alternatives. More rules, longer instructions or a new checklist are not the outcome.

## What changes

- Make OpenSpec Review independently assess each artifact's responsibility, every material acceptance boundary, substantive correctness, architecture and delivery feasibility, and both directions of traceability before deciding.
- Make Implementation Review independently derive expected behavior, inspect actual behavior, actively seek discriminating counterexamples, verify evidence, assess necessary refactoring and decide under existing authority.
- Preserve all current independence, evidence, source chronology, Human intent, exact revision, safety, stage/closure and lifecycle protections. Align procedural result descriptions with the existing executable Action model.
- Demonstrate improved review decisions on fixed representative inputs before and after the material procedural changes, and independent discovery on previously unused inputs at the existing independent review gate. Distinguish proposal and specification responsibility defects, material acceptance-boundary omissions, caller-visible defects and valid/advisory controls. Rehearsal of known findings alone does not demonstrate independent discovery. Preserve #481's Test First, test protection and independent refactoring outcomes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None at the normative specification level. This is implementation of existing repository-governance and scheduled-agent-workflow review, proportionality, Skill maintenance, Test First, evidence and exact-revision contracts. Use the explicit zero-delta path (skip_specs: true). No change to the normative acceptance predicates, executable transitions or required gates is authorized.

## Scope and impact

The two mapped Review Skills are the primary affected procedures; align only directly affected Reviewer responsibility wording, provenance and verification. Reuse existing engineering knowledge and canonical owners. No new review role, Action, Result, gate, runtime state, workflow, evaluator infrastructure or independent authority. Archive Review and unrelated governance remain outside scope.

One formal Change delivers both independently verifiable review-method increments, with the full parent outcome retained until the normal lifecycle is complete. Each increment is usable and verifiable on the current deployed substrate without #478 or #491. Neither a partial increment nor mechanical validation alone establishes acceptance.

#478 remains dependent on #493 (and its existing prerequisites). #491's pending A2 delivery stays paused until #493's formal lifecycle completes. Then independently re-review its exact OpenSpec revision under the newly deployed method; do not inherit the earlier PASS or decide now to retire #491. Preserve all other dependencies and approved outcomes. Any subsequent retirement, rework or replacement requires its own freshly qualified evidence and authority.

## Authority and source

- Human scope: [#493](https://github.com/royhsu-work/investment-strategy/issues/493), including the explicit methods, evaluation requirements and priority/restoration boundary.
- Same-Issue decision-complete Explore: [ACTION_RESULT 7210723113](https://github.com/royhsu-work/investment-strategy/issues/493#issuecomment-7210723113), accepted by [Application decision 7210722422](https://github.com/royhsu-work/investment-strategy/issues/493#issuecomment-7210722422).
- Historical review target: [#491 semantic review 6082424882](https://github.com/royhsu-work/investment-strategy/pull/491#pullrequestreview-6082424882).
- Positive review-method witness: [#486 review 6076168321](https://github.com/royhsu-work/investment-strategy/pull/486#pullrequestreview-6076168321).
- Exact-revision corrective review: [REVIEW_RESULT 7211825342](https://github.com/royhsu-work/investment-strategy/issues/493#issuecomment-7211825342) (F1–F3 at 81c8af88ea2cea0e2ce5ee2c922eb0633058e367); correction preserves the accepted Explore and existing gates.
- Authoring baseline: [f327e5f7f054affa40120c8ca93a2804032a3f25](https://github.com/royhsu-work/investment-strategy/commit/f327e5f7f054affa40120c8ca93a2804032a3f25). Current default-branch governance and exact source revalidation are the authority and feasibility basis, not the historical review's PASS.
