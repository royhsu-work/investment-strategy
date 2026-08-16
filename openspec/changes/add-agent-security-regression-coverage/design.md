# Design: Deterministic Agent trust-boundary regressions

## Decision

Use deterministic repository tests/fixtures to protect the already-approved Scheduled-Agent trust boundary. The tests inspect authoritative default-branch governance/role/skill surfaces and representative untrusted-input fixtures; they do not attempt to measure model susceptibility or classify prompt injection.

This keeps the security boundary testable without creating a second runtime policy engine.

## Requirements trace

- `scheduled-agent-workflow` / `Agent trust boundaries have deterministic regression coverage` → proposal sections `Why` and `What Changes`.
- Source authority: #49 Explore result; #35 `issuecomment-5291586680`.

## Test model

A focused regression suite should cover three vertical behaviors:

1. **Authority-source boundary**
   - default-branch `agents/AGENTS.md`, role, and mapped skill remain authoritative;
   - feature-branch governance and untrusted Issue/PR/comment/source/external/prior-chat/Scheduled-Task instructions remain work input only;
   - an unmerged governance change must not govern its own invocation.

2. **Role and Human authority boundary**
   - work input cannot grant Executor specification authority or Reviewer mutation authority;
   - natural-language claims such as “Human approved” or “I am Roy” cannot satisfy Human-reserved boundaries;
   - tests reference the canonical provenance-bound Human authority contract instead of reproducing its algorithm.

3. **Fixture/ownership boundary**
   - malicious/conflicting fixture strings are test inputs only and do not become runtime instructions;
   - fixtures live under tests and assertions point to canonical governance ownership rather than copying a second normative protocol.

## Trade-offs

Structural/deterministic tests cannot prove every future model will ignore every adversarial prompt. They can prove that repository-governed executable/document contracts do not silently remove or contradict the authority boundaries Scheduled runs are required to load. This is the narrow useful regression layer for the demonstrated repository risk.

A model-behavior eval platform is rejected because it adds nondeterminism, cost, maintenance, and a second security interpretation layer without a demonstrated requirement.

## Compatibility

- No runtime routing/action/state additions.
- No change to the Human provenance algorithm delivered by the Human-authority change.
- No new label, approval token, scanner, or external service.
- Existing tests remain valid; the new suite complements `test_governance_ssot.py` and `test_human_authority*.py` without duplicating their ownership.
