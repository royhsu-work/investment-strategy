# Investment Strategy

以歷史市場資料產生交易計畫，並使用相同策略核心進行歷史回測。

本專案的開發與執行方式：

- **AI-assisted development**：使用 ChatGPT Chat / Work，並依循 OpenSpec 流程進行規格驅動的 AI-assisted development。
- **Serverless-style execution**：以 GitHub Actions 執行事件或排程觸發的 Decision、Backtest 與驗證工作，無需維運常駐伺服器。

> 核心原則：Decision 與 Backtest 必須共用同一份策略實作。回測不能使用另一套簡化規則。

## 免責聲明

本專案及其產生之所有內容僅供個人研究、學習與策略驗證用途，不構成任何形式之投資建議、投資招攬、證券推薦或買賣依據。

本專案所呈現之市場資料、分析結果、價格區間、交易訊號及回測結果，均可能受到資料品質、模型假設、參數設定及市場變化影響，亦可能存在錯誤、延遲或不完整之情形。

任何投資決策均應由使用者自行評估並承擔相關風險。本專案作者不對依據本專案內容所進行之任何投資或交易行為，以及因此產生之損益負責。

公開的 Decision / Backtest Artifact 固定包含簡短免責聲明：`僅為個人研究與策略驗證，不構成任何形式之投資建議。`

---

## Strategy Engine baseline

以 OpenSpec 驅動的 Python 投資策略研究專案。Strategy Engine 已建立為 repository 的 canonical analytical baseline，提供可重現、無 look-ahead 的正式 Decision 與歷史 analytical Backtest，且兩者共用同一份 Strategy 實作。對 externally observable contract 的後續變更應透過新的 OpenSpec change lifecycle 進行。

## Taiwan EOD market-data support

- Instrument configuration 使用 provider-neutral `symbol + listing_venue` identity；目前支援 `TWSE` 與 `TPEX`。`.TW` / `.TWO` 等 provider ticker syntax 只存在於 concrete infrastructure adapter，不進入 StrategyContext。
- yfinance adapter 取得 provider/source-native daily OHLCV，明確停用 adapter-controlled `auto_adjust`、`back_adjust`、`repair`、actions 與 rounding；正式價格基礎直接使用 provider native `Open`/`High`/`Low`/`Close`/`Volume`，不以 `Adj Close` 取代 `Close`，也不宣稱跨 split/consolidation 的歷史價格等同交易所 raw nominal scale。
- provider `period=max` 只代表 acquisition breadth，不定義 analytical history 或 continuity scope。Backtest continuity 以 caller 已選定的 formal replay range 驗證；Decision 在尚未有 Strategy lookback/history-window contract 前不從 provider 第一筆資料自行發明 continuity 起點。
- Taiwan regular-securities calendar 由 pinned `exchange_calendars` XTAI adapter 提供，市場日期使用 `Asia/Taipei`，current session 採保守 `13:33 Asia/Taipei` 完成邊界。超出 engine 實際可建立的 coverage 時回 `DATA_FAILED / CALENDAR_UNAVAILABLE`，不改寫為 `DATA_GAP` 或 `STALE_DATA`。
- repository calendar overrides 是 sparse、discrepancy-driven 的 precedence layer；只有官方 TWSE/TPEx regular-market evidence 證實 XTAI discrepancy 時才新增 production override，不維護第二份完整歷史交易日曆。
- representative official regression evidence 用於驗證正常交易日、休市日、歷史額外週六交易與全市場例外休市等 calendar semantics；它不是完整 calendar dataset。
- 仍 deferred：Strategy-specific lookback contract、corporate-action methodology、fallback/cache、production strategy/workflow activation、intraday acquisition、prediction 與 execution state。

## 核心邊界

- 正式 Strategy input 僅使用**已完成的 daily OHLCV**；每根 `DailyBar` 必須有 open/high/low/close/volume。
- incomplete current-session snapshot 與正式歷史資料分離，只能成為 Decision 的 observational intraday overlay。
- Decision 只使用 instrument 的 active strategy + parameter set，不接受研究用 override。
- analytical Backtest 可使用 `ACTIVE` 或完整的 `EXPLICIT` strategy + parameter-set pair。
- Decision 與 Backtest 共用相同 Strategy evaluator；任何 evaluation at T 只能看到 T 以前可得資訊。
- `NEUTRAL` 是合法 StrategyResult，不是 configuration/data/strategy failure 的替代值。
- 目前 analytical baseline **不**模擬 fills、positions、cash、PnL、returns、drawdown、fees、taxes、slippage 或 pending execution lifecycle。

## Development lifecycle

Repository 採用下列穩定開發流程；這是 repository-level process，不記錄個別 PR 的歷史 review round、暫時性 finding、commit SHA 或 test count。

```text
Requirement / research direction
        ↓
OpenSpec change
proposal → design → specs → tasks
        ↓
Lead review / approval
        ↓
Implementation branch
agent/<change>  (branch convention)
        ↓
Draft PR
        ↓
Implementation + tests + quality/OpenSpec validation
        ↓
Lead implementation review
        ↓
Ready / merge to main
        ↓
Merged-PR archive classifier
same-repository PR changed files + active OpenSpec state
at the triggering merge snapshot
        ↓
0 active touched / incomplete
        → successful no-op
>1 active touched
        → fail ambiguous
exactly 1 active touched + Complete
        ↓
agent/archive-<change>  (archive workflow-created branch)
        ↓
strict validate active change
        ↓
openspec archive <change> --yes
        ↓
strict validate resulting canonical specs
        ↓
commit/push archive branch
        ↓
Archive PR / review / merge
        ↓
canonical openspec/specs + dated archive audit trail
```

High-level responsibilities:

- **Lead**：定義 scope 與 acceptance criteria，review/approve OpenSpec，執行 implementation review，決定 change completion 與 archive。
- **Executor**：依核准 change 實作、維持 scope boundary、完成 tests/validation、建立 Draft PR，並處理 review findings。
- **Repository automation**：執行 Python quality gates、project-level OpenSpec validation，以及 state-driven OpenSpec archive workflow。

`agent/<change>` 是 implementation branch 的 repository convention；normal archive routing 不依賴 branch name。Normal automatic archive 只支援 **same-repository** PR，並由 triggering merge snapshot 中仍 active 的 OpenSpec state，搭配 merged PR changed files 中的 `openspec/changes/<change>/...` 決定 candidate。`agent/archive-<change>` 由 archive workflow 建立；existing archive branch 會 fail loudly，automation 不會 force-push 或重用該 branch。`agent/archive-*` PR merge 一律 no-op，避免 archive recursion。

`Complete` 是 repository-level implementation completion signal。一個 change 可以跨多個 proposal / implementation / review-correction PR，但仍有必要工作未 merge 時不得把 active change 留成 `Complete`。使該 change 在 merged `main` 呈現 `Complete` 的 final implementation PR 必須同時更新 `openspec/changes/<change>/`，讓 completion transition 可由 merged-diff classifier 觀察。Normal path 對 0 個 active candidate 或 incomplete change 成功 no-op；一次觸及多個 active changes 則視為 ambiguous lifecycle scope 並失敗，不自動猜測。每個 normal PR run 都以該 PR 的 **triggering merge snapshot** 評估，不重新讀取 runner 啟動時較新的 moving `main`。

Fork PR 不屬於 normal automatic archive 支援範圍。Merged fork PR 若沒有 active OpenSpec candidate，維持 ordinary no-op；若 changed files 原本會形成 active OpenSpec candidate，workflow 必須明確 fail 為 `unsupported automatic source`，不得嘗試以 fork `pull_request` 的 read-only token 建立 archive branch，也不得把 archive 視為成功。這類 change 改走 base-repository recovery PR 或 manual fallback；本 change 不引入 `pull_request_target` 或 external-contributor trusted execution model。

Explicit recovery mode 用於已經 Complete、但 normal trigger 已錯過的 active change。Recovery PR 必須是 **same-repository** merged PR、帶有 `openspec-archive-recovery` label，且 head branch 必須為 `agent/<change>`；只有 recovery mode 會把 branch name 當 explicit change selector。Recovery PR 不需要製造 synthetic `openspec/` marker；selected change 不存在、尚未 Complete、validation failure 或 existing archive branch 都會 fail loudly。

`workflow_dispatch` 保留為 recovery / migration fallback。Normal、explicit recovery 與 manual 三條 path 在 change 進入 archive eligibility 後，共用相同的 strict validation、archive-branch existence check、OpenSpec archive、post-archive validation 與 push core；manual 或 recovery 指定 incomplete change 會 fail loudly。

Archive workflow 使用全域 concurrency group 搭配 `queue: max`，避免 GitHub Actions 預設 single-pending semantics 將較早 pending trigger 靜默替換。平台最多可在同一 concurrency group 保留 **100** 個 pending runs；超出容量的 run 會在 GitHub Actions 顯示為 canceled/rejected，屬可觀察 failure，不視為 archive success。

## OpenSpec lifecycle

```text
openspec/changes/<change>/
    active proposal/design/tasks/delta specs

openspec/specs/
    canonical capability specifications

openspec/changes/archive/YYYY-MM-DD-<change>/
    completed change audit trail
```

完成的 change 使用 OpenSpec CLI archive，而不是手動搬移目錄：

```bash
openspec archive <change> --yes
```

`openspec/specs/` 是 archive 後的 canonical contract source of truth。任何 Requirements、Scenarios 或 externally observable contract 的變更，仍必須透過新的 OpenSpec change lifecycle。

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
├── infrastructure/  # replaceable yfinance EOD and XTAI calendar adapters
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

`StrategyContext` does not contain listing venue, provider ticker syntax, real holdings, average cost, cash, benchmark, execution state, or previous runtime state.

Common `MarketState` is restricted to:

- `NEUTRAL`
- `ACCUMULATION`
- `TREND`
- `REVERSAL_RISK`

Implementation-specific regimes remain under `signals` or `diagnostics`.

## Configuration resolution

Configuration resolves before any market-data load. Market-data identity and Strategy assignment remain separate concerns: a configured instrument may have a valid listing venue without an active strategy。

Repository YAML adapters live behind registry interfaces. `config/instruments.yaml` may contain provider-neutral venue metadata without creating a fake production strategy assignment; `config/parameter_sets.yaml` remains empty until a production strategy exists.

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

For historical `Decision(as_of=T)` the framework first normalizes timestamps enough to establish temporal position, excludes timestamp-known rows after T, and only then validates their non-temporal OHLCV structure. Therefore a known T+1 row with invalid OHLC cannot contaminate the Decision at T；an un-normalizable timestamp can still fail because its temporal position is unknowable.

Trading-day continuity and freshness are based on the injected `TradingCalendar`, not calendar-day continuity. Weekends/holidays are not gaps. Market date/session interpretation is also owned by the `TradingCalendar`; a timezone-aware `Clock` instant is never reduced with the runner's local timezone before calendar evaluation.

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

Decision / Backtest artifact builders produce Python mappings, and the public serialization boundary emits strict JSON. Non-JSON-compatible strategy extension values are rejected deterministically instead of leaking into an Actions Artifact.

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
- `.github/workflows/openspec-validate.yml`：執行 `openspec list` 與 project-level `openspec validate --all --strict --json --no-interactive`，不綁定已 archived change。
- `.github/workflows/openspec-archive.yml`：對 merged-to-`main` 的 `pull_request.closed` 事件，固定 checkout triggering `merge_commit_sha`，從 PR changed files 與該 snapshot 的 active OpenSpec state 分類 candidate。Normal automatic path 只接受 same-repository PR；fork PR 若形成 OpenSpec candidate 則 fail `unsupported automatic source`。`openspec-archive-recovery` + same-repository `agent/<change>` 提供 explicit recovery；`workflow_dispatch` 保留 manual fallback。三條 path 共用 strict pre-validation、existing archive-branch guard、`openspec archive`、strict post-validation 與 push core。Workflow 使用 `queue: max` 保留最多 100 個 pending evaluations，超量 cancellation 是可觀察 failure；workflow 只 push `agent/archive-<change>`，不直接寫入 `main`。

Generated analytical results 應上傳 Actions Artifacts，不 commit 回 repository。Production strategy/workflow activation 保持 deferred。

## Local verification

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
openspec list
openspec validate --all --strict --json --no-interactive
```

針對仍 active 的 change，`openspec status --change <change>` 可在 change review 與 archive validation 使用。

## Deferred work

- production Bollinger swing strategy
- production time-series strategy
- hybrid strategy（待研究支持）
- Strategy-specific lookback/history-window contract
- corporate-action methodology
- fallback/cache
- production Strategy and workflow activation
- intraday acquisition beyond the existing observational overlay contract
- prediction
- execution/fill/portfolio state