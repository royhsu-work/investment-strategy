# Change: Validate no-API bridge and executable dispatch

## Why

The repository already contains production dispatch and effect-gating code, but the currently deployed Scheduled Agent GitHub Actions worker invokes the OpenAI Responses API. That does not prove the runtime path required by the actual ChatGPT Scheduled Task environment, where the model invocation originates in ChatGPT and repository-owned executable code must be reached without requiring an OpenAI API worker.

#140 first established a bounded transport prerequisite: one ChatGPT Scheduled Task invocation must be able to write an exact GitHub Issue comment, trigger default-branch GitHub Actions, execute bounded repository-owned code, and read back the exact correlated result. Subsequent Human scope correction and independent review established that transport alone is not lifecycle-complete for this Change. The same Change must also connect that proven no-API boundary to production pre-model dispatch and remove deterministic Issue-selection judgment from model-side natural-language reconstruction.

The current production runtime also demonstrates unnecessary coupling: ordinary dispatch acquires `state=all` Issues and reconstructs terminal comments, Human retirement evidence, legacy archive state, and closed-Issue re-observation before it may select an otherwise unambiguous open formal workflow. Correctness still requires a bounded structural closed-workflow conflict guard before a sole open formal workflow is authorized and detailed premature-close recovery whenever a possible conflict exists or open formal cardinality is zero, but it does not require every normal active-workflow selection to pay the full historical forensic cost.

## What Changes

- Add a standalone GitHub `issue_comment` transport canary that accepts only a bounded `DISPATCH_REQUEST` comment on one explicitly configured Human-created check-in Issue.
- Use the GitHub request comment ID as the sole correlation identity; do not introduce a custom request UUID and do not correlate by latest comment.
- Execute bounded repository-owned code from the current default-branch checkout and write an exactly correlated transport result; malformed, unrelated, repeated, or already-completed requests fail closed or become idempotent no-ops.
- Make `src/investment_strategy/workflow_dispatch.py` the single production normal-selection classifier consumed by runtime and regression tests. Normal selection deterministically returns an exact Issue/Role/Action, `NO_WORK`, or `FAIL_CLOSED` from the minimum provenance-qualified current Issue facts required for selection, consuming existing executable admission evaluators rather than interpreting admission prose.
- Separate normal open-Issue selection from detailed closed-history/premature-close recovery. Before a sole open formal workflow is authorized, a bounded complete structural projection must prove that no closed workflow-looking Issue can still be a conflicting unfinished/premature-close candidate; only a possible or indeterminate conflict enters detailed exceptional recovery/consistency evaluation. When open formal cardinality is zero, the bounded exceptional recovery gate still runs before either pre-activation authorization or `NO_WORK`.
- Keep PR, CI, OpenSpec, review, and effect-specific evidence out of global Issue selection. After an exact Issue/Role/Action is selected, the mapped action/effect preconditions own those correctness checks.
- Simplify default-branch dispatch governance so it defines authority, required authoritative input provenance, result meanings, and fail-closed boundaries while executable code owns deterministic classifier mechanics rather than duplicating that algorithm in natural-language instructions.
- After the bridge and corrected production dispatch are deployed to the default branch, extend the no-API path to return the exact correlated production dispatch decision and prove in one real ChatGPT Scheduled Task invocation that the model consumes that machine-selected identity instead of selecting Issue/Role/Action itself.
- Preserve the existing one-Change/multi-PR lifecycle: deployment prerequisites may merge first, but `finalize-change` returns `MORE_IMPLEMENTATION_REQUIRED` until the approved dispatch correction and real no-API machine-dispatch proof are complete.

## Scope

Affected capability:
- `scheduled-agent-workflow`

In scope:
- one standalone default-branch `issue_comment: created` bridge workflow and bounded repository-owned request/result handler;
- explicit check-in Issue configuration and exact request-comment-ID correlation/idempotency;
- `src/investment_strategy/workflow_dispatch.py` normal-selection responsibility and production classifier contract;
- `src/investment_strategy/scheduled_agent_runtime.py` acquisition/orchestration changes needed to separate normal open-Issue selection, bounded structural closed-conflict clearance, and detailed exceptional recovery/history reconstruction;
- consumption of existing executable admission authority such as `src/investment_strategy/human_authority.py` where queue eligibility requires it, without creating a second Human-authority algorithm;
- the minimum executable structural conflict guard required before sole-formal authorization plus the detailed premature-close recovery boundary required when a possible conflict exists or before pre-activation/`NO_WORK` at open formal cardinality zero;
- `agents/AGENTS.md` dispatch-governance simplification needed to consume executable decisions without duplicating their deterministic algorithm;
- focused production-path regression coverage for WIP=1, deterministic pre-activation selection, executable direct-Propose admission, incomplete/provenance-invalid fail-closed behavior, structural-conflict/recovery separation, and model-side selection exclusion;
- real no-API bridge evidence for both transport feasibility and, after deployment, exact production machine-dispatch readback.

Out of scope:
- consequential effect application or stale-state mutation authorization beyond preserving the existing boundary;
- mechanical no-bypass/capability separation;
- automatic daily check-in Issue creation or closure;
- multi-repository control-plane work;
- changing workflow topology in `agents/workflow.md`, role authority, or mapped Skills unless implementation proves an independently governed correction is unavoidable;
- #137 proposal-entry feasibility policy or #138 executable/semantic context reduction;
- removing the existing Responses API runtime path merely to complete this Change.

## Durable source decisions

- Coordination Issue: #140
- Human Phase 1 refinement: `issuecomment-5386416122`
- Decision-complete Explore result: `issuecomment-5386482159`
- Human scope correction: `issuecomment-5387096717`
- Independent Reviewer finding requiring same-Change dispatch correction: `issuecomment-5387268115`
- Independent Reviewer finding preserving open-formal + premature-close conflict safety: `issuecomment-5387597295`
- Lead accepted structural-conflict correction boundary: `issuecomment-5387856571`
- Explore baseline revision: `cb8f9ec12d826e0d71897a4c73ece961d00df59e`

The Phase 1 refinement remains authoritative for the transport correlation contract: the exact GitHub request comment ID replaces the earlier custom `request_id` wording. The later scope correction supersedes only the earlier transport-only lifecycle boundary: the bridge remains the first deployment proof, but production pre-model dispatch correction and live machine-selection proof are now required before this Change may complete. The later Reviewer/Lead correction preserves the existing fail-closed conflict invariant without restoring unconditional detailed closed-history forensics to every sole-formal wake.

## Deferred work

Consequential effect application refinements, mechanical no-bypass/capability separation, automatic check-in Issue lifecycle, multi-repository control-plane work, #137, and #138 remain outside this Change. Production pre-model dispatch itself is no longer deferred to a later Change.
