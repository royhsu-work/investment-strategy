# Tasks: Enable Ruff security rules in the existing Python quality gate

## Slice 1 — Existing Python Quality gate enforces bounded Ruff security policy

Trace: proposal `What Changes` 1–5; `repository-governance` requirement `Python static security extends the existing Ruff quality gate`; design Decisions 1–5; default-branch `openspec/config.yaml` engineering/governance task rules.

- [x] 1.1 RED — add focused regression coverage for the lint policy and run it before configuration changes; prove it fails because current `pyproject.toml` does not select `S` and does not yet define the tests-only `S101` exception.
- [x] 1.2 GREEN — add `S` to the existing Ruff lint family selection and add only `tests/** = ["S101"]` as the initial per-file security exception.
- [x] 1.3 GREEN — run the existing Ruff gate against the full repository and remediate stable `S` findings in production/source/repository Python code; add any further ignore only when a concrete finding proves the rule inappropriate and the exception can be narrowly scoped with rationale.
- [x] 1.4 REFACTOR — keep static-security ownership inside the existing Ruff configuration and Python Quality workflow; do not add a second scanner/job or enable preview rules unless the approved contract is proven insufficient by concrete evidence.
- [x] 1.5 VERIFY — run the focused regression test, full pytest suite, `ruff check .`, `ruff format --check .`, and mypy; all must pass under the selected security policy.
- [x] 1.6 VERIFY — run strict OpenSpec validation and resolve every reported issue before declaring the change complete.

## Completion boundary

Implementation is complete only when Slice 1 is verified and the repository's existing Python Quality gate enforces the approved Ruff security policy without a parallel static-analysis lifecycle.
