# Tasks

## Slice 1 — routing-complete producer postcondition

Trace: proposal `What Changes` 1–2 → added `scheduled-agent-workflow` requirement normal/interrupted/ambiguity/no-prose scenarios → design decisions 1–2, 4–5.

- [ ] RED: add focused regression tests showing a required follow-up is incomplete when tracker creation/source linkage exists without canonical `Lead / explore-change` routing; cover #98-style state, interrupted create-before-route, unique repair, duplicate ambiguity, and no prose-derived routing.
- [ ] GREEN: update the existing Lead required-follow-up producer procedure in `agents/skills/openspec-change/SKILL.md` so it reconstructs source authority/matches, creates or repairs exactly one tracker, completes canonical routing, and recognizes success only after the complete durable postcondition is observed.
- [ ] REFACTOR: remove duplicated/local wording that is unnecessary once the routing-complete postcondition is explicit; preserve shared governance and Lead role as SSOT.
- [ ] VERIFY: run the focused tests, full regression suite, type checks, lint checks, and strict OpenSpec validation; persist the verified slice marker only after all required gates pass.

## Slice 2 — lifecycle fail-safe alignment

Trace: proposal `What Changes` 3 → added lifecycle-preparation scenario → design decisions 3 and 5.

- [ ] RED: add regression coverage proving lifecycle preparation rejects an unrouted required tracker and can repair one uniquely matching incomplete tracker from still-valid approved source evidence; prove ambiguous/multiple matches fail closed.
- [ ] GREEN: align `agents/skills/lifecycle-finalize/SKILL.md` with the shared/Lead SSOT by removing the contradictory no-routing rule and verifying/repairing the same routing-complete required-follow-up postcondition before review handoff.
- [ ] REFACTOR: keep lifecycle-finalize as a reconstruction/fail-safe procedure rather than a second admission/dispatcher authority; remove obsolete contradictory guidance.
- [ ] VERIFY: run the focused tests, full regression suite, type checks, lint checks, and strict OpenSpec validation; persist the verified slice marker only after all required gates pass.

## Slice 3 — scope and regression closure

Trace: proposal scope/non-goals → optional-work and no-prose scenarios → design non-goals.

- [ ] RED: extend regression coverage to distinguish required separate/deferred obligations from optional, non-goal, ordinary out-of-scope, or merely deferred text.
- [ ] GREEN: make only the minimum test/procedure adjustments needed so ordinary optional/deferred work creates no routing obligation and dispatcher behavior remains unchanged.
- [ ] REFACTOR: verify Skill maintenance traceability matches the actual materially affected Skill set; do not add speculative shared abstractions.
- [ ] VERIFY: run the full regression suite, type checks, lint checks, and `openspec validate --all --strict --json --no-interactive`; all must pass on the exact final head before implementation-review handoff.
