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
- incomplete intraday data is observational and cannot mutate formal indicators, model state, market state, or StrategyResult;
- Decision uses the instrument's active assignment;
- analytical Backtest can use the active assignment or an explicit research assignment;
- StrategyResult contains analytical plans, not fills or portfolio state;
- execution simulation is a separate future change;
- failures must remain distinct from valid `NEUTRAL` results;
- public Decision and analytical Backtest artifacts contain the exact disclaimer `僅為個人研究與策略驗證，不構成任何形式之投資建議。`

The implementation is Python 3.11+ and should remain small, typed, testable, and dependency-light. Project tooling will use `uv`, `pytest`, and `ruff`; type annotations are required throughout the core contracts.

## Goals / Non-Goals

### Goals

- Provide one strategy contract used by both Decision and analytical Backtest.
- Make strategy evaluation deterministic for equivalent code revision, configuration, data, and `as_of`.
- Make information timing explicit and mechanically prevent look-ahead.
- Resolve instrument/strategy/parameter configuration before market-data loading.
- Validate normalized completed daily OHLCV before strategy evaluation.
- Support trading-calendar-aware `as_of`, continuity, freshness, and Backtest warm-up behavior.
- Keep an optional intraday overlay separate from the formal StrategyResult.
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
- Inferring intraday touch history from only open/latest snapshot values.

## Decisions

### 1. Use a dependency-inverted application architecture

The implementation will separate pure domain contracts, application orchestration, and infrastructure adapters.

```text
GitHub Actions / future CLI / tests
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
│   ├── service.py
│   ├── as_of.py
│   ├── intraday.py
│   └── artifact.py
├── backtest/
│   ├── service.py
│   └── artifact.py
└── strategies/
    └── registry.py
```

Test-only strategies and fixture market-data adapters stay under `tests/`; they are not production strategies.

**Why:** this keeps the common behavioral contract reusable while allowing future live providers, strategy implementations, and execution simulation to attach at explicit boundaries.

**Alternative rejected:** one large Decision/Backtest module containing config lookup, data fetching, indicators, strategy rules, and output generation. It would make Decision/Backtest equivalence difficult to guarantee and would encourage execution logic to leak into strategy evaluation.

### 2. Represent core values as immutable typed domain models

Core domain values will use typed immutable Python models, preferably frozen dataclasses plus enums/protocols in the framework core. Strategy-specific parameter models may use their own typed validation model behind the Strategy contract.

Key domain contracts:

```text
DataRequirement
├── frequency
├── required_fields
└── minimum_history

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

**Why:** immutable explicit inputs make reproducibility and hidden-state testing straightforward.

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

- declared data requirements;
- deterministic evaluation for equivalent inputs;
- no dependence on real portfolio/execution state;
- valid common MarketState values;
- StrategyResult identity/as-of consistency.

**Why:** Decision and Backtest can call the same contract without requiring a framework-level voting, hybrid, or strategy-specific abstraction.

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

The default repository-backed configuration adapters may use human-readable YAML files, while application code depends only on registry interfaces. A future private/external configuration adapter can replace them without changing resolver behavior.

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

Failure mapping:

```text
CONFIGURATION_FAILED
├── INSTRUMENT_NOT_FOUND
├── ACTIVE_STRATEGY_NOT_CONFIGURED
├── STRATEGY_NOT_FOUND
├── PARAMETER_SET_NOT_FOUND
├── STRATEGY_PARAMETER_MISMATCH
├── INVALID_STRATEGY_PARAMETERS
└── INVALID_AS_OF
```

A configuration failure terminates the application flow before market-data loading.

**Why:** this makes formal assignment, research overrides, and reproducibility explicit while keeping strategy code separate from parameter data.

### 5. Normalize first, validate the normalized completed-daily series second

Market-data providers return provider-specific records through a `MarketDataGateway`. The framework converts them into normalized `DailyBar` values before structural validation.

Normalization may reorder reverse-chronological provider data. Validation applies to the normalized series and verifies:

- valid timestamps;
- unique strictly chronological timestamps;
- required fields;
- positive OHLC values;
- valid OHLC relationships;
- non-negative volume when present;
- strategy-required fields;
- trading-calendar continuity;
- freshness relative to the resolved formal evaluation date;
- minimum-history eligibility.

Formal failures use:

```text
DATA_FAILED
├── DATA_UNAVAILABLE
├── STALE_DATA
├── INSUFFICIENT_HISTORY
├── MISSING_REQUIRED_FIELD
├── INVALID_OHLC
├── DUPLICATE_TIMESTAMP
└── DATA_GAP
```

Additional structural detail can be retained in diagnostics without expanding the stable top-level failure categories.

**Why:** provider ordering is an adapter concern; invalid normalized data is a domain/application failure and must never become `NEUTRAL`.

### 6. Make trading time an injected dependency

Decision `as_of` resolution and Backtest date iteration depend on a `TradingCalendar` and an injected `Clock` rather than directly reading system time.

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

The application output preserves `requested_as_of` separately when the caller supplied a date and resolution changed it.

**Why:** deterministic tests can freeze time/calendar behavior, and session-completion semantics remain separate from provider data.

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

After a successful formal Decision, an optional `IntradayOverlayBuilder` may compare a valid current snapshot with existing analytical entry/exit levels. The overlay may report current relationships such as above/near/at-or-below a level, but it cannot:

- mutate StrategyResult;
- recalculate formal indicators/model state;
- declare a fill;
- claim a price was touched earlier in the day when no intraday history is available.

Snapshot acquisition/validation is best-effort. If formal data and strategy evaluation succeed but the optional snapshot is unavailable or invalid, Decision remains successful and the overlay is omitted or marked unavailable.

**Why:** this preserves formal reproducibility while still making current open/latest information useful during the session.

### 8. Decision is a thin application service around the common evaluator

Decision input remains intentionally small:

```text
symbol
optional as_of
```

Application flow:

```text
DecisionRequest
    |
    v
validate request/as_of
    |
    v
resolve ACTIVE configuration
    |
    v
Strategy.requirements
    |
    v
load + normalize + validate completed daily data
    |
    v
Strategy.evaluate(resolved_as_of)
    |
    v
build formal Decision artifact
    |
    +--> optionally fetch/validate snapshot
             |
             v
          build observational overlay
```

Research strategy/parameter overrides are rejected at the Decision boundary.

A successful Decision contains one formal StrategyResult. A failed Decision contains no valid market state or plan.

### 9. Analytical Backtest is chronological replay of the same evaluator

Backtest accepts a requested range plus an assignment mode:

```text
symbol
mode = ACTIVE | EXPLICIT
strategy?       # required only for EXPLICIT
parameter_set?  # required only for EXPLICIT
start_date
end_date
```

The Backtest application resolves configuration once before loading data. In `ACTIVE`, an active assignment is required. In `EXPLICIT`, a complete compatible strategy+parameter-set pair is required and the instrument does not need an active assignment.

The loader may include pre-roll observations before `start_date`. For each requested trading date T, the evaluator receives a bounded historical view ending at T.

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

Rules:

- WARMUP is valid-but-ineligible and produces no StrategyResult.
- Invalid required data fails the Backtest; it is not skipped.
- Strategy failure at an eligible date is fail-fast.
- A range with zero eligible dates fails with `DATA_FAILED / INSUFFICIENT_HISTORY`.
- A successful Backtest contains at least one StrategyResult.
- No fills, positions, cash, PnL, or execution-derived metrics are created.

**Why:** this gives analytical replay and Decision equivalent semantics while leaving execution interpretation to a future simulator.

### 10. Use one stable application failure envelope

Both Decision and Backtest artifacts use the same top-level failure model:

```text
status = SUCCESS | FAILED

failure? =
├── category: CONFIGURATION_FAILED | DATA_FAILED | STRATEGY_FAILED
├── code: machine-readable code
└── reason: human-readable reason
```

A failed artifact contains no valid StrategyResult represented as successful output. Backtest may retain failure diagnostics, but a partial timeline is never labeled successful.

Strategy-specific internal failures may map to `STRATEGY_FAILED` with a strategy-owned machine-readable code. The common framework does not predefine production model/feature failure codes in this change.

**Why:** applications can expose consistent error semantics without conflating framework failures with strategy-specific details.

### 11. Artifact schemas are explicit and strategy-neutral

Decision artifact conceptual shape:

```text
DecisionArtifact
├── status
├── instrument
├── requested_as_of?
├── resolved_as_of?
├── strategy
├── parameter_set
├── resolved_parameters
├── git_sha
├── data_quality
├── strategy_result?       # success only
├── intraday_overlay?      # optional, observational
├── failure?               # failure only
└── disclaimer
```

Analytical Backtest artifact conceptual shape:

```text
AnalyticalBacktestArtifact
├── status
├── instrument
├── assignment_mode
├── strategy
├── parameter_set
├── resolved_parameters
├── git_sha
├── start_date
├── end_date
├── validation_status
├── timeline[]             # WARMUP markers and eligible StrategyResults
├── failure?               # failure only
└── disclaimer
```

The exact public disclaimer value is a shared constant at the artifact boundary:

```text
僅為個人研究與策略驗證，不構成任何形式之投資建議。
```

Artifacts are serialized as JSON for machine-readable GitHub Actions output. Large Backtest timelines may additionally use JSON Lines internally/output-side, but the semantic contract remains the same.

**Why:** artifacts remain stable across strategy implementations and are easy to validate in behavioral tests.

### 12. Keep GitHub Actions thin and defer live composition

The existing workflows are orchestration scaffolds. They must not contain strategy rules.

This change will align their wording and request contracts with analytical Decision/Backtest semantics, but live workflow composition remains dependent on later concrete market-data/provider configuration and at least one production strategy implementation.

The obsolete Backtest placeholder text referring to fill simulation must be removed. Generated results remain Actions Artifacts and are not committed back to the repository.

**Why:** implementing a fake live provider or fake production strategy merely to make the workflows appear complete would violate the approved scope.

### 13. Test outside-in with vertical slices

Tests are organized around observable application behavior rather than one test file per class.

Test levels:

```text
application acceptance/behavior tests
        |
        +-- Decision scenarios
        +-- Backtest scenarios
        |
contract tests
        +-- Strategy contract
        +-- registry/config adapters
        |
focused unit tests
        +-- normalization/validation
        +-- as_of resolution
        +-- intraday overlay comparisons
```

A minimal test-only Strategy and fixture market-data/calendar adapters provide deterministic application tests. They do not become configurable production strategies.

Every implementation slice follows:

```text
RED behavioral test
-> run and verify failure is the intended missing behavior
-> minimum GREEN implementation
-> REFACTOR while preserving behavior
-> full pytest + ruff + type checks when configured
```

Tooling baseline:

```text
uv
pytest
ruff check .
ruff format --check .
```

A dedicated type checker may be added if configured by the implementation change, but type annotations are mandatory regardless.

## Risks / Trade-offs

### Risk: framework abstractions become too generic before real strategies exist

Mitigation: keep only abstractions required by the four approved capabilities. Strategy-specific indicators, pattern types, forecast models, and hybrid semantics remain outside the common framework until a production strategy requires them.

### Risk: YAML configuration becomes coupled to domain behavior

Mitigation: YAML is only a repository adapter. Resolver/application code consumes registry interfaces and immutable resolved values, allowing future private or external storage without changing semantics.

### Risk: intraday overlay is mistaken for a new trading signal

Mitigation: place it outside StrategyResult, prohibit formal recalculation, use observational terminology, and make snapshot failure non-fatal to the formal Decision.

### Risk: analytical Backtest is mistaken for execution performance

Mitigation: name the capability and artifacts `analytical-backtest`, include StrategyResult/WARMUP timeline only, and explicitly exclude fills, positions, cash, and PnL from models and tests.

### Risk: calendar/session rules depend on market-specific details

Mitigation: inject `TradingCalendar` and `Clock`; this change defines their required behavior but not a concrete exchange-calendar provider.

### Risk: public artifacts expose research configuration/results

Mitigation: artifacts include the required disclaimer and no personal portfolio state. Configuration storage remains adapter-based so a future private execution arrangement can replace repository-backed adapters if desired.

## Migration Plan

This is a greenfield framework change; there is no production Strategy Engine state to migrate.

Implementation should proceed incrementally:

1. Add Python project/test tooling needed for the first behavioral slice.
2. Introduce the minimum domain/application contracts needed to make a Decision walking-skeleton test pass.
3. Add configuration resolution and formal data validation behaviors.
4. Add `as_of` and optional intraday overlay behavior.
5. Add analytical Backtest replay, assignment modes, warm-up, and failure behavior.
6. Add traceable artifact serialization and fixed disclaimer tests.
7. Align request examples and workflow scaffold wording with the new analytical contracts.
8. Run full regression, lint/format, and OpenSpec traceability verification.

No generated analytical result is committed to the repository during this migration.

## Open Questions

The following are deliberately deferred and must not block this change:

- Which concrete historical/intraday market-data provider will be used in GitHub Actions?
- Which concrete trading-calendar implementation/provider will be used for Taiwan markets?
- What production strategy is implemented first: Bollinger or time-series?
- What final corporate-action/adjusted-price methodology will production strategies consume?
- Whether repository-backed active assignments/parameter sets later move to private/external storage.
- Exact Execution Simulator fill, plan-activation, plan-replacement, fee, tax, slippage, and position-state semantics.
