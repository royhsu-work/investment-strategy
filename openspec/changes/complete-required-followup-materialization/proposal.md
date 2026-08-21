# Change: Complete required follow-up materialization

## Why

Required separate/deferred follow-up work is already governed as a repository-authorized bounded Explore, but the producer procedure can leave a tracker materially incomplete when Issue creation/source linkage succeeds and canonical `Lead / explore-change` routing does not. Current `lifecycle-finalize` guidance also contradicts the shared/Lead SSOT by forbidding routing on the very required-follow-up tracker that shared governance requires to be routed.

Issue #98 is the durable regression case: archived #85 requires a separate follow-up, while #98 exists without canonical routing. The revalidated #100 Explore result is `issuecomment-5368297271`; former #100 proposal/review/readiness evidence and closed PR #104 are historical only and are not reused as gates.

## What Changes

- Define required separate-follow-up materialization as one logical producer postcondition: one deduplicated tracker with `Change: unset`, exact source coordination/change plus defer-decision reference, and canonical `agent:lead + action:explore-change` routing.
- Require the Lead action owning the approved defer decision to fresh-read and idempotently repair one uniquely matching incomplete tracker instead of treating create-without-route as success; multiple or ambiguous matches fail closed.
- Align lifecycle-finalize preparation with the shared/Lead SSOT so it verifies or repairs the same routing-complete postcondition rather than preserving a contradictory no-routing rule.
- Keep dispatcher admission unchanged: routing is consumed from canonical labels and is never inferred from Issue prose.
- Add regression coverage for #98, interruption between tracker creation and routing, unique repair, duplicate ambiguity, optional/out-of-scope work, and lifecycle preparation of an unrouted required tracker.

## Capabilities

### Modified capabilities

- `scheduled-agent-workflow`: make required separate-follow-up materialization routing-complete and reconstructably repairable at the producing Lead/lifecycle boundary without changing dispatcher admission or Human authority.

## Scope

In scope:
- required separate/deferred follow-up tracker materialization and idempotent repair;
- alignment of affected Lead mapped Skill procedures with existing shared/Lead authority;
- lifecycle preparation fail-safe behavior;
- executable regression coverage.

Out of scope:
- dispatcher inference from Issue prose;
- new workflow states, locks, leases, claims, or retry engines;
- new Human authority/admission semantics;
- arbitrary Explore creation authority;
- substantive conversion of `agents/skills/openspec-semantic-adapter.md` tracked by #98.

## Skill maintenance traceability

- Modified: `agents/skills/openspec-change/SKILL.md`
  - Source: #100 / `issuecomment-5368297271` and this Change.
  - Responsibility preserved: Lead owns required deferred follow-up creation/reuse at the approved defer-decision boundary.
  - Change: make the existing responsibility executable as a routing-complete logical postcondition with unique incomplete-tracker repair and fail-closed ambiguity handling.
  - Rationale: current procedure can acknowledge the required tracker without making completion/recovery semantics explicit enough to prevent partial materialization.

- Modified: `agents/skills/lifecycle-finalize/SKILL.md`
  - Source: #100 / `issuecomment-5368297271` and this Change.
  - Responsibility preserved: lifecycle finalization is a fail-safe reconstruction/preparation boundary, not a dispatcher or new admission authority.
  - Change: remove contradictory local no-routing behavior and verify/repair the same routing-complete required-follow-up postcondition owned by shared/Lead governance.
  - Rationale: the local procedure currently conflicts with its authoritative shared/role owner.

No Skill is added or removed. No replacement/supersession target applies.

## Impact

Expected implementation touches the two mapped Lead Skills above and their existing governance/contract regression tests. Canonical `scheduled-agent-workflow` behavior is modified only to make the already-required follow-up obligation atomic/reconstructable; role authority, queue admission, workflow topology, and Human provenance contracts remain unchanged.
