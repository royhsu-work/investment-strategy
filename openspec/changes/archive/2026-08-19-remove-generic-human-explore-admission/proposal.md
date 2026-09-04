# Change: Remove generic Human admission from Formal Explore

## Why

The current Scheduled-Agent workflow treats initial `Lead / explore-change` admission as a Human-reserved boundary unless a bounded repository-authorized origin is separately reconstructed. Durable history from #84/#85/#86/#88/#91 shows that this makes routine bounded research depend on how the ticket entered GitHub rather than on whether the research itself requires Human judgment. That creates redundant approval friction in an otherwise non-interactive workflow.

Formal Explore is intentionally pre-Change: it keeps `Change: unset`, creates no OpenSpec artifacts, modifies no implementation code, and cannot itself consume a later Human-reserved product/scope/risk decision. The Human gate therefore belongs at genuine commitment/authority boundaries, not at routine research startup.

## What Changes

- Make an open, coherently routed `Change: unset + agent:lead + action:explore-change` Issue eligible for the deterministic pre-activation queue without requiring Human admission merely to execute Explore.
- Keep formal/terminal WIP finish-first behavior, deterministic `created_at`/Issue ordering, stale-run safety, and routing validity unchanged.
- Keep Scheduled-Agent creation of new routed Explore work bounded by existing independent-evidence, materiality, deduplication, and one-candidate idle-discovery rules. Dispatcher eligibility does not become creation authority.
- Preserve provenance-bound Human authority for direct `Lead / propose-change`, Human-only advisory admission, canonical `HUMAN_DECISION_REQUIRED` answers/resume, and every other explicitly Human-reserved decision.
- Keep `PROPOSAL_READY → Lead / propose-change` non-interactive only while formalization stays within the bounded researched/canonical evidence and introduces no new Human-reserved commitment.
- Remove the now-redundant #88 creation-bound Human Explore shortcut and the general Explore-admission decision-ref path instead of retaining parallel equivalent admission mechanisms.
- Migrate existing routed `Change: unset + Lead / explore-change` tickets into the ordinary deterministic Explore queue once this change is authoritative, subject to their dependencies and current durable state.

## Affected Capabilities

### Modified

- `scheduled-agent-workflow`
  - pre-activation Explore eligibility and queue selection;
  - Human-authority boundary mapping;
  - bounded Explore creation/admission semantics;
  - same-Issue Explore-to-Propose continuation;
  - migration of existing routed Explore tickets.

## Scope

In scope:

- Scheduled-Agent governance/spec/role/skill wording needed to separate Explore execution eligibility from Human authority.
- Removal of Explore-only Human admission implementation/adapters and README orientation that become unused.
- Regression coverage for routing/queue safety and remaining Human-only provenance behavior.

Out of scope:

- Weakening the general provenance-bound Human decision predicate.
- Treating GitHub Connector/App activity as Human activity.
- Removing direct-Propose Human admission, advisory admission, or `HUMAN_DECISION_REQUIRED` authority checks.
- Broadening autonomous Agent authority to create arbitrary Explore tickets.
- Redesigning the queue, adding priority scoring, locks, leases, delegation tokens, hidden state, or another workflow DAG.
- Performing the separate substantive follow-up scopes tracked by #83, #86, #98, or #100.

## Traceability

- Source decision-complete Explore: #93 issuecomment-5338928784.
- Historical friction/evidence: #84, #85, #86, #88, #91.
- Existing Human-provenance hardening remains authoritative for genuine Human-only boundaries.
- Capability delta: `specs/scheduled-agent-workflow/spec.md`.
- Design: `design.md`.
- Implementation slices: `tasks.md`.
