# scheduled-agent-workflow Delta Specification

## ADDED Requirements

### Requirement: A no-API Issue-comment canary proves the Scheduled Task transport boundary without granting workflow authority

The repository SHALL provide a bounded Phase 1 transport canary that can be triggered by a newly created GitHub Issue comment on one explicitly configured Human-created check-in Issue.

A valid canary request MUST contain exactly the transport marker `DISPATCH_REQUEST` and exactly one `Requested-At: <timestamp>` field. The GitHub comment ID of that exact request MUST be the sole correlation identity for the request/result round trip. A custom request identifier, latest-comment selection, comment ordering, or timestamp proximity MUST NOT substitute for the exact request comment ID.

For a valid request, repository-owned executable code running from the repository default-branch checkout SHALL produce a correlated result with exactly these transport fields:

```text
DISPATCH_RESULT
Request-Comment-ID: <exact GitHub request comment ID>
Default-Branch-Revision: <exact handler checkout revision>
Result: BRIDGE_OK
```

The canary MUST reject or ignore comments outside the configured check-in Issue, malformed request bodies, invalid request comment identities, and non-request comments. Reprocessing or duplicate delivery of a request that already has a valid correlated result MUST be an idempotent no-op and MUST NOT create a second effective result for the same request comment ID.

`DISPATCH_REQUEST` and `DISPATCH_RESULT` SHALL be transport/audit evidence only. A Phase 1 result MUST NOT contain or establish a mapped workflow Issue, Role, Action, Skill, routing transition, `Change:` mutation, review/merge gate, consequential effect authorization, or any other canonical workflow authority. A result comment MUST NOT satisfy the valid request contract.

Phase 1 acceptance SHALL include one real ChatGPT Scheduled Task invocation that writes the exact request, obtains the exact GitHub request comment ID, performs bounded fresh reads for that identity, and observes the exact matching Actions-produced result before that Scheduled Task invocation ends. The acceptance evidence MUST retain the request/result GitHub timestamps, exact handler default-branch revision, and the Scheduled Task observation sufficient to determine whether the matching result was received within the same invocation execution opportunity. Repository-only unit or structural tests MUST NOT substitute for this end-to-end transport proof.

#### Scenario: Valid request produces an exactly correlated bridge result

- GIVEN a Human-created check-in Issue is the explicitly configured Phase 1 canary target
- AND a new comment on that Issue contains exactly `DISPATCH_REQUEST` and one valid `Requested-At` field
- WHEN the default-branch canary workflow handles the `issue_comment` creation event
- THEN repository-owned executable code processes that exact request comment
- AND the result contains `Request-Comment-ID` equal to the triggering GitHub comment ID
- AND the result contains the exact default-branch revision used by the handler
- AND `Result` is `BRIDGE_OK`

#### Scenario: Scheduled Task correlates by exact comment identity

- GIVEN a Scheduled Task created request comment C
- AND multiple other request or result comments may exist on the same check-in Issue
- WHEN the Scheduled Task reads canary results
- THEN it accepts only a `DISPATCH_RESULT` whose `Request-Comment-ID` equals the exact GitHub ID of C
- AND it does not use the latest comment, relative ordering, timestamp proximity, or model inference as correlation

#### Scenario: Unrelated or malformed comment is not a valid request

- GIVEN a newly created Issue comment is outside the configured check-in Issue OR does not exactly satisfy the bounded request contract
- WHEN the canary workflow evaluates the event
- THEN it does not produce a valid `BRIDGE_OK` result for that comment
- AND it performs no workflow-routing, Change, review-gate, or consequential-effect mutation

#### Scenario: Duplicate request handling is idempotent

- GIVEN request comment C already has a valid correlated `DISPATCH_RESULT`
- WHEN the same event is redelivered, rerun, or otherwise reprocessed
- THEN the handler treats C as already completed
- AND it does not create a second effective result for C
- AND the existing result remains transport evidence only

#### Scenario: Result cannot re-enter the request protocol

- GIVEN the canary writes a `DISPATCH_RESULT` comment for request C
- WHEN that result comment is evaluated against the request parser
- THEN it does not satisfy the `DISPATCH_REQUEST` contract
- AND it cannot recursively authorize or invoke another canary request through its body

#### Scenario: Bridge success does not authorize mapped workflow work

- GIVEN a valid request receives `Result: BRIDGE_OK`
- WHEN any later workflow action is considered
- THEN the canary result does not identify or authorize a mapped Issue, Role, Action, or Skill
- AND it does not authorize any routing, `Change:`, review, merge, or consequential effect mutation
- AND later production machine-gating remains a separate governed capability boundary

#### Scenario: Same-invocation round trip is required for Phase 1 acceptance

- GIVEN the repository implementation and deterministic tests are green
- WHEN the Phase 1 deployment is evaluated for acceptance
- THEN one real ChatGPT Scheduled Task invocation writes a request and captures its exact GitHub comment ID
- AND that same invocation performs bounded fresh reads for the matching result
- AND acceptance is recorded only if the exact correlated result is observed before the invocation ends
- AND the evidence records request/result timestamps and the exact handler default-branch revision
