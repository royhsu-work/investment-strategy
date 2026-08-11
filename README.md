# Investment Strategy

以 OpenSpec 驅動的 Python 投資策略研究專案。此 repository 的核心目標是建立可重現、無 look-ahead 的分析型 Strategy Engine，讓正式 Decision 與歷史 analytical Backtest 共用同一份 Strategy 實作。

> 公開 Decision / Backtest Artifact 固定包含：`僅為個人研究與策略驗證，不構成任何形式之投資建議。`

## 核心邊界

- 正式 Strategy input 僅使用**已完成的 daily OHLCV**；每根 `DailyBar` 必須有 open/high/low/close/volume。
- incomplete current-session snapshot 與正式歷史資料分離，只能成為 Decision 的 observational intraday overlay。
- Decision 只使用 instrument 的 active strategy + parameter set，不接受研究用 override。
- analytical Backtest 可使用 `ACTIVE` 或完整的 `EXPLICIT` strategy + parameter-set pair。
- Decision 與 Backtest 共用相同 Strategy evaluator；任何 evaluation at T 只能看到 T 以前可得資訊。
- `NEUTRAL` 是合法 StrategyResult，不是 configuration/data/strategy failure 的替代值。
- 本 change **不**模擬 fills、positions、cash、PnL、returns、drawdown、fees、taxes、slippage 或 pending execution lifecycle。
- live market-data provider、Taiwan trading-calendar adapter 與 production strategy 仍刻意延後。

## Architecture

```text
request adapter
   │  schema / policy validation
   │  invalid shape -> reject, no public application artifact
   ▼
DecisionService / BacktestService
   ├─ calendar / clock
   ├─ StrategyConfigResolver
   ├─ market-data acquisition + normalization + validation
   └─ shared Strategy evaluator
          │
          ▼
      StrategyResult
```

```text
src/investment_strategy/
├── domain/          # immutable common contracts and failures
├── configuration/   # registry ports, YAML adapters, resolver
├── data/            # data/calendar ports, normalization, validation
├── strategies/      # code Strategy registry only; no production strategy yet
├── decision/        # request boundary, as-of, intraday overlay, artifact, service
└── backtest/        # strict request union, analytical replay, artifact, service
```

## Strategy contract

A Strategy is stateless and declares exactly the supported formal requirement:

```text
DataRequirement
├── frequency = DAILY
└── minimum_history
```

Evaluation inputs are explicit:

```text
StrategyContext
├── instrument
├── as_of
├── completed daily OHLCV bounded to as_of
└── ResolvedStrategyConfig
```

`StrategyContext` does not contain real holdings, average cost, cash, benchmark, execution state, or previous runtime state.

Common `MarketState` is restricted to:

- `NEUTRAL`
- `ACCUMULATION`
- `TREND`
- `REVERSAL_RISK`

Implementation-specific regimes remain under `signals` or `diagnostics`.

## Configuration resolution

Configuration resolves before any market-data load:

```text
1. instrument
2. ACTIVE or EXPLICIT assignment
3. code Strategy
4. parameter set
5. parameter-set ownership
6. Strategy-owned parameter validation
7. immutable ResolvedStrategyConfig
8. market-data acquisition
```

Repository YAML adapters live behind registry interfaces. `config/instruments.yaml` and `config/parameter_sets.yaml` are intentionally empty until a production strategy exists; the framework does not create a fake production assignment solely to make workflow scaffolds appear live.

## Market-data semantics

Acquisition and structural failures are distinct:

```text
provider failure / zero candidates
  -> DATA_FAILED / DATA_UNAVAILABLE

candidate acquired, then invalid
  -> structural code such as
     VALIDATION_ERROR
     MISSING_REQUIRED_FIELD
     INVALID_OHLC
     DUPLICATE_TIMESTAMP
     DATA_GAP
     STALE_DATA
```

For historical `Decision(as_of=T)` the framework first normalizes timestamps enough to establish temporal position, excludes timestamp-known rows after T, and only then validates their non-temporal OHLCV structure. Therefore a known T+1 row with invalid OHLC cannot contaminate the Decision at T; an un-normalizable timestamp can still fail because its temporal position is unknowable.

Trading-day continuity and freshness are based on the injected `TradingCalendar`, not calendar-day continuity. Weekends/holidays are not gaps.

## Decision request

Repository request shape:

```json
{
  "symbol": "00733",
  "as_of": "2026-08-10"
}
```

`as_of` is optional. Research fields such as `strategy` or `parameter_set` are rejected by the request boundary and produce no public Decision artifact.

Decision date resolution is calendar-only. A future accepted `as_of` is an application failure `CONFIGURATION_FAILED / INVALID_AS_OF`; missing data never causes silent fallback to an older date.

Successful artifact shape:

```json
{
  "status": "SUCCESS",
  "instrument": "00733",
  "requested_as_of": "2026-08-10",
  "resolved_as_of": "2026-08-10",
  "strategy": "strategy-id",
  "parameter_set": "parameter-set-id",
  "git_sha": "commit-sha",
  "data_quality": "PASS",
  "strategy_result": {
    "strategy": "strategy-id",
    "as_of": "2026-08-10",
    "market_state": "NEUTRAL",
    "entry_plan": {"levels": [], "triggers": []},
    "exit_plan": {"dynamic_levels": [], "triggers": []},
    "signals": {},
    "diagnostics": {},
    "reasons": []
  },
  "disclaimer": "僅為個人研究與策略驗證，不構成任何形式之投資建議。"
}
```

`requested_as_of` 只有在 caller 明確提供時才需要存在。Failed Decision 使用穩定最小 identity，不因內部已解析多少 metadata 而擴張 public contract。

## Current-only intraday overlay

若 current trading session 尚未完成，而且 request 是 omitted `as_of` 或 explicitly current date，formal StrategyResult 仍以 previous completed trading day 為 `resolved_as_of`。若 current snapshot 有效，可另外附加：

- session date
- open
- latest price
- snapshot time
- current price 對既有 analytical levels 的 deterministic relationship

Overlay 不會：

- 改寫 StrategyResult、indicators、model state 或 MarketState；
- 宣告 fill；
- 在未定義 tolerance 時輸出 `NEAR`；
- 只有 open/latest 時聲稱「今天早些時候曾 touch 某價位」；
- 附加到 explicitly historical Decision。

snapshot unavailable/invalid 不會讓 formal Decision 失敗。

## Analytical Backtest request

Backtest request 是 exact discriminated union。

`ACTIVE`：

```json
{
  "symbol": "00733",
  "mode": "ACTIVE",
  "start_date": "2026-01-01",
  "end_date": "2026-08-01"
}
```

`EXPLICIT`：

```json
{
  "symbol": "00733",
  "mode": "EXPLICIT",
  "strategy": "strategy-id",
  "parameter_set": "parameter-set-id",
  "start_date": "2026-01-01",
  "end_date": "2026-08-01"
}
```

`ACTIVE` 若帶 strategy/parameter-set、`EXPLICIT` 若缺任一欄位，都由 request boundary 拒絕；不借用 active assignment、不忽略 supplied fields、不自動切 mode，也不產生 public Backtest artifact。

`start_date` / `end_date` 是 inclusive calendar interval。只 replay 區間內 completed trading days；non-trading endpoints 不 clamp 到區間外，incomplete current day 不是 evaluation point。Future end date、start > end、或區間完全沒有 completed trading day，會回 `CONFIGURATION_FAILED / INVALID_BACKTEST_RANGE`。

Backtest 可讀取 start date 之前的 pre-roll history。requested early dates若資料有效但不足 `minimum_history`，timeline 標示 `WARMUP` 且不執行 Strategy。若所有 requested completed trading days 都是 WARMUP，Backtest 以 `DATA_FAILED / INSUFFICIENT_HISTORY` 失敗，而不是成功輸出空 timeline。

Successful analytical Backtest Artifact 含 assignment mode、strategy、parameter set、Git revision、requested range、validation status，以及只包含 `WARMUP` / `StrategyResult` 的 analytical timeline；沒有任何 execution-derived fields。

## Failure envelope

Accepted application request 的失敗統一為：

```json
{
  "status": "FAILED",
  "failure": {
    "category": "CONFIGURATION_FAILED | DATA_FAILED | STRATEGY_FAILED",
    "code": "MACHINE_READABLE_CODE",
    "reason": "human-readable reason"
  }
}
```

Request-boundary rejection 不屬於這個 envelope，因為 application 尚未開始，也不產生 Decision/Backtest public artifact。

## GitHub Actions

- `.github/workflows/decision.yml`：formal Decision orchestration scaffold。
- `.github/workflows/backtest.yml`：analytical Backtest orchestration scaffold；不含 fill simulation。
- `.github/workflows/quality.yml`：`uv run pytest`、`ruff check`、`ruff format --check`、`mypy src tests`。
- `.github/workflows/openspec-validate.yml`：對 `establish-strategy-engine` 執行 strict OpenSpec validation。

Generated analytical results 應上傳 Actions Artifacts，不 commit 回 repository。Live provider/calendar/production strategy composition 保持 deferred。

## Local verification

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
```

本 change 的最終驗收還包含：

```bash
openspec validate establish-strategy-engine --type change --strict --json --no-interactive
```

## Deferred work

- production Bollinger swing strategy
- production time-series strategy
- hybrid strategy（待研究支持）
- concrete historical/intraday provider and fallback policy
- concrete Taiwan trading calendar adapter
- final corporate-action methodology
- execution simulator：fills / pending orders / positions / cash / PnL / fees / taxes / slippage
