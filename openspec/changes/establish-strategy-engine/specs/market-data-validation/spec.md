## Purpose

Define the observable market-data eligibility, validation, as-of, and warm-up behavior required before strategy evaluation.

## ADDED Requirements

### Requirement: Completed daily OHLCV is the formal historical input

The system SHALL use completed daily OHLCV observations as the formal historical input for strategy evaluation.

#### Scenario: Incomplete current-session data is also available

- GIVEN completed daily OHLCV history through trading day T-1
- AND an incomplete intraday snapshot for trading day T
- WHEN formal strategy history is prepared
- THEN the historical daily dataset contains only completed daily observations
- AND the intraday snapshot is not inserted into the formal historical series

### Requirement: Historical observations are bounded by resolved as-of

The system SHALL provide strategy evaluation only with completed observations whose information is available on or before the resolved `as_of` date.

#### Scenario: Dataset extends beyond historical as-of

- GIVEN completed observations from T-20 through T+5
- WHEN evaluation is requested with resolved `as_of=T`
- THEN observations after T are excluded from the strategy input

### Requirement: Required market-data fields are validated

The system SHALL reject data that is missing a field required by the selected strategy.

#### Scenario: Required volume is unavailable

- GIVEN a strategy whose data requirements include volume
- AND an otherwise valid dataset contains a missing volume value for a required observation
- WHEN strategy data eligibility is validated
- THEN validation fails with `DATA_FAILED`
- AND the failure code is `MISSING_REQUIRED_FIELD`
- AND the missing value is not interpreted as zero or as a negative strategy signal

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

### Requirement: Volume is non-negative when present

The system SHALL reject an observation whose volume is negative.

#### Scenario: Negative volume

- GIVEN an observation with negative volume
- WHEN structural validation runs
- THEN validation fails with `DATA_FAILED`
- AND the failure code identifies invalid market data

### Requirement: Observation timestamps are valid, ordered, and unique

The system SHALL reject historical data containing invalid timestamps, duplicate timestamps, or an invalid chronological sequence.

#### Scenario: Duplicate trading date

- GIVEN two historical observations with the same normalized trading timestamp
- WHEN structural validation runs
- THEN validation fails with `DATA_FAILED`
- AND the failure code is `DUPLICATE_TIMESTAMP`

#### Scenario: Invalid chronological sequence

- GIVEN historical observations that cannot be normalized into a valid chronological order without ambiguity or data corruption
- WHEN structural validation runs
- THEN validation fails with `DATA_FAILED`

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
