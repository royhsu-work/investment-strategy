# Change: Normalize Archive PR creation ownership

## Why

The normal OpenSpec Archive workflow currently performs deterministic archive mutation, strict validation, commit, and archive-branch push successfully, then attempts `gh pr create` even though the deployed GitHub Actions environment is not permitted to create pull requests. This creates a known red happy path and forces Scheduled Lead to treat an expected environment boundary as recovery.

Human has explicitly classified this as an environment/deployment constraint to normalize around rather than a permission gap to widen. The workflow should therefore end normally at validated archive-branch readiness and let Lead create the final Archive PR as ordinary lifecycle continuation.

## What Changes

- Define successful validated archive-branch push as the normal repository-automation success boundary.
- Remove final Archive PR creation from the normal GitHub Actions archive mutation path.
- Make `Lead / finalize-change` reconstruct archive-branch readiness and create or reuse the final Archive PR with deterministic `Closes #<coordination-issue>` linkage as ordinary lifecycle continuation.
- Keep genuine archive mutation/validation/commit/push failures on the existing fail-closed recovery/diagnosis path.
- Preserve independent `review-archive`, exact-head Lead authorization, Executor merge, native Issue closure, and terminal `finalize-archive` reconstruction.

## Scope

Affected capability:
- `scheduled-agent-workflow`

In scope:
- normal archive automation terminal-success semantics;
- archive branch → final Archive PR ownership;
- Lead lifecycle reconstruction and idempotent PR creation;
- focused workflow/governance tests and high-level orientation updates where needed.

Out of scope:
- changing OpenSpec archive semantics;
- enabling broader GitHub Actions PR-creation authority;
- bypassing archive review/authorization/merge/native-close gates;
- adding a central workflow engine, lock, lease, or hidden state.

## Durable source decisions

- Coordination Issue: #58
- Human environment constraint: `issuecomment-5303723685`
- Explore `PROPOSAL_READY`: `issuecomment-5304797575`

## Deferred work

OpenSpec version/lifecycle semantic alignment remains separate from this ownership normalization.