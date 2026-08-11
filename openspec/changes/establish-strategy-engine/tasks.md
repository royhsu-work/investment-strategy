# Tasks — establish-strategy-engine

## 1. Decision walking skeleton

- [x] 1.1 RED — Add an outside-in Decision behavior test that supplies an instrument with a valid active assignment, deterministic completed daily OHLCV, a test-only Strategy, fixed Clock/TradingCalendar, and expects a successful analytical Decision artifact with one StrategyResult and the exact disclaimer.
- [x] 1.2 RED — Run the new test before production implementation and verify it fails because the Decision application/framework behavior is missing, not because of syntax, imports, fixtures, or test setup.
- [x] 1.3 GREEN — Add the minimum Python 3.11+ project/tooling configuration needed to run the slice with `uv`, `pytest`, `ruff`, and `mypy`; implement only the minimal typed domain models, ports, test adapters, request boundary, and Decision orchestration required to pass the walking-skeleton test.
- [x] 1.4 REFACTOR — Move framework-independent values into domain modules and keep test-only Strategy/data/calendar implementations under `tests/`; do not add a production strategy or live provider.
- [x] 1.5 VERIFY — Run the slice tests plus `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run mypy src tests`.

## 2. Configuration resolution before data loading

- [x] 2.1 RED — Add Decision/Backtest behavior tests for `INSTRUMENT_NOT_FOUND`, `ACTIVE_STRATEGY_NOT_CONFIGURED`, `STRATEGY_NOT_FOUND`, `PARAMETER_SET_NOT_FOUND`, `STRATEGY_PARAMETER_MISMATCH`, and `INVALID_STRATEGY_PARAMETERS`; include an adversarial Decision fixture with Strategy A/A1 and B/B1 present simultaneously so the test proves the configured active assignment is selected rather than the first/only registry entry.
- [x] 2.2 RED — Add spy/fake market-data gateway assertions proving no market-data loading or strategy evaluation occurs after any application `CONFIGURATION_FAILED` outcome; run the tests and verify the intended RED failures.
- [x] 2.3 GREEN — Implement Instrument Registry, Parameter Set Registry, code Strategy Registry, assignment resolution, strategy-owned parameter validation, and immutable `ResolvedStrategyConfig` containing strategy identity, parameter-set identity, internal resolved parameters, and Git revision.
- [x] 2.4 GREEN — Implement repository-backed YAML registry adapters for instrument assignments and parameter sets with tests using temporary fixture files; do not add a real production active assignment to a strategy that does not yet exist.
- [x] 2.5 REFACTOR — Keep YAML parsing/storage outside resolver/domain contracts and remove duplicated resolution logic between Decision and Backtest.
- [x] 2.6 VERIFY — Run configuration slice tests and the full pytest/ruff/mypy checks.

## 3. Strategy contract, immutability, and analytical result semantics

- [x] 3.1 RED — Add reusable Strategy Contract Tests for `DataRequirement` with the only supported frequency `DAILY`, explicit minimum history, equivalent-result reproducibility, StrategyResult strategy/as-of identity, common MarketState membership, and preservation of implementation-specific regime/details inside strategy-specific signals or diagnostics; do not introduce arbitrary additional per-bar data requirements in this change.
- [x] 3.2 RED — Add behavior tests proving Strategy evaluation requires no real holdings, average cost, cash, benchmark, prior execution state, or prior strategy runtime state; verify RED is caused by missing contract behavior.
- [x] 3.3 RED — Add tests proving `DataRequirement`, `StrategyContext`, `StrategyResult`, EntryPlan, and ExitPlan are immutable domain values, and result-contract tests proving EntryPlan may expose levels/triggers, ExitPlan may expose dynamic levels/triggers, no fixed profit target is mandatory, and analytical plans do not imply fills or portfolio state.
- [x] 3.4 GREEN — Implement the typed stateless Strategy protocol, DAILY-only `DataFrequency`, immutable `DataRequirement` containing only supported frequency and minimum history, `StrategyContext`, `StrategyResult`, `MarketState`, EntryPlan, ExitPlan, signals/diagnostics/reasons extension fields, and the minimum registry integration required by the tests.
- [x] 3.5 REFACTOR — Keep strategy-specific regimes and parameter internals out of common framework fields; retain only the four approved common MarketState values and do not introduce unsupported generic data frequencies or formal per-bar extension fields.
- [x] 3.6 VERIFY — Run Strategy Contract/immutability tests, application regression tests, and full pytest/ruff/mypy checks.

## 4. Formal OHLCV normalization, acquisition precedence, and structural validation

- [x] 4.1 RED — Add data behavior tests showing reverse-chronological provider records can normalize into strict chronological order and duplicate normalized timestamps fail with `DATA_FAILED / DUPLICATE_TIMESTAMP`.
- [x] 4.2 RED — Add tests proving every formal normalized `DailyBar` requires open, high, low, close, and volume; missing volume fails with `DATA_FAILED / MISSING_REQUIRED_FIELD`, negative volume/un-normalizable timestamps use `VALIDATION_ERROR`, invalid OHLC uses `INVALID_OHLC`, and missing base volume is never converted to zero or interpreted as a negative strategy signal.
- [x] 4.3 RED — Add acquisition/precedence tests proving provider failure or zero candidate observations yields `DATA_FAILED / DATA_UNAVAILABLE`, while acquired-but-invalid observations retain their structural code (for example an only observation with an invalid timestamp remains `VALIDATION_ERROR` rather than becoming `DATA_UNAVAILABLE`); also prove data failure never becomes `NEUTRAL`.
- [x] 4.4 GREEN — Implement provider-neutral acquisition handling, timestamp normalization needed for temporal classification, raw-record normalization into immutable mandatory-OHLCV `DailyBar` values, and structural validation with explicit acquisition-versus-structural failure precedence.
- [x] 4.5 REFACTOR — Keep provider ordering/conversion in normalization, acquisition failure distinct from validation failure, the formal data model limited to completed daily OHLCV, and validation independent of provider SDKs or live-network behavior.
- [x] 4.6 VERIFY — Run data slice tests plus full pytest/ruff/mypy checks.

## 5. Trading-calendar continuity, freshness, Decision as-of, and no-look-ahead

- [x] 5.1 RED — Add calendar-aware continuity tests proving weekends/holidays are not gaps and a missing expected trading day fails with `DATA_FAILED / DATA_GAP`.
- [x] 5.2 RED — Add freshness tests proving a missing latest required completed trading-day observation fails with `DATA_FAILED / STALE_DATA`.
- [x] 5.3 RED — Add Decision as-of tests for historical trading dates, historical non-trading dates, omitted `as_of` with no session in progress, omitted `as_of` during an incomplete session, explicit current trading day before completion, explicit current trading day after completion, and preservation of requested vs resolved as-of on successful output; assert every resolved date is selected by TradingCalendar/Clock only.
- [x] 5.4 RED — Add a calendar/data-boundary guard where TradingCalendar resolves T as the latest completed trading day but T data is missing; prove `resolved_as_of` remains T and Decision fails with the applicable data failure such as `STALE_DATA` rather than silently falling back to T-1.
- [x] 5.5 RED — Add a Decision-specific validation-stage no-look-ahead test with valid eligible data through T plus a candidate row at T+1 whose timestamp is valid but OHLC or volume is structurally invalid; prove `Decision(as_of=T)` is equivalent to the source truncated at T and the T+1 structural defect cannot fail the historical Decision. Separately prove an un-normalizable candidate timestamp may still fail with `DATA_FAILED / VALIDATION_ERROR` because its temporal position cannot be established.
- [x] 5.6 RED — Add a future-date accepted Decision request test expecting `status=FAILED`, `failure.category=CONFIGURATION_FAILED`, and `failure.code=INVALID_AS_OF`, with no market-data loading; run and verify intended RED failures.
- [x] 5.7 GREEN — Implement timezone-aware Clock/TradingCalendar ports, calendar-only as-of resolution, timestamp-first temporal classification, exclusion of timestamp-known future rows before non-temporal OHLCV validation for historical Decision, calendar-based continuity/freshness validation, successful requested/resolved date metadata, and bounded formal history.
- [x] 5.8 REFACTOR — Ensure market timezone/session rules are owned by the TradingCalendar adapter, data availability cannot change `resolved_as_of`, and future-row filtering cannot be used to suppress an un-normalizable timestamp whose temporal position is unknown.
- [x] 5.9 VERIFY — Run calendar/as-of/validation-stage-no-look-ahead tests plus full pytest/ruff/mypy checks.

## 6. Minimum history and Decision eligibility

- [x] 6.1 RED — Add a Decision behavior test with structurally valid data below the selected Strategy's `minimum_history`, expecting `DATA_FAILED / INSUFFICIENT_HISTORY`, no Strategy evaluation, and no `NEUTRAL` substitute.
- [x] 6.2 RED — Add a test proving `minimum_history` is an eligibility threshold and does not truncate a larger valid dataset to exactly that many observations; run and verify intended RED failures.
- [x] 6.3 GREEN — Implement Decision eligibility evaluation against the Strategy's declared minimum history while preserving the full eligible historical view bounded by resolved as-of.
- [x] 6.4 REFACTOR — Keep minimum-history policy in shared data eligibility behavior so Backtest can reuse it with different WARMUP semantics.
- [x] 6.5 VERIFY — Run eligibility tests plus full pytest/ruff/mypy checks.

## 7. Current-only Decision intraday overlay without formal-state contamination

- [x] 7.1 RED — Add a current-formal Decision behavior test for an incomplete current session where `as_of` is omitted or explicitly current, formal StrategyResult uses T-1 completed data, and a separate valid snapshot exposes session date, open, latest price, and snapshot time.
- [x] 7.2 RED — Add a historical-as-of test run during an incomplete current session proving a valid current snapshot is not attached to the historical Decision artifact.
- [x] 7.3 RED — Add tests proving snapshot values cannot change formal market state, entry/exit plans, indicators/model state, or StrategyResult and cannot declare a fill.
- [x] 7.4 RED — Add tests for deterministic current-price relationships to analytical levels and prove the framework does not emit `NEAR` when no explicit proximity tolerance rule exists.
- [x] 7.5 RED — Add a test proving open/latest-only snapshot data cannot claim a level was touched earlier in the session.
- [x] 7.6 RED — Add unavailable/invalid snapshot tests proving a current formal Decision can still succeed with the overlay omitted or unavailable; run and verify intended RED failures.
- [x] 7.7 GREEN — Implement optional `IntradaySnapshot`, snapshot validation, current-formal overlay eligibility, and observational overlay construction after formal Decision evaluation.
- [x] 7.8 REFACTOR — Keep intraday types/builders outside StrategyContext and StrategyResult and remove any path by which snapshot data can enter formal historical indicators or historical-as-of artifacts.
- [x] 7.9 VERIFY — Run intraday eligibility/isolation tests plus full pytest/ruff/mypy checks.

## 8. Decision success, neutral, application failure, and artifact contract

- [x] 8.1 RED — Add a valid `NEUTRAL` Decision test proving `NEUTRAL` is successful only after configuration/data eligibility and Strategy evaluation succeed.
- [x] 8.2 RED — Add a Strategy evaluation failure test expecting `status=FAILED`, `failure.category=STRATEGY_FAILED`, machine-readable `failure.code`, human-readable `failure.reason`, and no valid market state or plan represented as successful output.
- [x] 8.3 RED — Add successful artifact tests requiring `status=SUCCESS`, instrument, resolved as-of, explicitly requested as-of when supplied, strategy, parameter set, Git revision, StrategyResult, and data-quality status; do not require a public `resolved_parameters` field.
- [x] 8.4 RED — Add failed artifact tests requiring the stable minimum identity (`status=FAILED`, requested instrument, Git revision, explicitly requested `as_of` when supplied, canonical `failure.category/code/reason`, disclaimer), and prove `resolved_as_of`, strategy, parameter set, and data-quality fields are not required merely because internal processing may know them; unresolved metadata must not be fabricated.
- [x] 8.5 RED — Add success and application-failure artifact tests requiring exactly `僅為個人研究與策略驗證，不構成任何形式之投資建議。`; run and verify intended RED failures.
- [x] 8.6 GREEN — Implement the shared `SUCCESS|FAILED` status, nested failure envelope, and Decision success/failure artifact builders using the stable public presence rules rather than internal progress-dependent field presence.
- [x] 8.7 REFACTOR — Centralize the exact disclaimer and shared failure serialization so future strategies cannot override or duplicate them.
- [x] 8.8 VERIFY — Run Decision artifact tests plus full pytest/ruff/mypy checks.

## 9. Analytical Backtest walking skeleton, range boundaries, and no-look-ahead

- [x] 9.1 RED — Add an outside-in analytical Backtest test using deterministic fixtures and a test-only Strategy, expecting chronological StrategyResult replay across multiple eligible completed trading dates and no execution state.
- [x] 9.2 RED — Add a cross-application equivalence test proving Decision and Backtest produce equivalent analytical StrategyResults for equivalent strategy/config/code/data/`as_of=T` inputs.
- [x] 9.3 RED — Add a future-data test where the loaded dataset extends beyond T and prove observations after T cannot affect the StrategyResult evaluated at T.
- [x] 9.4 RED — Add range-contract tests for `start_date > end_date`, future `end_date`, non-trading endpoints, an incomplete current trading day inside the range, and an interval containing no completed trading day; assert inclusive-calendar-interval semantics and `CONFIGURATION_FAILED / INVALID_BACKTEST_RANGE` for invalid accepted ranges.
- [x] 9.5 GREEN — Implement Backtest application range validation, completed-trading-day selection inside the inclusive interval, chronological iteration using bounded historical views, and the same common Strategy evaluator used by Decision.
- [x] 9.6 REFACTOR — Remove duplicated strategy-evaluation paths, Backtest-only simplified strategy logic, and any Decision-style endpoint clamping from Backtest range handling.
- [x] 9.7 VERIFY — Run Backtest walking-skeleton/range/equivalence tests plus full pytest/ruff/mypy checks.

## 10. Backtest ACTIVE/EXPLICIT assignment and request-policy boundary

- [x] 10.1 RED — Add accepted `ACTIVE` mode tests proving the instrument active strategy+parameter set is used and missing active assignment fails with `CONFIGURATION_FAILED / ACTIVE_STRATEGY_NOT_CONFIGURED` before data loading.
- [x] 10.2 RED — Add accepted `EXPLICIT` mode tests proving a complete compatible strategy+parameter pair is used without mutating the instrument's active assignment and still works when the configured instrument has no active assignment.
- [x] 10.3 RED — Add discriminated-union rejection tests for `ACTIVE` with any supplied strategy/parameter-set field, `EXPLICIT` with neither field, strategy-only `EXPLICIT`, and parameter-set-only `EXPLICIT`; prove every invalid shape is rejected before application evaluation, produces no public Backtest artifact, is not silently converted to another mode, and never borrows or ignores assignment values.
- [x] 10.4 GREEN — Implement Backtest request-boundary validation as the exact `ACTIVE`/`EXPLICIT` discriminated union and reuse the common resolver only after a request has been accepted.
- [x] 10.5 REFACTOR — Keep request-policy validation and Decision's active-only policy outside Strategy and outside the application failure taxonomy.
- [x] 10.6 VERIFY — Run assignment/discriminated-union request-boundary tests plus full pytest/ruff/mypy checks.

## 11. Backtest pre-roll, WARMUP, and required-data failure semantics

- [x] 11.1 RED — Add a pre-roll test proving observations before requested `start_date` may satisfy minimum history but are not emitted as requested evaluation dates.
- [x] 11.2 RED — Add tests proving early valid-but-insufficient requested completed trading dates are `WARMUP`, produce no StrategyResult, and are not `NEUTRAL` or data failures.
- [x] 11.3 RED — Add a range test where all requested completed trading dates are WARMUP, expecting `DATA_FAILED / INSUFFICIENT_HISTORY` and no successful empty timeline.
- [x] 11.4 RED — Add a mixed range test proving WARMUP dates remain distinguishable while later eligible dates produce StrategyResults and the Backtest may succeed.
- [x] 11.5 RED — Add invalid required historical-data tests proving the Backtest fails with `DATA_FAILED` rather than silently skipping invalid bars; run and verify intended RED failures.
- [x] 11.6 GREEN — Implement pre-roll preparation, shared minimum-history eligibility, WARMUP timeline markers, zero-eligible detection, and fail-fast required-data handling.
- [x] 11.7 REFACTOR — Keep WARMUP as Backtest application semantics layered on shared eligibility rather than adding WARMUP to Strategy MarketState.
- [x] 11.8 VERIFY — Run pre-roll/WARMUP/data-failure tests plus full pytest/ruff/mypy checks.

## 12. Backtest Strategy failure and no-execution boundary

- [x] 12.1 RED — Add a test where Strategy evaluation succeeds on earlier eligible dates and fails at T, expecting `status=FAILED`, `failure.category=STRATEGY_FAILED`, immediate failure semantics, and no partial timeline labeled successful.
- [x] 12.2 RED — Add a test where a StrategyResult contains an entry plan and prove analytical Backtest records the plan without creating fills, positions, cash balances, PnL, returns, or drawdown.
- [x] 12.3 RED — Add dependency-boundary tests ensuring analytical Backtest does not import or require an execution simulator; run and verify intended RED failures.
- [x] 12.4 GREEN — Implement Backtest Strategy-failure propagation and keep output limited to analytical timeline/failure diagnostics.
- [x] 12.5 REFACTOR — Remove any execution-derived fields or placeholder abstractions that slipped into Backtest domain/application models.
- [x] 12.6 VERIFY — Run strategy-failure/no-execution tests plus full pytest/ruff/mypy checks.

## 13. Analytical Backtest artifact contract

- [x] 13.1 RED — Add successful artifact tests requiring `status=SUCCESS`, instrument, assignment mode, strategy, parameter set, Git revision, requested start/end dates, validation status, and a requested evaluation timeline that distinguishes WARMUP entries from eligible StrategyResults; do not require a public `resolved_parameters` field.
- [x] 13.2 RED — Add failed application artifact tests requiring the stable minimum identity (`status=FAILED`, requested instrument, assignment mode, requested start/end dates, Git revision, canonical `failure.category/code/reason`, disclaimer), proving strategy, parameter set, validation status, and partial timeline are not required merely because internal processing may know them, and proving no partial timeline is represented as successful output.
- [x] 13.3 RED — Add success and application-failure artifact tests requiring exactly `僅為個人研究與策略驗證，不構成任何形式之投資建議。`; run and verify intended RED failures.
- [x] 13.4 GREEN — Implement analytical Backtest success/failure artifact builders and JSON serialization using the shared status/failure/disclaimer contracts and stable field-presence rules.
- [x] 13.5 REFACTOR — Keep artifact schema strategy-neutral and avoid adding resolved-parameter duplication, internal-progress-dependent identity fields, trades, equity-curve, or execution fields.
- [x] 13.6 VERIFY — Run Backtest artifact tests plus full pytest/ruff/mypy checks.

## 14. Repository request boundaries, README, and GitHub Actions scaffold alignment

- [x] 14.1 RED — Add schema/parsing tests for the repository Decision request shape (`symbol`, optional `as_of`) and the exact Backtest discriminated union: `ACTIVE` with no strategy/parameter-set fields, or `EXPLICIT` with both fields plus `symbol`, `start_date`, and `end_date`.
- [x] 14.2 RED — Add request-boundary checks proving Decision research overrides, `ACTIVE` Backtests with explicit assignment fields, `EXPLICIT` Backtests with neither field, and partial `EXPLICIT` assignments are rejected before application evaluation and produce no public Decision/Backtest artifact.
- [x] 14.3 GREEN — Update `requests/decision.json` and `requests/backtest.json` examples to the approved request contracts without adding personal portfolio state or the legacy `period` shorthand.
- [x] 14.4 GREEN — Align README Decision/Backtest artifact examples and terminology with `MarketState`, `StrategyResult`, `entry_plan`, `exit_plan`, mandatory formal OHLCV, current-only intraday overlay, exact ACTIVE/EXPLICIT request shapes, request-boundary rejection versus application failure, the canonical `SUCCESS|FAILED` failure envelope, strategy/parameter-set/Git revision traceability, and analytical-only Backtest semantics.
- [x] 14.5 GREEN — Align `.github/workflows/decision.yml` and `.github/workflows/backtest.yml` inputs/placeholder wording with formal Decision and analytical Backtest semantics; remove the obsolete fill-simulation placeholder and keep workflow YAML free of strategy rules.
- [x] 14.6 GREEN — Keep live provider/calendar/production-strategy composition explicitly deferred rather than introducing fake production implementations solely to make the scaffolds execute live analysis.
- [x] 14.7 REFACTOR — Ensure workflow orchestration remains an adapter boundary and generated analytical outputs are intended for Actions Artifacts rather than repository commits.
- [x] 14.8 VERIFY — Run request parsing tests, documentation/contract consistency checks, workflow static checks if configured, and full pytest/ruff/mypy checks.

## 15. End-to-end framework regression and OpenSpec conformance

- [x] 15.1 RED — Add/confirm end-to-end smoke tests covering request-boundary rejection including invalid Backtest union shapes, one successful Decision, one successful analytical Backtest, representative configuration/data/strategy failures, mandatory OHLCV validation, calendar-only Decision as-of with no data-aware fallback, historical Decision validation with a timestamp-known invalid future row, historical as-of replay without current overlay, Backtest range boundaries, and a valid current-only intraday-overlay case using only test adapters.
- [x] 15.2 RED — Verify the end-to-end tests fail if request rejection leaks into application artifacts, arbitrary formal per-bar fields re-enter the common contract, acquisition/structural failure precedence changes, calendar resolution falls back because of missing data, timestamp-known future rows contaminate historical validation, Decision/Backtest strategy equivalence, core immutability, current-only overlay eligibility, the canonical failure envelope, the fixed disclaimer, execution-state isolation, or configuration-before-data-loading guarantees are broken.
- [x] 15.3 GREEN — Make only the minimum integration fixes necessary for all approved capability behaviors to pass together; do not implement deferred production strategies/providers/execution simulation.
- [x] 15.4 REFACTOR — Remove duplicate orchestration, dead abstractions, unsupported data extensibility, and strategy-specific assumptions introduced during vertical-slice implementation while preserving all behavior tests.
- [x] 15.5 VERIFY — Run the complete test suite and required quality gates: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run mypy src tests`.
- [x] 15.6 VERIFY — Perform reverse and forward traceability using the two approved provenance paths: Behavior/Product (`proposal -> spec -> design -> task`) and Engineering/Governance (`openspec/config.yaml -> design -> task`).
- [x] 15.7 VERIFY — Run strict OpenSpec validation/status for `establish-strategy-engine` and resolve every reported issue before implementation is declared complete.
