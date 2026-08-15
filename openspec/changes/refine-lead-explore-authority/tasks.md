# Tasks: Refine Lead Explore authority

## Slice 1 — Repository-authorized Explore admission

- [ ] **RED** Add focused regression tests proving canonical MUST/SHALL gaps, reconstructable required-deferred obligations, explicitly governed README commitments, and material behavior-preserving friction can authorize bounded autonomous Explore while arbitrary Issue/advisory text cannot.
- [ ] **GREEN** Update canonical workflow governance, Lead authority, and Explore procedure so idle Lead may materialize at most one deduplicated `Change: unset + Lead / explore-change` candidate with reconstructable admission evidence and no `intake:approved` or formal Change id.
- [ ] **REFACTOR** Consolidate admission-source/materiality validation in the narrowest authoritative ownership layer; remove duplicated Human-only assumptions without adding a new approval token, routing label, registry, priority engine, or hidden backlog state.
- [ ] **VERIFY** Run focused tests, full pytest suite, mypy, Ruff, and strict OpenSpec validation for the exact branch revision.

Trace: proposal `What Changes` items 1–3 and 6; modified requirement `Workflow admission is explicitly authority-controlled`; design Decisions 1, 3, 4, and 6.

## Slice 2 — README project-direction SSOT qualification

- [ ] **RED** Add regression tests proving descriptive/current-state/example/non-goal/plain-deferred README text cannot authorize autonomous admission while an explicitly governed prospective, scoped, affirmative, non-contradictory project-direction commitment can authorize only bounded in-direction Explore.
- [ ] **GREEN** Update README/governance presentation so README remains the project-level description/direction SSOT without becoming runtime governance, and define the minimum explicit forward-looking commitment surface consumed by Lead.
- [ ] **REFACTOR** Keep behavioral contract authority in canonical OpenSpec specs and runtime authority in `agents/AGENTS.md`; do not introduce a second project-direction registry or duplicate project direction into role/Skill files.
- [ ] **VERIFY** Run focused tests, full regression suite, mypy, Ruff, and strict OpenSpec validation for the exact branch revision.

Trace: proposal `What Changes` item 4; modified requirement `Workflow admission is explicitly authority-controlled`; design Decision 2.

## Slice 3 — Explore → Propose authority continuity

- [ ] **RED** Add regression tests proving valid Human- or repository-authorized `PROPOSAL_READY` can route the same Issue directly to `Lead / propose-change` when inside the admitted authority envelope, while new product direction, material behavior/scope trade-offs, explicit risk acceptance, materially different commitments, contradictory authority, or changed governing evidence still stop with `HUMAN_DECISION_REQUIRED`.
- [ ] **GREEN** Update shared governance and Explore/Lead procedure to remove the redundant generic post-Explore Human proceed boundary only for in-envelope proposal-ready results and consume existing #50 same-role continuation semantics without duplicating them.
- [ ] **REFACTOR** Preserve direct-to-Propose, `NO_CHANGE_REQUIRED`, `NO_GO`, Reviewer independence, and all later lifecycle gates; introduce no new transition message or second Explore lifecycle.
- [ ] **VERIFY** Run focused tests, full regression suite, mypy, Ruff, and strict OpenSpec validation for the exact branch revision.

Trace: proposal `What Changes` item 5; modified requirement `Lead Explore is decision-complete before lifecycle disposition`; design Decision 5.

## Slice 4 — Idle discovery noise/self-feeding controls

- [ ] **RED** Add regression tests proving formal/terminal-pending and already eligible pre-activation work win over idle discovery, one idle invocation creates at most one candidate, unresolved candidates are deduplicated, Agent-created tickets do not recursively self-authorize, and no-material-finding produces no repository noise.
- [ ] **GREEN** Update idle discovery/advisory governance to enforce the materiality, deduplication, one-candidate, and independent-source boundaries without exhaustive coverage state.
- [ ] **REFACTOR** Keep Rule-of-Three as evidence guidance rather than an automatic refactoring rule and retain support for clear single-instance structural hazards with concrete cost/risk/friction.
- [ ] **VERIFY** Run focused tests, full regression suite, mypy, Ruff, and strict OpenSpec validation for the exact branch revision.

Trace: proposal `What Changes` item 6; modified requirement `Lead idle advisory and discovery mode is bounded and non-disruptive`; design Decisions 3–4.

## Final verification

- [ ] Verify proposal → specs → design → tasks forward traceability and tasks → design → specs → proposal reverse traceability.
- [ ] Verify no global priority system, central workflow engine, coverage registry/cursor, autonomous product-roadmap authority, or Human-authority provenance redesign entered this change.
- [ ] Run `pytest`, `mypy`, `ruff`, and strict OpenSpec validation; record exact-revision evidence before Reviewer handoff.
