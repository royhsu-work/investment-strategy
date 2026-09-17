# Tasks: Introduce optional pre-Propose Explore lifecycle

## Trace map

- Proposal scope 1 / Spec `Optional pre-Propose Explore preserves upstream investigation semantics` / Design D1-D2 → Slice 1.
- Proposal scope 2 / Spec `Explore exits on decision-complete dispositions` / Design D4-D5 → Slice 2.
- Proposal scope 3 / Modified admission/discovery requirements / Design D3/D9 → Slice 3.
- Proposal scope 4 / Spec `Explore persists bounded reconstructable evidence` / Design D6-D7 → Slice 4.
- Proposal scope 5 / Spec terminal research closure + bootstrap requirement / Design D8 → Slice 5.
- OpenSpec config engineering/governance verification → Slice 6.

## Slice 1 — Add the Lead Explore action and authority boundary

- [x] **RED:** add/extend governance tests proving the authoritative normal action map accepts `Lead / explore-change`, maps it to one repository Explore skill, and still rejects unknown/contradictory role/action tuples.
- [x] **RED:** add behavioral governance tests proving Explore cannot create formal OpenSpec Change artifacts or modify implementation code, while direct Human-admitted `Lead / propose-change` remains valid without an Explore prerequisite.
- [x] **GREEN:** update `agents/AGENTS.md` to expose exactly ten normal actions and map `Lead / explore-change` to the new Explore skill without changing Reviewer/Executor authority or archive automation ownership.
- [x] **GREEN:** update `agents/roles/lead.md` with the minimum Explore responsibility/authority and map the new action; do not duplicate shared runtime invariants.
- [x] **GREEN:** create `agents/skills/openspec-explore/SKILL.md` using current upstream OpenSpec Explore semantics as design input while keeping repository default-branch governance authoritative. The skill must preserve problem-before-solution investigation, allow repository/external evidence inspection and bounded blast-radius analysis, and prohibit formal artifacts/code during Explore.
- [x] **REFACTOR/VERIFY:** remove duplicate wording across AGENTS/Lead/Explore skill so shared invariants retain one owner; run targeted governance tests, full regression suite, lint, and type checks.

## Slice 2 — Define decision-complete Explore outcomes and Human proposal boundary

- [x] **RED:** add tests for `PROPOSAL_READY`, `NO_CHANGE_REQUIRED`, `NO_GO`, and genuine `HUMAN_DECISION_REQUIRED`, including proof that `SPECIFICATION_BLOCKED` is not used as a terminal Explore no-go substitute.
- [x] **RED:** add a test proving `PROPOSAL_READY` alone does not persist a Change id or route to Propose before valid Human intent is reconstructed.
- [x] **RED:** add tests proving `NO_CHANGE_REQUIRED` and `NO_GO` can complete/close a research Issue without creating a fake OpenSpec Change; `NO_GO` evidence retains a material reconsideration condition when identifiable.
- [x] **GREEN:** implement the Explore skill/result semantics so decision completeness—not exhaustive research, fixed option count, checklist, or score—controls exit.
- [x] **GREEN:** reuse canonical `HUMAN_DECISION_REQUIRED` for the proposal-ready proceed/stop boundary and other genuine Human intent questions; change `agents/templates/messages.md` only if existing presentation cannot express the required evidence without ambiguity or duplication.
- [x] **GREEN:** grant Lead only the narrow terminal research-Issue close authority needed for `NO_CHANGE_REQUIRED`/`NO_GO`; do not weaken final Archive PR/native-close semantics for formal Changes.
- [x] **REFACTOR/VERIFY:** run targeted outcome/Human-boundary tests plus full regression, lint, and type checks.

## Slice 3 — Integrate deterministic Explore/direct-Propose queueing

- [x] **RED:** add tests for workflow-dynamic selection where a formal active/terminal-pending workflow always wins over queued Explore/Propose entries.
- [x] **RED:** add tests proving that, with no formal active workflow, Human-admitted open `explore-change + Change: unset` and `propose-change + Change: unset` participate in one queue ordered by GitHub `created_at`, then lower Issue number.
- [x] **RED:** add fixed-role tests proving lifecycle/blocker actions remain ahead of new intake, but once fixed-role Lead reaches pre-activation intake it uses the same combined Explore/direct-Propose queue; cover both older Explore + newer Propose and **older Propose + newer Explore**.
- [x] **RED:** add reconstruction tests proving an oldest open Explore remains the deterministic winner across wakes without `status:exploring`, claim, lease, heartbeat, or hidden ownership state.
- [x] **RED:** add concurrency/activation tests proving a later direct-Propose runner cannot persist a Change id while an older eligible Explore is the deterministic pre-activation winner.
- [x] **GREEN:** update shared discovery/admission contracts and any deterministic helper/tests so the pre-activation queue includes both Explore and direct Propose while preserving one selected work item per invocation.
- [x] **GREEN:** update legacy fixed-role Lead selection so `resolve-question > finalize-archive > finalize-change` remains ahead of new intake, then select Explore/Propose from the same combined pre-activation queue rather than applying `explore-change > propose-change` priority.
- [x] **REFACTOR/VERIFY:** verify fixed-role and workflow-dynamic cannot choose different winners for the same pre-activation candidate set; verify no global urgency scoring, second workflow DAG, or additional persistent queue state was introduced; run targeted selection/concurrency tests plus full regression, lint, and type checks.

## Slice 4 — Make Explore evidence reconstructable but bounded

- [x] **RED:** add tests/fixtures demonstrating a later wake can reconstruct an Explore Human-decision wait from the durable Issue evidence and current Human response without prior conversation memory.
- [x] **RED:** add governance assertions that Explore does not require live progress comments, fixed research templates/options, completeness scores, hidden memory, research database, or independent `review-explore` gate.
- [x] **GREEN:** define the minimum durable Explore result evidence in the Explore skill: problem/question, relevant evidence, material constraints/alternatives actually needed, disposition/rationale, next boundary, and reconsideration condition when applicable.
- [x] **GREEN:** ensure existing canonical `ACTION_RESULT` / `HUMAN_DECISION_REQUIRED` presentation remains the reusable message surface; add only the smallest template clarification if tests demonstrate a real gap.
- [x] **REFACTOR/VERIFY:** verify evidence ownership stays on the coordination Issue and does not create a parallel research artifact DAG; run targeted reconstruction tests plus full regression, lint, and type checks.

## Slice 5 — Bootstrap/migration and terminal compatibility

- [x] **RED:** add a bootstrap test proving #38-style feature-branch future Explore governance cannot govern the invocation that is creating it; default-branch governance remains authoritative until merge.
- [x] **RED:** add migration tests proving existing non-`unset` active Changes continue their current routing after Explore activation and existing Human-admitted `propose-change + Change: unset` Issues remain valid direct-to-Propose work.
- [x] **RED:** add tests proving deferred research Issues do not become Explore work merely because their text says "research"; they require valid Human routing/admission under authoritative post-merge governance.
- [x] **GREEN:** update README/migration orientation only where needed to expose the optional Explore entry without duplicating runtime semantics.
- [x] **GREEN:** update canonical governance/spec references needed for the new action while preserving existing formal Change review/implementation/archive lifecycle and final closing-linkage rules.
- [x] **REFACTOR/VERIFY:** confirm the deferred implementation/archive single-PR research remains out of scope and is not implemented by this Change; run targeted migration/bootstrap tests plus full regression, lint, and type checks.

## Slice 6 — OpenSpec and repository-wide verification

- [x] Verify proposal → specs → design → tasks forward traceability and tasks → design → specs → proposal reverse traceability for every Behavior/Product task in this Change.
- [x] Verify external OpenSpec Explore references remain non-authoritative runtime design evidence and no feature-branch instruction becomes current execution authority before default-branch merge.
- [x] Run the repository OpenSpec exact-revision validation path and require validator checkout identity to equal the handoff revision before accepting strict validation success.
- [x] Run the full repository regression suite, type checks, and lint checks required by current `openspec/config.yaml`.
- [x] Confirm the final implementation contains no central dispatcher engine, new role, research persistence subsystem, lock/lease/heartbeat, retry/progress counter, hidden ownership state, mandatory Explore gate, or `review-explore` action.
