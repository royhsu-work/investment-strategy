# Change: Fix machine dispatch recovery liveness

## Why

#155 reproduced a self-hosting failure in the deployed workflow-dynamic dispatcher after #140 completed. The failure was triggered by historical Issue #91, but #91 is already terminal history: its imperfect duplicate completion journal should not participate in authorization for unrelated current work.

Reviewer finding `issuecomment-5406357205` identified the remaining defect in the first proposal revision: replacing full closed-history forensics with a structural projection still makes every normal dispatch depend on a repository-history-sized closed set. That cost grows with accumulated history and does not satisfy #155's explicit requirement to avoid `O(repository-history)` normal-path reconstruction.

The safety boundary is therefore narrower: normal dispatch must authorize from **current unresolved obligations**, not from repeated re-adjudication of completed history. `FAIL_CLOSED` remains strict for incomplete or contradictory current evidence and genuine unresolved recovery state.

## What Changes

- Define normal workflow-dynamic selection from a complete provenance-qualified snapshot of current open Issues plus a bounded current unresolved-recovery set; completed closed workflow history is not normal authorization input.
- Reuse existing routing state instead of adding a recovery registry: a coordination Issue that is closed while it still retains an `agent:* + action:*` routing tuple is an explicit unresolved closed-routing candidate.
- Make repository-owned terminal close effects retire the workflow routing tuple in the same logical Issue mutation that closes the Issue, while preserving unrelated labels. Closed completed Issues therefore become closed + unrouted terminal history.
- Include one bounded rollout migration/reconciliation for pre-existing closed routed workflow Issues. Entries proven terminal/retired have workflow routing removed; genuine unfinished obligations remain explicit recovery work; ambiguous/incomplete entries fail closed. Until that normalization succeeds, retained legacy routing remains visible as unresolved debt and normal dispatch may remain fail closed rather than silently bypassing it.
- After normalization, normal unresolved-recovery acquisition queries only current closed Issues that still retain workflow routing labels. No activation flag, cutover cursor, timestamp watermark, cache, or recurring historical scan remains.
- If the current unresolved-recovery set is empty, normal dispatch uses only current open formal/pre-activation state. If one closed-routing candidate exists, detailed recovery evaluates only that candidate. Multiple candidates, incomplete enumeration/provenance, or genuinely contradictory recovery evidence remain `FAIL_CLOSED`.
- Keep semantic duplicate-terminal classification for migration and exceptional recovery: compatible repeated `LIFECYCLE_COMPLETE` journals are idempotent replay; conflicting immutable terminal facts remain indeterminate. This classifier no longer justifies keeping terminal history on the normal hot path.
- Include a bounded machine-owned diagnostic reason for `NO_WORK` and `FAIL_CLOSED` decisions without adding an Issue/Role/Action tuple or model override authority.
- Add production regressions proving that an already completed #91-like workflow does not participate in ordinary dispatch after normalization, while a genuinely premature close remains discoverable and recoverable from its retained routing tuple.

## Scope

Affected capability:
- `scheduled-agent-workflow`

In scope:
- `src/investment_strategy/scheduled_agent_runtime.py` current-state acquisition/orchestration needed to replace repository-history projection with bounded unresolved closed-routing acquisition;
- `src/investment_strategy/workflow_dispatch.py` current unresolved-recovery classification and exceptional terminal-evidence semantics;
- `src/investment_strategy/issue_comment_bridge.py` bounded non-authorization diagnostic presentation for `NO_WORK` / `FAIL_CLOSED`;
- repository-owned terminal Issue close effect semantics needed to retire routing labels while preserving unrelated labels;
- one bounded exact-evidence migration/reconciliation of pre-existing closed routed workflow Issues during rollout, with fail-closed transition until normalized;
- the canonical `Actionable workflow routing is one logical role/action tuple` and `Active-workflow cardinality and Issue-state coherence precede queue selection` requirements, plus directly related no-API decision behavior;
- minimum shared-governance wording required to remove normal closed-history projection while preserving WIP=1, premature-close recovery, and fail-closed boundaries.

Out of scope:
- weakening complete current open-Issue enumeration, provenance qualification, WIP=1, deterministic pre-activation ordering, exact selected action identity, stale-state rejection, or effect-time reauthorization;
- automatically resolving ambiguous or genuinely contradictory recovery state;
- a generic recovery registry, new workflow lifecycle status, activation flag, lock, lease, heartbeat, retry counter, cursor/watermark, or cache-based authorization;
- lightweight Python/control-plane packaging or removal of `uv run` from bridge/runtime workflows;
- the separate `scheduled-agent-runtime.yml` `PYTHONPATH` execution defect unless implementation proves it is inseparable from this Change's authorization semantics;
- the broader executable-governance inventory tracked by #138.

## Durable source decisions and evidence

- Coordination Issue: #155
- First-principles investigation: `issuecomment-5405282007`
- Decision-complete interactive Explore evidence: `issuecomment-5405497269`
- Exceptional self-hosting bootstrap record: `issuecomment-5405643748`
- Reviewer finding requiring current-unresolved-obligation semantics: `issuecomment-5406357205`
- Production reproduction source: closed workflow #91 with canonical completion comments `5333895069` and `5335505763`; #91 is terminal history and is evidence of the responsibility-boundary defect, not a current recovery obligation.
- Baseline default-branch revision for this correction: `00a0e5a2c8068077faf5d18980e4a6f84f72f74e`.

The bootstrap record is audit provenance for this exceptional self-repair only; it is not a synthesized machine `AUTHORIZE` and does not become a reusable normal-dispatch bypass.

## Deferred work

The lightweight control-plane runtime optimization identified by #155 remains independently reviewable follow-up work: proving and adopting the minimum Python execution environment for the bridge/dispatch path should not be coupled to this authorization/recovery semantic correction.
