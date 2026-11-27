## MODIFIED Requirements

### Requirement: Test-first delivery and independent engineering review preserve observable behavior

For executable feature or defect-correction work, Executor SHALL use the repository-owned TDD procedure to develop one observable behavior at a time through a relevant public test seam: a test with independently derived expected behavior, an intended target RED before implementation, and the minimum sufficient implementation yielding GREEN. The next behavior cycle SHALL follow the prior cycle rather than batching tests and implementation horizontally. A test double SHALL preserve the contract of the substituted boundary; implementation-coupled tests SHALL NOT be used as a substitute for relevant observable behavior coverage.

For each executable behavior developed under this requirement, actual repository-supported CI evidence SHALL establish that the test was executed against a revision before the target implementation and failed for the missing or incorrect target behavior, and that the corrected behavior subsequently passes. Static, syntax, import, setup, fixture and unrelated failures MUST NOT qualify as intended RED. A test added only after implementation MUST NOT be reported as Test First. Previously developed behavior retains its actual history; prior verified work MUST NOT be replayed merely to fabricate retrospective RED evidence. The existing approved CI-only, static-first and normal development iteration contracts remain applicable; this requirement MUST NOT add a CI mode, runner, durable TDD state or new Action. A test cycle may save durable partial work but does not establish formal slice completion. Checkpoint is persistence and continuation only; existing exact-revision, full regression/quality, task criteria, independently qualified formal delivery and lifecycle gates SHALL remain required.

For material changes to Skill or procedural decision behavior with no new executable behavior, the changed behavior SHALL be evaluated using applicable Skill/config inputs, fixed discriminating cases and actual before/after decisions, not a claim of executable CI RED. Non-material wording, formatting, reference-only or other documentation changes without changed procedural behavior do not require this evaluation. Existing mechanical verification and independent exact-revision review SHALL still apply. A text-presence assertion alone MUST NOT establish semantic Skill behavior. Unavailable execution evidence MUST NOT be represented as a successful test or used to reduce approved requirements.

Independent Implementation Review SHALL own proactive refactoring assessment of the exact reviewed implementation and test evidence. Executor SHALL retain responsibility for minimum sufficient correct implementation, actual regression correction and substantiated in-scope finding correction, not independent acceptance of its own work. Reviewer MUST NOT modify its own reviewed target or introduce a blocking condition for merely advisory improvement. Necessary corrections SHALL use the existing evidence-based finding closure contract, including independent re-review of the corrected exact revision.

OpenSpec Review and Implementation Review SHALL consume the repository-owned shared engineering knowledge appropriate to the reviewed stage. OpenSpec Review considers observable design and slice feasibility risks before implementation; Implementation Review considers actual implementation, architecture, test quality and refactoring opportunities. Engineering principles, design patterns, smells and general standards supplied as knowledge are advisory heuristics; they SHALL NOT create additional binding requirements, mechanical gates, fixed review checklists or mandatory item-by-item reports. Blocking findings remain governed by existing approved requirements or applicable invariants, exact evidence, stage and observable closure.

Within the affected scope, tests SHALL be retained, rewritten, consolidated or retired according to the existing authoring and review ownership rules. Retirement or replacement SHALL preserve still-applicable behavior, unique regression, supported compatibility and safety guarantees through verified equivalent or stronger coverage, or authoritative evidence of contract retirement. Tests MUST NOT be weakened, skipped or redefined merely to achieve GREEN, and obsolete implementation need not be preserved solely to satisfy obsolete assertions. The existing delivery evidence SHALL identify the affected guarantee, rationale and replacement or retirement evidence for independent review, without a new test registry or repository-wide cleanup obligation.

#### Scenario: A focused behavior establishes genuine Test First

- GIVEN an approved Slice requires multiple observable behaviors
- WHEN Executor develops one behavior through an agreed public seam and repository CI establishes the intended missing-behavior failure before implementation
- THEN Executor implements only enough behavior to achieve GREEN before the next behavior cycle
- AND the exact CI and revision evidence supports Test First
- AND partial work may be saved while formal Slice delivery remains subject to all required completion conditions

#### Scenario: An unrelated failure or retrospective test does not establish RED

- GIVEN a failing test run is caused by a static, syntax, import, fixture, setup or unrelated regression failure, or the purported test-only revision already contains the target implementation
- WHEN the TDD evidence is assessed
- THEN the evidence does not qualify as intended Test First RED
- AND no successful RED or verified Slice completion is manufactured

#### Scenario: Behavior test uses a representative public seam

- GIVEN an interface changes and an internal test double does not implement a required operation
- WHEN Executor and Reviewer assess the affected regression
- THEN they preserve the meaningful observable guarantee and correct the interface mismatch using an appropriate real collaborator or representative boundary substitute
- AND they do not remove the regression solely because an implementation-specific test double fails

#### Scenario: Skill behavior is evaluated without pretending Python RED

- GIVEN a governed change materially changes Skill or procedural decision behavior and introduces no new executable behavior
- WHEN Executor evaluates identical discriminating inputs before and after the relevant Skill change
- THEN the actual decisions and consulted source revisions establish the target semantic behavior evidence
- AND the existing mechanical quality gates and independent review remain required
- AND the semantic evaluation is not reported as executable CI RED

#### Scenario: OpenSpec Review examines a foreseeable delivery risk

- GIVEN a proposed Slice combines coupled interfaces and postpones behavior verification, while another plan has an appropriately small verifiable scope
- WHEN independent OpenSpec Review consumes the shared engineering knowledge and reviews the design and task plan
- THEN it can identify a demonstrable approved-requirement or delivery-feasibility violation before implementation
- AND a harmless alternative design or heuristic smell is advisory rather than a new acceptance gate

#### Scenario: Independent implementation review owns necessary refactoring assessment

- GIVEN the implementation has GREEN evidence and the exact reviewed revision contains an evidenced in-scope design or test defect
- WHEN Implementation Review assesses the revision
- THEN Reviewer records a substantiated finding using the existing closure contract
- AND Executor performs or substantiates the correction without self-clearing the finding
- AND independent Reviewer verifies closure on the exact corrected revision
- AND an unrelated aesthetic suggestion does not block PASS

#### Scenario: Superseded test differs from unique regression protection

- GIVEN an affected test asserts an obsolete implementation detail and another test protects a still-applicable unique safety or regression guarantee
- WHEN Executor evaluates test retirement and Reviewer independently inspects the evidence
- THEN the obsolete assertion may be retired with verified replacement coverage or authoritative contract retirement
- AND the unique applicable guarantee remains verified
- AND deleting or weakening a valid expectation merely to achieve GREEN is not accepted
