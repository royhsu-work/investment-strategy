## ADDED Requirements

### Requirement: Run-scoped dispatch Artifact consumption is canonical, diagnosable and recoverable

The existing repository-owned dispatch Artifact reader and NO_WORK idle-admission Application SHALL consume one successful native bridge run's unique, unexpired `dispatch-result.json` through the same canonical dispatch-result contract used by its producer and normal dispatch parser. The consumer MUST bind the exact source request comment, run identity and attempt, workflow, default-branch revision, Artifact id, declared size/digest, downloaded raw bytes and parsed disposition before allowing any idle admission. A connector filename or media type MUST NOT override the verified bytes or create a second representation/schema authority. The downloaded bytes MUST be checked against authoritative size/digest metadata before canonical parsing; missing, contradictory, duplicate or incomplete identity/integrity evidence MUST fail closed without mutation.

The existing reader/idle boundary SHALL retain a safe machine-readable failure stage and classification, the applicable request/run/attempt/Artifact/revision correlation, observed sanitized HTTP status or exception category when actually known, and `mutation_attempted`. It MUST distinguish transient read unavailability, untrusted redirect, invalid payload representation/schema, integrity mismatch, stale/contradictory identity, permanently invalid evidence, and a recoverable but incomplete observation. It MUST NOT collapse independent observed failures into a generic undiagnosable result or expose tokens, signed URLs or sensitive response content. Unknown causes MUST remain explicitly unknown until executable evidence proves them; a preexisting generic historical error MUST NOT be reclassified by assumption.

GitHub GET reads MAY retry only within an explicit bound after qualifying retryable statuses 500, 502, 503 or 504 or timeouts. Authorization/identity failures, malformed data and contradictory evidence MUST NOT be silently converted into successful admission. No POST, PATCH, Issue create, label or other consequential write may use automatic retry or mutation-based read/probe. An ambiguous prior write SHALL be reconciled by fresh current GitHub source objects and canonical postconditions before any later admission; a transient read failure SHALL remain eligible for the existing legal fresh-wake recovery path when authoritative evidence becomes available. Neither path may add persistent state, routing authority, a queue, lease, registry, cursor, or duplicate candidate.

**Canonical decision table (the existing reader/idle Application is the only execution owner; this is a specification oracle, not another runtime rules engine).** In every row, the preconditions MUST come from fresh GitHub run/attempt/Artifact/comment/ref/Issue sources, not a copied comment claim. The global postconditions/invariants are: no pre-write mutation; a single canonical producer/parser/disposition contract; no bearer forwarding on signed redirects; no write retry or probe; no duplicate admission; and a later ordinary Action only after a new wake. Each row MUST be covered by the stated rejected case and adjacent lawful-positive twin, with the named concrete blocked harm and recovery path.

| Guard / authoritative precondition | Reject or uncertainty; harm prevented | Adjacent lawful-positive twin; postcondition / continuation |
| --- | --- | --- |
| Exact successful completed bridge run/attempt, source comment, workflow and main revision | `IDENTITY_STALE` or `PERMANENT_INVALID`; prevents a prior/foreign request from authorizing an idle write | Same complete exact run/attempt/comment/revision can continue to Artifact qualification; any stale source requires a new normal dispatch |
| Exactly one unexpired Artifact ID, complete listing, declared size/digest matching downloaded raw bytes | `RECOVERABLE_INCOMPLETE`, `IDENTITY_STALE` or `INTEGRITY_MISMATCH` by observed stage; prevents partial/contradictory bytes from authorizing a write | Complete unique exact metadata plus size/hash-matched bytes proceeds to the canonical parser; incomplete reads may be fresh-observed later, contradictory identity cannot be reused |
| 200 direct bytes or 302 redirect with trusted HTTPS host and no forwarded API bearer | `REDIRECT_UNTRUSTED` or observed read error; prevents credential disclosure and untrusted bytes | Equally correlated 200/eligible trusted 302 returns the same raw content without token forwarding; only qualified transient GET failure can retry |
| Valid UTF-8 canonical JSON, schema and exact `NO_WORK / no-routed-work` disposition | `PAYLOAD_FORMAT_INVALID` or non-NO_WORK disposition; prevents malformed/alternate/AUTHORIZE evidence from selecting idle admission | Matching canonical NO_WORK qualifies for fresh normal dispatch; AUTHORIZE/FAIL_CLOSED yields zero idle write |
| GET 500/502/503/504 or timeout with no result bytes, versus 401/403/404 or invalid payload | `READ_UNAVAILABLE` for transient; observed nonretryable class for permanent/invalid; prevents guessing success or infinite/wrong retry | Bounded GET-only retry or later authorized fresh wake may produce valid exact evidence; unsupported status remains non-mutating |
| Current default branch and normal dispatch reauthorize NO_WORK; current candidate is eligible | stale/contradictory current formal work: no admission; prevents active WIP override | Current NO_WORK + exact eligible candidate authorizes at most one necessary Application write, followed by fresh full-tuple postcondition |
| Previous write outcome unknown or another idle attempt overlaps | `INDETERMINATE` on unresolved exact GitHub state; prevents duplicate Issue/label or replay | Fresh full-tuple match is `COMPLETE` with zero write; otherwise only still-needed non-contradictory effect may proceed after a fresh exact reauthorization, never an automatic write retry |

Table-driven test witnesses MUST include both sides of each row. A failing read with authoritative source unknown stays `UNKNOWN` for causal diagnosis, not converted to `PERMANENT_INVALID`. No row authorizes a new persisted state or independent router.

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

#### Scenario: Supported representations are metamorphically equivalent

- GIVEN the same fully correlated exact run/Artifact has equivalent digest-matched raw JSON bytes obtainable by supported native direct API, trusted signed redirect, or connector presentation
- WHEN each supported reader path normalizes through the same canonical parser and freshness qualifiers
- THEN the normalized schema, disposition and non-mutating eligibility decision MUST be identical for equivalent content
- AND unsupported ZIP/media claims, wrong raw bytes or missing identity MUST NOT become a second accepted representation or parser

#### Scenario: Bounded generated stateful sequences preserve safety and conditional progress

- GIVEN a small model generates combinations of accepted-intent, successful/corrupt run, read failure/repair, fresh/stale dispatch, one/two admissions, and pre/post-write interruption across two or more separate wakes
- WHEN the existing Application processes those sequences under its authoritative preconditions
- THEN safety properties hold for every prefix: no unauthorized mutation, no duplicate Issue/routing, no blind write retry, no replay/rewind, preserved unrelated content and no same-wake successor
- AND for sequences in which authoritative reads eventually recover and a later lawful wake exists, the eligible target can reach one verified complete admission rather than an unclassified permanent stall
- AND an unavailable upstream read does not itself guarantee completion

#### Scenario: Production acceptance crosses the real idle boundary

- GIVEN the formal T1 implementation, independent review and lifecycle have legally completed so true NO_WORK is possible
- WHEN a real Scheduled Task publishes `DISPATCH_REQUEST`, one successful native run publishes its exact raw Artifact, and the idle Application consumes it
- THEN fresh normal-dispatch eligibility can admit existing #218 exactly once without duplicate Issue or mutation
- AND a separate later fresh dispatch selects ordinary `Lead / explore-change`
- AND unit/CI success or a simulated E2E alone does not establish this production acceptance
