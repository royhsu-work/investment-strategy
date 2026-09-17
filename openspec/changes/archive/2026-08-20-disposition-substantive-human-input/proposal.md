# Proposal: disposition substantive Human input before consequential workflow boundaries

## Why

#105 demonstrated that a direct Human question on the persistent coordination Issue (`issuecomment-5346223908`) could remain undispositioned while later Scheduled-Agent actions emitted READY/review/handoff evidence. The question was only caught later and converted into a Reviewer finding. Current contracts reconstruct selected workflow artifacts but do not uniformly require a fresh coordination-Issue Human-input check immediately before consequential results or unsafe mutations.

This is a workflow-integrity gap: durable Human input can become operationally invisible even though the repository otherwise relies on fresh-read and contradictory-evidence preconditions.

## What Changes

- Add one shared governance invariant requiring a fresh check for newer direct-Human coordination-Issue comments before consequential workflow boundaries.
- Require material workflow-relevant Human input to receive an explicit durable disposition by exact comment id before READY, review PASS/findings completion, lifecycle handoff/finalization, or merge mutation can proceed when that input could affect the decision.
- Preserve role authority: the current role may answer only within its authority; implementation defects use existing correction paths, specification/scope questions route to Lead, and genuine Human-reserved decisions continue to use the existing provenance-bound `HUMAN_DECISION_REQUIRED` contract.
- Treat clearly non-substantive/administrative Human comments as non-blocking only with a bounded disposition when they are encountered at the consequential boundary.
- Use direct-Human raw creation provenance to distinguish Human-authored candidate comments from connector/App-authored workflow messages; this check does not itself grant Human authority.
- Add action-local consumption only where needed and executable regression fixtures reproducing the #105 timing cases.

## Capabilities

### Modified capabilities

- `scheduled-agent-workflow`: add a shared requirement that consequential workflow boundaries cannot silently skip newer substantive direct-Human coordination-Issue input.

### New capabilities

- None.

## Scope

In scope:

- shared Scheduled-Agent governance for Human-input freshness/disposition;
- minimum affected Lead/Reviewer/Executor action procedures;
- durable message presentation where a result needs to reference an exact Human comment disposition;
- executable workflow regression coverage.

Out of scope:

- changing the provenance-bound Human-reserved authorization model;
- treating every Human comment as approval, authority, or an automatic blocker;
- a comment queue, unread counter, new lifecycle action/status, generic blocker state, lock/lease/heartbeat, or second workflow DAG;
- reopening or changing #105 behavior after its completed lifecycle;
- general GitHub notification/inbox behavior.

## Evidence and traceability

- Source incident: #105 `issuecomment-5346223908` and detection `issuecomment-5346661630`.
- Decision-complete Explore: #107 `issuecomment-5348616467`.
- Current default-branch baseline used for Propose: `77ba3d9b746dc05f562626d13937f9c672996ba9`.
- Behavioral contract is specified in `specs/scheduled-agent-workflow/spec.md`.
- Design decisions D1-D6 in `design.md` implement the capability requirement without creating parallel workflow state.
- Tasks in `tasks.md` trace the behavioral scenarios into executable regressions and governed-surface changes.

## Impact

The change strengthens existing fail-closed/reconstruction semantics and may cause a scheduled action to stop or route to the correct owner when a newly posted direct-Human comment materially affects the evidence being relied upon. Clearly non-substantive Human comments do not create a new waiting lifecycle. Human-reserved authority remains unchanged.