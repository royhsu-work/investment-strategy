# Change: Adopt test-first delivery and independent engineering review

## Why

Issue #481 establishes a bounded improvement to repository development and review practice, before #478 resumes. PR #479's exact head `1dccdcd4178395a40f5259834480e61cb48337ed` has three regression failures caused by a test double without `development_materialization`. The interface change is visible at `389cb20c18ac180b577c9ed82b598e36f4aa39b4`; [the Python Quality job](https://github.com/royhsu-work/investment-strategy/actions/runs/45674452303/job/139418128717) reports 3 failed, 2368 passed, 1 xfailed. This is evidence of an interface/test-double mismatch, not proof that all historical tests were authored late or that the failing tests may be removed.

Human requires behavior-by-behavior Test First, independent Reviewer ownership of proactive refactoring assessment, a justified test lifecycle, and compact composable Skill knowledge. The current implementation procedure and task rules still assign REFACTOR to Executor. Review can already return substantiated findings, but must be equipped to detect architecture and slicing risks before implementation as well as inspect real code and test evidence afterward.

## What changes

- Adopt a reusable test-first procedure informed by Matt Pocock: observable behavior through public seams, a valid target RED before minimal GREEN, small vertical tracer bullets rather than horizontal bulk test/implementation phases, and trustworthy boundary substitutions and independent expected values.
- Transfer proactive REFACTOR assessment to independent Implementation Review; Executor implements the smallest correct behavior, fixes genuine regressions and substantiated findings, and does not self-clear review. Reviewers do not edit their own target.
- Equip OpenSpec Review and Implementation Review with shared engineering knowledge appropriate to their stage. Architectural principles and code smells are advisory heuristics, not an additional normative checklist, mechanical gate, or mandatory review report.
- Make test retention, replacement, consolidation and retirement evidence-based: preserve still-applicable behavior, unique regression, safety and supported compatibility; remove superseded assumptions when justified. Reuse existing test-retirement and finding-closure rules.
- Preserve exact-revision verification and the existing application, independent review, merge, archive, dependency and checkpoint boundaries. Reconcile existing procedure/config/canonical wording rather than creating parallel ownership.

## Capabilities

- Modified: `repository-governance` — test-first delivery, independent engineering review and evidence-based test lifecycle.
- Modified: `scheduled-agent-workflow` — align the existing complete Apply context with the new responsibility split; preserve all other applicable content.

## Scope and non-goals

This is one independently deployable Skill/governance delivery on the current N-1 substrate, not a runtime execution-engine implementation. No new Role, Action, Result, gate, scheduler, runner, TDD state machine, CI mode, test registry or extra token. No new production Python behavior. Behavioral Skill evaluation concerns material procedural changes, not ordinary documentation or wording-only edits. No blanket rewrite of tests, unrelated refactor or edits to #478 / PR #479. No locally installed dependencies assumed. The existing CI mechanism is authoritative for actual Python quality; #478 remains responsible for CI-only/static-first, multi-commit/multi-wake normal iteration and Recovery separation. Preserve #478's approved runtime outcomes, including the shared Task Contract and Strict Validation, exact-revision gates and recovery safety; do not assert that its future mechanisms already exist on main. The #481 dependency must be satisfied by formal archive completion, not merely closure or implementation merge. The latest Human decision in #481 and #478 explicitly supersedes the earlier plan to retain PR #479 and the fixed three-slice layout: after #481 deployment and lifecycle completion, #478 re-explores and redesigns from the then-current default branch, retains its Issue and immutable Change identity, and uses the lawful retirement and replacement-PR path under then-current governance. Preserve merged-main results, durable intent, dependencies and actual history, not unmerged implementation, test design, task markers or inherited review/CI qualification. Freshly qualify the downstream N-1 bootstrap and authority for the replacement; do not transfer historical permission automatically. This is a downstream boundary, not new #481 work.

## Evidence and traceability

- [Human scope #481](https://github.com/royhsu-work/investment-strategy/issues/481), [design supplement](https://github.com/royhsu-work/investment-strategy/issues/481#issuecomment-7171398396), [accepted same-Issue Explore](https://github.com/royhsu-work/investment-strategy/issues/481#issuecomment-7171597971). The current Human decision sections in [#481](https://github.com/royhsu-work/investment-strategy/issues/481) and [#478](https://github.com/royhsu-work/investment-strategy/issues/478) supersede only the conflicting older PR/slice and continuation design; [exact-R review F2](https://github.com/royhsu-work/investment-strategy/issues/481#issuecomment-7179951620) identifies the required correction.
- Immutable upstream: `mattpocock/skills@6f7f7831a625f040a8e06a0e7954826b87ce775a`, `skills/engineering/tdd/`, `skills/engineering/codebase-design/`, `skills/engineering/code-review/`; MIT license. Local provenance and responsibility differences must be recorded; no reliance on mutable upstream at runtime.
- N-1: `07d14987963e4ce7b87793cbdce8720b97ced1f8`; current verifier overlays exact candidate blobs, runs existing CI quality gates before ACCEPT, and does not implement a distinct persisted test-only RED path. Existing Skill-only delivery precedent: `openspec/changes/archive/2026-11-22-review-findings-scope-and-closure/`. The design distinguishes Skill evaluation from executable CI RED.

## Material repository Skill declarations

| Treatment | Skill | Responsibility before → after; rationale and source |
| --- | --- | --- |
| Added | `agents/skills/codebase-design/` | None → reusable engineering design/review knowledge, based on pinned codebase-design, deepening and code-review; shared by two review stages and seam design. No action authority. |
| Added | `agents/skills/tdd/` | None → reusable per-behavior RED/GREEN and test-seam guidance, based on pinned tdd/tests/mocking; no action authority or proactive refactor ownership. |
| Modified | `agents/skills/openspec-review/` | Independent semantic review preserved; consume shared knowledge to challenge interface, feasibility and vertical slicing risks in the existing proof loop before implementation. |
| Modified | `agents/skills/implementation-review/` | Independent exact-head review preserved; add proactive refactor assessment, test lifecycle evidence and appropriate shared design knowledge. Supersedes Executor proactive refactor assessment; uses existing findings loop. |
| Modified | `agents/skills/implementation/` | Approved implementation and checkpoint/verification preserved; compose TDD, replace proactive REFACTOR stage with independent review ownership and retain finding correction and test retirement responsibilities. |

All declarations derive from #481 and its accepted Explore. Keep existing provenance mappings and record material differences. No removed Skill; the superseded responsibility is transferred, not a new action. Role/config changes are not additional Skill declarations.

Refs #481
