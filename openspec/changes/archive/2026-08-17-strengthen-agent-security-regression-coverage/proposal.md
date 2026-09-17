# Proposal: Strengthen Agent security regression coverage

## Why

The repository has explicit default-branch trust boundaries, provenance-bound Human authority, and Ruff stable `S` security linting, but two related regression gaps remain on the current default branch.

First, representative Agent trust-boundary failures are not covered as one deterministic security contract: future governance or skill changes could accidentally let feature-branch governance, Issue/PR/comment/source/external content, prior conversation, or Scheduled Task metadata act as authority, or weaken role separation, without a focused regression test failing.

Second, #48 introduced three narrowly justified inline Ruff `S603` suppressions for test helpers that execute `sys.executable` plus repository-owned scripts. The lint suppressions intentionally waive a static finding at those call sites, but Ruff alone cannot prove that the safety assumptions behind the waiver remain true after later semantic drift.

This is the required deferred prompt/Agent security follow-up from #35, freshly revalidated after #48 against default-branch revision `e249da8e09a54eba14f0790933d5508806ad278b`.

## What Changes

- Add deterministic regression coverage for the existing Scheduled-Agent trust boundary rather than a prompt-injection classifier or model-behavior benchmark.
- Cover representative conflicting/malicious work-input fixtures across feature-branch governance, Issue/PR/comment/source/external content, prior conversation, and Scheduled Task metadata.
- Verify role authority remains bounded when work input asks Executor to redefine requirements or Reviewer to modify reviewed artifacts.
- Verify natural-language claims cannot satisfy Human-reserved authority and defer the actual provenance predicate to the already-canonical Human-authority contract.
- Keep tests/fixtures as evidence of canonical governance, not a parallel governance source.
- Add narrowly targeted deterministic regression protection for security-relevant inline suppressions whose justification depends on explicit trust/execution invariants, beginning with the three current `S603` subprocess helpers from #48.
- For those current helpers, preserve the assumptions that execution uses `sys.executable`, targets a repository-owned fixed script rather than a caller-selected executable/path, does not introduce shell execution, and does not silently route arbitrary unvalidated external/request/Issue/environment/filesystem/CLI input behind the suppression.

## Scope

In scope:
- deterministic repository tests and fixtures for existing Agent trust-boundary/authority invariants;
- minimum governance references needed so tests consume one authoritative rule rather than duplicated prose;
- regression coverage for default-branch activation and feature-branch non-authority;
- deterministic protection of material safety assumptions behind the current narrowly scoped `S603` suppressions.

Out of scope:
- prompt-injection detection/classification;
- model eval/benchmark infrastructure;
- external moderation or security services;
- redesign of provenance-bound Human authority;
- changing Ruff `S` selection or Python Quality ownership;
- a generic suppression registry, taint-analysis platform, or second SAST lifecycle;
- cryptographic or secret-phrase authorization.

## Affected capabilities

- `scheduled-agent-workflow` — add normative deterministic regression coverage for existing trust/role/Human-authority boundaries and for material security-suppression assumptions that static linting alone cannot preserve.

## Trace

Sources: #49 fresh current-baseline Explore `PROPOSAL_READY` (`issuecomment-5311100572`); required deferred source #35 `issuecomment-5291586680`; current #48 archive baseline and the three repository-owned-script `S603` call sites.