# Tasks

## Slice 1 — Routing-complete required-follow-up materialization

Trace: proposal `What changes` 1–3 → capability requirement `Approved required separate follow-ups are materialized as routing-complete Explore trackers` → Design Decisions 1–2.

- [ ] RED: add executable regressions proving create-without-route is incomplete, a unique matching incomplete tracker is repaired rather than duplicated, and ambiguous duplicates fail closed; run the focused tests and confirm failure is target-behavior RED.
- [ ] GREEN: implement the minimum shared/Lead materialization behavior needed to satisfy source linkage + `Change: unset` + `agent:lead + action:explore-change` as one logical postcondition.
- [ ] REFACTOR: remove duplicated/local interpretations while preserving source-authority, no-prose-inference, and at-least-once reconstruction semantics.
- [ ] VERIFY: run focused tests, full regression suite, type checks, lint checks, and strict OpenSpec validation; mark this slice complete only when all required checks are green.

## Slice 2 — Lifecycle preparation consumes the same postcondition

Trace: proposal `What changes` 4–6 and Skill maintenance traceability → lifecycle-preparation / optional-work / no-prose-inference scenarios → Design Decisions 3–4.

- [ ] RED: add executable regressions reproducing the #98-shaped unrouted required tracker and proving lifecycle preparation does not accept it as satisfied; also prove ordinary optional/out-of-scope work gains no routing authority.
- [ ] GREEN: modify `agents/skills/lifecycle-finalize/SKILL.md` and directly related executable support so lifecycle preparation verifies or unambiguously repairs the shared routing-complete postcondition; remove the contradictory local no-routing procedure without expanding Lead authority.
- [ ] REFACTOR: keep shared authority semantics in their existing owner and keep lifecycle procedure focused on reconstruction/preparation rather than creating a second dispatcher or generic recovery framework.
- [ ] VERIFY: run focused tests, full regression suite, type checks, lint checks, and strict OpenSpec validation; confirm Skill maintenance traceability still matches the implemented responsibility impact before marking complete.