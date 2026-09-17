## Purpose

Extend formal market-data validation semantics with an explicit source-native price basis for Taiwan EOD history while preserving the existing normalization, structural validation, freshness, and no-look-ahead rules without turning provider acquisition breadth into an implicit full-lifetime continuity requirement.

## ADDED Requirements

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
