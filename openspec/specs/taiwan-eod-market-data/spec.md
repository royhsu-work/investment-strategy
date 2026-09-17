# taiwan-eod-market-data Specification

## Purpose

Define provider-neutral acquisition and Taiwan exchange-session semantics for completed daily market facts consumed by formal Decision and analytical Backtest evaluation.

## Requirements
### Requirement: Taiwan EOD acquisition uses canonical instrument identity

The system SHALL acquire Taiwan EOD market data using the repository's configured instrument identity and listing venue without exposing provider-specific ticker syntax as part of the Strategy, Decision, or Backtest contract.

#### Scenario: Taiwan-listed instrument requires provider-specific symbol mapping

- GIVEN a configured Taiwan instrument with a canonical symbol and listing venue
- AND the selected market-data provider requires a provider-specific identifier
- WHEN completed daily history is acquired
- THEN provider-specific identifier resolution occurs behind the market-data provider boundary
- AND Strategy, Decision, and Backtest continue to identify the instrument by its canonical repository symbol

### Requirement: Taiwan EOD acquisition provides source-native daily OHLCV market facts

The system SHALL make completed Taiwan market sessions available as daily observations containing trading date and the selected provider's native `Open`, `High`, `Low`, `Close`, and `Volume` fields for the existing formal market-data preparation pipeline.

The provider adapter SHALL NOT substitute `Adj Close`, apply adapter-controlled dividend/capital-gain adjustment, enable automatic/back adjustment, repair observations, interpolate missing values, or synthesize fields to alter those source-native OHLCV observations.

This capability does not guarantee exchange-raw nominal historical price scale across splits or consolidations unless a future capability explicitly establishes that methodology.

#### Scenario: Completed Taiwan trading session is available

- GIVEN Taiwan trading day T has completed
- AND the market-data source provides the session's source-native daily OHLCV
- WHEN EOD history is acquired through T
- THEN the acquired candidate observation for T contains trading date, open, high, low, close, and volume
- AND the observation can be processed by the existing normalization and structural validation behavior

#### Scenario: Provider exposes adjusted analytical fields

- GIVEN the provider exposes native OHLCV and also exposes `Adj Close`, dividends, capital gains, split metadata, or another transformed analytical field
- WHEN formal EOD history is acquired
- THEN formal OHLCV is populated from the provider-native OHLCV fields
- AND those adjusted or action fields are not substituted into formal OHLCV
- AND the adapter does not apply an additional OHLC transformation

#### Scenario: Candidate EOD observation omits a required field

- GIVEN a provider returns a candidate Taiwan daily observation missing one or more required OHLCV fields
- WHEN the existing formal market-data preparation pipeline processes that observation
- THEN the existing structural market-data failure semantics apply
- AND the provider adapter does not fabricate the missing field solely to make the observation eligible

### Requirement: Incomplete current session is not formal EOD history

The system SHALL NOT treat an incomplete Taiwan trading session as a completed daily observation eligible for formal Strategy evaluation.

#### Scenario: Current Taiwan trading session is still in progress

- GIVEN Taiwan trading day T is currently in progress
- AND completed daily history exists through T-1
- WHEN a formal Decision resolves its evaluation date
- THEN T is not eligible as completed EOD history
- AND formal Strategy evaluation remains bounded to the latest completed trading day determined by the TradingCalendar

### Requirement: Taiwan market dates use the applicable market timezone

The system SHALL interpret Taiwan market dates and session completion using the Taiwan market timezone rather than the runner's local timezone or UTC calendar date alone.

#### Scenario: Runner timezone differs from Taiwan market timezone

- GIVEN the application clock returns a timezone-aware instant
- AND the runner's local timezone is not the Taiwan market timezone
- WHEN the applicable market date or current-session completion is determined
- THEN the result is based on the Taiwan market timezone
- AND changing the runner's local timezone does not change the resolved Taiwan market date for the same instant

### Requirement: Taiwan trading calendar represents actual exchange sessions

The system SHALL determine Taiwan trading days from exchange-session information that can represent scheduled holidays, additional trading sessions, and exceptional full-market closures rather than from a weekday-only rule.

#### Scenario: Weekday is an exchange holiday

- GIVEN a Monday-through-Friday calendar date that the applicable Taiwan market marks as closed
- WHEN trading-day eligibility is evaluated
- THEN the date is not treated as a trading day

#### Scenario: Additional session occurs outside the normal weekday pattern

- GIVEN a date that the applicable Taiwan market defines as an additional trading session
- WHEN trading-day eligibility is evaluated
- THEN the date is treated as a trading day even if a weekday-only heuristic would reject it

#### Scenario: Exceptional full-market closure occurs

- GIVEN a date that would otherwise be a trading day
- AND the applicable Taiwan market is exceptionally closed for the full session
- WHEN trading-day eligibility is evaluated
- THEN the date is not treated as a completed trading session

### Requirement: Calendar knowledge follows the configured engine's supported coverage

The system SHALL distinguish dates for which the configured Taiwan calendar engine can establish session status from dates outside or unavailable to that engine's supported coverage.

#### Scenario: Required date is supported by the configured calendar engine

- GIVEN an accepted Decision or Backtest evaluation requires Taiwan session knowledge for date T
- AND the configured calendar engine can establish session status for T
- WHEN calendar-dependent evaluation is performed
- THEN T is within supported calendar coverage
- AND no separate per-date official verification is required solely to use the engine's session answer

#### Scenario: Required date is outside or unavailable to the configured calendar engine

- GIVEN an accepted Decision or Backtest evaluation requires Taiwan session knowledge for date T
- AND the configured calendar engine cannot establish session status for T because T is outside its supported bounds or the engine cannot provide a session answer
- WHEN calendar-dependent evaluation is attempted
- THEN evaluation fails with `DATA_FAILED`
- AND the failure code is `CALENDAR_UNAVAILABLE`
- AND the system does not assume T is a trading day or non-trading day
- AND missing market data for T is not misclassified as `DATA_GAP` or `STALE_DATA`

### Requirement: Official verification is required for regression evidence and production overrides, not every supported engine date

The system SHALL use official TWSE/TPEx regular-market evidence for representative regression fixtures and for any repository-maintained production override, without requiring a duplicate officially enumerated calendar for every date supported by the configured engine.

#### Scenario: Calendar engine matches an officially verified regression date

- GIVEN a representative TWSE or TPEx regular-market date has official evidence for its expected session status
- AND the configured calendar engine returns the same status
- WHEN the regression test runs
- THEN the engine behavior is accepted for that fixture
- AND no production override entry is required

#### Scenario: Calendar engine has a verified discrepancy

- GIVEN official TWSE or TPEx regular-market evidence establishes the expected session status for date T
- AND the configured calendar engine returns a different status for T
- WHEN repository calendar corrections are applied
- THEN a sparse explicit override for T MAY be added
- AND that override takes precedence over the engine for T
- AND the override records the expected open/closed truth in deterministic repository test evidence

#### Scenario: No real discrepancy is identified during this change

- GIVEN the implementation verifies the required representative regression fixtures
- AND no real engine-versus-official discrepancy requiring correction is identified
- WHEN the Taiwan calendar adapter is completed
- THEN the override mechanism and precedence behavior are still testable with deterministic fixture data
- AND no production override entry is required solely to satisfy this change

### Requirement: Future calendar truth is not promised by this EOD capability

The system SHALL NOT claim automatic knowledge of future or newly announced exchange-calendar changes beyond the configured calendar engine and explicit repository corrections.

#### Scenario: Request is for a future evaluation date

- GIVEN an accepted application policy rejects future Decision or Backtest evaluation dates
- WHEN such a future request is submitted
- THEN existing request/application date-validation semantics apply
- AND the Taiwan calendar adapter is not required to guarantee future exchange-session truth for that request

### Requirement: Completed-session semantics drive latest EOD eligibility

The system SHALL use the Taiwan trading calendar's completed-session semantics to determine whether a market date may be treated as a completed trading session.

#### Scenario: Historical market date was not a trading session

- GIVEN historical date T is a holiday or exceptional full-market closure
- WHEN session completion is queried for T
- THEN T is not treated as a completed trading session

#### Scenario: Current trading date has not completed

- GIVEN current Taiwan market date T is a trading day
- AND its regular trading session has not completed
- WHEN the latest completed trading day is requested
- THEN the result is the previous completed Taiwan trading day

#### Scenario: Current trading date has completed

- GIVEN current Taiwan market date T is a trading day
- AND its regular trading session has completed
- WHEN the latest completed trading day is requested
- THEN T is eligible as the latest completed trading day

### Requirement: Provider acquisition details remain outside formal analytical contracts

The system SHALL keep provider SDK types, provider response schemas, provider-specific identifier formats, and provider-specific exception types outside the public and shared Strategy, Decision, and Backtest contracts.

#### Scenario: Underlying market-data provider implementation changes

- GIVEN two provider implementations can supply equivalent Taiwan EOD market facts for the same canonical instrument and dates
- WHEN the configured provider implementation is replaced
- THEN Strategy, Decision, and Backtest request contracts do not require provider-specific changes
- AND equivalent normalized market data remains eligible for equivalent analytical evaluation

### Requirement: Acquisition failure preserves existing market-data failure semantics

The system SHALL surface an unavailable Taiwan EOD source or absence of candidate historical observations through the existing formal market-data failure behavior rather than manufacturing stale observations or a valid Strategy result.

#### Scenario: Taiwan EOD source cannot provide required history

- GIVEN configuration resolution succeeds
- AND required Taiwan EOD history cannot be acquired
- WHEN formal market-data acquisition runs
- THEN evaluation fails according to the existing `DATA_FAILED / DATA_UNAVAILABLE` behavior
- AND Strategy evaluation does not run

#### Scenario: Latest completed session is absent from acquired history

- GIVEN the Taiwan trading calendar reliably resolves T as the latest required completed trading day
- AND the acquired historical dataset ends before T
- WHEN existing freshness validation runs
- THEN the existing `DATA_FAILED / STALE_DATA` behavior applies
- AND the system does not silently move the formal evaluation date backward to match the provider data

