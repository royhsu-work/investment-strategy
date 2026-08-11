# Design — establish-strategy-engine

## Context

The repository currently contains only a minimal Python package, request examples, and placeholder Decision/Backtest GitHub Actions workflows. The change must establish a reusable strategy-analysis foundation before any production Bollinger, time-series, hybrid, market-data-provider, or execution-simulation implementation is added.

The approved specifications require four capabilities to cooperate without duplicating strategy logic:

- `strategy-engine`
- `market-data-validation`
- `decision-evaluation`
- `analytical-backtest`

The design must preserve these boundaries:

- formal strategy analysis uses completed daily OHLCV only;
- every normalized formal daily bar contains open, high, low, close, and volume;
- incomplete intraday data is observational and cannot mutate formal indicators, model state, market state, or StrategyResult;
- Decision uses the instrument's active assignment;
- analytical Backtest can use the active assignment or an explicit research assignment;
- StrategyResult contains analytical plans, not fills or portfolio state;
- execution simulation is a separate future change;
- failures must remain distinct from valid `NEUTRAL` results;
- public Decision and analytical Backtest artifacts contain the exact disclaimer `僅為個人研究與策略驗證，不構成任何形式之投資建議。`

The implementation is Python 3.11+ and should remain small, typed, testable, and dependency-light. Project tooling will use `uv`, `pytest`, `ruff`, and `mypy`; type annotations are required throughout the core contracts.

## Goals / Non-Goals

### Goals

- Provide one strategy contract used by both Decision and analytical Backtest.
- Make strategy evaluation deterministic for equivalent code revision, configuration, data, and `as_of`.
- Make information timing explicit and mechanically prevent look-ahead.
- Resolve instrument/strategy/parameter configuration before market-data loading.
- Validate normalized completed daily OHLCV before strategy evaluation.
- Support trading-calendar-aware `as_of`, continuity, freshness, and Backtest warm-up behavior.
- Keep an optional current-session intraday overlay separate from the formal StrategyResult.
- Produce traceable, machine-readable Decision and analytical Backtest artifacts with consistent failures and the fixed disclaimer.
- Keep infrastructure replaceable so concrete market-data providers and alternative configuration storage can be introduced later without changing domain/application behavior.

### Non-Goals

- Production Bollinger, time-series, or hybrid strategy algorithms.
- Pattern detection, indicator thresholds, model fitting choices, or strategy-specific trading rules.
- Simulated fills, pending orders, execution lifecycle, positions, cash, PnL, returns, drawdown, fees, taxes, slippage, or liquidity modeling.
- Position sizing or use of real holdings, average cost, account cash, or other personal portfolio state.
- Benchmark/reference-instrument behavior.
- A concrete live market-data provider or fallback chain.
- Final corporate-action methodology.
- Provisional intraday recalculation of formal indicators or StrategyResult.
- Comparing the current-session snapshot to an explicitly historical Decision plan.
- Inferring intraday touch history from only open/latest snapshot values.

## Decisions

### 1. Use a dependency-inverted application architecture with explicit request boundaries

The implementation will separate request adapters, pure domain contracts, application orchestration, and infrastructure adapters.

```text
GitHub Actions / future CLI / tests
                |
                v
        Request boundary
        ├─ schema/policy validation
        └─ reject invalid request before application artifact semantics
                |
                v
        Application services
        +--------------------+
        | DecisionService    |
        | BacktestService    |
        +--------------------+
          |       |       |
          v       v       v
      Resolver   Data    Strategy
          |      Service  Registry
          |       |
          v       v
     Config ports / Market-data ports / TradingCalendar / Clock
          ^
          |
      infrastructure adapters
```

Request-boundary rejection is distinct from application failure. Examples include a Decision request containing a research strategy override and a Backtest `EXPLICIT` request that supplies only one member of the strategy/parameter-set pair. These requests do not enter Decision/Backtest application evaluation and do not produce public Decision/Backtest artifacts.

Syntactically valid requests that enter the application can still fail with the canonical application failure categories. Examples include unknown instruments, invalid strategy configuration, future Decision `as_of`, or an invalid Backtest date range.

Domain and application code must not import GitHub Actions, provider SDKs, or execution-simulation code. External data, clock/calendar behavior, and persisted configuration are supplied through ports/adapters.

Recommended package layout:

```text
src/investment_strategy/
├── domain/
│   ├── strategy.py
│   ├── result.py
│   ├── market_data.py
│   ├── configuration.py
│   └── failures.py
├── configuration/
│   ├── resolver.py
│   ├── instruments.py
│   └── parameter_sets.py
├── data/
│   ├── ports.py
│   ├── normalize.py
│   ├── validate.py
│   └── calendar.py
├── decision/
│   ├── request.py
│   ├── service.py
│   ├── as_of.py
│   ├── intraday.py
│   └── artifact.py
├── backtest/
│   ├── request.py
│   ├── service.py
│   └── artifact.py
└── strategies/
    └── registry.py
```

Test-only strategies and fixture market-data adapters stay under `tests/`; they are not production strategies.

### 2. Represent core values as immutable typed domain models

Core domain values will use typed immutable Python models, preferably frozen dataclasses plus enums/protocols in the framework core. Strategy-specific parameter models may use their own typed validation model behind the Strategy contract.

Key domain contracts:

```text
DataFrequency
└── DAILY

DataRequirement
├── frequency: DAILY
├── additional_required_fields
└── minimum_history

DailyBar
├── trading_timestamp
├── open
├── high
├── low
├── close
└── volume

StrategyContext
├── instrument
├── as_of
├── market_data
└── resolved_config

StrategyResult
├── strategy
├── as_of
├── market_state
├── entry_plan
├── exit_plan
├── signals
├── diagnostics
└── reasons

MarketState
├── NEUTRAL
├── ACCUMULATION
├── TREND
└── REVERSAL_RISK
```

This change intentionally supports only completed daily Strategy data. Additional frequencies require a later contract change rather than a generic string value that the data model cannot actually support.

The normalized formal base schema is always OHLCV. `DataRequirement` may declare additional strategy-required fields beyond that mandatory base; it does not make base volume optional.

`StrategyContext` contains no position, cost, cash, execution state, benchmark, or previous strategy runtime state.

Entry and exit are intentionally asymmetric:

```text
EntryPlan
├── levels[]
└── triggers[]

ExitPlan
├── dynamic_levels[]
└── triggers[]
```

A fixed profit target is not required.

Immutability is an architecture requirement for the common domain values used in evaluation: `DataRequirement`, `DailyBar`, `StrategyContext`, `StrategyResult`, `EntryPlan`, `ExitPlan`, and `ResolvedStrategyConfig`. Tests/tasks must verify this property rather than treating it as an undocumented implementation preference.

### 3. Strategy is a stateless contract resolved from code

The common Strategy contract has two responsibilities:

```text
Strategy
├── requirements() -> DataRequirement
└── evaluate(context) -> StrategyResult
```

The code Strategy Registry maps a stable strategy identity to its implementation. Strategy implementations do not persist runtime state between evaluations.

A strategy-specific parameter validator is owned by the strategy implementation. The resolver validates the parameter set against the selected strategy before any market-data loading.

A reusable Strategy Contract Test suite will verify future production strategies for:

- `DAILY` data requirements with explicit additional required fields and minimum history;
- deterministic evaluation for equivalent inputs;
- no dependence on real portfolio/execution state;
- valid common MarketState values;
- StrategyResult identity/as-of consistency.

### 4. Separate three registries and produce one immutable resolved configuration

Configuration resolution has three logical registries:

```text
Instrument Registry
  symbol -> active strategy assignment

Parameter Set Registry
  parameter_set id -> owning strategy + parameters

Code Strategy Registry
  strategy id -> Strategy implementation
```

The first repository-backed configuration adapters **will use human-readable YAML files** for instrument assignments and parameter sets. Application code depends only on registry interfaces, so a future private/external configuration adapter can replace YAML without changing resolver behavior.

Resolution order:

```text
1. resolve instrument
2. choose ACTIVE or EXPLICIT assignment
3. resolve strategy implementation
4. resolve parameter set
5. verify parameter-set ownership
6. validate strategy parameters
7. create immutable ResolvedStrategyConfig
8. only then load market data
```

`ResolvedStrategyConfig` records at least:

```text
symbol
strategy
parameter_set
resolved_parameters
git_sha
```

`resolved_parameters` is an internal execution input and diagnostic value. It is not a mandatory public artifact field in this change; `parameter_set + git_sha` identifies the versioned parameter definition used by a public result.

Configuration failure codes include:

```text
CONFIGURATION_FAILED
├── INSTRUMENT_NOT_FOUND
├── ACTIVE_STRATEGY_NOT_CONFIGURED
├── STRATEGY_NOT_FOUND
├── PARAMETER_SET_NOT_FOUND
├── STRATEGY_PARAMETER_MISMATCH
├── INVALID_STRATEGY_PARAMETERS
├── INVALID_AS_OF
└── INVALID_BACKTEST_RANGE
```

A configuration failure terminates the application flow before market-data loading.

### 5. Separate acquisition failure from acquired-data structural failure

Market-data providers return provider-specific candidate records through a `MarketDataGateway`. The framework then converts them into normalized immutable `DailyBar` values and validates them.

The base normalized `DailyBar` requires open, high, low, close, and volume. A provider record missing any mandatory OHLCV field cannot become a valid formal `DailyBar`.

Failure precedence is explicit:

```text
acquisition
├─ provider/request cannot obtain required historical data
└─ provider returns zero candidate observations
        ↓
DATA_FAILED / DATA_UNAVAILABLE

candidate observations acquired
        ↓
normalization / structural validation
├─ missing mandatory OHLCV       -> MISSING_REQUIRED_FIELD
├─ invalid timestamp             -> VALIDATION_ERROR
├─ invalid OHLC                  -> INVALID_OHLC
├─ negative volume               -> VALIDATION_ERROR
├─ duplicate timestamp           -> DUPLICATE_TIMESTAMP
├─ continuity gap                -> DATA_GAP
└─ other defined structural code
```

An acquired observation does not become `DATA_UNAVAILABLE` merely because validation leaves zero usable observations. This prevents failure codes from depending on validator execution order.

Normalization may reorder reverse-chronological provider data. Validation applies to the normalized series and verifies:

- valid timestamps;
- unique strictly chronological timestamps;
- mandatory OHLCV fields;
- positive OHLC values;
- valid OHLC relationships;
- non-negative volume;
- additional strategy-required fields;
- trading-calendar continuity;
- freshness relative to the resolved formal evaluation date;
- minimum-history eligibility.

Formal data failure codes include:

```text
DATA_FAILED
├── DATA_UNAVAILABLE
├── STALE_DATA
├── INSUFFICIENT_HISTORY
├── MISSING_REQUIRED_FIELD
├── INVALID_OHLC
├── DUPLICATE_TIMESTAMP
├── DATA_GAP
└── VALIDATION_ERROR
```

`VALIDATION_ERROR` is the stable fallback code for structural failures whose specs do not assign a more specific code, including negative volume and an un-normalizable timestamp. Detailed diagnostics may still identify the field-level cause.

### 6. Make trading time an injected dependency

Decision `as_of` resolution and Backtest date iteration depend on a `TradingCalendar` and an injected `Clock` rather than directly reading system time.

The `Clock` returns timezone-aware instants. The applicable `TradingCalendar` owns the market timezone and session-completion rules so `latest completed trading day` is not derived from the runner's local timezone.

The calendar boundary exposes behavior equivalent to:

```text
is_trading_day(date)
previous_trading_day(date)
latest_completed_trading_day(now)
trading_days(start, end)
is_session_complete(date, now)
```

Decision resolution rules:

```text
historical trading date       -> that completed trading date
historical non-trading date   -> previous completed trading date
current trading day, complete -> current completed trading date
current trading day, open     -> previous completed trading date
omitted as_of                 -> latest completed trading date
future date                   -> CONFIGURATION_FAILED / INVALID_AS_OF
```

When the caller explicitly supplies `as_of`, a successful public Decision artifact preserves `requested_as_of` as well as `resolved_as_of`. Failed-artifact requirements are intentionally smaller and are defined separately below.

### 7. Keep formal historical data and intraday snapshot in separate channels

The market-data boundary has two independent concepts:

```text
FormalMarketData
└── completed_daily[]

IntradaySnapshot (optional)
├── session_date
├── open
├── latest_price
└── snapshot_at
```

The Strategy receives only `FormalMarketData` bounded by `resolved_as_of`.

The current-session intraday overlay is available only for the current formal Decision: during an incomplete current session, the request must omit `as_of` or explicitly request the current trading date, and the formal result is based on the latest completed trading day. An explicitly historical Decision never receives today's current-session overlay.

```text
current session T incomplete
AND request is current-formal Decision
        ↓
formal StrategyResult as of T-1
+ optional snapshot for T

explicit historical as_of=H
        ↓
formal StrategyResult as of H
+ no current-session overlay
```

An optional `IntradayOverlayBuilder` may compare a valid current snapshot with existing analytical entry/exit levels. The framework may report direct deterministic relationships such as `ABOVE_LEVEL` or `AT_OR_BELOW_LEVEL`.

The framework does not infer `NEAR` unless a future explicit tolerance rule is defined. It also cannot:

- mutate StrategyResult;
- recalculate formal indicators/model state;
- declare a fill;
- claim a price was touched earlier in the day when no intraday history is available.

Snapshot acquisition/validation is best-effort. If the current formal data and strategy evaluation succeed but the optional snapshot is unavailable or invalid, Decision remains successful and the overlay is omitted or marked unavailable.

### 8. Decision is a thin application service around the common evaluator

Accepted Decision application input remains intentionally small:

```text
symbol
optional as_of
```

A request adapter rejects research strategy/parameter overrides before the application is invoked.

Application flow:

```text
raw request
    |
    v
Decision request boundary
    | invalid override -> reject, no Decision artifact
    v
accepted DecisionRequest
    |
    v
validate application as_of
    |
    v
resolve ACTIVE configuration
    |
    v
Strategy.requirements
    |
    v
load + normalize + validate completed daily OHLCV
    |
    v
Strategy.evaluate(resolved_as_of)
    |
    v
build formal Decision artifact
    |
    +--> if current-formal Decision, optionally fetch/validate snapshot
             |
             v
          build observational overlay
```

A successful Decision contains one formal StrategyResult. An application-level failed Decision contains no valid market state or plan.

### 9. Analytical Backtest is chronological replay of the same evaluator

Accepted Backtest input is:

```text
symbol
mode = ACTIVE | EXPLICIT
strategy?       # both strategy and parameter_set required for EXPLICIT
parameter_set?
start_date
end_date
```

The Backtest request boundary rejects partial `EXPLICIT` assignments before the application is invoked. Such rejected requests do not produce public Backtest artifacts.

Range semantics are intentionally different from Decision `as_of` resolution:

```text
[start_date, end_date] inclusive calendar interval
        ↓
completed trading days inside the interval
        ↓
chronological evaluation points
```

Rules for accepted requests:

- `start_date > end_date` -> `CONFIGURATION_FAILED / INVALID_BACKTEST_RANGE`.
- a future `end_date` -> `CONFIGURATION_FAILED / INVALID_BACKTEST_RANGE` rather than truncation.
- non-trading endpoints are legal and are not clamped outside the interval.
- an incomplete current trading day inside the interval is not an evaluation point.
- an interval containing no completed trading day -> `CONFIGURATION_FAILED / INVALID_BACKTEST_RANGE`.
- an interval with completed trading days that all lack minimum history reaches WARMUP processing and ultimately fails with `DATA_FAILED / INSUFFICIENT_HISTORY` if zero dates become eligible.

The Backtest application resolves configuration once before loading data. In `ACTIVE`, an active assignment is required. In `EXPLICIT`, a complete compatible strategy+parameter-set pair is required and the instrument does not need an active assignment.

The loader may include pre-roll observations before `start_date`. For each completed requested trading date T, the evaluator receives a bounded historical view ending at T.

```text
pre-roll history -----------------------+
                                       |
requested range: T1 -> T2 -> ... -> Tn |
                  |     |          |    |
                  v     v          v    |
               history<=T          |    |
                  |                 |    |
              eligibility           |    |
              /         \           |    |
          WARMUP      Strategy.evaluate
                         |
                         v
                    StrategyResult
```

Invalid required data fails the Backtest rather than being skipped. Strategy failure at an eligible date is fail-fast. A successful Backtest contains at least one StrategyResult and creates no fills, positions, cash, PnL, or execution-derived metrics.

### 10. Use one stable application failure envelope

Decision and Backtest application artifacts use the same canonical application status and failure model:

```text
status = SUCCESS | FAILED

failure? =
├── category: CONFIGURATION_FAILED | DATA_FAILED | STRATEGY_FAILED
├── code: machine-readable code
└── reason: human-readable reason
```

`CONFIGURATION_FAILED`, `DATA_FAILED`, and `STRATEGY_FAILED` are failure categories, not top-level artifact status values.

Request-boundary rejection is outside this envelope and produces no Decision/Backtest application artifact.

A failed application artifact contains no valid StrategyResult represented as successful output. Backtest may retain internal diagnostics about where failure occurred, but a partial timeline is never labeled successful.

Strategy-specific internal failures may map to `STRATEGY_FAILED` with a strategy-owned machine-readable code. The common framework does not predefine production model/feature failure codes in this change.

### 11. Keep failed public artifact contracts minimal

Successful artifacts carry the full traceability fields required by the capability specs. Failed artifacts intentionally expose a smaller stable identity contract rather than making public field presence depend on how far internal processing progressed.

Decision successful artifact conceptual shape:

```text
DecisionArtifact SUCCESS
├── status
├── instrument
├── requested_as_of?       # when caller explicitly supplied as_of
├── resolved_as_of
├── strategy
├── parameter_set
├── git_sha
├── data_quality
├── strategy_result
├── intraday_overlay?      # only current-formal Decision, optional
└── disclaimer
```

Decision failed artifact minimum shape:

```text
DecisionArtifact FAILED
├── status
├── instrument
├── requested_as_of?       # preserve caller input when supplied
├── git_sha
├── failure
└── disclaimer
```

`resolved_as_of`, `strategy`, `parameter_set`, and `data_quality` are not mandatory public fields on a failed Decision even if internal processing already resolved them. They may exist only as non-contract diagnostics in a future change. Unresolved metadata is never fabricated.

Analytical Backtest successful artifact conceptual shape:

```text
AnalyticalBacktestArtifact SUCCESS
├── status
├── instrument
├── assignment_mode
├── strategy
├── parameter_set
├── git_sha
├── start_date
├── end_date
├── validation_status
├── timeline[]
└── disclaimer
```

Analytical Backtest failed artifact minimum shape:

```text
AnalyticalBacktestArtifact FAILED
├── status
├── instrument
├── assignment_mode
├── start_date
├── end_date
├── git_sha
├── failure
└── disclaimer
```

`strategy`, `parameter_set`, `validation_status`, and partial timeline content are not mandatory public fields on a failed Backtest even if internal processing already produced them. Public artifacts do not require a duplicate `resolved_parameters` payload; the versioned `parameter_set + git_sha` pair is the public reproducibility reference for successful results.

The exact public disclaimer value is a shared constant at the artifact boundary:

```text
僅為個人研究與策略驗證，不構成任何形式之投資建議。
```

Artifacts are serialized as JSON for machine-readable GitHub Actions output.

### 12. Keep GitHub Actions thin and defer live composition

The existing workflows are orchestration scaffolds. They must not contain strategy rules.

This change will align request examples, README examples, and workflow wording with analytical Decision/Backtest semantics, but live workflow composition remains dependent on later concrete market-data/provider configuration and at least one production strategy implementation.

The obsolete Backtest placeholder text referring to fill simulation must be removed. Generated results remain Actions Artifacts and are not committed back to the repository.

### 13. Test outside-in with vertical slices and explicit provenance

Tests are organized around observable application behavior rather than one test file per class.

Test levels:

```text
request-contract tests
        +-- Decision override rejection
        +-- Backtest partial EXPLICIT rejection

application acceptance/behavior tests
        +-- Decision scenarios
        +-- Backtest scenarios

contract tests
        +-- Strategy contract
        +-- registry/config adapters

focused unit tests
        +-- normalization/validation
        +-- as_of and range resolution
        +-- intraday overlay eligibility/comparisons
        +-- immutable domain values
```

A minimal test-only Strategy and fixture market-data/calendar adapters provide deterministic application tests. They do not become configurable production strategies.

Every implementation slice follows:

```text
RED behavioral test
-> run and verify failure is the intended missing behavior
-> minimum GREEN implementation
-> REFACTOR while preserving behavior
-> full pytest + ruff + mypy verification
```

Traceability uses two legitimate provenance paths:

```text
Behavior / Product
proposal -> capability spec -> design -> task

Engineering / Governance
openspec/config.yaml -> design/testing rule -> task
```

Lint, type checks, immutable-model architecture checks, strict OpenSpec validation, and similar governance work therefore do not require artificial capability requirements unless they affect an external contract.

Tooling baseline:

```text
uv
pytest
ruff check .
ruff format --check .
mypy src tests
```

## Risks / Trade-offs

### Risk: framework abstractions become too generic before real strategies exist

Mitigation: support only DAILY formal data in this change, require a concrete OHLCV base schema, and keep strategy-specific indicators, pattern types, forecast models, and hybrid semantics outside the common framework until a production strategy requires them.

### Risk: YAML configuration becomes coupled to domain behavior

Mitigation: YAML is the first repository adapter, not the domain contract. Resolver/application code consumes registry interfaces and immutable resolved values, allowing future private or external storage without changing semantics.

### Risk: request rejection is confused with application failure

Mitigation: validate structural request policy before invoking Decision/Backtest services. Rejected override/partial-assignment requests produce no application artifact; accepted requests use the canonical application failure envelope if later evaluation fails.

### Risk: intraday overlay is mistaken for a new trading signal or attached to historical analysis

Mitigation: place it outside StrategyResult, allow it only for the current formal Decision, prohibit formal recalculation, use observational terminology, prohibit implicit `NEAR` without a defined tolerance, and make snapshot failure non-fatal to the formal Decision.

### Risk: analytical Backtest is mistaken for execution performance

Mitigation: name the capability and artifacts `analytical-backtest`, include StrategyResult/WARMUP timeline only, and explicitly exclude fills, positions, cash, and PnL from models and tests.

### Risk: calendar/session rules depend on market-specific details

Mitigation: inject `TradingCalendar` and timezone-aware `Clock`; this change defines their required behavior but not a concrete exchange-calendar provider.

### Risk: public artifact schemas expand based on internal progress

Mitigation: keep failed-artifact identity fields deliberately minimal and stable. Internal resolved values do not automatically become public contract fields.

### Risk: public artifact reproducibility is duplicated across fields

Mitigation: keep resolved parameter values internal and use versioned `parameter_set + git_sha` as the public parameter-definition reference for successful results.

## Migration Plan

This is a greenfield framework change; there is no production Strategy Engine state to migrate.

Implementation should proceed incrementally:

1. Add Python project/test tooling needed for the first behavioral slice.
2. Introduce the request boundaries and minimum immutable domain/application contracts needed to make a Decision walking-skeleton test pass.
3. Add YAML-backed configuration resolution and mandatory formal daily OHLCV validation behaviors.
4. Add `as_of` and current-only optional intraday overlay behavior.
5. Add analytical Backtest request policy, range validation, replay, assignment modes, warm-up, and failure behavior.
6. Add traceable success/failure artifact serialization and fixed disclaimer tests.
7. Align README, request examples, and workflow scaffold wording with the approved analytical contracts.
8. Run full regression, lint/format/type checks, strict OpenSpec validation, and traceability verification.

No generated analytical result is committed to the repository during this migration.

## Open Questions

The following are deliberately deferred and must not block this change:

- Which concrete historical/intraday market-data provider will be used in GitHub Actions?
- Which concrete trading-calendar implementation/provider will be used for Taiwan markets?
- What production strategy is implemented first: Bollinger or time-series?
- What final corporate-action/adjusted-price methodology will production strategies consume?
- Whether repository-backed active assignments/parameter sets later move to private/external storage.
- Exact Execution Simulator fill, plan-activation, plan-replacement, fee, tax, slippage, and position-state semantics.
