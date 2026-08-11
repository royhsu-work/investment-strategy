## Purpose

Extend formal market-data validation semantics with an explicit price basis for Taiwan EOD history while preserving the existing normalization, structural validation, freshness, and no-look-ahead rules without turning provider acquisition breadth into an implicit full-lifetime continuity requirement.

## ADDED Requirements

### Requirement: Formal Taiwan EOD history preserves reported trading prices

The system SHALL use reported regular-session daily OHLC values for formal Taiwan EOD history and SHALL NOT silently replace them with retroactively adjusted, repaired, interpolated, or synthetic prices.

#### Scenario: Source exposes reported and transformed price history

- GIVEN a market-data source can provide both reported daily trading prices and a transformed or adjusted historical series
- WHEN formal Taiwan EOD history is acquired
- THEN the reported daily trading-price series is used as the formal OHLC basis
- AND the transformed or adjusted series is not silently substituted for it

#### Scenario: Source offers automatic historical repair

- GIVEN a market-data source can automatically rewrite suspected price errors, missing observations, or corporate-action effects
- WHEN formal Taiwan EOD history is acquired
- THEN such provider-side rewriting is not silently applied to the formal historical series
- AND any resulting missing or structurally invalid market facts remain subject to the existing validation and failure semantics

#### Scenario: Trading-day observation is missing from formal history

- GIVEN the applicable TradingCalendar expects trading day T within the formal historical range required by the evaluation
- AND the acquired provider history has no reported observation for T
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

### Requirement: Corporate-action analytical adjustment is not implicit market-data validation

The system SHALL keep any future corporate-action or total-return analytical transformation separate from the formal EOD acquisition and structural-validation behavior defined by this capability.

#### Scenario: Historical corporate action exists

- GIVEN an instrument has a historical distribution, split, consolidation, or other corporate action
- WHEN its reported EOD market facts are normalized and structurally validated
- THEN the validation layer does not silently rewrite prior OHLC observations according to a provider-specific adjustment methodology
- AND any analytical transformation of that history requires an explicitly defined methodology outside this market-data validation behavior
