## Purpose

Define provider-neutral acquisition and Taiwan exchange-session semantics for completed daily market facts consumed by formal Decision and analytical Backtest evaluation.

## ADDED Requirements

### Requirement: Taiwan EOD acquisition uses canonical instrument identity

The system SHALL acquire Taiwan EOD market data using the repository's configured instrument identity and listing venue without exposing provider-specific ticker syntax as part of the Strategy, Decision, or Backtest contract.

#### Scenario: Taiwan-listed instrument requires provider-specific symbol mapping

- GIVEN a configured Taiwan instrument with a canonical symbol and listing venue
- AND the selected market-data provider requires a provider-specific identifier
- WHEN completed daily history is acquired
- THEN provider-specific identifier resolution occurs behind the market-data provider boundary
- AND Strategy, Decision, and Backtest continue to identify the instrument by its canonical repository symbol

### Requirement: Taiwan EOD acquisition provides daily OHLCV market facts

The system SHALL make completed Taiwan market sessions available as daily observations containing trading date, open, high, low, close, and volume for the existing formal market-data preparation pipeline.

#### Scenario: Completed Taiwan trading session is available

- GIVEN Taiwan trading day T has completed
- AND the market-data source provides the session's reported daily trading data
- WHEN EOD history is acquired through T
- THEN the acquired candidate observation for T contains trading date, open, high, low, close, and volume
- AND the observation can be processed by the existing normalization and structural validation behavior

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

### Requirement: Calendar knowledge has an explicit supported boundary

The system SHALL distinguish a known exchange-session answer from a date whose session status cannot be established reliably by the configured calendar implementation.

#### Scenario: Requested date is outside supported calendar coverage

- GIVEN an accepted Decision or Backtest evaluation requires Taiwan session knowledge for date T
- AND the configured Taiwan calendar implementation cannot establish session status for T within its supported coverage
- WHEN calendar-dependent evaluation is attempted
- THEN evaluation fails with `DATA_FAILED`
- AND the failure code is `CALENDAR_UNAVAILABLE`
- AND the system does not assume T is a trading day or non-trading day
- AND missing market data for T is not misclassified as `DATA_GAP` or `STALE_DATA`

#### Scenario: Calendar engine has a known incorrect session that is covered by an explicit override

- GIVEN the underlying calendar engine disagrees with an officially verified Taiwan regular-market session fact
- AND the repository contains an explicit override for that known discrepancy
- WHEN session status is evaluated
- THEN the explicit verified override takes precedence for that date

### Requirement: Completed-session semantics drive latest EOD eligibility

The system SHALL use the Taiwan trading calendar's completed-session semantics to determine whether the current market date may be used as formal EOD history.

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
