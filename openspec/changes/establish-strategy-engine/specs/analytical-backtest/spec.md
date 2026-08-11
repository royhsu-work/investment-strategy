## Purpose

Define the observable behavior of analytical walk-forward Backtest evaluation that replays the same Strategy implementation used by Decision without simulating fills, positions, cash, or execution-derived performance.

## ADDED Requirements

### Requirement: Analytical Backtest reuses Strategy evaluation behavior

The system SHALL evaluate historical Backtest dates through the same common Strategy evaluation behavior used by Decision rather than through a separate simplified strategy implementation.

#### Scenario: Decision and Backtest evaluate equivalent inputs

- GIVEN equivalent strategy identity, parameter set, code revision, market data, and `as_of=T`
- WHEN Decision and analytical Backtest evaluate those equivalent inputs
- THEN their analytical Strategy Results are equivalent

### Requirement: Analytical Backtest advances chronologically

The system SHALL evaluate Backtest dates in chronological trading-day order.

#### Scenario: Replay a historical range

- GIVEN a valid historical range containing multiple completed trading days
- WHEN the analytical Backtest runs
- THEN evaluation points are processed in chronological trading-day order

### Requirement: Analytical Backtest prevents look-ahead

The system SHALL ensure that evaluation at historical date T uses only information available on or before T.

#### Scenario: Future observations exist in the loaded dataset

- GIVEN the Backtest has loaded data through T+N
- WHEN the Strategy is evaluated at T
- THEN observations after T do not affect the Strategy Result at T

### Requirement: Backtest range is an inclusive calendar interval over completed trading days

The system SHALL interpret `start_date` and `end_date` as an inclusive calendar interval and SHALL evaluate only completed trading days contained within that interval without resolving non-trading endpoints to dates outside the requested range.

#### Scenario: Range endpoints are non-trading days

- GIVEN `start_date` is a non-trading day
- AND `end_date` is a later non-trading day
- AND completed trading days exist between them
- WHEN the analytical Backtest range is prepared
- THEN only completed trading days inside the inclusive calendar interval are evaluation dates
- AND neither endpoint is clamped to a trading day outside the requested interval

#### Scenario: Current incomplete trading day is inside the range

- GIVEN the requested range includes the current trading day
- AND the current trading session is not complete
- WHEN evaluation dates are prepared
- THEN the incomplete current trading day is not an evaluation date
- AND earlier completed trading days inside the interval remain eligible for replay

### Requirement: Invalid Backtest ranges are rejected before market-data loading

The system SHALL reject a syntactically valid Backtest request whose range cannot define a valid completed historical evaluation interval.

#### Scenario: Start date is after end date

- GIVEN an accepted Backtest request whose `start_date` is later than `end_date`
- WHEN application request validation runs
- THEN the Backtest fails
- AND the failure category is `CONFIGURATION_FAILED`
- AND the failure code is `INVALID_BACKTEST_RANGE`
- AND market-data loading and strategy evaluation do not run

#### Scenario: End date is in the future

- GIVEN an accepted Backtest request whose `end_date` is later than the current applicable calendar date
- WHEN application request validation runs
- THEN the Backtest fails
- AND the failure category is `CONFIGURATION_FAILED`
- AND the failure code is `INVALID_BACKTEST_RANGE`
- AND market-data loading and strategy evaluation do not run

#### Scenario: Range contains no completed trading day

- GIVEN an accepted Backtest request whose `start_date` is not later than `end_date`
- AND the inclusive requested interval contains no completed trading day
- WHEN the Backtest request range is resolved against the trading calendar
- THEN the Backtest fails
- AND the failure category is `CONFIGURATION_FAILED`
- AND the failure code is `INVALID_BACKTEST_RANGE`
- AND strategy evaluation does not run

### Requirement: Backtest assignment request is a discriminated union

The Backtest request boundary SHALL accept exactly one of two assignment shapes: `ACTIVE`, where `strategy` and `parameter_set` are absent, or `EXPLICIT`, where both `strategy` and `parameter_set` are present. Any request that violates the shape selected by `mode` SHALL be rejected before Backtest application evaluation begins and SHALL NOT produce a public Backtest artifact.

#### Scenario: ACTIVE request includes explicit assignment fields

- GIVEN an analytical Backtest request with `mode=ACTIVE`
- AND the request supplies a strategy or parameter set
- WHEN the Backtest request boundary validates the request contract
- THEN the request is rejected
- AND Backtest application evaluation does not begin
- AND no public Backtest artifact is produced
- AND the supplied explicit fields are not silently ignored or converted into `EXPLICIT` mode

#### Scenario: EXPLICIT request omits both assignment fields

- GIVEN an analytical Backtest request with `mode=EXPLICIT`
- AND the request supplies neither strategy nor parameter set
- WHEN the Backtest request boundary validates the request contract
- THEN the request is rejected
- AND Backtest application evaluation does not begin
- AND no public Backtest artifact is produced
- AND the active assignment is not silently borrowed

#### Scenario: EXPLICIT request supplies only strategy

- GIVEN an analytical Backtest request with `mode=EXPLICIT`
- AND the request supplies a strategy but no parameter set
- WHEN the Backtest request boundary validates the request contract
- THEN the request is rejected
- AND Backtest application evaluation does not begin
- AND no public Backtest artifact is produced
- AND the active parameter set is not silently borrowed

#### Scenario: EXPLICIT request supplies only parameter set

- GIVEN an analytical Backtest request with `mode=EXPLICIT`
- AND the request supplies a parameter set but no strategy
- WHEN the Backtest request boundary validates the request contract
- THEN the request is rejected
- AND Backtest application evaluation does not begin
- AND no public Backtest artifact is produced
- AND the active strategy is not silently borrowed

### Requirement: Analytical Backtest supports active assignment mode

The system SHALL support an accepted `ACTIVE` research mode that uses the instrument's configured active strategy and parameter set.

#### Scenario: Run Backtest with active assignment

- GIVEN an instrument with a valid active strategy assignment
- WHEN an accepted analytical Backtest is requested in `ACTIVE` mode
- THEN each eligible evaluation uses that active strategy and parameter set

#### Scenario: Active assignment is missing

- GIVEN a configured instrument without an active strategy assignment
- WHEN an accepted analytical Backtest is requested in `ACTIVE` mode
- THEN the Backtest fails
- AND the failure category is `CONFIGURATION_FAILED`
- AND the failure code is `ACTIVE_STRATEGY_NOT_CONFIGURED`
- AND market-data loading and strategy evaluation do not run

### Requirement: Analytical Backtest supports explicit strategy assignment

The system SHALL support an accepted `EXPLICIT` research mode that uses a fully specified strategy and parameter-set pair without changing or requiring the instrument's active formal assignment.

#### Scenario: Research another strategy pair

- GIVEN an instrument whose active assignment is strategy A with parameter set A1
- AND a compatible strategy B with parameter set B1 exists
- WHEN an accepted analytical Backtest is requested in `EXPLICIT` mode with strategy B and parameter set B1
- THEN the Backtest evaluates strategy B with parameter set B1
- AND the instrument's active assignment remains strategy A with parameter set A1

#### Scenario: Instrument has no active assignment

- GIVEN a configured instrument without an active strategy assignment
- AND a compatible explicit strategy B with parameter set B1 exists
- WHEN an accepted analytical Backtest is requested in `EXPLICIT` mode with strategy B and parameter set B1
- THEN the Backtest evaluates strategy B with parameter set B1
- AND the missing active assignment does not cause the explicit Backtest to fail

### Requirement: Backtest data range may include pre-roll history

The system SHALL allow strategy input history to begin before the Backtest requested evaluation start date so that minimum-history requirements can be satisfied without treating pre-roll dates as part of the requested evaluation range.

#### Scenario: Minimum history requires observations before Backtest start

- GIVEN a Backtest evaluation range beginning at T
- AND the selected strategy requires historical observations before T
- WHEN the Backtest data range is prepared
- THEN the system may load and validate observations before T as pre-roll history
- AND those pre-roll dates are not reported as requested Backtest evaluation dates

### Requirement: Valid but insufficient early history is warm-up

The system SHALL classify an early historical evaluation point as `WARMUP` when its available data is valid but does not yet satisfy the selected strategy's minimum-history requirement.

#### Scenario: Early date has insufficient observations

- GIVEN valid historical data
- AND an early Backtest date has fewer eligible observations than the strategy minimum-history requirement
- WHEN the Backtest reaches that date
- THEN the date is classified as `WARMUP`
- AND no Strategy Result is evaluated for that date
- AND it is not classified as `NEUTRAL` or a data failure

### Requirement: Backtest requires at least one eligible evaluation date

The system SHALL NOT report a successful analytical Backtest when every requested completed trading-day evaluation date is `WARMUP` and no Strategy Result can be evaluated.

#### Scenario: Entire requested range is warm-up

- GIVEN the requested Backtest range contains completed trading-day evaluation dates with valid historical data
- AND every requested evaluation date has fewer observations than the selected strategy's minimum-history requirement
- WHEN the analytical Backtest completes eligibility processing
- THEN the Backtest fails
- AND the failure category is `DATA_FAILED`
- AND the failure code is `INSUFFICIENT_HISTORY`
- AND the Backtest does not present an empty analytical timeline as a successful result

#### Scenario: Requested range contains warm-up and eligible dates

- GIVEN early requested evaluation dates are `WARMUP`
- AND at least one later requested evaluation date satisfies the selected strategy's minimum-history requirement
- WHEN the analytical Backtest runs
- THEN the Backtest may complete successfully
- AND the eligible dates contain Strategy Results
- AND the warm-up dates remain distinguishable from eligible dates

### Requirement: Invalid Backtest data fails instead of being silently skipped

The system SHALL fail an analytical Backtest when required historical data is invalid rather than silently omitting invalid observations and continuing with potentially biased results.

#### Scenario: Invalid bar exists within required Backtest data

- GIVEN the historical data required by the Backtest contains an invalid observation
- WHEN validation runs
- THEN the Backtest fails
- AND the failure category is `DATA_FAILED`
- AND the invalid observation is not silently skipped

### Requirement: Strategy failure during Backtest is fail-fast

The system SHALL fail the analytical Backtest if strategy evaluation fails at any eligible historical evaluation point and SHALL NOT present a partial timeline as a successful Backtest.

#### Scenario: Strategy evaluation fails at an eligible date

- GIVEN configuration and required market data are valid
- AND strategy evaluation succeeds for earlier eligible dates
- AND strategy evaluation fails at historical date T
- WHEN the analytical Backtest reaches T
- THEN the Backtest fails
- AND the failure category is `STRATEGY_FAILED`
- AND it stops successful analytical replay at that failure
- AND it does not represent the partial Strategy Result timeline as a successful Backtest

### Requirement: Analytical Backtest does not simulate execution state

The system SHALL limit this capability to analytical Strategy Result replay and SHALL NOT require or produce simulated fills, positions, cash balances, or execution-derived performance metrics.

#### Scenario: Strategy emits an entry plan during replay

- GIVEN a Strategy Result at T contains an entry plan
- WHEN the analytical Backtest records that result
- THEN the Backtest preserves the analytical entry plan
- AND it does not claim a fill occurred
- AND it does not update a simulated position or cash balance

### Requirement: Analytical Backtest output is traceable

The system SHALL identify enough metadata in a successful analytical Backtest output to reproduce the evaluated strategy assignment and historical range.

#### Scenario: Successful analytical Backtest artifact is generated

- GIVEN an analytical Backtest completes successfully
- WHEN its public artifact is produced
- THEN the artifact status is `SUCCESS`
- AND it identifies the instrument
- AND it identifies the assignment mode
- AND it identifies the strategy
- AND it identifies the parameter set
- AND it identifies the Git revision
- AND it identifies the requested start and end dates
- AND it includes validation status
- AND its requested evaluation timeline distinguishes `WARMUP` dates from eligible dates containing Strategy Results

### Requirement: Failed analytical Backtest output uses a minimal common failure contract

The system SHALL represent application configuration, data, or strategy failures explicitly in failed analytical Backtest artifacts and SHALL NOT present partial results as a successful Backtest.

#### Scenario: Accepted analytical Backtest fails

- GIVEN an accepted analytical Backtest request fails during application request validation, configuration resolution, formal data loading or validation, or strategy evaluation
- WHEN the Backtest artifact is produced
- THEN the artifact status is `FAILED`
- AND it identifies the requested instrument
- AND it identifies the requested assignment mode
- AND it identifies the requested start and end dates
- AND it identifies the Git revision used by the application
- AND `failure.category` is `CONFIGURATION_FAILED`, `DATA_FAILED`, or `STRATEGY_FAILED` as applicable
- AND `failure.code` contains a machine-readable failure code
- AND `failure.reason` contains a human-readable failure reason
- AND it does not present a partial analytical timeline as a successful Backtest

#### Scenario: Failure occurs after some internal metadata was resolved

- GIVEN an accepted analytical Backtest request later fails
- AND internal processing may already know a strategy, parameter set, validation status, or partial analytical timeline
- WHEN the failed public artifact is produced
- THEN those internally known fields are not required by the public failure contract
- AND unresolved strategy or parameter-set metadata is not fabricated
- AND no partial analytical timeline is represented as successful output

### Requirement: Public analytical Backtest artifact includes the fixed disclaimer

The system SHALL include exactly `僅為個人研究與策略驗證，不構成任何形式之投資建議。` in every public analytical Backtest artifact produced by the Backtest application.

#### Scenario: Successful public analytical Backtest artifact

- GIVEN an analytical Backtest completes successfully
- WHEN the public artifact is generated
- THEN the artifact contains exactly `僅為個人研究與策略驗證，不構成任何形式之投資建議。`

#### Scenario: Failed public analytical Backtest artifact

- GIVEN an accepted analytical Backtest request fails during application validation, configuration, data validation, or strategy evaluation
- WHEN the public artifact is generated
- THEN the artifact still contains exactly `僅為個人研究與策略驗證，不構成任何形式之投資建議。`
