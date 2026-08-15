# Change: Refine Lead Explore authority

## Why

The current Scheduled-Agent contract requires Human admission for every Formal Explore and a second generic Human proceed decision after `PROPOSAL_READY`. #52 established two concrete problems with that boundary: it can interrupt same-Issue progress after decision-complete Explore, and it prevents Lead from autonomously advancing material work that is already entailed by approved repository direction or by demonstrated behavior-preserving workflow/maintenance friction.

The correction must preserve Human ownership of genuinely new project direction, material scope/behavior trade-offs, explicit risk acceptance, and materially different security/privacy/cost/operational commitments. It must also prevent Agent-generated Issues from recursively becoming authority for more Agent-generated backlog.

## What Changes

- Permit Lead, only from the bounded idle-discovery boundary, to materialize at most one `Change: unset + Lead / explore-change` candidate when admission is independently grounded in an applicable default-branch canonical requirement, a reconstructable required-deferred obligation, an explicitly governed README project-direction commitment, or concrete material behavior-preserving maintenance/friction evidence.
- Define minimum reconstructable autonomous-admission evidence and require later reconstruction to validate the cited source/materiality rather than trust an Agent-authored assertion.
- Keep `intake:approved` Human-only; autonomous repository-authorized Explore admission does not manufacture or consume it.
- Define README as the project-level description/direction SSOT while distinguishing explicit prospective project-direction commitments from descriptive/current-state, non-goal, example, or merely deferred text that cannot authorize autonomous workflow admission.
- Allow valid Human-admitted or repository-authorized Explore to flow from `PROPOSAL_READY` directly to same-Issue `Lead / propose-change` when the proposed direction remains inside the admitted authority envelope and introduces no new Human-reserved decision.
- Keep Human escalation for new direction, material scope/behavior trade-offs, explicit risk acceptance, materially different commitments, contradictory authority, or materially changed evidence/governance.
- Add noise and self-feeding controls: workflow work wins over idle discovery, deduplicate unresolved candidates, materialize at most one candidate per idle invocation, and prohibit Agent-created advisory/ticket conclusions from recursively serving as admission authority by themselves.

## Scope

Affected capability:
- `scheduled-agent-workflow`

In scope:
- Formal Explore admission and Explore → Propose authority;
- bounded idle discovery/materialization;
- README project-direction presentation/authority boundary;
- Lead/Explore runtime specialization and focused regression tests;
- interaction with existing same-role continuation semantics.

Out of scope:
- autonomous product-roadmap ownership;
- global priority/scoring systems;
- central dispatcher/workflow engine;
- scan cursors, TTL coverage registries, leases, heartbeats, retry/progress state, or hidden backlog state;
- a second Explore lifecycle or new normal action;
- weakening Reviewer, merge, archive, or Human-reserved risk/scope gates.

## Durable source decisions

- Coordination Issue: #52
- Superseding revised Explore result: `issuecomment-5303803193`
- Human scope revision: `issuecomment-5303691369`
- Human README/SSOT clarification: `issuecomment-5303701665`
- Human proceed decision: `issuecomment-5303816381`
- #50 same-role continuation is an already-approved dependency consumed by this change; it is not redefined here.

## Deferred work

- Archive PR creation ownership/environment-constraint normalization remains tracked separately by #58.
- Human-authority provenance hardening remains tracked separately by #47.
- Python Ruff security and prompt/Agent security work remain separate tracked changes.
