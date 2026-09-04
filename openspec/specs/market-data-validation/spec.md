# market-data-validation Specification

## Purpose
Define the formal market-data eligibility, normalization, validation, continuity, freshness, and no-look-ahead rules that protect Decision and analytical Backtest evaluation from incomplete, unavailable, invalid, or temporally ineligible observations.
## Requirements
### Requirement: Completed daily OHLCV is the formal historical input

The system SHALL use completed daily OHLCV observations as the formal historical input for strategy evaluation, and every normalized formal daily observation SHALL contain open, high, low, close, and volume.

#### Scenario: Incomplete current-session data is also available

- GIVEN completed daily OHLCV history through trading day T-1
- AND an incomplete intraday snapshot for trading day T
- WHEN formal strategy history is prepared
- THEN the historical daily dataset contains only completed daily observations
- AND each formal daily observation contains open, high, low, close, and volume
- AND the intraday snapshot is not inserted into the formal historical series

#### Scenario: Volume is missing from a formal daily observation

- GIVEN a provider returns a candidate completed daily observation with open, high, low, and close but no volume
- WHEN the observation is normalized and validated for formal history
- THEN validation fails with `DATA_FAILED`
- AND the failure code is `MISSING_REQUIRED_FIELD`
- AND the missing volume is not interpreted as zero or as a negative strategy signal

### Requirement: Intraday snapshots remain observational

The system SHALL keep incomplete current-session snapshot data separate from formal historical data and SHALL NOT use such snapshot values to recalculate formal indicators, model state, or common market state.

#### Scenario: Current session open and latest price are available

- GIVEN formal historical data through completed trading day T-1
- AND current-session open, latest price, and snapshot time for trading day T
- WHEN the data is prepared for Decision output
- THEN those current-session values remain separate from formal historical OHLCV
- AND they do not alter the Strategy Result evaluated as of T-1

### Requirement: Optional intraday snapshot failure does not invalidate formal data

The system SHALL treat unavailable or invalid optional intraday snapshot data separately from the completed historical data required for formal Decision evaluation.

#### Scenario: Formal data is valid but intraday snapshot is unavailable

- GIVEN completed historical data is valid and eligible for formal Decision evaluation
- AND the optional current-session snapshot cannot be obtained
- WHEN Decision data is prepared
- THEN the formal historical data remains eligible
- AND the formal Decision is not failed solely because the optional intraday snapshot is unavailable
- AND the intraday overlay may be omitted or reported as unavailable

#### Scenario: Optional intraday snapshot is structurally invalid

- GIVEN completed historical data is valid and eligible for formal Decision evaluation
- AND the optional intraday snapshot contains a non-positive open or latest price, an invalid snapshot time, or a session date inconsistent with the current session
- WHEN the snapshot is validated
- THEN the invalid snapshot does not alter or invalidate the formal historical Strategy Result
- AND the intraday overlay may be omitted or reported as unavailable

### Requirement: Historical observations are bounded by resolved as-of

The system SHALL provide strategy evaluation only with completed observations whose information is available on or before the resolved `as_of` date.

#### Scenario: Dataset extends beyond historical as-of

- GIVEN completed observations from T-20 through T+5
- WHEN evaluation is requested with resolved `as_of=T`
- THEN observations after T are excluded from the strategy input

### Requirement: Formal market data must be available

The system SHALL report `DATA_FAILED` with failure code `DATA_UNAVAILABLE` when required formal market data cannot be acquired or when the provider returns no candidate historical observations for the required request.

#### Scenario: Required historical data cannot be obtained

- GIVEN configuration resolution succeeds
- AND required formal historical market data cannot be obtained
- WHEN formal market-data acquisition completes
- THEN evaluation fails with `DATA_FAILED`
- AND the failure code is `DATA_UNAVAILABLE`
- AND strategy evaluation does not run

#### Scenario: Provider returns no candidate historical observations

- GIVEN configuration resolution succeeds
- AND the provider successfully responds but returns no candidate historical observations for the required request
- WHEN formal market-data acquisition completes
- THEN evaluation fails with `DATA_FAILED`
- AND the failure code is `DATA_UNAVAILABLE`
- AND strategy evaluation does not run

### Requirement: Acquired invalid observations retain structural failure semantics

The system SHALL NOT convert acquired-but-invalid market observations into `DATA_UNAVAILABLE`; once candidate observations are acquired, normalization and structural validation failures SHALL use their applicable structural failure code.

#### Scenario: Only acquired observation has an invalid timestamp

- GIVEN the provider returns one candidate historical observation
- AND its timestamp cannot be normalized into a valid trading timestamp
- WHEN normalization and structural validation run
- THEN validation fails with `DATA_FAILED`
- AND the failure code is `VALIDATION_ERROR`
- AND the failure is not rewritten as `DATA_UNAVAILABLE` merely because zero observations remain usable

### Requirement: OHLC structural relationships are valid

The system SHALL reject observations whose OHLC values violate valid bar relationships or contain non-positive prices.

#### Scenario: High is below close

- GIVEN an observation whose high price is lower than its close price
- WHEN structural validation runs
- THEN validation fails with `DATA_FAILED`
- AND the failure code is `INVALID_OHLC`

#### Scenario: Price is non-positive

- GIVEN an observation with an open, high, low, or close price less than or equal to zero
- WHEN structural validation runs
- THEN validation fails with `DATA_FAILED`
- AND the failure code is `INVALID_OHLC`

### Requirement: Volume is non-negative

The system SHALL reject a formal daily observation whose mandatory volume value is negative.

#### Scenario: Negative volume

- GIVEN a formal daily observation with negative volume
- WHEN structural validation runs
- THEN validation fails with `DATA_FAILED`
- AND the failure code is `VALIDATION_ERROR`

### Requirement: Normalized historical timestamps are valid, unique, and strictly chronological

The system SHALL validate the normalized historical series such that timestamps are valid, unique, and strictly chronological. Provider-specific input ordering MAY be normalized before this validation.

#### Scenario: Provider returns reverse chronological data

- GIVEN otherwise valid provider data ordered newest to oldest
- WHEN normalization prepares the historical series
- THEN the series may be reordered into strict chronological order
- AND reverse provider ordering alone is not treated as a data-integrity failure

#### Scenario: Duplicate trading date remains after normalization

- GIVEN two historical observations with the same normalized trading timestamp
- WHEN structural validation runs
- THEN validation fails with `DATA_FAILED`
- AND the failure code is `DUPLICATE_TIMESTAMP`

#### Scenario: Invalid timestamp cannot be normalized

- GIVEN a historical observation whose timestamp cannot be normalized into a valid trading timestamp
- WHEN structural validation runs
- THEN validation fails with `DATA_FAILED`
- AND the failure code is `VALIDATION_ERROR`

### Requirement: Trading-calendar continuity is used for gap detection

The system SHALL assess historical continuity using the applicable trading calendar rather than calendar-day continuity.

#### Scenario: Weekend between observations

- GIVEN valid completed observations for Friday and the following Monday
- AND neither Saturday nor Sunday is a trading day
- WHEN continuity validation runs
- THEN the weekend is not reported as a data gap

#### Scenario: Expected trading day is absent

- GIVEN valid observations surrounding a date that the trading calendar marks as an expected trading day
- AND the expected trading-day observation is absent
- WHEN continuity validation runs
- THEN validation fails with `DATA_FAILED`
- AND the failure code is `DATA_GAP`

### Requirement: Freshness is trading-calendar aware

The system SHALL determine whether formal historical data is stale relative to the resolved evaluation date using the applicable trading calendar.

#### Scenario: Latest required completed trading day is missing

- GIVEN the resolved evaluation date requires a more recent completed trading-day observation than the dataset contains
- WHEN freshness validation runs
- THEN validation fails with `DATA_FAILED`
- AND the failure code is `STALE_DATA`

### Requirement: Strategy minimum history is an eligibility threshold

The system SHALL treat a strategy's minimum-history requirement as the minimum number of valid historical observations required for eligible evaluation, not as an instruction to fetch exactly that many observations.

#### Scenario: Decision has too little valid history

- GIVEN structurally valid data
- AND the number of eligible historical observations is below the selected strategy's minimum-history requirement
- WHEN Decision data eligibility is checked
- THEN evaluation fails with `DATA_FAILED`
- AND the failure code is `INSUFFICIENT_HISTORY`
- AND the strategy is not evaluated

### Requirement: Backtest distinguishes warm-up from invalid data

The system SHALL distinguish valid-but-not-yet-eligible historical points from invalid historical data during analytical Backtest.

#### Scenario: Early backtest date lacks minimum history

- GIVEN historical data is structurally valid
- AND an early evaluation date has fewer observations than the strategy minimum-history requirement
- WHEN analytical Backtest advances to that date
- THEN that date is classified as `WARMUP`
- AND no strategy result is evaluated for that date
- AND the date is not classified as `NEUTRAL` or as invalid data

#### Scenario: Historical observation is invalid during backtest

- GIVEN a historical observation in the Backtest data range fails structural or continuity validation
- WHEN the analytical Backtest validates its data
- THEN the Backtest fails rather than silently skipping that invalid observation

### Requirement: Data failures are not neutral strategy outcomes

The system SHALL keep data-validation failure semantics separate from valid strategy market-state semantics.

#### Scenario: Data validation fails before strategy evaluation

- GIVEN the market data is invalid or ineligible
- WHEN a Decision or analytical Backtest evaluation is attempted
- THEN the result reports a data failure
- AND `NEUTRAL` is not reported as a substitute for that failure

### Requirement: Formal Taiwan EOD history preserves source-native OHLC fields without adapter transformation

The system SHALL use the selected market-data source's native daily `Open`, `High`, `Low`, `Close`, and `Volume` fields as the formal Taiwan EOD basis and SHALL NOT silently apply additional adapter-controlled price adjustment, repair, interpolation, or synthesis.

This capability does not assert that a provider's native historical OHLC remains on the original exchange nominal price scale across splits, consolidations, or equivalent corporate actions unless a future capability explicitly establishes that methodology.

#### Scenario: Source exposes native OHLC and an adjusted analytical field

- GIVEN a market-data source exposes native daily `Open`, `High`, `Low`, `Close`, and `Volume`
- AND the source also exposes `Adj Close` or another adjusted analytical field
- WHEN formal Taiwan EOD history is acquired
- THEN the native OHLCV fields are used as the formal source fields
- AND `Adj Close` or another adjusted analytical field is not substituted for formal OHLC
- AND the adapter does not apply a second price adjustment on top of the source-native OHLC

#### Scenario: Provider-native history has a corporate-action convention

- GIVEN the selected source's native historical OHLC may reflect the source's own split or consolidation convention
- WHEN formal Taiwan EOD history is acquired
- THEN the adapter preserves those source-native OHLC fields without claiming they reconstruct the original exchange nominal price scale
- AND any strategy-specific exchange-raw, split-adjusted, total-return, or other analytical transformation requires an explicitly defined methodology outside this capability

#### Scenario: Source offers automatic historical repair

- GIVEN a market-data source can automatically rewrite suspected price errors, missing observations, or corporate-action effects
- WHEN formal Taiwan EOD history is acquired
- THEN provider-side repair controlled by the adapter is disabled
- AND any resulting missing or structurally invalid market facts remain subject to the existing validation and failure semantics

#### Scenario: Trading-day observation is missing from formal history

- GIVEN the applicable TradingCalendar expects trading day T within the formal historical range required by the evaluation
- AND the acquired provider history has no observation for T
- WHEN continuity or freshness validation runs for that formal range
- THEN the system does not synthesize or interpolate an OHLCV observation for T solely to satisfy continuity
- AND the applicable existing `DATA_GAP` or `STALE_DATA` failure semantics apply

### Requirement: Provider acquisition breadth does not define continuity scope

The system SHALL NOT infer a full-instrument-lifetime continuity requirement solely because a provider returns observations earlier than the formal historical range required by the evaluation.

#### Scenario: Provider returns additional older history with an unrelated gap

- GIVEN the provider returns candidate observations that extend earlier than the formal historical range selected for an evaluation
- AND the extra older provider history contains a missing expected trading-day observation
- AND the formal historical range selected for the evaluation is otherwise complete and valid through resolved `as_of`
- WHEN formal history is bounded and continuity validation runs
- THEN the unrelated gap in extra older provider history does not by itself fail the evaluation
- AND continuity is assessed only over the formal historical range selected by the analytical flow

#### Scenario: Provider fetch mode changes acquisition breadth

- GIVEN two equivalent provider configurations return the same formal historical observations required by an evaluation
- AND one provider configuration also returns additional older observations
- WHEN the same evaluation is prepared
- THEN the additional provider history alone does not change continuity eligibility or the resulting Strategy input

### Requirement: Strategy-specific lookback remains outside EOD acquisition semantics

The system SHALL NOT derive strategy-specific history-window or lookback policy from provider request parameters or provider response breadth.

#### Scenario: Provider can return maximum available history

- GIVEN a provider is capable of returning the instrument's maximum available historical dataset
- WHEN EOD market data is acquired
- THEN that provider capability does not define how much historical data a Strategy must use
- AND any strategy-specific history selection remains governed by the analytical Strategy/Application behavior rather than by the provider adapter

### Requirement: Corporate-action analytical methodology remains separate from EOD acquisition

The system SHALL keep any future exchange-raw reconstruction, split/consolidation normalization, dividend/total-return adjustment, or other corporate-action analytical transformation separate from the formal EOD acquisition and structural-validation behavior defined by this capability.

#### Scenario: Historical corporate action exists

- GIVEN an instrument has a historical distribution, split, consolidation, or other corporate action
- WHEN its source-native EOD fields are normalized and structurally validated
- THEN the validation layer does not apply an additional provider-specific analytical transformation to prior OHLC observations
- AND the capability does not claim that source-native history is exchange-raw or total-return adjusted
- AND any analytical transformation of that history requires an explicitly defined methodology outside this market-data validation behavior

