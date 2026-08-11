# Proposal — integrate-taiwan-eod-market-data

## Why

The Strategy Engine can already evaluate formal Decisions and analytical Backtests from completed daily OHLCV, but the repository still has no production-capable way to acquire real Taiwan market data or resolve Taiwan trading sessions.

The project needs a provider-neutral Taiwan EOD market-data capability so existing Decision and Backtest flows can evaluate current market state from facts that have already occurred, without coupling strategy or application contracts to a particular SDK, ticker syntax, realtime feed, or prediction mechanism.

This change establishes that data boundary before introducing any production strategy implementation.

## What Changes

This change introduces provider-neutral Taiwan EOD market-data integration with the following behavior:

- Instrument configuration identifies the instrument's Taiwan listing venue independently of any provider-specific ticker format.
- The first supported Taiwan listing venues are TWSE and TPEx.
- Market-data acquisition accepts the repository's canonical instrument identity and resolves any provider-specific identifier behind the data-provider boundary.
- Formal Taiwan market history is acquired as completed daily OHLCV only.
- Formal EOD prices represent reported regular-session trading prices for each trading date and are not silently replaced by retroactively adjusted, repaired, interpolated, or synthetic price history.
- Taiwan market dates and completed sessions are resolved in the Taiwan market timezone from an exchange-aware trading calendar rather than a weekday-only heuristic.
- The Taiwan trading calendar accounts for scheduled holidays, additional trading sessions, and exceptional market closures when determining continuity, freshness, and the latest completed trading day.
- Calendar support follows the configured pinned calendar engine's actual supported range; if that engine cannot establish required session status, evaluation fails explicitly rather than assuming a session and misclassifying missing price data as `DATA_GAP` or `STALE_DATA`.
- Official TWSE/TPEx evidence is required for representative regression fixtures and any real repository override, not as per-date certification for the entire engine-supported range.
- Existing market-data normalization, structural validation, no-look-ahead, freshness, continuity, minimum-history, and Backtest warm-up semantics remain authoritative for the formal historical range selected by the analytical flow; provider acquisition breadth alone does not create a full-instrument-lifetime continuity requirement.
- Provider acquisition failures or absence of candidate history continue to surface through the existing market-data failure contract rather than being converted into a valid neutral strategy result.
- The capability can be consumed by existing Decision and analytical Backtest services without changing their public request or artifact schemas.

## Capabilities

### New Capabilities

- `taiwan-eod-market-data`: provider-neutral acquisition of completed Taiwan daily OHLCV and Taiwan exchange-session/calendar semantics required by Decision and analytical Backtest.

### Modified Capabilities

- `strategy-engine`: extend instrument configuration with provider-neutral listing-venue identity needed before Taiwan market-data acquisition.
- `market-data-validation`: make the formal EOD price basis explicit and clarify that continuity applies to the formal history required by an evaluation rather than to arbitrary extra history returned by a provider.

## Scope Boundaries

This change is intentionally limited to acquiring and identifying completed Taiwan EOD market facts.

It does **not** define or implement:

- intraday snapshots, realtime quotes, minute bars, ticks, streaming, or WebSocket feeds;
- price prediction, future-return prediction, or forecasting;
- production Bollinger, time-series, hybrid, or other strategy algorithms;
- strategy-specific history-window or lookback policy beyond the existing Strategy contracts;
- corporate-action adjustment or total-return methodology;
- adjusted analytical price-series construction;
- cross-provider reconciliation or provider fallback policy;
- persistent market-data databases, caches, or historical-data warehousing;
- publication of raw provider history as a public repository file or public market-data artifact;
- automatic discovery of future or newly announced exchange-calendar changes;
- production activation of Decision or Backtest GitHub Actions workflows;
- simulated execution, fills, pending orders, positions, cash, PnL, fees, taxes, or slippage;
- benchmark/reference-instrument logic.

Provider SDK choice, provider-specific symbol mapping, request parameters, and concrete calendar data-source selection are design and implementation concerns and are not part of the capability contract.

## Impact

Expected affected areas:

- OpenSpec definitions for Taiwan EOD market-data acquisition, instrument venue identity, formal market-data semantics, and calendar-engine support failure behavior.
- Instrument configuration domain and YAML adapter behavior.
- Concrete market-data and Taiwan trading-calendar adapters behind existing ports.
- Dependency composition for Decision and analytical Backtest services.
- Integration tests demonstrating completed Taiwan EOD data can pass through the existing normalization and validation pipeline without changing Strategy evaluation semantics.

Public Decision and analytical Backtest request and artifact schemas are unchanged by this change.

## Deferred Work

Follow-up changes are expected for:

- final corporate-action and analytical price-adjustment methodology;
- production strategy implementations such as `implement-bollinger-swing-strategy`, including any strategy-specific historical lookback policy they require;
- production workflow activation after a production strategy assignment exists;
- provider fallback, authoritative cross-validation, persistent market-data storage, or automatic calendar-update ingestion if later justified;
- execution simulation under a dedicated execution capability.
