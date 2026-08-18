# Tasks: Allow Human-created Explore admission

## Slice 1 — Raw Human-created Explore admission predicate

- [ ] RED: add focused tests showing directly Human-created Formal Explore intake is accepted only with raw `performed_via_github_app == null`, exact creation-time `Admission: Lead / explore-change`, `Change: unset`, and legal current routing.
- [ ] RED: add negative tests for app-created Human-looking Issues, missing raw provenance, missing/duplicate declaration, wrong action, and invalid routing.
- [ ] GREEN: implement the minimum raw Issue-creation adapter/predicate beside the existing Human decision/approval evaluator without weakening `is_human_decision_approved`.
- [ ] REFACTOR: keep creation parsing/evaluation deterministic and reusable only at the initial Explore admission boundary; do not introduce hidden approval state.
- [ ] VERIFY: run focused tests, full regression suite, type checks, lint checks, and strict OpenSpec validation.

Trace: proposal `What Changes` creation-bound admission -> spec `Human-required authority is bound to the repository Human actor` -> design D1/D2.

## Slice 2 — Mutation ambiguity and fallback semantics

- [ ] RED: add tests proving ambiguous/unavailable creation declaration history fails closed and does not infer Human admission from current body or routing snapshots.
- [ ] RED: add tests proving the existing `Human-Decision-For + human:approved` predicate can still authorize Explore when the creation-bound shortcut fails but the full existing predicate passes.
- [ ] GREEN: implement the minimum durable-history/raw-evidence handling needed to detect supported creation-declaration state and return explicit non-qualification when evidence is incomplete or contradictory.
- [ ] REFACTOR: avoid duplicating the existing event-first Human-decision evaluator; keep fallback composition at the admission consumer boundary.
- [ ] VERIFY: run focused tests, full regression suite, type checks, lint checks, and strict OpenSpec validation.

Trace: proposal fallback rule -> spec ambiguous/mutated scenario -> design D3.

## Slice 3 — Governance admission consumption

- [ ] RED: add governance/behavior tests proving initial `Lead / explore-change` admission accepts either the new qualifying Human-created Issue path or the existing provenance-bound Human decision path.
- [ ] RED: add regression tests proving direct Propose, advisory admission, escalation answers/resume, and later Human-reserved decisions do not consume the creation-bound shortcut.
- [ ] GREEN: update the narrow shared governance/Lead Explore-Propose reconstruction surfaces required to consume the new alternative while preserving repository-authorized Explore origins unchanged.
- [ ] GREEN: define/present the exact Human intake declaration `Admission: Lead / explore-change` + `Change: unset` in the existing appropriate Human-facing repository guidance surface without creating a second authority owner.
- [ ] REFACTOR: remove any duplicated authority wording introduced during implementation; keep one owner for predicate semantics and references elsewhere.
- [ ] VERIFY: run focused tests, full regression suite, type checks, lint checks, and strict OpenSpec validation.

Trace: proposal scope boundaries -> both modified requirements -> design D2/D4.

## Completion verification

- [ ] Confirm proposal -> specs -> design -> tasks forward traceability and tasks -> design -> specs -> proposal reverse traceability.
- [ ] Confirm no production strategy/data/execution behavior changed.
- [ ] Confirm no new Human shortcut exists outside initial Formal Explore admission.
- [ ] Confirm strict OpenSpec validation passes on the exact final PR head revision.
