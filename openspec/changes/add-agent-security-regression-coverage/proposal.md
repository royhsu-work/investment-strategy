# Proposal: Add Agent security regression coverage

## Why

The repository now has explicit default-branch trust boundaries and provenance-bound Human authority, but representative Agent trust-boundary regressions are not covered as one deterministic security contract. A future governance or skill change could accidentally let feature-branch governance, Issue/PR/comment/source/external content, prior chat, or Scheduled Task metadata act as authority, or weaken role separation, without a focused regression test failing.

This is the required deferred prompt/Agent security follow-up from #35, revalidated by #49 Explore against default-branch revision `587fb65862f4cbc2a0c870bc3bc075651497b8e6`.

## What Changes

- Add deterministic regression coverage for the existing Scheduled-Agent trust boundary rather than a prompt-injection classifier or model-behavior benchmark.
- Cover representative conflicting/malicious work-input fixtures across feature-branch governance, Issue/PR/comment/source/external content, prior conversation, and Scheduled Task metadata.
- Verify role authority remains bounded when work input asks Executor to redefine requirements or Reviewer to modify reviewed artifacts.
- Verify natural-language claims cannot satisfy Human-reserved authority and defer the actual provenance predicate to the already-canonical Human-authority contract.
- Keep tests/fixtures as evidence of the canonical governance contract, not a parallel governance source.

## Scope

In scope:
- deterministic repository tests and fixtures for existing Agent trust-boundary/authority invariants;
- minimum governance references needed so tests consume one authoritative rule rather than duplicated prose;
- regression coverage for default-branch activation and feature-branch non-authority.

Out of scope:
- prompt-injection detection/classification;
- model eval/benchmark infrastructure;
- external moderation or security services;
- redesign of provenance-bound Human authority;
- Python Ruff `S` policy;
- cryptographic or secret-phrase authorization.

## Affected capabilities

- `scheduled-agent-workflow` — add a normative regression-coverage requirement for existing trust-boundary behavior.

## Trace

Source: #49 decision-complete Explore `PROPOSAL_READY`; required deferred source #35 `issuecomment-5291586680`.
