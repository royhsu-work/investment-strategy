# Change: Fix machine dispatch recovery liveness

## Why

#155 reproduced a self-hosting failure in the deployed workflow-dynamic dispatcher after #140 completed. With no open formal workflow, production acquisition enters detailed exceptional closed-history reconstruction before it may authorize a queued pre-activation Issue. Historical Issue #91 contains two canonical `LIFECYCLE_COMPLETE` journals for the same completed workflow. The current terminal recognizer treats more than one valid completion journal as `indeterminate`, so an at-least-once replay of the same terminal fact becomes repository-wide `FAIL_CLOSED` and prevents otherwise legal pre-activation work from starting.

The failure exposes two related responsibility defects in the current dispatch contract:

1. formal-zero dispatch unconditionally pays detailed historical recovery cost before pre-activation selection or `NO_WORK`, even when a bounded complete structural projection can prove that no closed Issue is capable of changing current authorization; and
2. terminal evidence uniqueness is inferred from comment cardinality instead of semantic consistency, so repeated equivalent durable evidence is treated as contradiction.

The safety goal is not to weaken `FAIL_CLOSED`. It is to reserve `INDETERMINATE` for missing/incomplete/unqualified authoritative input or genuinely contradictory facts, while deterministically classifying evidence that is sufficient to prove one outcome.

## What Changes

- Modify the existing `scheduled-agent-workflow` dispatch contract so formal cardinality zero uses the same bounded, complete structural closed-workflow conflict projection before detailed exceptional recovery.
- When that structural projection is `CLEAR`, allow the executable dispatcher to select the deterministic eligible pre-activation winner or return `NO_WORK` without fetching detailed terminal/recovery evidence for unrelated historical closed workflows.
- When the structural projection is `POSSIBLE_CONFLICT` or `INDETERMINATE`, preserve detailed exceptional recovery before any pre-activation authorization or `NO_WORK` result.
- Classify multiple canonical terminal completion journals by semantic consistency rather than raw comment count. Repeated journals that establish the same terminal fact are one idempotent at-least-once completion; conflicting immutable terminal identity/evidence remains `INDETERMINATE` and fails closed.
- Keep detailed recovery scoped to closed candidates that can actually affect current recovery/conflict classification instead of treating every historical completed workflow as a mandatory forensic input.
- Include a bounded machine-owned diagnostic reason for `NO_WORK` and `FAIL_CLOSED` dispatch decisions so the durable no-API decision exposes the classifier's reason without adding an Issue/Role/Action tuple or giving the model override authority.
- Add production-path regression coverage reproducing the #91 duplicate-terminal-history + formal-zero + queued-Explore failure and proving that equivalent replay no longer seals the pre-activation queue.

## Scope

Affected capability:
- `scheduled-agent-workflow`

In scope:
- `src/investment_strategy/scheduled_agent_runtime.py` acquisition/orchestration needed to apply bounded structural closed-conflict screening at formal cardinality zero;
- `src/investment_strategy/workflow_dispatch.py` terminal/recovery classification contract where required to distinguish equivalent terminal replay from genuine contradiction;
- `src/investment_strategy/issue_comment_bridge.py` bounded non-authorization diagnostic presentation for `NO_WORK` / `FAIL_CLOSED`;
- the existing canonical `Active-workflow cardinality and Issue-state coherence precede queue selection` requirement and directly related no-API dispatch-decision behavior;
- focused regressions for structural-clear formal-zero dispatch, exceptional recovery retention, terminal replay identity, contradictory terminal evidence, and diagnostic publication;
- only the minimum shared governance wording needed to stop requiring unconditional detailed formal-zero history reconstruction after the executable contract changes.

Out of scope:
- removing or weakening WIP=1, complete current open-Issue enumeration, provenance qualification, deterministic pre-activation ordering, exact selected action identity, stale-state rejection, or effect-time reauthorization;
- automatic recovery of ambiguous or genuinely contradictory closed workflow state;
- changing the premature-close recovery ownership or topology;
- locks, leases, heartbeats, retry counters, hidden durable state, caching as authorization evidence, or a second workflow DAG;
- lightweight Python/control-plane packaging or removal of `uv run` from bridge/runtime workflows;
- the separate `scheduled-agent-runtime.yml` `PYTHONPATH` execution defect unless implementation proves it is inseparable from this Change's dispatch semantics;
- the broader executable-governance inventory tracked by #138.

## Durable source decisions and evidence

- Coordination Issue: #155
- First-principles investigation: `issuecomment-5405282007`
- Decision-complete interactive Explore evidence: `issuecomment-5405497269`
- Exceptional self-hosting bootstrap record: `issuecomment-5405643748`
- Production reproduction source: closed workflow #91 with canonical completion comments `5333895069` and `5335505763`
- Baseline default-branch revision used to activate this Change: `00a0e5a2c8068077faf5d18980e4a6f84f72f74e`
- Prior approved boundary being corrected: archived Change `validate-no-api-issue-comment-bridge`, which intentionally retained unconditional detailed exceptional recovery for formal cardinality zero.

The bootstrap record is audit provenance for this exceptional self-repair only; it is not a synthesized machine `AUTHORIZE` and does not become a reusable normal-dispatch bypass. After #155 was activated as the sole formal workflow, the normal formal lifecycle resumes from current durable state.

## Deferred work

The lightweight control-plane runtime optimization identified by #155 remains independently reviewable follow-up work: proving and adopting the minimum Python execution environment for the bridge/dispatch path should not be coupled to this authorization/recovery semantic correction.
