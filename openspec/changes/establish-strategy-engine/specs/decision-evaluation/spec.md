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
- THEN the Decision fails
- AND the failure category is `CONFIGURATION_FAILED`
- AND the failure code is `INSTRUMENT_NOT_FOUND`
- AND market-data loading and strategy evaluation do not run

#### Scenario: Instrument has no active assignment

- GIVEN a configured instrument with no active strategy assignment
- WHEN a Decision evaluation is requested
- THEN the Decision fails
- AND the failure category is `CONFIGURATION_FAILED`
- AND the failure code is `ACTIVE_STRATEGY_NOT_CONFIGURED`
- AND market-data loading and strategy evaluation do not run

### Requirement: Decision resolves the formal evaluation date to a completed trading day

The system SHALL evaluate the formal Strategy Result against a completed trading day and SHALL preserve the distinction between a requested date and the resolved evaluation date when they differ.

#### Scenario: No as-of date is supplied when no session is in progress

- GIVEN valid market data and trading-calendar information
- AND there is no incomplete current trading session
- WHEN a Decision request omits `as_of`
- THEN the system resolves `as_of` to the latest eligible completed trading day

#### Scenario: No as-of date is supplied during an incomplete trading session

- GIVEN trading day T is currently in progress
- AND valid completed daily history is available through T-1
- WHEN a Decision request omits `as_of`
- THEN the formal `resolved_as_of` is T-1
- AND an optional intraday overlay for session T may be included when valid snapshot data is available

#### Scenario: Requested date is not a trading day

- GIVEN a requested `as_of` date that is not a trading day
- AND the requested date is not in the future
- WHEN the Decision date is resolved
- THEN the system selects the most recent eligible completed trading day according to the trading calendar
- AND the Decision output preserves both the requested date and resolved `as_of` date

#### Scenario: Requested date is the current trading day before completion

- GIVEN the requested `as_of` date is the current trading day
- AND the current trading session is not yet complete
- WHEN the Decision date is resolved
- THEN the formal `resolved_as_of` is the most recent eligible completed trading day
- AND the incomplete current-session bar is not used as formal daily history

#### Scenario: Requested date is the current trading day after completion

- GIVEN the requested `as_of` date is the current trading day
- AND the current trading session is complete
- AND the completed daily observation for that trading day is available and eligible
- WHEN the Decision date is resolved
- THEN the formal `resolved_as_of` is the current trading day

### Requirement: Future Decision as-of dates are rejected

The system SHALL reject a Decision request whose requested `as_of` is later than the current applicable date/time boundary rather than silently clamping it to an available trading day.

#### Scenario: Requested as-of is in the future

- GIVEN a Decision request specifies a future `as_of` date
- WHEN request validation runs
- THEN the Decision fails
- AND the failure category is `CONFIGURATION_FAILED`
- AND the failure code is `INVALID_AS_OF`
- AND market-data loading and strategy evaluation do not run

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

### Requirement: Decision may include an observational intraday overlay

The system SHALL allow a Decision produced during an incomplete current trading session to include a separate intraday overlay containing current-session observations without changing the formal Strategy Result.

#### Scenario: Current-session open and latest price are available

- GIVEN the formal Strategy Result is evaluated through completed trading day T-1
- AND trading day T is currently in progress
- AND current-session open, latest price, and snapshot time are available
- WHEN the Decision output is produced
- THEN the formal `resolved_as_of` remains T-1
- AND the output may include a separate intraday overlay for session T
- AND the overlay identifies the session date, open, latest price, and snapshot time
- AND the overlay does not modify the formal market state, entry plan, exit plan, indicators, or model state

#### Scenario: Intraday snapshot is unavailable

- GIVEN the formal Strategy Result can be evaluated successfully from completed historical data
- AND the optional intraday snapshot is unavailable or invalid
- WHEN the Decision output is produced
- THEN the Decision may still complete successfully
- AND the formal Strategy Result remains valid
- AND the intraday overlay is omitted or reported as unavailable

### Requirement: Intraday overlay describes current relationship to the formal plan

The system SHALL allow the intraday overlay to describe the current open or latest price relative to analytical entry or exit plan levels without representing execution, historical intraday touch events, or an undefined proximity threshold.

#### Scenario: Latest price is below an entry level

- GIVEN the formal entry plan contains a price level
- AND the current latest price is at or below that level
- WHEN the intraday overlay is generated
- THEN the overlay may indicate that the current price is at or below the analytical entry level
- AND it does not claim that an order was filled

#### Scenario: Only current snapshot values are available

- GIVEN only the current-session open and latest price are available
- AND no intraday high, low, bar history, or tick history is available
- WHEN the intraday overlay is generated
- THEN the output does not claim that an analytical level was touched earlier in the session

#### Scenario: No proximity tolerance is defined

- GIVEN an analytical plan contains a price level
- AND no explicit proximity tolerance rule is defined
- WHEN the intraday overlay compares the current price with that level
- THEN the framework does not classify the relationship as `NEAR`
- AND only deterministic relationships supported by the known values may be reported

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

The system SHALL identify enough evaluation metadata in a successful Decision output to trace the strategy configuration and code revision used for the formal result.

#### Scenario: Successful Decision artifact is generated

- GIVEN a Decision completes successfully
- WHEN its public artifact is produced
- THEN the artifact status is `SUCCESS`
- AND it identifies the instrument
- AND it identifies the resolved `as_of` date
- AND it identifies the strategy
- AND it identifies the parameter set
- AND it identifies the Git revision used for evaluation
- AND it includes the analytical Strategy Result
- AND it includes data-quality status

#### Scenario: Explicit requested as-of is present in a successful artifact

- GIVEN a Decision request explicitly supplies `as_of`
- AND the Decision completes successfully
- WHEN its public artifact is produced
- THEN the artifact identifies the requested `as_of`
- AND it identifies the resolved `as_of`

### Requirement: Failed Decision output uses a common failure contract

The system SHALL represent configuration, data, or strategy failures explicitly and SHALL NOT serialize a failure as a valid analytical Decision.

#### Scenario: Decision fails

- GIVEN a Decision fails during configuration resolution, formal data loading or validation, or strategy evaluation
- WHEN the Decision artifact is produced
- THEN the artifact status is `FAILED`
- AND `failure.category` is `CONFIGURATION_FAILED`, `DATA_FAILED`, or `STRATEGY_FAILED` as applicable
- AND `failure.code` contains a machine-readable failure code
- AND `failure.reason` contains a human-readable failure reason
- AND it does not present a valid market state or trading plan as if evaluation succeeded

#### Scenario: Decision fails before strategy identity is resolved

- GIVEN a Decision fails before a strategy or parameter set can be resolved
- WHEN the failed artifact is produced
- THEN unresolved strategy or parameter-set metadata is not fabricated

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
