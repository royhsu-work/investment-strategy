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

## Project direction commitments

本節是 README 中唯一可表達 **prospective project-direction commitment** 的明確 presentation surface。只有刻意放在本節、且同時是 **prospective、scoped、affirmative、non-contradictory** 的承諾，才可能作為 repository-authorized bounded Explore 的 project-direction evidence；實際 admission 與 runtime 判斷仍由 default-branch `agents/AGENTS.md` 擁有。

其他 README 內容，包括 descriptive/current-state 說明、example、non-goal，以及一般 `Deferred work` 清單，都不因出現在 README 就自動成為 workflow admission authority。Plain deferred / uncommitted 項目仍需後續明確治理決策後，才能升格為本節 commitment。

目前沒有額外的 autonomous project-direction commitment。既有 production Strategy、workflow activation、prediction、execution 等 deferred 項目維持未承諾狀態。

## Taiwan EOD market-data support

Taiwan EOD market-data infrastructure 已合併至 `main`，目前作為 repository 的 Taiwan daily market-data baseline，涵蓋 provider-neutral identity、source-native EOD acquisition、Taiwan trading calendar，以及 Decision / Backtest composition。這代表資料基礎設施已可用，但不代表 production Strategy 或排程 workflow 已啟用；production strategy/workflow activation 仍維持 deferred。

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

Repository 使用 OpenSpec + GitHub Issue/PR 進行規格驅動開發。README 只提供 Human/contributor 導覽，不複製 Scheduled-Agent runtime protocol 或 lifecycle topology。

**Authoritative Scheduled-Agent shared runtime governance** is in default-branch agents/AGENTS.md;
the Human-readable Action projection is in agents/workflow.md; semantic Role authority is in
agents/roles/*.md; and action procedure is in agents/skills/*. OpenSpec authoring conventions are in
openspec/config.yaml and approved capability requirements are in openspec/specs/*. README is Human/
contributor orientation and does not duplicate the runtime protocol or lifecycle topology.

Canonical current workflow state is Issue lifecycle + immutable Change + action:<action>. Role is
derived as role_for(Action). The executable Action model, fresh application reauthorization, exact
postconditions, and stale/replay/no-rewind/fail-closed guards are repository-owned. The mapped Role
and Skill perform one Action per wake; application persists the derived successor or terminal state,
and a later wake executes any successor.

External Scheduled Task slot count, topology, cadence, notification, and associated-conversation
configuration are product/deployment configuration. The repository governs bootstrap and bounded
dispatch behavior. The Asia/Taipei daily shard is transport/audit only and is not workflow state.

Implementation review PASS and archive review PASS select review-implementation and the explicit merge-implementation-pr and
merge-archive-pr Actions. Exact-R validation, content-addressed ingress, WIP=1, finish-first,
Human authority, independent review, exact-head merge safety, and mutation-carrier separation remain
required. Detailed semantics belong to the default-branch governance, role, Skill, OpenSpec, and
workflow projection files; README does not redefine them.

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

Pinned OpenSpec CLI 在本 repository 已觀察到：建立新的 canonical capability 時，archive 可能以 generated `Purpose: TBD ...` 取代 delta spec 已核准的 Purpose。Repository archive workflow 因此在 archive 前 snapshot Purpose contract，archive 後只針對已知 generated placeholder 做 deterministic preservation：new capability 的 canonical Purpose 必須精確等於 approved delta Purpose；existing canonical capability 的 Purpose 必須保持不變。未知 Purpose transformation、缺失／空白／重複／placeholder delta Purpose，或不符合預期 canonical section shape 都會 fail loudly，且不 push archive branch。這是 pinned CLI compatibility guard，不改寫 Requirements / Scenarios。

### Archive automation orientation

Merged-PR archive classifier 是 repository automation 的 project-level 行為摘要，不是 Scheduled-Agent routing authority。Implementation branch 使用 `agent/<change>` branch convention，但 normal archive routing 不依賴 branch name。Classifier 在 triggering merge snapshot 上依 merged PR changed files 與 active OpenSpec state 判斷 candidate：0 個 active candidate 或 incomplete change 為 successful no-op，`>1 active touched` fail ambiguous；`Complete` 是 repository-level implementation completion signal。Normal automatic path 只接受 same-repository PR；fork candidate fail `unsupported automatic source`。Explicit recovery 使用 `openspec-archive-recovery`，`workflow_dispatch` 保留為 recovery / migration fallback。Archive request path 使用 application-owned `workflow_dispatch` actuator，帶有 exact Change/Issue/revision/request_key inputs；不假設由 GITHUB_TOKEN 寫入的 issue-comment 會再次觸發 workflow。仍使用 bounded daily control transport 與 non-cancelling concurrency group (`cancel-in-progress: false`)，保留 in-flight request/run/result chain，不把 concurrency 或 archive Issue 當作 lifecycle state / response mailbox；`workflow_dispatch` 也保留給 recovery / migration fallback，詳細 deterministic archive mechanics 以 `.github/workflows/openspec-archive.yml` 與其 tests 為準。

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

`StrategyContext` does not contain listing venue, provider ticker syntax, real holdings, average cost, cash, benchmark, execution state, or previous runtime state。

Common `MarketState` is restricted to:

- `NEUTRAL`
- `ACCUMULATION`
- `TREND`
- `REVERSAL_RISK`

Implementation-specific regimes remain under `signals` or `diagnostics`。

## Configuration resolution

Configuration resolves before any market-data load. Market-data identity and Strategy assignment remain separate concerns: a configured instrument may have a valid listing venue without an active strategy。

Repository YAML adapters live behind registry interfaces. `config/instruments.yaml` may contain provider-neutral venue metadata without creating a fake production strategy assignment；`config/parameter_sets.yaml` remains empty until a production strategy exists。

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

For historical `Decision(as_of=T)` the framework first normalizes timestamps enough to establish temporal position, excludes timestamp-known rows after T, and only then validates their non-temporal OHLCV structure. Therefore a known T+1 row with invalid OHLC cannot contaminate the Decision at T；an un-normalizable timestamp can still fail because its temporal position is unknowable。

Trading-day continuity and freshness are based on the injected `TradingCalendar`, not calendar-day continuity. Weekends/holidays are not gaps. Market date/session interpretation is also owned by the `TradingCalendar`; a timezone-aware `Clock` instant is never reduced with the runner's local timezone before calendar evaluation。

## Decision request

Repository request shape:

```json
{
  "symbol": "00733",
  "as_of": "2026-08-10"
}
```

`as_of` is optional. Research fields such as `strategy` or `parameter_set` are rejected by the request boundary and produce no public Decision artifact。

Decision date resolution is calendar-only. A future accepted `as_of` is an application failure `CONFIGURATION_FAILED / INVALID_AS_OF`; missing data never causes silent fallback to an older date。

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

Decision / Backtest artifact builders produce Python mappings, and the public serialization boundary emits strict JSON. Non-JSON-compatible strategy extension values are rejected deterministically instead of leaking into an Actions Artifact。

## Current-only intraday overlay

若 current trading session 尚未完成，而且 request 是 omitted `as_of` 或 explicitly current date，formal StrategyResult 仍以 previous completed trading day為 `resolved_as_of`。若 current snapshot 有效，可另外附加：

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
- `.github/workflows/openspec-validate.yml`：執行 `openspec list` 與 project-level `openspec validate --all --strict --json --no-interactive`，不綁定已 archived change；對 exact-revision mechanical gate，workflow 先決定 target revision/repository、checkout 該 target、以 `git rev-parse HEAD` 驗證實際 validator `HEAD` 等於 target，並把 target/checkout identity 寫入 job log/summary 後才執行 strict validation。`run.head_sha` 只是 association metadata，單獨使用是 insufficient checkout proof；PR synthetic merge revision validation 不等於不同 PR head 的 exact-head validation。此 mechanical PASS 不自行建立或刷新 semantic acceptance。
- `.github/workflows/openspec-archive.yml`：state-driven archive automation；詳細 classifier/request/linkage/carrier behavior 見上方 orientation 與 workflow/tests。

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

針對仍 active 的 change，`openspec status --change <change>` 可在 change review 與 archive validation 使用。當 exact-revision `OpenSpec Validate` GitHub Actions 已成功，且 durable job evidence 已證明 validator checkout `HEAD` 就是 relevant revision 時，Scheduled Role gate 不需只為重複證明同一 strict mechanical validation 而再次執行 local OpenSpec CLI；是否需要新的 semantic review gate 依 material OpenSpec meaning change 判斷，不依 raw SHA recency。

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

The default-branch merge is the activation boundary. An unmerged governance PR is review target/input
and must not govern its own current invocation. A run head_sha is association metadata; validator
checkout `HEAD` and exact target identity are the checkout proof, and synthetic merge validation
is not exact-head validation for another PR head.

The current runtime contract is Role = role_for(Action): review-implementation PASS and review-archive
PASS select merge-implementation-pr and merge-archive-pr. A run head_sha is association metadata;
validator checkout `HEAD` and exact target identity are checkout proof, and synthetic merge
validation is not exact-head validation for another PR head. The default-branch merge is the
activation boundary, so an unmerged governance PR is review target/input and must not govern its own
current invocation.
