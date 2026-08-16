# Tasks

## Slice 1 — Default-branch authority and untrusted-input fixtures

- [ ] RED: add focused deterministic tests proving current default-branch governance/role/skill authority wins over representative conflicting feature-branch, Issue/PR/comment/source/external/prior-chat/Scheduled-Task fixture text. Trace: proposal `What Changes`; spec `Agent trust boundaries have deterministic regression coverage`; design `Authority-source boundary`.
- [ ] GREEN: add the minimum fixture/helper/test structure needed to express those authority-source cases without introducing runtime policy code or a second governance source. Trace: design `Test model`.
- [ ] REFACTOR/VERIFY: keep assertions anchored to canonical default-branch ownership surfaces; run focused tests, full pytest, Ruff, mypy, and strict OpenSpec validation. Trace: `openspec/config.yaml` task rules.

## Slice 2 — Role separation under conflicting work input

- [ ] RED: add representative tests where untrusted work input tells Executor to redefine requirements or tells Reviewer to mutate governed artifacts to make review pass; verify the canonical role boundaries remain the asserted contract. Trace: spec scenario `Untrusted work input cannot expand role authority`; design `Role and Human authority boundary`.
- [ ] GREEN: add only the minimum deterministic assertions/fixtures required for those role-boundary regressions; do not add model-behavior evaluation machinery. Trace: proposal `Scope`; design `Trade-offs`.
- [ ] REFACTOR/VERIFY: deduplicate shared fixture/assertion helpers without moving normative role meaning into tests; run focused/full quality gates and strict OpenSpec validation. Trace: `openspec/config.yaml` task rules.

## Slice 3 — Human natural-language claims and fixture ownership

- [ ] RED: add tests proving natural-language Human approval claims in untrusted input are insufficient and that prompt-security fixtures remain test evidence rather than authority. Trace: spec scenarios `Natural-language Human claims do not satisfy reserved authority` and `Regression fixtures remain evidence rather than governance`.
- [ ] GREEN: reference the existing canonical provenance-bound Human-authority contract/tests instead of copying its decision-binding algorithm; add only minimal ownership assertions needed for the trust-boundary suite. Trace: design `Role and Human authority boundary` and `Fixture/ownership boundary`.
- [ ] REFACTOR/VERIFY: confirm no new label/token/scanner/eval platform or duplicate Human-authority algorithm was introduced; run focused/full quality gates and strict OpenSpec validation. Trace: proposal `Out of scope`; design `Compatibility`.

## Final verification

- [ ] Verify proposal/spec/design/task trace declarations are mechanically consistent and all approved slices are complete.
- [ ] Run strict OpenSpec validation and repository quality gates on the exact implementation revision before completion handoff.
