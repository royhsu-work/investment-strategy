# Tasks

## Slice 1 — Default-branch authority and untrusted-input fixtures

- [x] RED: add focused deterministic tests proving current default-branch governance/role/skill authority wins over representative conflicting feature-branch, Issue/PR/comment/source/external/prior-conversation/Scheduled-Task fixture text. Trace: proposal `What Changes`; spec `Agent security boundaries have deterministic regression coverage`; design `Slice A — Authority-source boundary`.
- [x] GREEN: add the minimum fixture/helper/test structure needed to express those authority-source cases without introducing runtime policy code or a second governance source. Trace: design `Test model` and `Ownership boundary`.
- [x] REFACTOR/VERIFY: keep assertions anchored to canonical default-branch ownership surfaces; run focused tests, full pytest, Ruff, mypy, and strict OpenSpec validation. Trace: `openspec/config.yaml` task rules.

## Slice 2 — Role and Human authority under conflicting work input

- [x] RED: add representative tests where untrusted work input tells Executor to redefine requirements, tells Reviewer to mutate governed artifacts to make review pass, or claims Human approval through natural language; verify canonical boundaries remain the asserted contract. Trace: spec scenarios `Untrusted work input cannot expand role authority` and `Natural-language Human claims do not satisfy reserved authority`; design `Slice B — Role and Human authority boundary`.
- [x] GREEN: add only the minimum deterministic assertions/fixtures required for those regressions; reference the canonical provenance-bound Human-authority contract instead of copying its decision-binding algorithm. Trace: proposal `Scope`; design `Ownership boundary`.
- [x] REFACTOR/VERIFY: deduplicate shared fixture/assertion helpers without moving normative role or Human-authority meaning into tests; run focused/full quality gates and strict OpenSpec validation. Trace: `openspec/config.yaml` task rules.

## Slice 3 — Current S603 suppression semantic-drift protection

- [x] RED: add deterministic tests that fail if any of the three current justified `S603` subprocess helpers stops using `sys.executable`, stops targeting its repository-owned fixed script, introduces shell execution, gains an arbitrary caller/external-controlled executable or script slot, or begins forwarding arbitrary unvalidated external-derived values as ordinary subprocess arguments while the suppression remains. Trace: proposal `What Changes`; spec scenario `Scoped S603 suppression safety assumptions drift`; design `Slice C — Security-suppression semantic invariants`.
- [x] GREEN: implement the smallest regression helper/assertions that protect only those demonstrated current safety assumptions, including the ordinary-argument trust boundary; permit a specific external-derived argument only when an explicit deterministic validation boundary is represented by the concrete helper/test contract. Do not add a generic suppression registry, taint engine, or Ruff policy layer. Trace: design `Ownership boundary` and `Trade-offs`.
- [x] REFACTOR/VERIFY: keep the S603 evidence tied to the concrete suppressed sites and their rationale, confirm ordinary suppressions do not acquire bespoke-test obligations, and run focused/full quality gates plus strict OpenSpec validation. Trace: spec scenario `Ordinary lint suppressions do not create a registry obligation`; `openspec/config.yaml` task rules.

## Final verification

- [ ] Verify proposal/spec/design/task trace declarations are mechanically consistent and all approved slices are complete.
- [ ] Run strict OpenSpec validation and repository quality gates on the exact implementation revision before completion handoff.
