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
- provider acquisition breadth must not silently become a full-instrument-lifetime continuity requirement;
- Strategy-specific history-window/lookback policy remains outside this change;
- Taiwan market-date/session semantics must be timezone-aware and exchange-session-aware;
- calendar knowledge that cannot be established within supported coverage must fail explicitly rather than being misclassified as missing market data;
- existing normalization, structural validation, freshness, no-look-ahead, minimum-history, and Backtest WARMUP semantics remain authoritative.

The implementation remains Python 3.11+, typed, dependency-inverted, and testable without requiring live network access in the default test suite.

## Goals / Non-Goals

### Goals

- Add provider-neutral listing-venue identity to configured instruments.
- Fail missing or unsupported venue configuration before market-data loading.
- Pass provider-neutral market-data identity through the application/data boundary without exposing venue details to Strategy implementations.
- Provide one concrete completed-daily OHLCV adapter suitable for Taiwan-listed instruments while keeping it replaceable.
- Preserve reported EOD OHLCV rather than provider-transformed price history.
- Prevent provider fetch breadth from defining continuity-validation scope.
- Provide Taiwan regular-securities trading-session behavior for TWSE and TPEx-listed instruments.
- Make unsupported/unverified calendar coverage an explicit data failure.
- Preserve existing Decision/Backtest public request and artifact contracts.
- Keep default automated tests deterministic and independent of live provider availability.

### Non-Goals

- Intraday/realtime price acquisition or overlays.
- Forecasting or future-return estimation.
- Production strategy algorithms or active production assignments.
- Defining a Strategy-specific lookback/history-window contract.
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

Add an immutable value at the configuration/data boundary:

```text
MarketDataInstrument
├── symbol
└── listing_venue
```

`listing_venue` supports exactly:

```text
TWSE
TPEX
```

Application flow:

```text
request symbol
    |
    v
StrategyConfigResolver
    ├─ resolve instrument
    ├─ validate listing venue
    ├─ resolve strategy/parameter assignment
    └─ return resolved configuration + market-data identity
    |
    +----------------------------+
    |                            |
    v                            v
MarketDataGateway           StrategyContext
(symbol + venue)            canonical symbol only
```

The `MarketDataGateway` port changes from accepting only a string symbol to accepting `MarketDataInstrument`. A concrete adapter therefore does not query `InstrumentRegistry` or parse YAML itself.

`StrategyContext.instrument` remains the canonical symbol string.

### 2. Validate listing venue before market-data loading

`InstrumentConfig` gains an optional provider-neutral `listing_venue` field so existing fixtures/configuration can represent instruments before venue migration is complete.

Resolution behavior:

```text
missing venue
  -> CONFIGURATION_FAILED / LISTING_VENUE_NOT_CONFIGURED

unsupported venue
  -> CONFIGURATION_FAILED / UNSUPPORTED_LISTING_VENUE
```

The YAML adapter accepts `TWSE` and `TPEX`. Provider-specific identifiers such as `.TW` or `.TWO` are not canonical venue values.

### 3. Use yfinance only as the first concrete EOD adapter

The capability remains provider-neutral. The first infrastructure implementation uses `yfinance` behind the market-data port.

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

Only the adapter owns provider-specific symbol mapping:

```text
TWSE + 00733  -> 00733.TW
TPEX + 00679B -> 00679B.TWO
```

The first implementation may request provider history equivalent to:

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

`period=max` is an acquisition convenience only. It does **not** mean every provider observation from the instrument's first available date becomes part of the formal continuity contract.

The adapter converts provider output to plain candidate mappings containing only:

```text
timestamp
open
high
low
close
volume
```

Provider DataFrame/index types, provider ticker syntax, and yfinance exceptions do not cross the infrastructure boundary. `Adj Close`, dividends, splits, capital gains, and repair metadata are not formal OHLCV fields.

### 4. Separate acquisition breadth, structural validation, freshness, and formal-range continuity

The current validator derives continuity start from the first acquired bar. Combined with `period=max`, that would accidentally impose full-lifetime continuity. This change removes that coupling.

The responsibilities become:

```text
provider acquisition
        ↓
candidate temporal bounding to as_of
        ↓
structural normalization/validation of observations that remain formal candidates
        ↓
freshness check against resolved_as_of
        ↓
continuity check only for an explicitly selected formal historical range
        ↓
Strategy/Application evaluation
```

Rules:

- acquisition breadth does not define analytical history breadth;
- extra older provider observations outside the formal range must not cause `DATA_GAP`;
- freshness always verifies that the latest required completed session equals `resolved_as_of`;
- continuity validation must receive an explicit formal start/end (or equivalent selected range) rather than infer its start from the provider's first returned observation;
- if no analytical caller has selected a formal range, the shared EOD layer does not invent one merely to run continuity validation;
- a gap inside an explicitly selected formal range remains `DATA_FAILED / DATA_GAP`;
- this change does not define how a production Strategy chooses lookback/history range. That remains Strategy/Application behavior for the future production-strategy change.

A practical refactor may split the existing combined helper into behavior equivalent to:

```text
validate_freshness(bars, resolved_as_of)
validate_continuity(bars, calendar, required_start, required_end)
```

The exact function names are implementation details; the behavior above is normative for this design.

### 5. Do not silently hide provider data defects

The provider adapter does not:

- fill missing OHLCV values;
- synthesize missing trading dates;
- interpolate bars;
- use adjusted OHLC in place of reported OHLC;
- enable provider-side price repair;
- fall back to another provider.

Missing/invalid candidate fields remain visible to the existing normalization and structural validation behavior.

### 6. Use a replaceable Taiwan regular-securities calendar adapter

Application code continues to depend only on `TradingCalendar`.

The first implementation uses `exchange_calendars` XTAI as a session engine for Taiwan regular-securities dates and keeps the dependency inside infrastructure. TWSE and TPEx regular listed-securities/ETF evaluation share this behavior in this change, guarded by deterministic official-schedule regression fixtures for both venues.

The adapter owns `Asia/Taipei` market timezone behavior.

Regression fixtures cover at least:

- normal weekday session;
- weekday exchange holiday;
- historical additional Saturday trading session;
- historical/declared exceptional full-market closure;
- non-Taipei runner timezone;
- previous/latest completed trading-day behavior.

If later evidence proves TWSE and TPEx regular-session calendars diverge materially, a later change can route venue-specific calendar implementations without changing Strategy.

### 7. Calendar knowledge is bounded and fails closed outside supported coverage

The calendar adapter must distinguish:

```text
known session answer
vs
session status cannot be established reliably
```

The adapter exposes/owns a supported coverage boundary derived from the selected calendar engine plus repository-maintained verified corrections. A requested date outside that supported coverage does not fall back to weekday logic.

Failure behavior:

```text
calendar status unavailable / outside supported coverage
  -> DATA_FAILED / CALENDAR_UNAVAILABLE
```

This failure occurs before `DATA_GAP` or `STALE_DATA` because those codes require reliable knowledge that a session was expected.

Within supported coverage, the configured calendar engine plus repository explicit overrides are authoritative for this application. A newly declared exceptional closure/session that is not represented must be added as a verified override before the affected date is treated as verified calendar truth.

Overrides are **sparse and discrepancy-driven**:

- no duplicate full historical calendar is maintained;
- add an override only when an officially verified TWSE/TPEx regular-market fact differs from the selected calendar engine or is not representable by it;
- every override must identify the affected date and expected open/closed session truth in test fixtures or equivalent repository evidence;
- Task implementation is not required to recreate the entire historical range returned by `period=max`.

### 8. Use a conservative current-day completion boundary

Formal EOD eligibility must never include an in-progress session. Taiwan regular trading normally closes at 13:30, while closing matching can be postponed for affected securities. The calendar adapter treats the current Taiwan trading date as formally complete only after 13:33 Asia/Taipei.

This only establishes calendar eligibility. It does not claim provider EOD data is already published.

```text
calendar says T complete
provider still ends at T-1
  -> DATA_FAILED / STALE_DATA
```

The application never moves `resolved_as_of` backward to match provider availability.

### 9. Keep calendar source and market-data source independent

```text
MarketDataGateway
  -> completed EOD candidates

TradingCalendar
  -> expected sessions / completion semantics
```

Provider-returned dates do not define exchange sessions. The calendar does not synthesize market-data observations.

Only when session knowledge is reliable may missing provider observations become `DATA_GAP` or `STALE_DATA`.

### 10. Default tests are offline and external availability is not a correctness oracle

Default tests use:

```text
contract/behavior tests
├─ in-memory/fake provider records
├─ injected yfinance history loader / provider-table fixtures
├─ fixed clocks
├─ explicit formal continuity ranges
└─ deterministic Taiwan calendar regression dates
```

Optional/manual smoke verification may call the real external provider, but default `pytest` must not depend on Yahoo/TWSE/TPEx network availability.

### 11. Do not activate public Decision/Backtest workflows yet

The repository still has no production strategy assignment. This change makes the concrete EOD adapter/calendar composable but leaves Decision/Backtest workflows as scaffolds.

No real active strategy assignment is added to `config/instruments.yaml`.

## Requirement Traceability

| Requirement area | Design decision |
| --- | --- |
| Canonical instrument identity / provider isolation | 1–3 |
| TWSE/TPEX support / venue validation | 1–2 |
| Completed daily OHLCV | 3, 5 |
| Reported unadjusted price basis | 3, 5 |
| Provider breadth does not define continuity scope | 3–4 |
| Strategy-specific history policy remains separate | 4 |
| Taiwan timezone / completed session | 6, 8 |
| Actual sessions / holidays / additional sessions / closures | 6–9 |
| Calendar unsupported coverage / `CALENDAR_UNAVAILABLE` | 7, 9 |
| Existing `DATA_UNAVAILABLE` / `STALE_DATA` semantics | 3, 5, 8–9 |
| No provider SDK leakage | 1–3 |
| No production workflow activation | 11 |

## Risks / Trade-offs

### yfinance is an external unofficial market-data implementation

Provider outages/schema changes remain possible. Isolation behind `MarketDataGateway`, explicit call parameters, offline tests, and canonical data failures limit the blast radius.

### `period=max` may reacquire more data than an evaluation uses

This is accepted for the current small research scope. The extra data is acquisition breadth only and must not expand continuity requirements. Ranged acquisition or caching can be proposed later if scale justifies it.

### Calendar maintenance is explicit

A third-party calendar engine can be stale or have unsupported dates. This design prefers explicit `CALENDAR_UNAVAILABLE` outside supported knowledge and sparse verified corrections over silently inventing session truth. The cost is occasional maintenance of supported coverage/overrides.

### Shared regular-securities calendar behavior may eventually diverge by venue

Venue remains explicit so future calendar routing can split TWSE/TPEX without changing Strategy contracts.

### Raw reported prices can contain corporate-action discontinuities

This is deliberate. Any future analytical adjustment methodology must be specified separately before a production strategy relies on adjusted continuity or total-return semantics.

## Deferred Decisions

- Strategy-specific lookback/history-window policy.
- Corporate-action and total-return adjustment methodology.
- Provider fallback or authoritative price reconciliation.
- Persistent cache/database and ranged acquisition.
- Venue-specific calendar divergence if future evidence requires it.
- Production workflow activation.
- Production strategy assignment.
- Execution simulation.
