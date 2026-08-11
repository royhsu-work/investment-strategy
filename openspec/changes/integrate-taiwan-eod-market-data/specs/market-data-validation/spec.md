## Purpose

Extend formal market-data validation semantics with an explicit price basis for Taiwan EOD history while preserving the existing normalization, structural validation, continuity, freshness, and no-look-ahead rules.

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

#### Scenario: Trading-day observation is missing

- GIVEN the applicable TradingCalendar expects trading day T
- AND the acquired provider history has no reported observation for T
- WHEN continuity or freshness validation runs
- THEN the system does not synthesize or interpolate an OHLCV observation for T solely to satisfy continuity
- AND the applicable existing `DATA_GAP` or `STALE_DATA` failure semantics apply

### Requirement: Corporate-action analytical adjustment is not implicit market-data validation

The system SHALL keep any future corporate-action or total-return analytical transformation separate from the formal EOD acquisition and structural-validation behavior defined by this capability.

#### Scenario: Historical corporate action exists

- GIVEN an instrument has a historical distribution, split, consolidation, or other corporate action
- WHEN its reported EOD market facts are normalized and structurally validated
- THEN the validation layer does not silently rewrite prior OHLC observations according to a provider-specific adjustment methodology
- AND any analytical transformation of that history requires an explicitly defined methodology outside this market-data validation behavior
