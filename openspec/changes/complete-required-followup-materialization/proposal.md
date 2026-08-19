# Change: Complete required follow-up materialization

## Why

#98 demonstrates a workflow-integrity gap: an approved required separate follow-up can be durably tracked yet remain unrouted and therefore invisible to the canonical pre-activation queue. Current default-branch governance already intends required separate follow-ups to be source-authorized and routed directly to `Lead / explore-change`; the missing piece is making creation + source linkage + canonical routing one required materialization postcondition rather than accepting tracker existence alone.

## What Changes

- Define a required separate follow-up as fully materialized only when exactly one deduplicated tracker has `Change: unset`, exact source Issue/Change/defer-decision linkage, and canonical `agent:lead + action:explore-change` routing.
- Require the Lead action that owns the approved defer decision to create or reuse that tracker and complete the whole postcondition before treating the obligation as satisfied.
- Make interrupted create-before-route recovery idempotent: repair the unique matching incomplete tracker after fresh reconstruction instead of creating a duplicate; ambiguous/multiple matches fail closed.
- Strengthen lifecycle preparation/finalization so an inert, malformed, or ambiguously duplicated required tracker cannot satisfy required-follow-up obligations or permit false lifecycle completion.
- Keep dispatcher semantics unchanged: canonical routing remains authoritative and missing routing is never inferred from Issue prose.
- Define bounded repair semantics for existing malformed trackers such as #98 using the independently approved source obligation/linkage rather than the tracker text as self-authority.

## Capabilities

### Modified

- `scheduled-agent-workflow`
  - make required-separate-follow-up materialization routing-complete, idempotently repairable, and fail-closed at lifecycle verification boundaries.

## Scope Boundaries

In scope:
- required separate/deferred follow-up producer postconditions;
- exact source linkage needed for reconstruction;
- partial-failure/idempotent repair semantics;
- lifecycle preparation/finalization fail-safe checks;
- regression coverage reproducing #98.

Out of scope:
- redesigning the dispatcher or pre-activation queue;
- inferring routing from Issue prose;
- changing Human-reserved authority semantics;
- broadening Agent authority to create arbitrary Explore work;
- performing the substantive `openspec-semantic-adapter` Skill conversion tracked by #98.

## Evidence and Intent

- #100 decision-complete Explore: issuecomment-5343343331.
- #98 is open with no routing labels despite being the required separate follow-up created from #85.
- Archived #85 proposal explicitly keeps conversion of `agents/skills/openspec-semantic-adapter.md` as separate follow-up work.
- Current `agents/roles/lead.md` already requires approved required deferred follow-up to be created/reused with source linkage, `Change: unset`, and direct `Lead / explore-change` routing.
- Current dispatcher already consumes coherent routed Explore without generic Human approval, so producer correction is narrower than dispatcher inference.

## Traceability

- Routing-complete materialization invariant -> scheduled-agent-workflow ADDED requirement `Required separate follow-up materialization is routing-complete` -> Design D1 -> Slice 1.
- Interrupted partial creation / duplicate prevention -> same requirement -> Design D2 -> Slice 2.
- Lifecycle fail-safe + #98 repair/no-prose-inference -> same requirement -> Design D3 -> Slice 3.

Refs #100
