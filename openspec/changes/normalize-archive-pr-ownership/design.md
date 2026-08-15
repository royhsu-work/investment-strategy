# Design: Normalize Archive PR creation ownership

## Context

Current archive automation already owns the deterministic mechanics through validated archive-branch push, but then attempts a platform-disallowed PR creation. Human has declared that restriction an environment constraint to normalize around.

## Decision 1: Archive branch readiness is the automation success boundary

Repository automation retains classification, OpenSpec archive mutation, canonical validation, commit, and push. Successful validated branch production is success, not partial failure.

## Decision 2: Lead owns normal final Archive PR creation

`Lead / finalize-change` reconstructs the exact archive branch and persistent coordination Issue. When branch readiness is proven and no equivalent PR exists, Lead creates the final Archive PR to `main` with deterministic `Closes #N` linkage. If an equivalent valid PR already exists, Lead reuses it.

This moves only PR presentation/orchestration ownership. Lead still does not run archive mutation or merge PRs.

## Decision 3: Preserve independent lifecycle gates

The resulting PR still requires independent `review-archive`, exact-head Lead authorization, Executor merge, native Issue close, and Lead terminal reconstruction. Closing linkage remains a lifecycle side effect, not authorization.

## Decision 4: Genuine failure stays fail-closed

Classification, archive mutation, validation, commit, push, contradictory branch state, or ambiguous Issue linkage remains genuine failure/diagnosis territory. No hidden status, retry counter, lock, or second DAG is added.

## Blast radius

Expected implementation surfaces:
- `.github/workflows/openspec-archive.yml`;
- `agents/AGENTS.md` archive ownership orientation/runtime contract;
- `agents/skills/lifecycle-finalize/SKILL.md` normal branch-ready reconstruction and idempotent PR creation;
- focused archive workflow/lifecycle regression tests;
- README only if its high-level ownership wording becomes inaccurate.

## Rejected alternative

Enabling GitHub Actions PR creation is rejected because Human explicitly selected the environment-boundary normalization and least-authority direction.