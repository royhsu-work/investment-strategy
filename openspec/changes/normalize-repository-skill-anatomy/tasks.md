# Tasks: Normalize repository Skill anatomy and provenance

## Slice 1 — Standard mapped-Skill anatomy

- [x] 1.1 RED: add focused regression coverage enumerating the eight repository-authored mapped Skills and proving the current branch fails because their `SKILL.md` files lack required YAML frontmatter with non-empty `name` and `description`.
- [x] 1.2 GREEN: add minimal stable YAML frontmatter to `archive-review`, `implementation-review`, `implementation`, `lifecycle-finalize`, `merge-pr`, `openspec-change`, `openspec-explore`, and `openspec-review` without changing their existing procedure/authority meaning.
- [x] 1.3 REFACTOR: remove any test duplication and keep metadata descriptions bounded to the existing mapped responsibility; do not introduce new routing or role semantics.
- [x] 1.4 VERIFY: run focused Skill anatomy tests, adopted `skill-creator` quick validation where applicable, full pytest, Ruff lint/format, and mypy; persist the verified Slice checkpoint before proceeding.

Trace: proposal standard-anatomy scope → repository-governance requirement `Repository Skills use standard anatomy and explicit provenance` → Design D1/D3.

## Slice 2 — Immutable upstream responsibility provenance

- [ ] 2.1 RED: add regression assertions that every OpenSpec-derived/adapted mapped Skill has reconstructable Skill-local upstream repository/path/revision and explicit Added / Delete-or-omit / Modified responsibility categories, while repository-original Skills are not required to fabricate an upstream mapping.
- [ ] 2.2 GREEN: add Skill-local provenance/delta ledgers for the actual upstream relationships identified by #85 using immutable `Fission-AI/OpenSpec@2826b8889e5223a9a8095d4428b60b56597e1020` baselines.
- [ ] 2.3 GREEN: explicitly document repository role/stage decomposition for Propose/Resolve, Apply, independent implementation verification, and Archive lifecycle ownership; identify alternative local owners for intentionally moved upstream responsibilities.
- [ ] 2.4 REFACTOR: keep provenance maintenance-only and progressively disclosed; do not duplicate runtime governance, role authority, or full upstream Skill bodies.
- [ ] 2.5 VERIFY: run focused provenance tests plus full repository quality gates and persist the verified Slice checkpoint.

Trace: proposal upstream-maintainability scope → provenance/decomposition scenarios → Design D2/D3.

## Slice 3 — Behavior-preserving final regression and boundaries

- [ ] 3.1 RED/GREEN: add or refine regression assertions that standard metadata/provenance does not add dispatcher actions, alter mapped role/action ownership, or require fabricated provenance for `openspec-review` and other repository-original Skills.
- [ ] 3.2 Verify `agents/skills/openspec-semantic-adapter.md` remains a separate root-level follow-up finding rather than being converted in this Change; #83/#80/#86 scope remains untouched.
- [ ] 3.3 Run the full test suite, Ruff lint, Ruff format check, mypy, adopted Skill validation checks, and strict OpenSpec validation.
- [ ] 3.4 Confirm all proposal → spec → design → task and task → design → spec → proposal trace declarations remain coherent and that no material behavior/routing/Human-authority semantics changed.
- [ ] 3.5 Mark the Change implementation-ready only when exact-head required gates are green.

Trace: proposal scope boundaries → repository-governance requirement → Design D3/D4.
