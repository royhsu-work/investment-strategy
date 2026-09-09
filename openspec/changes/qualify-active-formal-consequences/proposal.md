# Change: Qualify active formal consequences

## Why

Issue #229 is the current pre-activation workflow for a bounded repository-wide correctness refinement. Its exact same-Issue Explore result, issuecomment-5595057852, is a durable ACTION_RESULT with PROPOSAL_READY at default-branch revision e4dcad8ad0326a6a38620998ee2f03ebcc060a19. The result identifies a narrow gap: the current ingress treats structurally valid Issue fields as authoritative current state, while the effect layer can accept an active route when it merely equals the requested target. That permits an out-of-band formal route to become eligible without affirmative repository-owned qualification.

The current Human direction in issuecomment-5594516745 and issuecomment-5594806867 requires a phase distinction. Change: unset remains compatible with legitimate bounded Explore and Propose intake, including Human-requested Explore, idle discovery, and scope-split intake. Once Change is non-unset, active formal routing, derived successor, and terminal consequences require affirmative repository-owned qualification. Consequence authority belongs to the repository-owned application and executable model; actor identity alone is not authority. No new Human decision is required for this bounded formalization.

## Upstream verification

Before persisting a Change identity, Propose dereferenced the exact durable same-Issue Explore result issuecomment-5595057852 and reverse-verified each material formalization claim against fresh current default-branch evidence:

| Explore claim | Fresh current evidence | Verification |
| --- | --- | --- |
| Current ingress promotes structural Issue validity to current-state authority | src/investment_strategy/scheduled_agent_runtime.py normalizes labels, Change, timestamps, and closed-state fields into authoritative observations; acquire_current_github_preflight passes those observations to dispatch | Confirmed |
| The effect layer accepts an active route when it equals the requested target | src/investment_strategy/scheduled_agent_effects.py currently returns success for a matching observed route before consulting its formal evidence set | Confirmed |
| Existing provenance primitives are reusable | The runtime already recognizes GitHub Actions authorship, and the effect layer already parses bounded formal Action/Result markers and observes comment postconditions | Confirmed |
| The current direction is bounded and does not require a new decision | Fresh Human comments issuecomment-5594516745 and issuecomment-5594806867 preserve the same scope, phase distinction, and explicit non-goals; no newer direct Human decision was found | Confirmed |

Fresh repository reconstruction also confirmed that main is e4dcad8ad0326a6a38620998ee2f03ebcc060a19, Issue #227 is completed, Issue #229 is the sole open pre-activation Propose candidate, and Issue #218 remains downstream and out of scope. The current default-branch governance, executable Action model, OpenSpec configuration, Lead role, and OpenSpec Change Skill were loaded from main. The existing canonical active-formal provenance requirement is the scheduled-agent-workflow owner and is modified in this Change; no competing workflow requirement is added.

## What changes

- Add one project-wide repository-governance requirement: an active formal machine-decidable consequence needs one canonical owner and an affirmative fresh-evidence qualification predicate. The shared requirement defines ownership and the failure rule; it does not duplicate the workflow-specific predicate.
- Modify the existing scheduled-agent-workflow requirement Active formal transitions require repository-owned provenance so qualification is required during current-state reconstruction and dispatch ingress, before an active formal state can authorize work or a consequence. The concrete predicate binds the accepted repository-owned Action/Result, source and default-branch revisions, model-derived successor, and exact durable postcondition.
- Update the existing runtime, application, and test surfaces only as needed to make the current executable owner enforce that contract. Reuse ObservationProvenance, the finite Action/Result model, application reauthorization, existing formal evidence parsing, carrier plans, and postcondition observation.
- Keep openspec/config.yaml unchanged unless implementation evidence shows that its current authoring guidance is insufficient; no authoring rule is duplicated in the new delta.

## Acceptance boundary

The Change is complete when:

1. A Change: unset Issue remains eligible through the existing pre-activation contract, including legitimate bounded Explore, idle discovery, scope split, and Propose behavior.
2. A repository-owned formal transition with fresh authorization, exact evidence binding, and its durable postcondition is classified QUALIFIED.
3. A direct, connector-authored, equal-but-unqualified, missing, stale, ambiguous, contradictory, incomplete, or merely structural active formal state is classified INDETERMINATE and fails closed before dispatch or consequence.
4. An exact authorized carrier plan and later observed postcondition can be qualified by the next fresh repository-owned wake; the carrier remains an actuator without workflow authority.
5. Formal priority, single-active-workflow/WIP, finish-first, no-rewind, and no-fallback semantics remain unchanged.
6. No new Action, Result kind, workflow phase/state, registry, cursor, mailbox, policy engine, carrier protocol, or second DAG is introduced.

## Scope and non-goals

In scope are the two canonical specification owners, the existing executable current-state/dispatch and application/effect boundaries, and focused regression tests for the acceptance boundary. The only formal workflow target is Issue #229.

Out of scope are Issue #218, historical Issue reopening or rewriting, semantic correctness that requires Human or mapped Role judgment, generic provenance/security frameworks, new persistent workflow state, new transport or GitHub App infrastructure, ruleset redesign, and unrelated product behavior.

## Delivery

This is one independently reviewable implementation stage. The stage records the complete affirmative-qualification outcome, its N-1 prerequisites, vertical implementation slices, and executable exit checks. The application owns Change materialization and later lifecycle routing; this Propose result does not execute a successor in the current wake.
