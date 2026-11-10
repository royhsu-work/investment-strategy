# Change: Restore exact dispatch Artifact consumption and idle-admission recovery

## Why

Issue #435 documents a production T1 failure at an existing read-only boundary. Successful native dispatch runs `42746001986` and `42751607415` produced one unexpired `dispatch-result.json` each, but the corresponding idle Application jobs in runs `42746612839` and `42752047060` exited `FAIL_CLOSED / idle-dispatch-artifact-content-unavailable`, `mutation_attempted=false`. No #218 admission occurred. The existing `_fresh_gate` catches several independent artifact-read/parser exceptions under that one reason, so the exact runner-side HTTP/redirect/bytes exception is **not yet observed**. Neither valid connector-downloaded JSON nor 31 passing focused tests establishes that the runner's own GET succeeded. The failure is reproducible as a boundary outcome, not yet as an identified transport cause.

Human requires a general, evidence-backed repair using mature engineering methods, eventual correctness and legal recovery, one producer/parser/validator contract, no extra workflow authority/state, and a real production-shaped end-to-end demonstration. This Change preserves that outcome without declaring an unverified ZIP, JSON, redirect, host, authentication, or permission hypothesis to be the cause.

## What changes

- Make the **existing** run-scoped Artifact reader retain safe, typed stage/error evidence from its actual GitHub Actions execution. Capture the original failure before choosing any transport-specific correction. Never expose credentials, signed redirect URLs, or private payloads.
- Verify the fetched bytes against the exact unique unexpired Artifact's declared identity, size/digest and successful request/run/revision correlation, and decode through the **existing canonical** `parse_dispatch_result_document`. Do not add a second JSON or ZIP contract or acceptance decision.
- Reconcile the overlapping Artifact GET/redirect logic in `scheduled_agent_dispatch_result` and `scheduled_agent_carrier` only after characterization proves compatible host, content type, bounded response and authentication behavior. Preserve trusted-redirect/no-bearer-forwarding security.
- Distinguish transient unavailable reads, untrusted redirect, malformed representation/content, integrity mismatch, stale identity, permanently invalid data, and recoverable incomplete evidence. Bounded retries may repeat **only qualified GETs** (such as 500/502/503/504 and timeouts); consequential writes are never retried on an unknown outcome.
- Preserve repository-owned idle Application preflight, normal dispatch reauthorization, atomic existing/new admission, read-only post-write reconciliation and later independent normal wake. A temporary fault must have a legal fresh-wake recovery path, while invalid or contradictory evidence remains fail-closed.
- Require RED-first production-shaped fixtures/fault injection, exact-head lint/type/tests/strict OpenSpec gates, independent Reviewer, and a **later real** NO_WORK → #218 admission → independent `explore-change` dispatch acceptance trace. CI or a simulated E2E is not production acceptance.

## Affected capability

- **Modified behavior:** `scheduled-agent-workflow` — add one externally verifiable run-scoped dispatch Artifact consumption/recovery requirement; use the already authoritative idle-admission, dispatch, and canonical wire-contract requirements without rewriting their owners.
- **No new capability or workflow dimension.** The canonical producer/schema, Action model, Role mapping, issue/PR routing, immutable Change, WIP=1 and one Action per wake remain unchanged.

## Source and authority

- Human authorization and full acceptance constraints: [#435](https://github.com/royhsu-work/investment-strategy/issues/435), established from the current conversation.
- Same-Issue, durable `Explore / PROPOSAL_READY`: [#435 comment 6760519420](https://github.com/royhsu-work/investment-strategy/issues/435#issuecomment-6760519420), accepted by Application [decision 6760518797](https://github.com/royhsu-work/investment-strategy/issues/435#issuecomment-6760518797). Propose independently checked the claims against current-main reader/idle source and exact run/Artifact metadata; the original runner-side exception remains explicitly unverified.
- Reproducing source runs: [dispatch 42746001986](https://github.com/royhsu-work/investment-strategy/actions/runs/42746001986), [dispatch 42751607415](https://github.com/royhsu-work/investment-strategy/actions/runs/42751607415), [idle 42746612839](https://github.com/royhsu-work/investment-strategy/actions/runs/42746612839), [idle 42752047060](https://github.com/royhsu-work/investment-strategy/actions/runs/42752047060). The downloaded 199-byte Artifact digests are `6cf122171ef4a82d09ed3f34e50fe65bb39a04c179beef6afce8dcc1cd6a14cd` (ID `13731193002`) and `7a9da20934c78dd4f03d62432a37901ea853e53d4e88f7f3ba0f3b84e6015625` (ID `13733163299`); each contains canonical raw JSON as observed via connector, not proven runner bytes.
- Governance and behavior baseline: `main@8bf5007c4dc6fb8368473af3aba86dbe5136a627`, `agents/AGENTS.md`, `agents/workflow.md`, `openspec/config.yaml`, `openspec/specs/scheduled-agent-workflow/spec.md`, `openspec/specs/repository-governance/spec.md`.

## Scope boundaries and proportionality

| Classification | Affected existing responsibility | Why this is sufficient |
| --- | --- | --- |
| REUSE | `issue_comment_bridge` canonical wire renderer/parser; `scheduled_agent_dispatch_result.fetch_dispatch_result` identity gate; `scheduled_agent_idle_admission._fresh_gate` and application admit/reconcile | One authoritative schema and one normal dispatch/idle consequence owner already exist. |
| CONSOLIDATE | Duplicate GitHub bytes/redirect code in `scheduled_agent_dispatch_result` versus `scheduled_agent_carrier.read_github_artifact_bytes` | One characterized adapter can serve both consumers without another parser or separate success definition. |
| NO-DELTA | Action model, WIP/finish-first, Human admission, routing, producer schema, daily shard transport, concurrency boundary, no-replay/no-rewind, write retry policy | None caused or authorizes this read failure. |
| ADD | Safe structured failure stage/cause at the existing reader/idle boundary and missing raw-byte size/digest verification | Current generic catch loses the decisive runner evidence; declared digest alone does not establish downloaded-byte integrity. These are not persistent state, a registry or a new service. |

Out of scope: #218 direct routing, #419 newline fix, a new library/framework, alternate artifact format, additional scheduler, synthetic `ACTION_RESULT`, manually triggered GitHub Actions, and feature-specific exception patches. This single-purpose Change may use sequential testable vertical slices inside the existing implementation lifecycle; it does not create additional routed Changes or relax the parent outcome.

## Production acceptance and continuation

Implementation tasks close at independently verifiable code/test checkpoints; formal OpenSpec review, implementation review, merge/archive and terminal lifecycle are **separate workflow gates**. When true `NO_WORK` is again possible after the formal lifecycle, capture the real `DISPATCH_REQUEST` comment, exact successful native run/attempt, one digest-matched raw Artifact, Application successful NO_WORK consumption and fresh eligibility, exactly-one #218 admission with unrelated state preserved, and a **later separate** normal `Lead / explore-change` dispatch. Verify no duplicate Issue/Action/mutation, no replay/stale evidence, an interrupted-at-read recovery path and independent exact-head reviewer/CI evidence. Until this chain is observed, T1 is not accepted as fixed even if all tests pass.
