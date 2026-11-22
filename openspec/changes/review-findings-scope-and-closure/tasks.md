# Tasks

## 1. Reviewer blocking-Finding boundary

- [x] 1.1 RED: write focused Skill-contract/behavioral checks for the current implementation-review procedure, proving that an unsupported preferred fix or a later-stage gate cannot be promoted into a blocking Finding without an approved invariant, exact-head evidence, current gate/stage and observable closure condition. Cover PR #455 accepted preimage contradiction (immutable manifest and zero unauthorized mutation) and PR #453 intended RED-stage failure. Confirm RED failures are caused by missing procedural behavior, not tooling/setup.
- [x] 1.2 GREEN: minimally revise `agents/skills/implementation-review/SKILL.md` to require the four-part blocking Finding and to assess independent alternatives or counterevidence against the original closure condition while keeping recommendations advisory and unchanged independent Reviewer ownership.
- [x] 1.3 REFACTOR/VERIFY: remove unnecessary duplicated explanation; verify the original RED examples, the Skill declaration and unchanged current-stage/future-gate separation. Run focused tests, `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run mypy src tests`.

Trace: proposal Reviewer correction → `repository-governance` requirement and PR #455/#453 scenarios → design Decisions 1 and 3.

## 2. Executor independent verification and in-scope correction

- [x] 2.1 RED: add focused procedure/behavioral checks proving Executor must independently substantiate a Finding before editing and must not silently adopt a suggested mechanism as a requirement. Cover Issue #435 historical UNKNOWN (no non-idempotent replay and only a concrete current conflict blocks a separately authorized correction) and independent Reviewer adjudication of an alternative fix/counterevidence against the original closure condition. Confirm intended RED.
- [x] 2.2 GREEN: minimally revise `agents/skills/implementation/SKILL.md` to require evidence reproduction/verification, smallest approved-scope repair, original-or-equivalent counterexample proof, review-record counterevidence and existing `SPEC_BLOCKER → Lead / resolve-question` when materially changing approved semantics or scope. Keep independent Reviewer PASS outside Executor authority.
- [x] 2.3 REFACTOR/VERIFY: confirm no new Action/Result/gate/state/parser, no #435 writes or replay, and no conflict with the existing RED–GREEN–REFACTOR–VERIFY implementation Skill. Verify both separately declared `Modified` Skills and run focused checks plus `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run mypy src tests`.

Trace: proposal Executor correction → `repository-governance` requirement and #435/alternative-fix scenarios → design Decisions 2 and 3.

Review PASS, PR merge, archive and post-merge verification remain governed lifecycle gates, **not** Executor implementation task markers.
