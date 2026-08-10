## Purpose

Define the observable behavior of formal Decision evaluation for a configured instrument using completed historical data and the instrument's active strategy assignment.

## ADDED Requirements

### Requirement: Decision uses the active strategy assignment

The system SHALL evaluate a formal Decision using the active strategy and parameter set configured for the requested instrument.

#### Scenario: Instrument has a valid active assignment

- GIVEN an instrument with an active strategy and parameter set
- AND the assignment resolves successfully
- WHEN a Decision evaluation is requested
- THEN the Decision uses that active strategy and parameter set

### Requirement: Decision does not accept research strategy overrides

The system SHALL NOT allow a formal Decision request to override the instrument's active strategy or parameter set.

#### Scenario: Strategy override is supplied to Decision

- GIVEN an instrument with a configured active assignment
- WHEN a Decision request attempts to provide a different strategy or parameter set
- THEN the request is rejected as invalid for formal Decision evaluation
- AND the configured active assignment remains unchanged

### Requirement: Missing Decision configuration fails before data evaluation

The system SHALL reject a Decision when the requested instrument or its active assignment cannot be resolved.

#### Scenario: Instrument is not configured

- GIVEN a Decision request for an unknown instrument
- WHEN configuration resolution runs
- THEN the Decision fails with `CONFIGURATION_FAILED`
- AND the failure code is `INSTRUMENT_NOT_FOUND`
- AND market-data loading and strategy evaluation do not run

#### Scenario: Instrument has no active assignment

- GIVEN a configured instrument with no active strategy assignment
- WHEN a Decision evaluation is requested
- THEN the Decision fails with `CONFIGURATION_FAILED`
- AND the failure code is `ACTIVE_STRATEGY_NOT_CONFIGURED`
- AND strategy evaluation does not run

### Requirement: Decision resolves the evaluation date to a completed trading day

The system SHALL evaluate a Decision against a completed trading day and SHALL preserve the distinction between a requested date and the resolved evaluation date when they differ.

#### Scenario: No as-of date is supplied

- GIVEN valid market data and trading-calendar information
- WHEN a Decision request omits `as_of`
- THEN the system resolves `as_of` to the latest eligible completed trading day

#### Scenario: Requested date is not a trading day

- GIVEN a requested `as_of` date that is not a trading day
- WHEN the Decision date is resolved
- THEN the system selects the most recent eligible completed trading day according to the trading calendar
- AND the Decision output preserves both the requested date and resolved `as_of` date

### Requirement: Decision uses only information available by resolved as-of

The system SHALL prevent observations or intraday information unavailable by the resolved `as_of` point from affecting the formal Decision result.

#### Scenario: Source data contains later observations

- GIVEN market data that extends beyond resolved `as_of=T`
- WHEN the Decision is evaluated
- THEN the strategy result is based only on eligible information available on or before T

#### Scenario: Intraday snapshot is available

- GIVEN completed daily history through the resolved `as_of` date
- AND a separate incomplete intraday snapshot
- WHEN the formal Decision is evaluated
- THEN the intraday snapshot does not alter the formal historical strategy evaluation

### Requirement: Successful Decision returns an analytical strategy plan

The system SHALL return the selected strategy's analytical result for a successful Decision without representing entry or exit plan elements as completed trades.

#### Scenario: Strategy identifies an entry opportunity

- GIVEN valid configuration and market data
- AND the selected strategy produces an entry plan
- WHEN the Decision completes successfully
- THEN the Decision output contains the analytical strategy result and entry plan
- AND it does not claim that the entry was filled or that a real position exists

### Requirement: Neutral Decision requires valid data

The system SHALL report `NEUTRAL` only when configuration and required market data are valid and the strategy itself identifies no actionable swing-stage opportunity.

#### Scenario: Strategy returns neutral state

- GIVEN valid configuration
- AND valid eligible market data
- AND the strategy evaluates the market state as `NEUTRAL`
- WHEN the Decision completes
- THEN the Decision is successful
- AND the market state is `NEUTRAL`

#### Scenario: Market data is invalid

- GIVEN invalid or ineligible market data
- WHEN a Decision is attempted
- THEN the Decision reports the corresponding failure
- AND it does not report `NEUTRAL` as the market state

### Requirement: Decision output is reproducible and traceable

The system SHALL identify enough evaluation metadata in a successful Decision output to trace the strategy configuration and code revision used for the result.

#### Scenario: Successful Decision artifact is generated

- GIVEN a Decision completes successfully
- WHEN its public artifact is produced
- THEN the artifact identifies the instrument
- AND it identifies the resolved `as_of` date
- AND it identifies the strategy
- AND it identifies the parameter set
- AND it identifies the Git revision used for evaluation
- AND it includes the analytical Strategy Result
- AND it includes data-quality status

### Requirement: Failed Decision output does not contain a valid trading decision

The system SHALL represent configuration, data, or strategy failures explicitly and SHALL NOT serialize a failure as a valid analytical Decision.

#### Scenario: Strategy evaluation fails

- GIVEN configuration and data validation succeed
- AND the strategy evaluation fails
- WHEN the Decision artifact is produced
- THEN the artifact reports `STRATEGY_FAILED`
- AND it contains a machine-readable failure code and human-readable reason
- AND it does not present a valid market state or trading plan as if evaluation succeeded

### Requirement: Public Decision artifact includes the fixed disclaimer

The system SHALL include exactly `僅為個人研究與策略驗證，不構成任何形式之投資建議。` in every public Decision artifact.

#### Scenario: Successful public Decision artifact

- GIVEN a Decision completes successfully
- WHEN the public Decision artifact is generated
- THEN the artifact contains exactly `僅為個人研究與策略驗證，不構成任何形式之投資建議。`

#### Scenario: Failed public Decision artifact

- GIVEN a Decision fails during configuration, data validation, or strategy evaluation
- WHEN the public Decision artifact is generated
- THEN the artifact still contains exactly `僅為個人研究與策略驗證，不構成任何形式之投資建議。`
