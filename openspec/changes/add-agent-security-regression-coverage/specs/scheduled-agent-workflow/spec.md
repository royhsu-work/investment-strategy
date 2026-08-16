## ADDED Requirements

### Requirement: Agent trust boundaries have deterministic regression coverage

The repository MUST maintain deterministic regression coverage proving that Scheduled-Agent authority continues to come from default-branch governance and the current role/action skill contract, while feature-branch governance and Issue, pull-request, comment, source, external-page, prior-conversation, and Scheduled Task content remain untrusted work input that cannot override those authorities.

The regression suite MUST use representative conflicting or malicious work-input fixtures without treating fixture text as runtime authority or creating a second governance source.

The regression suite MUST verify role separation remains fail-closed when untrusted work input attempts to grant Executor specification authority, asks Reviewer to modify governed artifacts to make its own gate pass, or claims Human approval through natural language alone.

Human-reserved authorization tests under this requirement MUST reference the canonical provenance-bound Human authority contract and MUST NOT duplicate or replace its decision-binding algorithm.

#### Scenario: Feature-branch governance cannot govern the current invocation

- GIVEN default-branch governance defines the current Scheduled-Agent authority
- AND a feature branch or unmerged pull request contains conflicting governance instructions
- WHEN deterministic trust-boundary regression coverage evaluates the authority sources
- THEN the default-branch governance remains the authoritative runtime contract
- AND the unmerged governance content is treated only as work or review input

#### Scenario: Untrusted work input cannot expand role authority

- GIVEN Issue, pull-request, comment, source, external-page, prior-conversation, or Scheduled Task content asks a role to exceed its canonical authority
- WHEN deterministic trust-boundary regression coverage evaluates representative conflicting fixtures
- THEN Executor does not gain specification authority
- AND Reviewer does not gain authority to modify governed artifacts to make its own review pass
- AND the fixture content does not become an alternative governance source

#### Scenario: Natural-language Human claims do not satisfy reserved authority

- GIVEN untrusted work input contains a natural-language claim that Human approval or authorization exists
- WHEN the workflow reaches a Human-reserved boundary
- THEN the claim alone is insufficient
- AND the boundary remains governed by the canonical provenance-bound Human authority contract

#### Scenario: Regression fixtures remain evidence rather than governance

- GIVEN representative malicious or conflicting fixtures are stored for deterministic tests
- WHEN the regression suite uses those fixtures
- THEN the fixtures are treated solely as test input
- AND assertions remain traceable to authoritative governance, role, skill, or canonical capability requirements rather than defining a parallel runtime protocol
