# Proposal — establish-strategy-engine

## Why

The project needs a shared, reproducible strategy-evaluation framework that can be used by both formal Decision runs and historical analytical Backtests without duplicating strategy logic.

The framework must support multiple strategy implementations while preventing look-ahead bias, hidden runtime-state dependencies, and accidental mixing of configuration, data-validation, strategy-evaluation, and execution concerns.

This change establishes that common evaluation foundation before implementing any production Bollinger, time-series, hybrid, or execution-simulation logic.

## What Changes

This change introduces a common Strategy Engine with the following capabilities:

- A common Strategy contract for declaring data requirements and evaluating a strategy as of a specific trading date.
- A common Strategy Result for swing-strategy analysis, including market state, entry plan, exit plan, strategy-specific signals, diagnostics, and reasons.
- Stateless and reproducible strategy evaluation based only on explicit inputs available at or before `as_of`.
- Separation of strategy implementation from parameter sets.
- Instrument configuration with one active strategy assignment for formal Decision evaluation.
- Explicit strategy plus parameter-set selection for research Backtests without modifying the production assignment.
- Configuration resolution and validation before market-data loading or strategy evaluation.
- Normalized completed daily OHLCV as the formal strategy input.
- Structural and strategy-requirement data validation with clear separation between valid `NEUTRAL` outcomes and failures.
- Trading-calendar-aware as-of resolution, freshness, continuity, and warm-up handling.
- Formal isolation of incomplete intraday snapshots from completed historical daily data.
- Decision evaluation using the configured active assignment.
- Analytical walk-forward Backtest evaluation using the same Strategy implementation as Decision and without future information.
- Reproducibility metadata including strategy identity, parameter set, `as_of`, and Git revision in generated results/artifacts.

## Capabilities

### New Capabilities

- `strategy-engine`: common strategy evaluation contract, common swing-plan result, stateless evaluation, strategy/parameter separation, and strategy resolution.
- `market-data-validation`: normalized completed daily OHLCV, trading-calendar-aware validation, strategy data requirements, warm-up, and failure semantics.
- `decision-evaluation`: formal active-strategy evaluation for a symbol and optional historical `as_of` date.
- `analytical-backtest`: walk-forward historical strategy evaluation with active or explicit strategy assignment and no look-ahead.

### Modified Capabilities

None. This repository does not yet contain an established Strategy Engine capability to modify.

## Scope Boundaries

This change is intentionally limited to strategy analysis and analytical replay.

It does **not** define or implement:

- simulated order execution or fills;
- simulated cash, positions, or portfolio state;
- price-level fill rules;
- close-confirmed trigger execution timing;
- daily pending-order or execution-state lifecycle;
- PnL, returns, drawdown, or other execution-derived performance metrics;
- transaction fees, taxes, slippage, or liquidity assumptions;
- a production Bollinger strategy;
- W-bottom, V-reversal, M-top, or inverted-V detection rules;
- Bollinger `%B`, BandWidth, ATR, or volume-confirmation thresholds;
- a production time-series model;
- a hybrid strategy algorithm;
- benchmark/reference-instrument logic;
- position sizing or Buy 1 / Buy 2 capital allocation;
- concrete market-data providers or provider fallback rules;
- final corporate-action methodology.

Execution simulation will be proposed separately under a dedicated change such as `add-backtest-execution-simulator`.

Production strategy implementations will also be introduced by separate changes, for example `implement-bollinger-swing-strategy` and `implement-time-series-strategy`.

## Impact

Expected affected areas:

- OpenSpec definitions for strategy evaluation, market-data validation, Decision, and analytical Backtest behavior.
- New common domain contracts for Strategy, Strategy Result, market state, entry/exit plans, and data requirements.
- Configuration for instrument active assignments and reusable parameter sets.
- Decision application flow.
- Analytical Backtest walk-forward flow.
- Validation and failure reporting.
- GitHub Actions artifacts for reproducible Decision and analytical Backtest outputs.

Existing workflow scaffolds may be adapted to call these applications, but generated results remain GitHub Actions Artifacts and are not committed back into the repository.

## Deferred Work

Follow-up changes are expected for:

- `implement-bollinger-swing-strategy`
- `implement-time-series-strategy`
- `add-backtest-execution-simulator`
- a future hybrid-strategy change when research justifies it

These follow-up changes must consume the Strategy Engine contracts rather than reimplementing parallel Decision or Backtest strategy logic.
