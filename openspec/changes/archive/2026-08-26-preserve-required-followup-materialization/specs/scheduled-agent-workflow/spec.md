# scheduled-agent-workflow Delta Specification

## ADDED Requirements

### Requirement: Explore-originated required follow-up decisions are materialized before Propose and preserved through formalization

When decision-complete `Lead / explore-change` explicitly classifies bounded later work as a **required separate follow-up**, the exact durable Explore `ACTION_RESULT` that establishes `PROPOSAL_READY` SHALL record that required-follow-up decision and sufficient bounded identity to reconstruct the intended separate work. After that result is durable and therefore supplies the exact defer-decision reference, the owning Explore action MUST create, reuse, or repair the required tracker under the existing routing-complete required-follow-up contract and MUST NOT complete routing of the source Issue to `Lead / propose-change` until a fresh observation proves the required tracker postcondition.

Ordinary deferred, optional, non-goal, or out-of-scope work MUST NOT gain a tracker obligation merely from presentation wording such as `Deferred work`, `follow-up`, `out of scope`, or `separately reviewable`. Work whose exact separate tracker is already durably established MUST reuse that tracker and MUST NOT create a duplicate.

If the Explore result is durable but materialization or successor routing is interrupted, reconstruction SHALL consume that same exact Explore result and complete only the missing idempotent materialization/routing effects. It MUST NOT create a second defer decision, infer a replacement classification from prose, or treat a partially materialized tracker as complete.

For an Explore-originated `Lead / propose-change`, Lead MUST dereference the exact durable Explore `ACTION_RESULT`, preserve every still-applicable required-follow-up classification from that result in proposal/readiness evidence, and fresh-verify the corresponding routing-complete tracker state before declaring OpenSpec readiness. If exactly one matching tracker is incomplete only in fields/routing that current source authority permits Lead to establish, Propose MAY repair only those missing parts under the existing idempotent materialization contract. Missing source authority, multiple/ambiguous matches, or contradictory tracker evidence MUST fail closed.

Propose MUST NOT downgrade a required separate-follow-up decision into ordinary deferred prose merely by excluding that later work from the current Change, and MUST NOT upgrade ordinary deferred/optional prose into a required follow-up without the approved source decision. Reviewer and lifecycle responsibilities remain those of the existing global required-follow-up contract; this requirement adds no new Reviewer producer authority or lifecycle topology.

#### Scenario: Explore materializes a newly required separate follow-up before successor routing

- GIVEN `Lead / explore-change` reaches a decision-complete direction
- AND that decision explicitly requires bounded later work to be handled as a separate follow-up change
- WHEN Lead records the durable `PROPOSAL_READY` Explore `ACTION_RESULT`
- THEN that exact result records the required-follow-up classification and bounded follow-up identity
- AND the owning Explore action creates, reuses, or repairs exactly one tracker linked to the exact source coordination/change and that durable defer-decision reference
- AND a fresh observation proves `Change: unset` plus `agent:lead + action:explore-change` on the tracker
- AND only after that postcondition is complete may the source Issue complete routing to `Lead / propose-change`

#### Scenario: Interrupted Explore materialization resumes from the same durable decision

- GIVEN the exact Explore `ACTION_RESULT` already durably records `PROPOSAL_READY` and one required separate-follow-up decision
- AND the source Issue remains routed to `Lead / explore-change` because tracker materialization or successor routing was interrupted
- WHEN a later Explore invocation reconstructs that source
- THEN it consumes the existing exact Explore result rather than creating a new defer decision
- AND it fresh-reads matching trackers
- AND it creates or repairs only the missing routing-complete postcondition when uniquely authorized
- AND multiple or ambiguous matches fail closed rather than creating another tracker

#### Scenario: Ordinary deferred wording creates no tracker obligation

- GIVEN an Explore result or formal proposal describes later work as `Deferred work`, `out of scope`, `follow-up`, or `separately reviewable`
- BUT the approved Explore decision does not classify that work as required separate follow-up
- WHEN Explore or Propose evaluates tracker materialization
- THEN no required tracker is created from that wording alone
- AND the existing semantic distinction between ordinary deferred work and required separate follow-up is preserved

#### Scenario: Propose preserves a required follow-up while keeping it outside current implementation scope

- GIVEN exact Explore result E records one required separate-follow-up decision
- AND the required tracker is routing-complete and linked to E
- WHEN the same coordination Issue enters `Lead / propose-change`
- THEN Lead dereferences E exactly
- AND proposal/readiness evidence preserves the required-follow-up classification and tracker reference
- AND the separate work MAY remain outside the current Change implementation scope
- BUT its required status is not downgraded to ordinary deferred prose
- AND Reviewer can independently reconstruct the same approved obligation and tracker at `review-openspec`

#### Scenario: Propose repairs only a unique incomplete required tracker

- GIVEN exact Explore result E records a required separate-follow-up decision
- AND exactly one source-linked matching tracker exists
- AND that tracker is incomplete only in durable materialization fields or canonical routing that current source authority permits Lead to establish
- WHEN `Lead / propose-change` prepares OpenSpec readiness
- THEN Lead repairs only the missing fields/routing
- AND does not create a duplicate tracker
- AND readiness is not reported until a fresh observation proves the routing-complete postcondition
- AND multiple or ambiguous matching trackers instead fail closed
