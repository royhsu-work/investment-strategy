## ADDED Requirements

### Requirement: Run-scoped dispatch Artifact consumption is canonical, diagnosable and recoverable

The existing repository-owned dispatch Artifact reader and NO_WORK idle-admission Application SHALL consume one successful native bridge run's unique, unexpired `dispatch-result.json` through the same canonical dispatch-result contract used by its producer and normal dispatch parser. The consumer MUST bind the exact source request comment, run identity and attempt, workflow, default-branch revision, Artifact id, declared size/digest, downloaded raw bytes and parsed disposition before allowing any idle admission. A connector filename or media type MUST NOT override the verified bytes or create a second representation/schema authority. The downloaded bytes MUST be checked against authoritative size/digest metadata before canonical parsing; missing, contradictory, duplicate or incomplete identity/integrity evidence MUST fail closed without mutation.

The existing reader/idle boundary SHALL retain a safe machine-readable failure stage and classification, the applicable request/run/attempt/Artifact/revision correlation, observed sanitized HTTP status or exception category when actually known, and `mutation_attempted`. It MUST distinguish transient read unavailability, untrusted redirect, invalid payload representation/schema, integrity mismatch, stale/contradictory identity, permanently invalid evidence, and a recoverable but incomplete observation. It MUST NOT collapse independent observed failures into a generic undiagnosable result or expose tokens, signed URLs or sensitive response content. Unknown causes MUST remain explicitly unknown until executable evidence proves them; a preexisting generic historical error MUST NOT be reclassified by assumption.

GitHub GET reads MAY retry only within an explicit bound after qualifying retryable statuses 500, 502, 503 or 504 or timeouts. Authorization/identity failures, malformed data and contradictory evidence MUST NOT be silently converted into successful admission. No POST, PATCH, Issue create, label or other consequential write may use automatic retry or mutation-based read/probe. An ambiguous prior write SHALL be reconciled by fresh current GitHub source objects and canonical postconditions before any later admission; a transient read failure SHALL remain eligible for the existing legal fresh-wake recovery path when authoritative evidence becomes available. Neither path may add persistent state, routing authority, a queue, lease, registry, cursor, or duplicate candidate.

#### Scenario: Native raw JSON is consumed under the canonical contract

- GIVEN one completed successful correlated bridge run has exactly one unexpired `dispatch-result.json` with raw UTF-8 JSON bytes and matching metadata digest and size
- AND the canonical parser returns `NO_WORK / no-routed-work` for the same source comment and default-branch revision
- WHEN the idle Application re-reads the Artifact and current repository state
- THEN it accepts the unique valid NO_WORK evidence for fresh normal-dispatch/eligibility evaluation
- AND it does not require a connector-declared ZIP format or a separate parser

#### Scenario: Signed redirect does not forward credentials

- GIVEN the exact Artifact GET returns HTTP 302 to an eligible trusted HTTPS Artifact host
- WHEN the existing reader follows the signed URL
- THEN it does not forward the GitHub API bearer token to the redirected host
- AND an untrusted host, scheme or redirect failure is rejected with a specific sanitized stage and without mutation

#### Scenario: Consumer detects incomplete and invalid Artifact identity

- GIVEN the run is wrong, incomplete, unsuccessful or for another request, attempt, workflow or main revision
- OR the Artifact is missing, duplicated, expired, stale, wrong-sized, wrong-digested or listed with incomplete pagination
- WHEN the Application attempts read-only qualification
- THEN it rejects admission with a stage-specific machine-readable cause and `mutation_attempted=false`
- AND it does not substitute another run, Artifact, Issue or dispatch result

#### Scenario: Payload format and integrity are not the same failure

- GIVEN downloaded Artifact bytes are truncated, have the wrong digest, contain unexpected ZIP or malformed JSON, or parse to a wrong disposition/schema
- WHEN the canonical consumer validates the bytes
- THEN byte integrity failures are distinguishable from format/schema and disposition failures
- AND none can authorize idle admission or silently fall back to another parser

#### Scenario: Retryable GET failure recovers on a later valid observation

- GIVEN the native reader observes an HTTP 500, 502, 503, 504 or timeout and no write has been attempted
- WHEN a bounded read-only retry succeeds or a later legitimate fresh wake repeats normal qualification after the fault clears
- THEN the existing Application can reach the same canonical admission postcondition without needing an extra state record
- AND exhaustion remains a diagnosable, non-mutating recoverable failure

#### Scenario: Permanent read invalidity cannot be bypassed by retry

- GIVEN the reader observes 401, 403, 404, an untrusted redirect, malformed or conflicting identity, or invalid payload
- WHEN it classifies the failure
- THEN it preserves the specific non-authorizing cause and performs no write or mutation probe
- AND it does not automatically reclassify the response as retryable transient success

#### Scenario: Interrupted and concurrent admissions remain idempotent

- GIVEN one admission is interrupted before writing, after an ambiguous write, or overlaps another idle admission
- WHEN later legitimate wakes reconstruct current GitHub Issues, labels, bodies and normal dispatch inside the existing application boundary
- THEN at most one canonical `Change: unset + action:explore-change` admission can be accepted
- AND prior matching completion is reconciled read-only, unrelated state is preserved, stale/replayed evidence does not write, and the later ordinary Action waits for a separate fresh wake

#### Scenario: Production acceptance crosses the real idle boundary

- GIVEN the formal T1 implementation, independent review and lifecycle have legally completed so true NO_WORK is possible
- WHEN a real Scheduled Task publishes `DISPATCH_REQUEST`, one successful native run publishes its exact raw Artifact, and the idle Application consumes it
- THEN fresh normal-dispatch eligibility can admit existing #218 exactly once without duplicate Issue or mutation
- AND a separate later fresh dispatch selects ordinary `Lead / explore-change`
- AND unit/CI success or a simulated E2E alone does not establish this production acceptance
