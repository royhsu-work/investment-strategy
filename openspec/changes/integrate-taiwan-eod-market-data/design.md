# Design — integrate-taiwan-eod-market-data

## Context

The repository already has provider-neutral Strategy, Decision, Backtest, market-data normalization/validation, Clock, and TradingCalendar contracts. What is missing is a production-capable path from a configured Taiwan instrument to completed EOD OHLCV and an exchange-aware Taiwan session calendar.

The approved proposal/specifications constrain this change to facts that have already occurred:

- formal Strategy evaluation consumes completed daily OHLCV only;
- this change does not introduce intraday, realtime, prediction, execution, or production strategy behavior;
- `TWSE` and `TPEX` are the supported provider-neutral listing venues;
- provider SDK types and provider ticker syntax must not leak into Strategy, Decision, or Backtest contracts;
- reported regular-session OHLC is the formal EOD price basis;
- provider-side automatic adjustment, repair, interpolation, or synthesis must not silently rewrite formal history;
- Taiwan market-date/session semantics must be timezone-aware and exchange-session-aware;
- existing normalization, structural validation, continuity, freshness, no-look-ahead, minimum-history, and Backtest WARMUP behavior remain authoritative.

The implementation remains Python 3.11+, typed, dependency-inverted, and testable without requiring live network access in the default test suite.

## Goals / Non-Goals

### Goals

- Add provider-neutral listing-venue identity to configured instruments.
- Fail missing or unsupported venue configuration before market-data loading.
- Pass a provider-neutral market-data identity through the existing application/data boundary without exposing venue details to Strategy implementations.
- Provide one concrete completed-daily OHLCV adapter suitable for Taiwan-listed instruments while keeping the adapter replaceable.
- Preserve reported EOD OHLCV rather than provider-transformed price history.
- Provide Taiwan regular-securities trading-session behavior for TWSE and TPEx-listed instruments.
- Preserve existing Decision/Backtest public request and artifact contracts.
- Keep default automated tests deterministic and independent of live provider availability.

### Non-Goals

- Intraday/realtime price acquisition or overlays.
- Forecasting or future-return estimation.
- Production strategy algorithms or active production assignments.
- Corporate-action adjusted analytical series or total-return methodology.
- Cross-provider validation/fallback.
- Persistent market-data storage or caching.
- Raw provider-data publication.
- Production GitHub Actions activation.
- Execution/fill/portfolio simulation.
- TPEx International Bond Market or Emerging Stock Board session semantics; `TPEX` in this change refers to regular listed securities/ETF EOD data compatible with the common daily-OHLCV strategy contract.

## Decisions

### 1. Keep Strategy symbol-only and introduce a provider-neutral market-data identity

The Strategy contract does not need listing venue. Venue exists to route external market data, not to define strategy behavior.

Add a small immutable value at the configuration/data boundary:

```text
MarketDataInstrument
├── symbol
└── listing_venue
```

`listing_venue` is provider-neutral and supports exactly:

```text
TWSE
TPEX
```

Application flow becomes:

```text
request symbol
    |
    v
StrategyConfigResolver
    ├─ resolve instrument
    ├─ validate listing venue
    ├─ resolve strategy/parameter assignment
    └─ return resolved configuration including market-data identity
    |
    +----------------------------+
    |                            |
    v                            v
MarketDataGateway           StrategyContext
(symbol + venue)            canonical symbol only
```

The `MarketDataGateway` port changes from accepting only a string symbol to accepting `MarketDataInstrument`. This avoids making a concrete provider adapter depend on `InstrumentRegistry` or YAML storage and mechanically preserves configuration-before-data-loading ordering.

`StrategyContext.instrument` remains the canonical symbol string; provider routing is not added to strategy-specific inputs.

### 2. Listing venue is validated during configuration resolution

`InstrumentConfig` gains an optional provider-neutral `listing_venue` field so an existing fixture/configuration can represent a configured instrument before a venue is added.

Resolution validates venue before market-data loading:

```text
missing venue
  -> CONFIGURATION_FAILED / LISTING_VENUE_NOT_CONFIGURED

unsupported venue
  -> CONFIGURATION_FAILED / UNSUPPORTED_LISTING_VENUE
```

The YAML adapter accepts human-readable values `TWSE` and `TPEX`. Provider-specific identifiers such as `.TW` or `.TWO` are rejected as unsupported listing venues rather than normalized into canonical configuration.

The resolved strategy configuration carries the validated `MarketDataInstrument` (or equivalent immutable fields) so Decision and Backtest can pass it directly to the data port.

### 3. Use yfinance only as the first concrete EOD adapter

The capability remains provider-neutral. The first infrastructure implementation will use `yfinance` because it provides historical daily OHLCV for Yahoo Finance symbols and can be isolated behind the existing market-data port.

Recommended infrastructure boundary:

```text
src/investment_strategy/
├── data/
│   ├── ports.py
│   ├── normalize.py
│   ├── validate.py
│   └── calendar.py
└── infrastructure/
    └── market_data/
        ├── yfinance_eod.py
        └── taiwan_calendar.py
```

The adapter alone owns provider-specific symbol mapping:

```text
TWSE + 00733  -> 00733.TW
TPEX + 00679B -> 00679B.TWO
```

No provider suffix is stored in `config/instruments.yaml`, StrategyContext, Decision request, Backtest request, or public artifacts.

The yfinance call must explicitly request reported daily history rather than rely on library defaults. The implementation will use behavior equivalent to:

```text
period=max
interval=1d
prepost=false
auto_adjust=false
back_adjust=false
repair=false
actions=false
rounding=false
raise_errors=true
```

The adapter converts the returned provider table into plain candidate mappings containing only:

```text
timestamp
open
high
low
close
volume
```

Provider DataFrame/index types and yfinance exceptions do not cross the adapter boundary. Existing `acquire_candidates()` converts provider failure/empty history into the canonical `DATA_UNAVAILABLE` behavior.

`Adj Close`, dividend, split, capital-gain, and provider repair metadata are not formal OHLCV fields in this change.

### 4. Do not silently hide provider data defects

The provider adapter must not make invalid data appear valid.

It therefore does not:

- fill missing OHLCV values;
- synthesize missing trading dates;
- interpolate bars;
- use adjusted OHLC in place of reported OHLC;
- enable yfinance price repair;
- fall back to another provider.

Candidate records are passed to the existing normalization/validation pipeline. Missing fields, invalid OHLC, duplicate dates, data gaps, stale history, and other existing failures remain the framework's responsibility.

This separation is intentional:

```text
provider acquisition / conversion
        ↓
plain candidate records
        ↓
existing temporal bounding
        ↓
existing normalization
        ↓
existing structural + calendar validation
```

### 5. Use a replaceable Taiwan regular-securities calendar adapter

Application code continues to depend only on the existing `TradingCalendar` protocol.

The first implementation may use `exchange_calendars`' `XTAI` calendar as the session engine because it explicitly models Taiwan Stock Exchange sessions, holidays, and historical exceptional closures. The adapter remains local infrastructure so the dependency can be replaced without changing application/domain contracts.

For this change, TWSE and TPEx regular listed-securities/ETF EOD evaluation share the Taiwan regular-securities calendar behavior. This design assumption must be guarded by regression fixtures drawn from both TWSE and TPEx official holiday/session schedules. If a future divergence appears, a later change can route venue-specific calendar implementations without changing the Strategy contract.

The adapter owns `Asia/Taipei` market timezone behavior.

Tests must cover at least:

- a normal weekday session;
- a weekday exchange holiday;
- a historical additional Saturday trading session;
- a historical/declared exceptional full-market closure;
- conversion from a non-Taipei runner timezone;
- previous/latest completed trading-day behavior.

### 6. Use a conservative current-day completion boundary

Formal EOD eligibility must never include an in-progress session. Taiwan regular trading normally closes at 13:30, while closing matching can be postponed for affected securities. The infrastructure calendar will therefore treat the current Taiwan trading date as formally complete only after a conservative post-close boundary of 13:33 Asia/Taipei.

This does not assert that provider EOD data is already available at 13:33. It only makes the calendar date eligible. If the provider has not yet published the completed bar, existing freshness semantics produce `DATA_FAILED / STALE_DATA`; the application does not move `resolved_as_of` backward.

Historical dates before the current Taiwan market date are complete if they are sessions in the calendar.

### 7. Keep calendar source and market-data source independent

The market-data adapter and TradingCalendar are separate infrastructure dependencies:

```text
MarketDataGateway
  -> completed EOD candidates

TradingCalendar
  -> expected sessions / completion semantics
```

A provider's returned dates do not define the trading calendar. This prevents missing provider rows from being interpreted as exchange holidays and preserves existing `DATA_GAP`/`STALE_DATA` behavior.

Likewise, the calendar does not synthesize market-data records.

### 8. Do not add a persistent cache in this change

Decision and Backtest may initially reacquire history from the concrete provider. This is acceptable for the current project scale and keeps the change single-purpose.

The existing `MarketDataGateway` remains the seam for a future cached/database-backed implementation. A later storage/fallback proposal may extend acquisition efficiency without changing Strategy semantics.

### 9. Default tests are offline; external availability is not a CI correctness oracle

Tests are split into two levels:

```text
contract/behavior tests
├─ in-memory/fake provider records
├─ fake/injected yfinance history loader or DataFrame fixtures
├─ fixed clocks
└─ deterministic calendar regression dates

optional/manual smoke verification
└─ real external provider call
```

The default `pytest` suite must not depend on Yahoo/TWSE/TPEx network availability. Provider invocation arguments, symbol mapping, conversion, and failure mapping are verified with injected/mocked provider behavior.

This prevents transient external outages from making framework correctness nondeterministic while still leaving the production adapter usable in real composition.

### 10. Do not activate public Decision/Backtest workflows yet

The repository still has no production strategy assignment. This change updates the application/data boundary so the concrete EOD adapter and calendar can be composed, but `.github/workflows/decision.yml` and `backtest.yml` remain scaffolds until a later change introduces a production strategy and explicitly activates those workflows.

No real active strategy assignment is added to `config/instruments.yaml` here.

## Requirement Traceability

| Requirement area | Design decision |
| --- | --- |
| Canonical instrument identity / provider isolation | Decisions 1–3 |
| TWSE/TPEX support / venue validation | Decisions 1–2 |
| Completed daily OHLCV | Decisions 3–4 |
| Reported unadjusted price basis | Decisions 3–4 |
| Incomplete current session excluded | Decisions 5–6 |
| Taiwan timezone | Decisions 5–6 |
| Actual exchange sessions / holidays / additional sessions / closures | Decisions 5, 7 |
| Existing DATA_UNAVAILABLE / STALE_DATA / validation semantics | Decisions 3–4, 6–7 |
| No public contract/provider SDK leakage | Decisions 1–3 |
| No production workflow activation | Decision 10 |

## Risks / Trade-offs

### yfinance is an external unofficial market-data implementation

The project does not treat yfinance/Yahoo as a domain contract or authoritative calendar. Provider outages/schema changes remain possible. Isolation behind `MarketDataGateway`, explicit call parameters, offline adapter tests, and existing data failures limit the blast radius.

### `period=max` reacquires more history than a strategy may need

The existing gateway contract intentionally does not expose strategy-specific range requirements. For the current small-instrument research scope this is simpler and naturally supports Backtest pre-roll. A ranged/cached acquisition capability can be proposed later if scale justifies it.

### Shared regular-securities calendar behavior may eventually diverge by venue

The first implementation shares a Taiwan regular-securities session calendar for TWSE and TPEx-listed instruments while testing known dates from both official schedules. Venue remains explicit in domain configuration so a later venue-specific calendar split does not require provider-specific ticker syntax or Strategy changes.

### Raw reported prices can contain corporate-action discontinuities

This is deliberate. The acquisition layer must preserve market facts and must not silently choose an adjustment methodology. A future corporate-action/analytical-price-series change must define that transformation explicitly before production strategies rely on it where adjustment is required.

## Deferred Decisions

- Corporate-action and total-return adjustment methodology.
- Provider fallback or authoritative price reconciliation.
- Persistent cache/database and ranged acquisition.
- Venue-specific calendar divergence if future evidence requires it.
- Production workflow activation.
- Production strategy assignment.
- Execution simulation.
