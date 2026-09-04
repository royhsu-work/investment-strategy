# decision-evaluation Specification

## Purpose
Define formal Decision evaluation semantics, including active assignment resolution, trading-calendar as-of behavior, no-look-ahead data boundaries, optional current-session observation, reproducible artifacts, and explicit failure reporting.
## Requirements
### Requirement: Decision uses the active strategy assignment

The system SHALL evaluate a formal Decision using the active strategy and parameter set configured for the requested instrument.

#### Scenario: Instrument has a valid active assignment

- GIVEN an instrument with an active strategy and parameter set
- AND the assignment resolves successfully
- WHEN a Decision evaluation is requested
- THEN the Decision uses that active strategy and parameter set

### Requirement: Decision does not accept research strategy overrides

The Decision request boundary SHALL accept only the formal Decision request contract and SHALL reject attempts to supply a research strategy or parameter-set override before Decision application evaluation begins.

#### Scenario: Strategy override is supplied to Decision

- GIVEN an instrument with a configured active assignment
- WHEN a Decision request attempts to provide a different strategy or parameter set
- THEN the request is rejected by the Decision request boundary
- AND Decision application evaluation does not begin
- AND no public Decision artifact is produced for the rejected request
- AND the configured active assignment remains unchanged

### Requirement: Missing Decision configuration fails before data evaluation

The system SHALL reject a Decision when the requested instrument or its active assignment cannot be resolved after a request has passed the Decision request boundary.

#### Scenario: Instrument is not configured

- GIVEN an accepted Decision request for an unknown instrument
- WHEN configuration resolution runs
- THEN the Decision fails
- AND the failure category is `CONFIGURATION_FAILED`
- AND the failure code is `INSTRUMENT_NOT_FOUND`
- AND market-data loading and strategy evaluation do not run

#### Scenario: Instrument has no active assignment

- GIVEN an accepted Decision request for a configured instrument with no active strategy assignment
- WHEN a Decision evaluation is requested
- THEN the Decision fails
- AND the failure category is `CONFIGURATION_FAILED`
- AND the failure code is `ACTIVE_STRATEGY_NOT_CONFIGURED`
- AND market-data loading and strategy evaluation do not run

### Requirement: Decision resolves the formal evaluation date from the trading calendar only

The system SHALL resolve the formal Decision `as_of` to a completed trading day using the applicable TradingCalendar before market-data availability, freshness, or structural eligibility is considered. Missing or invalid market data SHALL NOT cause date resolution to fall back to an older trading day.

#### Scenario: No as-of date is supplied when no session is in progress

- GIVEN trading-calendar information
- AND there is no incomplete current trading session
- WHEN a Decision request omits `as_of`
- THEN the system resolves `as_of` to the latest completed trading day according to the TradingCalendar

#### Scenario: No as-of date is supplied during an incomplete trading session

- GIVEN trading day T is currently in progress
- WHEN a Decision request omits `as_of`
- THEN the formal `resolved_as_of` is the previous completed trading day according to the TradingCalendar
- AND an optional intraday overlay for session T may be included when valid snapshot data is available

#### Scenario: Requested date is not a trading day

- GIVEN a requested `as_of` date that is not a trading day
- AND the requested date is not in the future
- WHEN the Decision date is resolved
- THEN the system selects the previous completed trading day according to the TradingCalendar
- AND the Decision output preserves both the requested date and resolved `as_of` date when the Decision succeeds

#### Scenario: Requested date is the current trading day before completion

- GIVEN the requested `as_of` date is the current trading day
- AND the current trading session is not yet complete
- WHEN the Decision date is resolved
- THEN the formal `resolved_as_of` is the previous completed trading day according to the TradingCalendar
- AND the incomplete current-session bar is not used as formal daily history

#### Scenario: Requested date is the current trading day after completion

- GIVEN the requested `as_of` date is the current trading day
- AND the current trading session is complete
- WHEN the Decision date is resolved
- THEN the formal `resolved_as_of` is the current trading day

#### Scenario: Latest completed trading day has missing data

- GIVEN the TradingCalendar resolves T as the latest completed trading day
- AND required formal market data for T is missing or stale
- WHEN Decision data loading and validation run
- THEN `resolved_as_of` remains T
- AND the Decision reports the applicable data failure
- AND the system does not silently resolve to T-1 to avoid the data failure

### Requirement: Future Decision as-of dates are rejected

The system SHALL reject a Decision request whose requested `as_of` is later than the current applicable date/time boundary rather than silently clamping it to an available trading day.

#### Scenario: Requested as-of is in the future

- GIVEN an accepted Decision request specifies a future `as_of` date
- WHEN application request validation runs
- THEN the Decision fails
- AND the failure category is `CONFIGURATION_FAILED`
- AND the failure code is `INVALID_AS_OF`
- AND market-data loading and strategy evaluation do not run

### Requirement: Decision uses only information available by resolved as-of

The system SHALL prevent observations or intraday information unavailable by the resolved `as_of` point from affecting formal Decision data validation or the formal Strategy Result. Candidate observations whose timestamps can be normalized and are later than `resolved_as_of` SHALL be excluded before their non-temporal OHLCV structure can affect the historical Decision. A candidate observation whose timestamp cannot be normalized MAY fail with the defined timestamp validation failure because its temporal position cannot be established.

#### Scenario: Source data contains later valid observations

- GIVEN market data that extends beyond resolved `as_of=T`
- WHEN the Decision is evaluated
- THEN the formal Decision uses only eligible information available on or before T
- AND observations after T do not affect the formal Strategy Result

#### Scenario: Future observation has invalid OHLC

- GIVEN all candidate observations on or before resolved `as_of=T` are valid and eligible
- AND a candidate observation has a valid normalized timestamp after T
- AND that future observation contains structurally invalid OHLC values
- WHEN the historical Decision data is prepared and evaluated
- THEN the future observation is excluded before its OHLC structure can fail the historical Decision
- AND the Decision outcome is equivalent to evaluating the same source truncated at T

#### Scenario: Candidate timestamp cannot be normalized

- GIVEN the provider returns a candidate historical observation whose timestamp cannot be normalized
- WHEN the Decision data is prepared
- THEN the system cannot establish whether that candidate belongs on or before or after `resolved_as_of`
- AND the Decision may fail with `DATA_FAILED / VALIDATION_ERROR`

#### Scenario: Intraday snapshot is available

- GIVEN completed daily history through the resolved `as_of` date
- AND a separate incomplete intraday snapshot
- WHEN the formal Decision is evaluated
- THEN the intraday snapshot does not alter the formal historical strategy evaluation

### Requirement: Decision may include an observational intraday overlay only for the current formal Decision

The system SHALL allow a Decision produced during an incomplete current trading session to include a separate current-session intraday overlay only when the formal Decision represents the current analytical view derived from the latest completed trading day. A historical Decision requested for an earlier `as_of` SHALL NOT include the current-session overlay.

#### Scenario: Current-session open and latest price are available for the current formal Decision

- GIVEN trading day T is currently in progress
- AND the Decision request omits `as_of` or explicitly requests the current trading date
- AND the formal Strategy Result is evaluated through completed trading day T-1
- AND current-session open, latest price, and snapshot time are available
- WHEN the Decision output is produced
- THEN the formal `resolved_as_of` remains T-1
- AND the output may include a separate intraday overlay for session T
- AND the overlay identifies the session date, open, latest price, and snapshot time
- AND the overlay does not modify the formal market state, entry plan, exit plan, indicators, or model state

#### Scenario: Historical as-of is requested during the current session

- GIVEN trading day T is currently in progress
- AND the caller explicitly requests historical `as_of=H` where H is earlier than the current formal Decision date
- AND a valid current-session snapshot for T is available
- WHEN the historical Decision output is produced
- THEN the formal Strategy Result is evaluated only for H
- AND the current-session intraday overlay is not included

#### Scenario: Intraday snapshot is unavailable for the current formal Decision

- GIVEN the current formal Strategy Result can be evaluated successfully from completed historical data
- AND the optional current-session snapshot is unavailable or invalid
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

### Requirement: Failed Decision output uses a minimal common failure contract

The system SHALL represent application configuration, data, or strategy failures explicitly and SHALL NOT serialize a failure as a valid analytical Decision.

#### Scenario: Accepted Decision fails

- GIVEN an accepted Decision request fails during application request validation, configuration resolution, formal data loading or validation, or strategy evaluation
- WHEN the Decision artifact is produced
- THEN the artifact status is `FAILED`
- AND it identifies the requested instrument
- AND it identifies the Git revision used by the application
- AND `failure.category` is `CONFIGURATION_FAILED`, `DATA_FAILED`, or `STRATEGY_FAILED` as applicable
- AND `failure.code` contains a machine-readable failure code
- AND `failure.reason` contains a human-readable failure reason
- AND it does not present a valid market state or trading plan as if evaluation succeeded

#### Scenario: Explicit requested as-of is preserved in a failed artifact

- GIVEN an accepted Decision request explicitly supplies `as_of`
- AND application evaluation later fails
- WHEN the failed public artifact is produced
- THEN the artifact identifies the originally requested `as_of`

#### Scenario: Failure occurs after some internal metadata was resolved

- GIVEN an accepted Decision request later fails
- AND internal processing may already know a resolved `as_of`, strategy, parameter set, or data-quality detail
- WHEN the failed public artifact is produced
- THEN those internally known fields are not required by the public failure contract
- AND unresolved strategy or parameter-set metadata is not fabricated

### Requirement: Public Decision artifact includes the fixed disclaimer

The system SHALL include exactly `僅為個人研究與策略驗證，不構成任何形式之投資建議。` in every public Decision artifact produced by the Decision application.

#### Scenario: Successful public Decision artifact

- GIVEN a Decision completes successfully
- WHEN the public Decision artifact is generated
- THEN the artifact contains exactly `僅為個人研究與策略驗證，不構成任何形式之投資建議。`

#### Scenario: Failed public Decision artifact

- GIVEN an accepted Decision request fails during application validation, configuration, data validation, or strategy evaluation
- WHEN the public Decision artifact is generated
- THEN the artifact still contains exactly `僅為個人研究與策略驗證，不構成任何形式之投資建議。`

