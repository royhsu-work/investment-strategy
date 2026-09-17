# Design: Refine Lead Explore authority

## Context

The repository already has one persistent coordination Issue, a deterministic single-active workflow model, bounded idle advisory behavior, optional Formal Explore, Human escalation, and same-role action continuation. The missing piece is the authority boundary: current governance treats all new Explore admission as Human-only and treats `PROPOSAL_READY` as requiring a second generic Human proceed decision.

Primary source evidence:
- #52 superseding Explore result `issuecomment-5303803193`;
- #52 Human scope revision `issuecomment-5303691369`;
- #52 README/SSOT clarification `issuecomment-5303701665`;
- #52 Human proceed decision `issuecomment-5303816381`;
- current default-branch README, `agents/AGENTS.md`, Lead/Explore skill, and canonical `scheduled-agent-workflow` spec;
- #50 same-role continuation semantics already active on default branch.

## Decision 1: Admission authority depends on independent source authority, not actor-generated ticket text

Lead may materialize Formal Explore autonomously only when the candidate traces to one independent source class:

1. an applicable default-branch canonical MUST/SHALL requirement with a concrete material gap;
2. an approved required-deferred obligation with reconstructable source linkage;
3. an explicitly governed README project-direction commitment; or
4. current concrete behavior-preserving maintenance/friction evidence above the materiality threshold.

The created Issue is evidence and coordination state, not the authority source. An Agent-authored advisory, prior Explore conclusion, or prior Agent-created ticket cannot recursively authorize another autonomous admission by itself.

## Decision 2: README remains project-direction SSOT but only explicit prospective commitments authorize admission

README continues to own project-level purpose, direction/capability boundary, and current/target framing. Runtime action semantics remain owned by `agents/AGENTS.md`; canonical behavioral contracts remain in `openspec/specs/`.

To avoid arbitrary-prose inference, autonomous admission may rely on README only when the direction is presented through an explicitly governed forward-looking commitment surface and is:

- prospective rather than merely descriptive;
- scoped enough to identify a bounded gap;
- affirmative rather than a non-goal or example;
- not marked merely deferred/uncommitted;
- non-contradictory with canonical specs and current Human-reserved decisions.

Existing descriptive baseline text and plain `deferred` lists remain non-authorizing until intentionally promoted into that commitment surface through normal governance.

## Decision 3: Bounded maintenance/friction can authorize Explore without becoming roadmap ownership

Material behavior-preserving maintenance includes demonstrated SSOT conflict, repeated workaround, recurring workflow failure, fragmented ownership, dead/circular abstraction, or equivalent structural friction when there is a concrete cost/risk mechanism and bounded ownership surface.

Rule-of-Three is sufficient evidence for a recurring pattern but not mandatory for a clear single-instance structural hazard such as dual authority or a known-always-failing normal workflow step. Style preference, speculative cleanup, and generic simplicity claims are insufficient.

## Decision 4: Autonomous materialization is an idle-only, one-candidate operation

Normal formal/terminal-pending work and already eligible pre-activation work remain ahead of idle discovery. When the idle boundary is reached, one invocation may materialize at most one candidate and must deduplicate against open/reconstructably unresolved Issues and required-deferred trackers.

The candidate shape stays deliberately small:

```text
Change: unset
agent:lead
action:explore-change
```

The Issue body/evidence records admission kind, observed default-branch revision, exact authority/evidence source, bounded problem, and why no Human-reserved decision is being made. No new routing label, approval token, priority score, cursor, lease, or backlog database is introduced.

## Decision 5: Explore admission grants bounded authority through Propose when no new Human decision appears

Both Human-admitted Explore and valid repository-authorized Explore establish an authority envelope for the admitted problem. If decision-complete Explore produces `PROPOSAL_READY` within that envelope and no new Human-reserved decision appears, Lead records the result, fresh-reads the same Issue, routes to `Lead / propose-change`, reloads the mapped skill, and may continue under the existing same-role continuation contract.

Lead must stop with `HUMAN_DECISION_REQUIRED` for:
- new product/project direction outside the admitted envelope;
- material externally observable behavior or mutually exclusive scope trade-offs not already authorized;
- explicit risk acceptance or materially different security/privacy/cost/operational commitment;
- contradictory/unrecoverable authority evidence;
- materially changed default-branch governance/evidence that invalidates the admission basis.

## Decision 6: Reconstruction validates autonomous admission evidence fail-closed

Dispatcher/Explore reconstruction does not trust the Agent-authored statement that a ticket is repository-authorized. It verifies the cited default-branch revision/source or current friction evidence, confirms the problem remains bounded/material, and confirms no Human-reserved decision was smuggled into admission. Missing, stale, contradictory, merely descriptive, or insufficient evidence fails closed.

## Blast radius

Expected implementation surfaces:
- `openspec/specs/scheduled-agent-workflow/spec.md`;
- `agents/AGENTS.md` shared admission, pre-activation, Explore completion, and idle-discovery rules;
- `agents/roles/lead.md` autonomous materialization authority/prohibitions;
- `agents/skills/openspec-explore/SKILL.md` admission-evidence reconstruction and disposition procedure;
- `README.md` only to establish an explicit project-direction commitment presentation surface if the capability is intentionally used;
- focused governance/workflow regression tests.

`openspec-change` should consume the changed authority boundary but does not need a second authorization mechanism. Existing #50 continuation remains authoritative.

## Compatibility

- New semantics activate only after merge to default branch.
- Existing Human-admitted workflows remain valid.
- Existing arbitrary README prose and current plain `deferred` lists do not retroactively become autonomous admission authority.
- Existing `intake:approved` remains Human-only and continues to serve only its existing Human-admission capability.
- Historical Explore outcomes remain governed by the contract active when written; unresolved current work is reconstructed under current default-branch governance and still-applicable Human decisions.

## Rejected alternatives

### Treat every README statement as roadmap authority
Rejected because descriptive/current-state/non-goal/deferred prose is too ambiguous to confer autonomous workflow authority.

### Create a project-direction registry
Rejected because README already owns project-level direction; a second registry would violate SSOT.

### Keep all autonomous discovery advisory-only
Rejected because it cannot advance already-authorized repository direction or recurring behavior-preserving friction without redundant Human admission.

### Add a new autonomous-admission label/token
Rejected because reconstructable source evidence plus existing routing is sufficient and avoids hidden authorization state.

### Add coverage cursor/TTL/global priority state
Rejected because no requirement currently needs exhaustive repository coverage or model-derived global prioritization.
