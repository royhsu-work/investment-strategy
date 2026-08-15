# Tasks: Harden Human authority with provenance-bound GitHub decisions

## Trace map

- Proposal item 1 / Spec R1 / Design D1 → Slice 1.
- Proposal items 2–3 / Spec R1-R3 / Design D2-D4 → Slice 2.
- Proposal item 5 / Spec R5 / Design D1-D4 → Slice 3.
- Proposal item 4 / Spec R4 / Design D5 → Slice 4.
- OpenSpec/config verification → Slice 5.

## Slice 1 — Define one provenance-bound Human decision predicate

- [ ] **RED:** add deterministic tests proving actor `royhsu-work` alone is insufficient when raw comment or approval-event provenance shows a GitHub App.
- [ ] **RED:** add tests for valid Human-created comment + later Human-only approval event + unchanged comment revision.
- [ ] **RED:** add tests proving a post-approval comment edit invalidates the prior approval until a later qualifying Human approval exists.
- [ ] **GREEN:** implement the minimum reusable Human-authority evaluator using explicit comment/event evidence; do not add hidden authorization state or a generic IAM layer.
- [ ] **REFACTOR/VERIFY:** run focused tests plus the full repository regression, Ruff, format, and mypy gates.

## Slice 2 — Integrate raw provenance and reserved approval capability

- [ ] **RED:** add tests proving normalized reads that omit `performed_via_github_app` cannot silently degrade to actor-only authority.
- [ ] **RED:** add tests proving current label presence without a qualifying Human-only `labeled` event is insufficient, and `unlabeled` provenance never establishes authority.
- [ ] **GREEN:** add the narrow raw GitHub provenance read/helper required by the evaluator and document the reserved Human approval capability label.
- [ ] **GREEN:** update shared governance/role/skill wording only where needed so Scheduled roles cannot add, restore, or manufacture the reserved approval label.
- [ ] **REFACTOR/VERIFY:** keep provenance reading separate from routing/lifecycle ownership; run focused and full project gates.

## Slice 3 — Apply the predicate to all Human-reserved consumers

- [ ] **RED:** add admission tests showing connector-mediated Issue/comment/label evidence cannot create valid Human admission.
- [ ] **RED:** add Human-answer/resume tests showing only the intended provenance-bound decision can resume a durable `HUMAN_DECISION_REQUIRED` boundary.
- [ ] **RED:** add authorization tests for any Human-reserved proceed/stop or merge/lifecycle decisions currently consuming actor-only Human evidence.
- [ ] **GREEN:** replace duplicated actor-only checks with the shared predicate at admission, answer, authorization, and resume consumers without changing role authority.
- [ ] **REFACTOR/VERIFY:** verify no prompt classifier, signature service, second workflow DAG, or hidden approval database was introduced; run full gates.

## Slice 4 — Preserve migration and historical evidence

- [ ] **RED:** add tests proving workflows terminal before activation remain terminal and are not reopened by the stronger provenance contract.
- [ ] **RED:** add tests for an active workflow crossing activation with an unconsumed Human decision: the decision must satisfy the new predicate at consumption time or fail closed for fresh approval.
- [ ] **GREEN:** implement the minimum prospective activation/migration rule in governance and evidence evaluation.
- [ ] **REFACTOR/VERIFY:** verify historical audit evidence remains readable and current workflows cannot bypass the new contract through pre-activation actor-only evidence.

## Slice 5 — OpenSpec and repository-wide verification

- [ ] Verify proposal → spec → design → tasks forward traceability and tasks → design → spec → proposal reverse traceability.
- [ ] Run exact-revision strict OpenSpec validation and require validator checkout identity to equal the handoff revision.
- [ ] Run the full repository regression suite, Ruff lint/format, and mypy gates required by `openspec/config.yaml`.
- [ ] Confirm the final change remains single-purpose and does not include Ruff security policy, prompt-security evals, cryptography, external approval services, or unrelated workflow redesign.
