# Investment Strategy

以歷史市場資料產生交易計畫，並使用相同策略核心進行歷史回測。

本專案的開發與執行方式：

- **AI-assisted development**：使用 ChatGPT Chat / Work，並依循 OpenSpec 流程進行規格驅動的 AI-assisted development。
- **Serverless-style execution**：以 GitHub Actions 執行事件或排程觸發的 Decision、Backtest 與驗證工作，無需維運常駐伺服器。

本專案以三個 GitHub Actions Workflow 分工：

- `decision.yml`：依最新完整歷史資料判定位階，計算當日買點 / 賣點並輸出交易計畫。
- `backtest.yml`：使用歷史資料逐日重播相同策略，輸出逐日 analytical StrategyResult timeline；成交模擬由後續 Execution Simulator change 處理。
- `openspec-validate.yml`：在 OpenSpec 變更時執行 strict validation，避免 proposal、specs、design、tasks 出現結構或格式問題。

> 核心原則：Decision 與 Backtest 必須共用同一份策略實作。回測不能使用另一套簡化規則。

---

## 免責聲明

本專案及其產生之所有內容僅供個人研究、學習與策略驗證用途，不構成任何形式之投資建議、投資招攬、證券推薦或買賣依據。

本專案所呈現之市場資料、分析結果、價格區間、交易訊號及回測結果，均可能受到資料品質、模型假設、參數設定及市場變化影響，亦可能存在錯誤、延遲或不完整之情形。

任何投資決策均應由使用者自行評估並承擔相關風險。本專案作者不對依據本專案內容所進行之任何投資或交易行為，以及因此產生之損益負責。

公開的 Decision / Backtest Artifact 亦應包含簡短免責聲明：`僅為個人研究與策略驗證，不構成任何形式之投資建議。`

---

## 目標

### 1. 輸出決策

Decision Workflow 負責回答：

> 根據截至目前可用的完整歷史資料，目前位階為何？今天的買點與賣點在哪裡？

流程：

```text
取得歷史資料
    ↓
Data Integrity Check
    ↓
計算指標 / 相對位置
    ↓
判定位階
    ↓
套用策略
    ↓
計算買點 / 賣點
    ↓
輸出當日交易計畫
    ↓
GitHub Actions Artifact
```

Decision **不負責宣告成交**。

策略計算出的買點或賣點只是交易計畫。市場可能沒有觸及該價格，因此：

```text
產生買點 ≠ 已買進
產生賣點 ≠ 已賣出
```

買點與賣點每日依最新完整歷史資料重新計算；新的 Decision 代表最新 analytical view。本 change 不定義 pending execution plan 的替換、存續或有效期限。

---

### 2. 分析型回測

Backtest Workflow 負責回答：

> 如果在歷史上每天使用完全相同的策略，以當時可用資料重新評估，逐日會得到什麼 StrategyResult？

流程：

```text
取得歷史資料與 pre-roll
    ↓
Data Integrity Check
    ↓
逐交易日推進
    ↓
只提供截至當日可用資料
    ↓
使用共用 Strategy 計算 StrategyResult
    ↓
記錄 analytical timeline
    ↓
GitHub Actions Artifact
```

Backtest 不得看到當時尚未發生的資料（避免 look-ahead bias）。本 change 不模擬成交、持倉、現金或執行衍生績效。

---

## Workflow

專案包含三個 Workflow：

```text
.github/workflows/
├── decision.yml
├── backtest.yml
└── openspec-validate.yml
```

### Decision Workflow

用途：

- 抓取最新所需市場資料
- 驗證資料完整性
- 計算策略所需指標
- 判定位階
- 計算當日買點 / 賣點
- 將結果存為 Artifact

預期主要輸出：

```text
decision/
├── decision.json
├── indicators.json
└── data_quality.json
```

`decision.json` 建議結構：

```json
{
  "status": "SUCCESS",
  "symbol": "00733",
  "as_of": "YYYY-MM-DD",
  "strategy_version": "git-sha-or-version",
  "position": {
    "state": "LOW"
  },
  "buy_plan": {
    "enabled": true,
    "price": 0
  },
  "sell_plan": {
    "enabled": false,
    "price": null
  },
  "reasons": [],
  "data_quality": "PASS"
}
```

若資料驗證失敗，不應把資料問題解讀成 `HOLD`：

```json
{
  "status": "FAILED",
  "decision": null,
  "reason": "OHLCV data integrity check failed"
}
```

---

### Backtest Workflow

用途：

- 抓取指定期間與所需 pre-roll 歷史資料
- 每個交易日使用同一份 Strategy 進行 walk-forward evaluation
- 嚴格限制每個 evaluation point 只能使用當時可用資料
- 區分 `WARMUP`、有效 StrategyResult 與失敗
- 輸出 analytical StrategyResult timeline
- 將結果存為 Artifact

預期輸出：

```text
backtest/
├── summary.json
├── strategy_results.jsonl
└── data_quality.json
```

### OpenSpec Validate Workflow

用途：

- `openspec/**` 變更時自動執行 OpenSpec strict validation
- Workflow 本身變更時重新驗證
- 支援手動 `workflow_dispatch`
- 使用 workflow 內固定的 OpenSpec 版本，避免不同執行環境產生驗證差異
- 對目前 change 執行 strict validation；任何 validation issue 都應先修正，再宣告 change 完成

OpenSpec 版本只在 workflow 中固定；`openspec/config.yaml` 定義的是專案規格撰寫與驗收規則，不重複綁定工具版本。

---

## Strategy 與 Execution 分離

Strategy 只負責：

```text
歷史資料
   ↓
位階判斷
   ↓
買點 / 賣點
```

Strategy **不負責假設成交**。

成交判斷屬於後續獨立的 Execution Simulator change：

```text
Strategy
   │
   ├── Decision → 輸出 analytical plan
   │
   └── Analytical Backtest → 輸出 StrategyResult timeline

後續：
StrategyResult / Plan → Execution Simulator → simulated fills / positions / PnL
```

這項分離可以避免把「策略希望成交的價格」誤當成「市場實際可以成交的價格」。

---

## 共用核心

建議程式結構：

```text
src/investment_strategy/
├── data/
│   ├── fetch.py
│   └── validate.py
├── indicators/
├── strategies/
│   ├── base.py
│   └── ...
├── decision/
│   └── engine.py
└── backtest/
    └── engine.py
```

Decision / Backtest Workflow 只負責 orchestration，不在 YAML 內實作策略規則。

理想 CLI：

```bash
python -m investment_strategy decision ...
python -m investment_strategy backtest ...
```

---

## 資料時點

正式位階與策略指標應以「已完成的歷史交易資料」計算。

資料需明確區分：

- 完整交易日 OHLCV
- 當日開盤價
- 盤中即時價

盤中資料不得無意間回寫或污染正式歷史 K 棒與技術指標。

---

## 每日 analytical view 更新規則

目前確定規則：

1. 使用最新完整歷史資料重新判定位階。
2. 根據最新位階重新計算 Entry / Exit Plan。
3. 新的 Decision 代表目前最新的 analytical view。
4. 不因為產生 Entry / Exit Plan 就宣告成交。
5. pending execution plan 的有效期限、替換與存續規則不屬於本 change，留給後續 Execution Simulator 定義。

---

## GitHub Actions 與 Artifact

計算結果不 commit 回 repository。

```text
GitHub Actions Runner
    ↓
執行計算
    ↓
output/
    ↓
actions/upload-artifact
```

Repository 保存：

- 程式
- 策略
- Workflow
- 設定
- 必要的執行 request

計算結果則保存在 GitHub Actions Artifact。

由於 repository 與 GitHub Actions 輸出可能公開存取，所有公開的 Decision / Backtest Artifact 必須自帶研究用途免責聲明，不得僅依賴 README 的說明。

---

## ChatGPT / GitHub Connector 執行方式

目前 GitHub Connector 可以：

- 讀取 Workflow Run
- 讀取 Jobs / Steps
- 讀取 Job Logs
- 取得及下載 Artifact
- 重新執行既有失敗 Job / Run

若 Connector 沒有直接提供 `workflow_dispatch`，可以保留 request 檔案作為觸發入口：

```text
requests/
├── decision.json
└── backtest.json
```

流程：

```text
ChatGPT
   ↓
更新 request
   ↓
push
   ↓
GitHub Actions
   ↓
Artifact
   ↓
ChatGPT 讀取結果
```

Artifact 不需要 commit 回 repository。

---

## Strategy Version

每一份 Decision 與 Backtest 結果都應包含策略版本，例如：

```text
strategy_version
git_commit_sha
```

目的：

- 可以追溯某次 Decision 使用哪一版策略。
- 可以確認某次 Backtest 是否與正式 Decision 使用相同邏輯。
- 策略修改後，不會把舊結果誤認為目前策略結果。

---

## 尚待確認

以下項目刻意不在目前版本中自行假設：

- OHLCV / 即時價主要資料來源
- 資料來源 fallback 規則
- 實際位階定義
- 買點 / 賣點公式
- Execution Simulator 成交價格模型
- 手續費
- 證交稅
- 滑價
- 股息 / 還原權值處理
- 資金與部位管理
- Backtest benchmark
- Artifact retention

這些規則確認後，再寫入 Strategy / Backtest Engine，避免將尚未確認的假設硬編碼進實作。

---

---

## OpenSpec 開發流程

本專案採用 OpenSpec 管理需求、設計與實作變更。

README 用來說明專案目標、架構與使用方式；真正會約束實作行為的需求與規則，應寫入 `openspec/`。

```text
README.md
    ↓
專案說明 / 架構導覽

openspec/
    ↓
正式需求 / 設計 / 任務 / 變更紀錄
```

### 基本流程

每次功能新增或策略規則修改，都先建立一個 OpenSpec change：

```text
proposal
   ↓
specs
   ↓
design
   ↓
tasks
   ↓
implement
   ↓
verify
   ↓
archive
```

典型操作：

```text
/opsx:explore          # 可選：先討論需求與方案
/opsx:propose <change> # 建立 change
/opsx:apply            # 依 tasks 實作
/opsx:archive          # 驗證完成後歸檔
```

若需要細粒度操作，也可以：

```text
/opsx:new <change>
/opsx:ff
/opsx:apply
/opsx:archive
```

任何 `openspec/**` 變更都會由 `openspec-validate.yml` 自動執行 strict validation。CI 驗證通過不取代人工的 proposal/specs/design/tasks traceability review；change 在實作完成並準備宣告完成前，仍應再次確認 strict validation 為綠燈。

### 專案結構

建議加入：

```text
openspec/
├── specs/
│   ├── decision/
│   │   └── spec.md
│   ├── backtest/
│   │   └── spec.md
│   └── strategy/
│       └── spec.md
└── changes/
    └── <change-name>/
        ├── proposal.md
        ├── design.md
        ├── tasks.md
        └── specs/
            └── <capability>/
                └── spec.md
```

`openspec/specs/` 代表目前已生效的正式規格。

`openspec/changes/` 代表尚在提案、設計、實作或驗證中的變更。

### Initial Change

專案第一個 change 建議為：

```text
openspec/changes/establish-strategy-engine/
```

負責正式定義目前已確認的基礎能力：

```text
Decision
├── 使用完整歷史資料判定位階
├── 根據位階計算 Entry / Exit Plan
├── Entry / Exit Plan 不代表成交
└── 每日重新計算，新的 Decision 代表最新 analytical view

Backtest
├── 與 Decision 共用同一 Strategy
├── 歷史資料逐日推進
├── 不得使用未來資料
├── 輸出逐日 StrategyResult analytical timeline
└── 不模擬成交、持倉、現金或績效

Strategy
├── 接收當時可用的歷史資料
├── 判定位階
├── 計算買點 / 賣點
└── 不處理成交狀態

Intraday Overlay
├── 正式 StrategyResult 仍使用最近完整交易日
├── 可獨立列示當日開盤價、即時價與 snapshot time
├── 可描述即時價相對既有 Entry / Exit Plan 的位置
└── 不回寫正式指標、market state 或成交狀態
```

### Strategy 變更原則

策略規則不可直接修改正式 spec 後立即實作。

例如新增 ATR 賣出規則，應建立：

```text
openspec/changes/add-atr-exit/
```

在 change 中描述差異，例如：

```text
ADDED
- ATR exit rule

MODIFIED
- sell point calculation
```

完成以下流程後再 archive：

```text
需求確認
   ↓
Spec
   ↓
Design
   ↓
Tasks
   ↓
Implementation
   ↓
Backtest / Tests
   ↓
Review
   ↓
Archive
```

這可以避免 Decision、Backtest 或不同版本的策略邏輯發生漂移。

### 實作原則

OpenSpec change 是實作工作的來源。

AI / 開發工具在實作前應先讀取：

```text
proposal.md
specs/
design.md
tasks.md
```

實作時不得自行擴大未定義需求，也不得將尚未確認的假設直接寫進 Strategy。

若發現規格不足，應先更新 change，再繼續實作。


## 專案狀態

目前階段：

```text
Architecture / Rules Definition
```

已確認：

- [x] Decision 與 Backtest 分為兩個 Workflow
- [x] 兩者共用同一份 Strategy
- [x] Decision 使用過去完整資料判定位階
- [x] 由位階計算買點 / 賣點
- [x] 買點 / 賣點不代表成交
- [x] Entry / Exit Plan 每日重算，新的 Decision 代表最新 analytical view
- [x] Backtest 僅進行 analytical walk-forward replay，不模擬成交
- [x] 計算結果以 GitHub Actions Artifact 輸出
- [x] 計算結果不 commit 回 repository
- [x] 採用 OpenSpec 管理正式需求與變更
- [x] 建立 initial OpenSpec change：`establish-strategy-engine`
- [x] 建立 OpenSpec strict validation CI