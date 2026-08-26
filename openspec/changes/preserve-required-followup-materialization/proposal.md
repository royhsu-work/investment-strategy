# Change: Preserve required follow-up materialization across Explore and Propose

Explore source: #158 `issuecomment-5422771356` (`Lead / explore-change → PROPOSAL_READY`).

## Why

The canonical workflow already distinguishes ordinary deferred/optional work from an approved **required separate follow-up** and already requires the latter to have one source-linked routing-complete tracker before lifecycle completion. The demonstrated gap is earlier and action-local: when decision-complete Explore itself splits current work from a required later change, `openspec-explore` does not explicitly materialize that obligation, and Explore-originated `propose-change` does not explicitly preserve that classification and verify/repair the tracker postcondition.

That omission permits a required later obligation to be editorially moved under `Deferred work`, `out of scope`, or similar prose during formalization and thereby lose the materialization trigger even though the global invariant remains correct. Conversely, wording such as `follow-up` or `separately reviewable` must not by itself create a tracker when the approved source decision did not classify the work as required.

The exact #158 Explore reconstruction found no retrospective required-follow-up defect in #140 or #155. Their historical text remains evidence for classification boundaries, not authority to invent trackers after the fact.

## What Changes

- Make decision-complete `Lead / explore-change` explicitly classify later work as one of: ordinary deferred/optional/non-goal, required separate follow-up, or already-tracked separate work.
- When Explore semantically decides a required separate follow-up, require it to create, reuse, or repair exactly one source-linked tracker and fresh-verify the routing-complete postcondition before persisting `PROPOSAL_READY`.
- Keep tracker materialization idempotent: no match creates one; one incomplete match repairs only missing durable fields/routing; multiple or ambiguous matches fail closed.
- Make Explore-originated `Lead / propose-change` dereference the exact durable Explore `ACTION_RESULT`, preserve its required-follow-up classification, and verify/repair the required tracker before readiness/handoff. Formalization must neither downgrade a required obligation into ordinary deferred prose nor upgrade ordinary deferred prose from wording alone.
- Keep the existing Reviewer and lifecycle responsibilities unchanged: Reviewer verifies the already-required tracker at the semantic gate; lifecycle remains a fail-safe rather than the normal producer.
- Add focused RED/GREEN coverage for the Explore producer boundary and Explore → Propose preservation boundary.

## Affected Capabilities

### Added

- `scheduled-agent-workflow`
  - Explore-originated required-follow-up classification is materialized at the decision boundary and preserved through Propose.

## Scope

In scope:

- `openspec-explore` required-follow-up classification/materialization at decision-complete Explore;
- `openspec-change` preservation and materialization verification/repair for Explore-originated Propose;
- one narrow canonical workflow requirement that makes those producer/preservation boundaries externally verifiable;
- focused regressions in `tests/test_required_followup_materialization.py` and `tests/test_explore_proposal_handoff.py`.

Out of scope:

- changing the existing three-way semantic meaning of ordinary deferred vs required separate follow-up vs already-tracked work;
- changing workflow topology, WIP/cardinality, Human authority, direct-Propose admission, Reviewer ownership, or lifecycle ownership;
- moving normal tracker production to Reviewer or lifecycle finalization;
- creating trackers merely from words such as `Deferred work`, `out of scope`, `follow-up`, or `separately reviewable`;
- retrospective tracker creation for #140 or #155;
- unrelated runtime/deployment changes.

## Skill maintenance traceability

| Skill | Class | Approved source | Responsibility treatment | Rationale |
| --- | --- | --- | --- | --- |
| `agents/skills/openspec-explore/SKILL.md` | Modified | #158 `issuecomment-5422771356` / this Change | Preserve Lead Explore ownership; add action-local classification and routing-complete materialization when Explore itself decides a required separate follow-up | The global invariant currently lacks an explicit Explore producer step at the decision boundary |
| `agents/skills/openspec-change/SKILL.md` | Modified | #158 `issuecomment-5422771356` / this Change | Preserve Lead Propose/resolve ownership; add Explore-originated preservation plus tracker verification/repair at Propose | Formalization must not silently downgrade an already-decided required follow-up or lose its materialized tracker |

No Skill is Added or Removed. Reviewer and lifecycle Skills retain their existing verification/fail-safe responsibilities and are not modified by this Change.

## Traceability

- Decision-complete Explore baseline: #158 `issuecomment-5422771356`.
- Historical global obligation/materialization baselines: #50 and #100.
- Historical classification checks with no retrospective tracker required: #140 and #155.
- Capability delta: `specs/scheduled-agent-workflow/spec.md`.
- Design: `design.md`.
- Implementation slices: `tasks.md`.
