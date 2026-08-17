# Proposal: Clarify Scheduled-Agent operational flow control

## Why

The Scheduled-Agent lifecycle is deterministic and reconstructable, but production incidents show that lifecycle stage, execution eligibility, queue/WIP, and external waiting are still easy to conflate. This has contributed to multiple-active activation, premature Issue closure, durable required follow-ups that were not runnable, and attempts to model operational waits as if they were lifecycle states.

Current default-branch governance already contains most safety primitives. The missing change is a small, explicit flow-control contract that composes those primitives without creating another workflow state machine.

## What Changes

- Define execution eligibility/blocking as a derived condition over the existing role/action lifecycle. CI/Human/environment/dependency waits remain action-specific durable evidence, not new workflow states or a global `blocked` enum.
- Make the existing single-active invariant explicit as formal WIP=1: a blocked formal workflow still consumes WIP, so queued work cannot activate merely because the active workflow is waiting.
- Require active/terminal-pending workflow cardinality and Issue-state/routing coherence to be established before pre-activation queue or visualization decisions; contradictory closed/nonterminal state fails closed.
- Allow an approved still-applicable required separate follow-up to be materialized/reused directly as repository-authorized `Change: unset + Lead / explore-change`, while optional/out-of-scope/deferred prose remains non-admitted.
- Allow a valid pre-activation direct-Propose intake to route conservatively to Explore while `Change: unset` when proposal readiness is insufficient, then return to Propose only after `PROPOSAL_READY`, using existing same-role continuation semantics.
- Keep GitHub Project/Kanban and flow metrics as derived presentation only; they do not become execution authority.

## Affected capabilities

- `scheduled-agent-workflow` — operational eligibility, WIP/queue ordering, deferred-follow-up admission, pre-activation fallback, and state-coherence rules.

## Scope boundaries

In scope:
- repository Scheduled-Agent governance and the directly mapped Lead action contracts required to express the above behavior;
- deterministic regression coverage for the observed state/queue/fallback incidents.

Out of scope:
- new lifecycle states such as `Waiting CI`, `Paused`, or `Environment Limited`;
- a global blocker label/result taxonomy, priority scoring engine, expedite lane, claim/lease/heartbeat, retry counter, hidden backlog, or second workflow DAG;
- external Scheduled Task enable/disable policy or guaranteed wake-source liveness;
- removing Lead `MERGE_AUTHORIZED` or redesigning Reviewer/Executor merge authority;
- GitHub Project becoming a workflow authority source.

## Evidence / trace

Source: #65 decision-complete Explore `issuecomment-5317001684`, including the #40 premature-close incident, #48/#49 multiple-active incident, required-follow-up routing incidents (#49/#63), direct-Propose fallback hypothesis, scheduler auto-pause observation, and active-workflow enumeration failure case.

Baseline: default branch `634440b17b1b779e61b619fd7742e2496edcdbab`.