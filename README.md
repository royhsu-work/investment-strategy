# Investment Strategy

以歷史市場資料產生交易計畫，並使用相同策略核心進行歷史回測。

本專案將「目前交易決策」與「歷史策略驗證」拆成兩個獨立 GitHub Actions Workflow：

- `decision.yml`：依最新完整歷史資料判定位階，計算當日買點 / 賣點並輸出交易計畫。
- `backtest.yml`：使用歷史資料逐日重播相同策略，模擬買賣點是否實際觸價成交並統計績效。

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

買點與賣點每日依最新完整歷史資料重新計算，新 Decision 直接取代前一日的交易計畫。

---

### 2. 執行回測

Backtest Workflow 負責回答：

> 如果在歷史上每天使用完全相同的策略產生交易計畫，實際可能產生什麼交易結果？

流程：

```text
取得歷史資料
    ↓
Data Integrity Check
    ↓
逐交易日推進
    ↓
使用共用 Strategy 計算當日位階
    ↓
產生買點 / 賣點
    ↓
使用後續 OHLC 判斷是否觸價
    ↓
模擬成交 / 未成交
    ↓
持倉與資金管理
    ↓
統計績效
    ↓
GitHub Actions Artifact
```

回測不能看到當時尚未發生的資料（避免 look-ahead bias）。

---

## Workflow

專案包含兩個 Workflow：

```text
.github/workflows/
├── decision.yml
└── backtest.yml
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

- 抓取指定期間的歷史資料
- 每個交易日使用同一份 Strategy 產生買賣點
- 使用後續市場資料判斷是否觸價
- 模擬成交與持倉
- 計算策略績效
- 將詳細結果存為 Artifact

預期輸出：

```text
backtest/
├── summary.json
├── trades.csv
├── equity_curve.csv
└── signals.csv
```

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

成交判斷屬於 Execution / Backtest Engine：

```text
Strategy
   │
   ├── Decision → 輸出交易計畫
   │
   └── Backtest → Execution Engine → 模擬成交
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
├── backtest/
│   └── engine.py
└── execution/
    └── fill.py
```

兩個 Workflow 只負責 orchestration，不在 YAML 內實作策略規則。

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

## 每日買賣點更新規則

目前確定規則：

1. 使用最新完整歷史資料重新判定位階。
2. 根據最新位階重新計算買點與賣點。
3. 新 Decision 取代前一個 Decision。
4. 不另外維護「買點有效 N 天」。
5. 不因為產生買點 / 賣點就宣告成交。
6. Backtest 必須額外判斷市場是否真正觸及策略價格。

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
- 回測成交價格模型
- 手續費
- 證交稅
- 滑價
- 股息 / 還原權值處理
- 資金與部位管理
- Backtest benchmark
- Artifact retention

這些規則確認後，再寫入 Strategy / Backtest Engine，避免將尚未確認的假設硬編碼進實作。

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
├── 根據位階計算買點
├── 根據位階計算賣點
├── 買點 / 賣點不代表成交
└── 每日重新計算，新 Decision 取代舊 Decision

Backtest
├── 與 Decision 共用同一 Strategy
├── 歷史資料逐日推進
├── 不得使用未來資料
├── 依 OHLC 判斷買賣點是否觸價
└── 模擬實際成交與持倉結果

Strategy
├── 接收當時可用的歷史資料
├── 判定位階
├── 計算買點 / 賣點
└── 不處理成交狀態
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
- [x] 買賣點每日重算，新 Decision 取代舊 Decision
- [x] Backtest 模擬實際是否觸價成交
- [x] 計算結果以 GitHub Actions Artifact 輸出
- [x] 計算結果不 commit 回 repository
- [x] 採用 OpenSpec 管理正式需求與變更
- [ ] 建立 initial OpenSpec change：`establish-strategy-engine`
