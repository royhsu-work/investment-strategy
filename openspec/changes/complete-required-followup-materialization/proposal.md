# Change: Complete required follow-up materialization

Explore source: #100 `issuecomment-5368297271`.

## Why

Current shared governance and Lead authority require an approved required separate follow-up to become one source-linked `Change: unset` tracker routed to `Lead / explore-change`. Current `lifecycle-finalize` procedure contradicts that SSOT by saying such a tracker must not receive workflow routing. #98 remains the concrete malformed historical tracker. This dual-authority contradiction can leave an approved obligation durable but non-executable.

The 2026-08-19 administrative reset invalidated the former #100 proposal/review/readiness gates and PR #104. This Change is authored anew from current `main` and the revalidated Explore result above.

## What changes

- Define required separate-follow-up materialization as one logical postcondition: exactly one deduplicated tracker with `Change: unset`, exact source coordination/change and defer-decision linkage, and canonical `agent:lead + action:explore-change` routing.
- Treat create/reuse without required routing as incomplete rather than successful materialization.
- Require idempotent repair of the unique matching incomplete tracker from independently approved source evidence; multiple or ambiguous candidates fail closed.
- Align lifecycle preparation with the shared/Lead SSOT so it verifies or repairs the same routing-complete postcondition instead of preserving a contradictory no-routing rule.
- Preserve dispatcher behavior: missing routing is never inferred from Issue prose.
- Add executable regression coverage for interrupted create-before-route, unique repair, duplicate ambiguity, ordinary optional/out-of-scope work, no prose-derived routing, and lifecycle preparation of malformed required trackers.

## Affected capabilities

- `scheduled-agent-workflow` — add the routing-complete materialization requirement for approved required separate follow-ups.

## Scope boundaries

In scope: required separate-follow-up tracker materialization, idempotent repair, lifecycle preparation consistency, and regression coverage.

Out of scope: the substantive #98 semantic-adapter Skill conversion; dispatcher priority/topology changes; arbitrary Explore creation; Human-authority semantics; optional/non-goal future work; a generic issue-creation or recovery framework.

## Skill maintenance traceability

| Skill | Class | Approved source | Responsibility treatment | Rationale |
| --- | --- | --- | --- | --- |
| `agents/skills/lifecycle-finalize/SKILL.md` | Modified | #100 / this Change | Preserve Lead `finalize-change` / `finalize-archive` ownership; remove the contradictory local no-routing instruction and consume the shared routing-complete required-follow-up postcondition | Lifecycle preparation must not declare an unrouted required tracker complete when shared/Lead governance requires routed Explore materialization |

No Skill is Added or Removed. Other mapped Skills remain unchanged unless implementation proves a materially different approved responsibility impact, in which case Executor must return through specification authority rather than self-authorize it.

## Deferred work

#98 remains the separate substantive follow-up for converting `agents/skills/openspec-semantic-adapter.md` into a reusable Skill. This Change only makes its required tracker lifecycle executable and reconstructable.