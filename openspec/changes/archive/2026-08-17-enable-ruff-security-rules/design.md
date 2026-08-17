# Design: Enable Ruff security rules in the existing Python quality gate

## Context

The repository already owns Python linting through Ruff in the `Python Quality` workflow. The missing behavior is security-family selection, not a missing static-analysis lifecycle. #35 preserved a separate Ruff `S` follow-up with a preferred minimal shape, and #48 Explore confirmed that current default-branch configuration still omits `S` while tests concretely rely on Python assertions.

A local read-only attempt to inventory exact current `S` findings could not execute because the local runtime lacked network resolution and Ruff. That limitation does not justify assuming zero findings; implementation must use the repository quality gate to expose and remediate actual stable findings.

## Decision 1: Reuse the existing Ruff gate

`pyproject.toml` remains the policy/configuration owner and `.github/workflows/quality.yml` continues to execute `uv run ruff check .`. Adding a second scanner would duplicate ownership without an evidenced capability gap.

Trace: proposal What Changes 1–2; `repository-governance` requirement `Python static security extends the existing Ruff quality gate`.

## Decision 2: Select the stable `S` family without preview mode

Add `S` to the existing Ruff family selection. Do not enable Ruff preview mode as part of this change. This keeps the policy aligned with the demonstrated source-security goal while avoiding experimental rules that were not part of the approved direction.

The repository does not add a new Ruff version pin solely for this change. Prefix selection therefore follows the same resolved-toolchain behavior already accepted for the existing Ruff families.

Trace: proposal What Changes 1; requirement scenarios `Stable security rule is applicable` and `Preview security rule exists`.

## Decision 3: Scope `S101` only to tests

Add a per-file ignore for `tests/** = ["S101"]`. Assertions are normal test behavior and are concretely present in the current suite. Production `src/**` and repository Python scripts do not receive this blanket exception.

Trace: proposal What Changes 3; requirement scenario `Test assertion is linted`.

## Decision 4: Remediate findings before adding further ignores

When the quality gate exposes stable `S` findings, Executor should correct the code where feasible. A further ignore is acceptable only when a concrete repository pattern makes the rule inappropriate and the exception can be scoped narrowly. The change does not authorize disabling `S` globally or adding speculative per-file exclusions.

Trace: proposal What Changes 4; requirement scenario `Additional security finding appears`.

## Decision 5: Protect the policy with focused regression coverage

Add a focused repository test that reads `pyproject.toml` and proves:
- `S` remains selected;
- `tests/**` is the only configured `S101` blanket exception introduced by this change;
- no production/source blanket `S101` exception is introduced.

The existing Python Quality workflow already runs pytest and Ruff, so no new workflow job is required.

Trace: proposal What Changes 5; requirement scenario `Security lint configuration regresses`; tasks Slice 1.

## Rejected alternatives

- **Bandit in parallel with Ruff:** rejected absent a demonstrated rule/severity/plugin capability that this change requires and Ruff cannot provide.
- **Semgrep/generic SAST:** rejected because no current data-flow or custom-rule requirement justifies the added platform/lifecycle.
- **Global `S101` ignore:** rejected because the concrete false-positive context is tests, not production code.
- **Enable Ruff preview rules:** rejected because the approved evidence calls for stable rules and no current requirement needs experimental coverage.
- **Pin Ruff only for this change:** rejected as a separate dependency/version-policy expansion without demonstrated need.

## Blast radius

Expected implementation surfaces are limited to:
- `pyproject.toml`;
- Python files that must be remediated for newly exposed stable `S` findings;
- one focused regression test for the lint policy;
- no new CI workflow or scanner lifecycle unless implementation evidence proves the approved contract cannot be met otherwise.
