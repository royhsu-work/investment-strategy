# Change: Enable Ruff security rules in the existing Python quality gate

## Why

#48 carries the Python static-security follow-up explicitly deferred from #35. The repository already runs Ruff as the single Python lint gate, but `pyproject.toml` does not select the `S` (flake8-bandit) security family. The approved follow-up evidence calls for the smallest extension of that existing gate rather than a parallel SAST lifecycle.

Current default-branch evidence shows a concrete exception need in tests: the test suite uses Python `assert`, so `S101` must not make ordinary test assertions invalid. No equivalent evidence justifies a production or repository-script exemption.

## What Changes

1. Extend the existing Ruff lint selection with the stable `S` security family while leaving Ruff preview rules disabled.
2. Keep the existing `uv run ruff check .` Python Quality step as the single executable static-security gate; do not add Bandit, Semgrep, or another scanner without a demonstrated capability gap.
3. Add one narrowly scoped exception: `tests/**` may ignore `S101` so tests can continue to use assertions. Production code and repository Python scripts receive no blanket `S101` exemption.
4. Remediate any stable `S` findings exposed by the selected family. Any additional ignore must be narrowly scoped and justified by concrete repository context rather than silently weakening the family.
5. Add focused regression coverage that proves the `S` family remains selected and the `S101` exception remains tests-only.

## Affected Capabilities

- **MODIFIED** `repository-governance`: add the repository-level contract that Python static-security checks extend the existing Ruff quality gate with bounded exceptions and no duplicate scanner by default.

## Scope Boundaries

In scope:
- Ruff `S` policy in `pyproject.toml`;
- the existing Python Quality Ruff gate;
- remediation of stable `S` findings exposed by that policy;
- focused configuration/regression tests.

Out of scope unless implementation evidence demonstrates a concrete Ruff capability gap:
- Bandit, Semgrep, or a generic SAST platform;
- dependency/SCA redesign;
- prompt/Agent security regression coverage;
- Human-authority provenance;
- Ruff preview security rules;
- repository-wide security architecture.

## Security / Maintenance Trade-off

Selecting the `S` prefix follows the repository's existing prefix-based Ruff policy. Stable rules that enter the selected family in the repository-resolved Ruff toolchain will therefore become part of the gate in the same way as the existing `E`, `F`, `I`, `UP`, `B`, and `SIM` families. Pinning Ruff solely for this change would add a separate version-policy decision without demonstrated need, so this change does not introduce one.

The only pre-authorized exception is `tests/** -> S101`, supported by current test code. Additional findings are implementation work first, not automatic grounds for broader suppression.

## Evidence / Trace

- Coordination/admission: #48; repository-authorized required-deferred source from #35.
- Preserved source evidence: #35 `issuecomment-5291586680` and archived `2026-08-15-adopt-skill-creator-and-project-simplicity` proposal `Security evidence disposition`.
- Current implementation baseline: `pyproject.toml` and `.github/workflows/quality.yml` on default branch.
- Current test evidence: test modules use `assert`, including `tests/test_human_authority.py`.
- Authoring rules: default-branch `openspec/config.yaml` and spec-driven semantic adapter.
- Delta requirement: `specs/repository-governance/spec.md`.
- Design decisions: `design.md` Decisions 1–5.
- Implementation slices: `tasks.md` Slice 1.
