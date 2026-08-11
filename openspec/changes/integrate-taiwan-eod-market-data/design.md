# Design — integrate-taiwan-eod-market-data

## Context

The repository already has provider-neutral Strategy, Decision, Backtest, market-data normalization/validation, Clock, and TradingCalendar contracts. What is missing is a production-capable path from a configured Taiwan instrument to completed EOD OHLCV and an exchange-aware Taiwan session calendar.

The approved proposal/specifications constrain this change to facts that have already occurred:

- formal Strategy evaluation consumes completed daily OHLCV only;
- this change does not introduce intraday, realtime, prediction, execution, or production strategy behavior;
- `TWSE` and `TPEX` are the supported provider-neutral listing venues;
- provider SDK types and provider ticker syntax must not leak into Strategy, Decision, or Backtest contracts;
- source-native provider OHLCV is the formal EOD acquisition basis;
- adapter-controlled automatic/back adjustment, `Adj Close` substitution, dividend/capital-gain adjustment, repair, interpolation, or synthesis must not silently rewrite formal history;
- this capability does not guarantee exchange-raw nominal historical price scale across splits or consolidations;
- provider acquisition breadth must not silently become a full-instrument-lifetime continuity requirement;
- Strategy-specific history-window/lookback policy remains outside this change;
- Taiwan market-date/session semantics must be timezone-aware and exchange-session-aware;
- calendar dates that the configured engine cannot establish must fail explicitly rather than being misclassified as missing market data;
- existing normalization, structural validation, freshness, no-look-ahead, minimum-history, and Backtest WARMUP semantics remain authoritative.

The implementation remains Python 3.11+, typed, dependency-inverted, and testable without requiring live network access in the default test suite.

## Goals / Non-Goals

### Goals

- Add provider-neutral listing-venue identity to configured instruments.
- Fail missing or unsupported venue configuration before market-data loading.
- Pass provider-neutral market-data identity through the application/data boundary without exposing venue details to Strategy implementations.
- Provide one concrete completed-daily OHLCV adapter suitable for Taiwan-listed instruments while keeping it replaceable.
- Preserve the selected provider's source-native OHLCV fields without adapter-controlled analytical transformation.
- Prevent provider fetch breadth from defining continuity-validation scope.
- Provide Taiwan regular-securities trading-session behavior for TWSE and TPEx-listed instruments.
- Make calendar-engine unsupported dates an explicit data failure.
- Preserve existing Decision/Backtest public request and artifact contracts.
- Keep default automated tests deterministic and independent of live provider availability.

### Non-Goals

- Intraday/realtime price acquisition or overlays.
- Forecasting or future-return estimation.
- Production strategy algorithms or active production assignments.
- Defining a Strategy-specific lookback/history-window contract.
- Canonical exchange-raw historical price reconstruction across splits/consolidations.
- Corporate-action adjusted analytical series or total-return methodology.
- Cross-provider validation/fallback.
- Persistent market-data storage or caching.
- Raw provider-data publication.
- Production GitHub Actions activation.
- Execution/fill/portfolio simulation.
- Maintaining a repository copy of every historical Taiwan trading session.
- Automatically discovering future or newly announced exchange-calendar changes.
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

The formal price-basis boundary is intentionally **source-native**, not exchange-raw:

- native provider `Open`/`High`/`Low`/`Close`/`Volume` are passed through as candidate OHLCV;
- `auto_adjust=false` and `back_adjust=false` mean the adapter itself does not apply another OHLC adjustment;
- `Adj Close` is not substituted for `Close`;
- adapter-controlled dividend/capital-gain adjustment is not applied;
- provider-native historical conventions around splits/consolidations are not reinterpreted as exchange-raw truth by this capability;
- any future exchange-raw reconstruction, split normalization, or total-return series is a separate analytical methodology.

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
- substitute `Adj Close` or another adjusted analytical field into formal OHLCV;
- apply an additional adapter-controlled OHLC transformation;
- enable provider-side price repair;
- fall back to another provider.

Missing/invalid candidate fields remain visible to the existing normalization and structural validation behavior. Numeric normalization must also reject non-finite provider values such as `NaN`, `+Infinity`, and `-Infinity` through the canonical data-failure envelope rather than allowing implementation exceptions to escape.

### 6. Use a replaceable Taiwan regular-securities calendar adapter

Application code continues to depend only on `TradingCalendar`.

The first implementation uses a pinned `exchange_calendars` XTAI calendar as the session engine for Taiwan regular-securities dates and keeps the dependency inside infrastructure. TWSE and TPEx regular listed-securities/ETF evaluation share this behavior in this change, guarded by deterministic official-schedule regression fixtures for both venues.

The adapter owns `Asia/Taipei` market timezone behavior.

Regression fixtures cover at least:

- normal weekday session;
- weekday exchange holiday;
- historical additional Saturday trading session;
- historical/declared exceptional full-market closure;
- non-Taipei runner timezone;
- previous/latest completed trading-day behavior.

A date must first be a trading session before it can be considered a completed trading session; historical holidays and exceptional closures therefore return false from session-completion queries.

If later evidence proves TWSE and TPEx regular-session calendars diverge materially, a later change can route venue-specific calendar implementations without changing Strategy.

### 7. Calendar support follows the configured engine's actual supported range

This change does not hard-code a separate earliest or latest calendar date and does not maintain a duplicate official calendar for every session.

The supported coverage rule is:

```text
configured pinned calendar engine can establish session status
  -> supported calendar date

configured calendar engine cannot establish session status
because the date is outside its supported bounds or the engine cannot answer
  -> DATA_FAILED / CALENDAR_UNAVAILABLE
```

The adapter may expose or inspect the selected engine's actual session bounds as an infrastructure detail, but those concrete dates are not part of the public Strategy/Decision/Backtest contract.

`CALENDAR_UNAVAILABLE` occurs before `DATA_GAP` or `STALE_DATA`, because those market-data failures require a reliable calendar answer that a session was expected.

Existing application request policy already rejects future Decision/Backtest evaluation dates. Therefore this change does not define a future-calendar promise or require the adapter to certify sessions beyond an accepted current/historical evaluation.

### 8. Official evidence is used for regression and real corrections, not per-date certification

Within the configured engine's supported range, the engine is the initial session source for application behavior. The repository does not require official evidence for every individual date merely to use that supported engine answer.

Official TWSE/TPEx regular-market evidence is required for:

- representative deterministic regression fixtures used to validate the chosen engine for this project;
- any production override added because an actual engine-versus-official discrepancy is identified.

Overrides remain sparse and discrepancy-driven:

- do not duplicate the full historical calendar;
- do not add an override when the engine already matches the verified fixture;
- if a real discrepancy is identified, add only the affected date(s) with deterministic evidence of expected open/closed truth;
- the override mechanism and precedence behavior must be testable even when this implementation finds no real discrepancy;
- no production override entry is required solely to satisfy the task when no actual discrepancy is found.

A newly announced exceptional closure/session that has not yet reached the pinned engine or repository corrections is not automatically discoverable by this offline calendar adapter. Once such a discrepancy is known and relevant to supported evaluation, dependency update or an explicit verified override is the maintenance path.

### 9. Use a conservative current-day completion boundary

Formal EOD eligibility must never include an in-progress session. The calendar adapter treats the current Taiwan trading date as formally complete only after 13:33 Asia/Taipei.

This only establishes calendar eligibility. It does not claim provider EOD data is already published.

```text
calendar says T complete
provider still ends at T-1
  -> DATA_FAILED / STALE_DATA
```

The application never moves `resolved_as_of` backward to match provider availability.

### 10. Keep calendar source and market-data source independent

```text
MarketDataGateway
  -> completed EOD candidates

TradingCalendar
  -> expected sessions / completion semantics
```

Provider-returned dates do not define exchange sessions. The calendar does not synthesize market-data observations.

Only when session knowledge is available from the configured calendar source may missing provider observations become `DATA_GAP` or `STALE_DATA`.

### 11. Default tests are offline and external availability is not a correctness oracle

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

### 12. Do not activate public Decision/Backtest workflows yet

The repository still has no production strategy assignment. This change makes the concrete EOD adapter/calendar composable but leaves Decision/Backtest workflows as scaffolds.

No real active strategy assignment is added to `config/instruments.yaml`.

## Requirement Traceability

| Requirement area | Design decision |
| --- | --- |
| Canonical instrument identity / provider isolation | 1–3 |
| TWSE/TPEX support / venue validation | 1–2 |
| Completed daily OHLCV | 3, 5 |
| Source-native price basis / no adapter transformation | 3, 5 |
| Provider breadth does not define continuity scope | 3–4 |
| Strategy-specific history policy remains separate | 4 |
| Taiwan timezone / completed session | 6, 9 |
| Actual sessions / holidays / additional sessions / closures | 6, 8–10 |
| Calendar unsupported coverage / `CALENDAR_UNAVAILABLE` | 7, 10 |
| Official regression evidence / sparse corrections | 6, 8 |
| Existing `DATA_UNAVAILABLE` / `STALE_DATA` semantics | 3, 5, 9–10 |
| No provider SDK leakage | 1–3 |
| No production workflow activation | 12 |

## Risks / Trade-offs

### yfinance is an external unofficial market-data implementation

Provider outages/schema changes remain possible. Isolation behind `MarketDataGateway`, explicit call parameters, offline tests, and canonical data failures limit the blast radius.

### Source-native OHLC may encode provider corporate-action conventions

The capability deliberately preserves provider-native OHLCV without claiming exchange-raw nominal history or total-return semantics. This keeps EOD acquisition independent from corporate-action analytics, but it means a future production Strategy that is sensitive to long-horizon price continuity must define and validate its own corporate-action/price-basis methodology before relying on that continuity.

### `period=max` may reacquire more data than an evaluation uses

This is accepted for the current small research scope. The extra data is acquisition breadth only and must not expand continuity requirements. Ranged acquisition or caching can be proposed later if scale justifies it.

### Calendar correctness depends on the pinned engine plus sparse project corrections

The project does not duplicate or independently certify every historical session. Representative official fixtures detect important incompatibilities, and confirmed discrepancies can be corrected explicitly. The trade-off is that a newly announced or previously unknown calendar discrepancy may require a dependency update or repository override once discovered.

### Shared regular-securities calendar behavior may eventually diverge by venue

Venue remains explicit so future calendar routing can split TWSE/TPEX without changing Strategy contracts.

## Deferred Decisions

- Strategy-specific lookback/history-window policy.
- Exchange-raw historical reconstruction, corporate-action, and total-return analytical methodology.
- Provider fallback or authoritative price reconciliation.
- Persistent cache/database and ranged acquisition.
- Venue-specific calendar divergence if future evidence requires it.
- Automatic ingestion of newly announced exchange-calendar changes.
- Production workflow activation.
- Production strategy assignment.
- Execution simulation.
