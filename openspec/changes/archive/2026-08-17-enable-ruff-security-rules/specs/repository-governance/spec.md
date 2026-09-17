## ADDED Requirements

### Requirement: Python static security extends the existing Ruff quality gate

The repository SHALL enforce Ruff's non-preview `S` security rule family through the existing Python Quality Ruff lint gate rather than requiring a parallel static-analysis lifecycle. The selected security family SHALL apply to repository Python code under the normal Ruff scope. Test files under `tests/**` MAY ignore `S101` so ordinary test assertions remain valid, but production/source code and repository Python scripts MUST NOT receive a blanket `S101` exemption. Any additional security-rule ignore MUST be narrowly scoped and justified by concrete repository context; the `S` family MUST NOT be globally disabled to avoid remediation. Bandit, Semgrep, or another static-security scanner MUST NOT be required by this contract unless a separately demonstrated capability gap shows the existing Ruff gate cannot satisfy a required security property.

#### Scenario: Stable security rule is applicable

- GIVEN repository Python code violates a non-preview rule selected by Ruff's `S` family
- WHEN the existing Python Quality Ruff lint step runs
- THEN the same Ruff gate reports the violation
- AND no second static-analysis lifecycle is required for that coverage

#### Scenario: Test assertion is linted

- GIVEN a Python file is under `tests/**`
- AND it uses an ordinary `assert` statement for test verification
- WHEN Ruff evaluates `S101`
- THEN the configured test-only exception permits that assertion
- AND the exception does not grant a blanket `S101` exemption to production/source code or repository Python scripts

#### Scenario: Preview security rule exists

- GIVEN Ruff exposes a security rule that is still preview-only
- WHEN the repository selects the `S` family under this contract
- THEN this change does not enable Ruff preview mode merely to activate that rule
- AND preview-rule adoption requires separate evidence before becoming part of the quality contract

#### Scenario: Additional security finding appears

- GIVEN enabling the `S` family exposes a stable security finding
- WHEN Executor implements the approved change
- THEN the finding is remediated where feasible
- AND any exception is narrowly scoped and justified by the concrete repository pattern
- AND the `S` family is not globally disabled to make the gate pass

#### Scenario: Security lint configuration regresses

- GIVEN the repository has adopted the Ruff security-family policy
- WHEN a later change removes `S` from the configured lint families or broadens the test-only `S101` exception into production scope
- THEN focused repository regression coverage fails
- AND the existing Python Quality workflow surfaces the regression without a second scanner job

#### Scenario: Another scanner is proposed

- GIVEN Bandit, Semgrep, or another static-security scanner is proposed in addition to Ruff
- WHEN no concrete required capability gap in Ruff has been demonstrated
- THEN the repository does not add the duplicate scanner lifecycle under this requirement
- AND a separately evidenced need is required before such an expansion is governed
