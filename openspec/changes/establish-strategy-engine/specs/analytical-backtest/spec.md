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

- GIVEN a valid historical range containing multiple trading days
- WHEN the analytical Backtest runs
- THEN evaluation points are processed in chronological trading-day order

### Requirement: Analytical Backtest prevents look-ahead

The system SHALL ensure that evaluation at historical date T uses only information available on or before T.

#### Scenario: Future observations exist in the loaded dataset

- GIVEN the Backtest has loaded data through T+N
- WHEN the Strategy is evaluated at T
- THEN observations after T do not affect the Strategy Result at T

### Requirement: Analytical Backtest supports active assignment mode

The system SHALL support an `ACTIVE` research mode that uses the instrument's configured active strategy and parameter set.

#### Scenario: Run Backtest with active assignment

- GIVEN an instrument with a valid active strategy assignment
- WHEN an analytical Backtest is requested in `ACTIVE` mode
- THEN each eligible evaluation uses that active strategy and parameter set

#### Scenario: Active assignment is missing

- GIVEN a configured instrument without an active strategy assignment
- WHEN an analytical Backtest is requested in `ACTIVE` mode
- THEN the Backtest fails with `CONFIGURATION_FAILED`
- AND the failure code is `ACTIVE_STRATEGY_NOT_CONFIGURED`
- AND market-data loading and strategy evaluation do not run

### Requirement: Analytical Backtest supports explicit strategy assignment

The system SHALL support an `EXPLICIT` research mode that uses a fully specified strategy and parameter-set pair without changing or requiring the instrument's active formal assignment.

#### Scenario: Research another strategy pair

- GIVEN an instrument whose active assignment is strategy A with parameter set A1
- AND a compatible strategy B with parameter set B1 exists
- WHEN an analytical Backtest is requested in `EXPLICIT` mode with strategy B and parameter set B1
- THEN the Backtest evaluates strategy B with parameter set B1
- AND the instrument's active assignment remains strategy A with parameter set A1

#### Scenario: Instrument has no active assignment

- GIVEN a configured instrument without an active strategy assignment
- AND a compatible explicit strategy B with parameter set B1 exists
- WHEN an analytical Backtest is requested in `EXPLICIT` mode with strategy B and parameter set B1
- THEN the Backtest evaluates strategy B with parameter set B1
- AND the missing active assignment does not cause the explicit Backtest to fail

### Requirement: Partial explicit override is rejected

The system SHALL reject an explicit Backtest assignment that specifies only a strategy or only a parameter set.

#### Scenario: Strategy is specified without parameter set

- GIVEN an analytical Backtest request in `EXPLICIT` mode
- AND the request provides a strategy but no parameter set
- WHEN configuration resolution runs
- THEN the Backtest fails with `CONFIGURATION_FAILED`
- AND the system does not silently reuse the active parameter set
- AND market-data loading and strategy evaluation do not run

#### Scenario: Parameter set is specified without strategy

- GIVEN an analytical Backtest request in `EXPLICIT` mode
- AND the request provides a parameter set but no strategy
- WHEN configuration resolution runs
- THEN the Backtest fails with `CONFIGURATION_FAILED`
- AND the system does not silently reuse the active strategy
- AND market-data loading and strategy evaluation do not run

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

The system SHALL NOT report a successful analytical Backtest when every requested evaluation date is `WARMUP` and no Strategy Result can be evaluated.

#### Scenario: Entire requested range is warm-up

- GIVEN the requested Backtest range contains valid historical data
- AND every requested evaluation date has fewer observations than the selected strategy's minimum-history requirement
- WHEN the analytical Backtest completes eligibility processing
- THEN the Backtest fails with `DATA_FAILED`
- AND the failure code is `INSUFFICIENT_HISTORY`
- AND the Backtest does not present an empty analytical timeline as a successful result

#### Scenario: Requested range contains warm-up and eligible dates

- GIVEN early requested dates are `WARMUP`
- AND at least one later requested date satisfies the selected strategy's minimum-history requirement
- WHEN the analytical Backtest runs
- THEN the Backtest may complete successfully
- AND the eligible dates contain Strategy Results
- AND the warm-up dates remain distinguishable from eligible dates

### Requirement: Invalid Backtest data fails instead of being silently skipped

The system SHALL fail an analytical Backtest when required historical data is invalid rather than silently omitting invalid observations and continuing with potentially biased results.

#### Scenario: Invalid bar exists within required Backtest data

- GIVEN the historical data required by the Backtest contains an invalid observation
- WHEN validation runs
- THEN the Backtest reports `DATA_FAILED`
- AND the invalid observation is not silently skipped

### Requirement: Strategy failure during Backtest is fail-fast

The system SHALL fail the analytical Backtest if strategy evaluation fails at any eligible historical evaluation point and SHALL NOT present a partial timeline as a successful Backtest.

#### Scenario: Strategy evaluation fails at an eligible date

- GIVEN configuration and required market data are valid
- AND strategy evaluation succeeds for earlier eligible dates
- AND strategy evaluation fails at historical date T
- WHEN the analytical Backtest reaches T
- THEN the Backtest reports `STRATEGY_FAILED`
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

The system SHALL identify enough metadata in a successful analytical Backtest output to reproduce the evaluated strategy configuration and historical range.

#### Scenario: Successful analytical Backtest artifact is generated

- GIVEN an analytical Backtest completes successfully
- WHEN its public artifact is produced
- THEN the artifact identifies the instrument
- AND it identifies the strategy
- AND it identifies the parameter set
- AND it identifies the Git revision
- AND it identifies the requested start and end dates
- AND it includes validation status
- AND it contains the analytical Strategy Result timeline for eligible evaluation dates

### Requirement: Failed analytical Backtest output uses a common failure contract

The system SHALL represent configuration, data, or strategy failures explicitly in failed analytical Backtest artifacts and SHALL NOT present partial results as a successful Backtest.

#### Scenario: Analytical Backtest fails

- GIVEN an analytical Backtest fails during configuration resolution, formal data loading or validation, or strategy evaluation
- WHEN the Backtest artifact is produced
- THEN the artifact identifies the applicable top-level failure status as `CONFIGURATION_FAILED`, `DATA_FAILED`, or `STRATEGY_FAILED`
- AND it contains a machine-readable failure code
- AND it contains a human-readable failure reason
- AND it does not present a partial analytical timeline as a successful Backtest

### Requirement: Public analytical Backtest artifact includes the fixed disclaimer

The system SHALL include exactly `僅為個人研究與策略驗證，不構成任何形式之投資建議。` in every public analytical Backtest artifact.

#### Scenario: Successful public analytical Backtest artifact

- GIVEN an analytical Backtest completes successfully
- WHEN the public artifact is generated
- THEN the artifact contains exactly `僅為個人研究與策略驗證，不構成任何形式之投資建議。`

#### Scenario: Failed public analytical Backtest artifact

- GIVEN an analytical Backtest fails during configuration, data validation, or strategy evaluation
- WHEN the public artifact is generated
- THEN the artifact still contains exactly `僅為個人研究與策略驗證，不構成任何形式之投資建議。`
