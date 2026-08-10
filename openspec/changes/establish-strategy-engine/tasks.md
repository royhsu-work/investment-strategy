# Tasks — establish-strategy-engine

## 1. Decision walking skeleton

- [ ] 1.1 RED — Add an outside-in Decision behavior test that supplies an instrument with a valid active assignment, deterministic completed daily data, a test-only Strategy, fixed Clock/TradingCalendar, and expects a successful analytical Decision artifact with one StrategyResult and the exact disclaimer.
- [ ] 1.2 RED — Run the new test before production implementation and verify it fails because the Decision application/framework behavior is missing, not because of syntax, imports, fixtures, or test setup.
- [ ] 1.3 GREEN — Add the minimum Python 3.11+ project/tooling configuration needed to run the slice with `uv`, `pytest`, `ruff`, and `mypy`; implement only the minimal typed domain models, ports, test adapters, and Decision orchestration required to pass the walking-skeleton test.
- [ ] 1.4 REFACTOR — Move framework-independent values into domain modules and keep test-only Strategy/data/calendar implementations under `tests/`; do not add a production strategy or live provider.
- [ ] 1.5 VERIFY — Run the slice tests plus `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run mypy src tests`.

## 2. Configuration resolution before data loading

- [ ] 2.1 RED — Add Decision/Backtest behavior tests for `INSTRUMENT_NOT_FOUND`, `ACTIVE_STRATEGY_NOT_CONFIGURED`, `STRATEGY_NOT_FOUND`, `PARAMETER_SET_NOT_FOUND`, `STRATEGY_PARAMETER_MISMATCH`, and `INVALID_STRATEGY_PARAMETERS`.
- [ ] 2.2 RED — Add spy/fake market-data gateway assertions proving no market-data loading or strategy evaluation occurs after any `CONFIGURATION_FAILED` outcome; run the tests and verify the intended RED failures.
- [ ] 2.3 GREEN — Implement Instrument Registry, Parameter Set Registry, code Strategy Registry, assignment resolution, strategy-owned parameter validation, and immutable `ResolvedStrategyConfig` with strategy/parameter/git revision identity.
- [ ] 2.4 GREEN — Implement repository-backed YAML registry adapters with tests using temporary fixture files; do not add a real production active assignment to a strategy that does not yet exist.
- [ ] 2.5 REFACTOR — Keep YAML parsing/storage outside the resolver/domain contracts and remove duplicated resolution logic between Decision and Backtest.
- [ ] 2.6 VERIFY — Run configuration slice tests and the full pytest/ruff/mypy checks.

## 3. Strategy contract and analytical result semantics

- [ ] 3.1 RED — Add reusable Strategy Contract Tests for declared `DataRequirement` (`frequency`, `required_fields`, `minimum_history`), equivalent-result reproducibility, StrategyResult strategy/as-of identity, and common MarketState membership.
- [ ] 3.2 RED — Add behavior tests proving Strategy evaluation requires no real holdings, average cost, cash, benchmark, prior execution state, or prior strategy runtime state; verify RED is caused by missing contract behavior.
- [ ] 3.3 RED — Add result-contract tests proving EntryPlan may expose levels/triggers, ExitPlan may expose dynamic levels/triggers, no fixed profit target is mandatory, and analytical plans do not imply fills or portfolio state.
- [ ] 3.4 GREEN — Implement the typed stateless Strategy protocol, `DataRequirement`, `StrategyContext`, `StrategyResult`, `MarketState`, EntryPlan, ExitPlan, signals/diagnostics/reasons extension fields, and the minimum registry integration required by the tests.
- [ ] 3.5 REFACTOR — Keep strategy-specific regimes and parameter internals out of common framework fields; retain only the four approved common MarketState values.
- [ ] 3.6 VERIFY — Run Strategy Contract Tests, application regression tests, and full pytest/ruff/mypy checks.

## 4. Formal market-data normalization and structural validation

- [ ] 4.1 RED — Add data behavior tests showing reverse-chronological provider records can normalize into strict chronological order and that duplicate normalized timestamps fail with `DATA_FAILED / DUPLICATE_TIMESTAMP`.
- [ ] 4.2 RED — Add tests for invalid/un-normalizable timestamps, non-positive OHLC, invalid OHLC relationships, negative volume, and missing strategy-required fields; assert specific required codes and `VALIDATION_ERROR` fallback where no more specific code is specified.
- [ ] 4.3 RED — Add tests proving missing required formal data yields `DATA_FAILED / DATA_UNAVAILABLE` and that data failure never becomes `NEUTRAL`; run and verify intended RED failures.
- [ ] 4.4 GREEN — Implement provider-neutral raw-record normalization into immutable completed `DailyBar` values and structural/requirement validation with the stable data-failure envelope.
- [ ] 4.5 REFACTOR — Keep provider ordering/conversion in normalization and keep validation independent of provider SDKs or live-network behavior.
- [ ] 4.6 VERIFY — Run data slice tests plus full pytest/ruff/mypy checks.

## 5. Trading-calendar continuity, freshness, and Decision as-of

- [ ] 5.1 RED — Add calendar-aware continuity tests proving weekends/holidays are not gaps and a missing expected trading day fails with `DATA_FAILED / DATA_GAP`.
- [ ] 5.2 RED — Add freshness tests proving a missing latest required completed trading-day observation fails with `DATA_FAILED / STALE_DATA`.
- [ ] 5.3 RED — Add Decision as-of tests for historical trading dates, historical non-trading dates, omitted `as_of` with no session in progress, omitted `as_of` during an incomplete session, current trading day before completion, and preservation of requested vs resolved as-of.
- [ ] 5.4 RED — Add a future-date request test expecting `CONFIGURATION_FAILED / INVALID_AS_OF` and proving market-data loading does not begin; run and verify intended RED failures.
- [ ] 5.5 GREEN — Implement timezone-aware Clock/TradingCalendar ports, deterministic as-of resolution, calendar-based continuity/freshness validation, and requested/resolved date metadata.
- [ ] 5.6 REFACTOR — Ensure market timezone/session rules are owned by the TradingCalendar adapter and never inferred from the GitHub runner/local system timezone.
- [ ] 5.7 VERIFY — Run calendar/as-of tests plus full pytest/ruff/mypy checks.

## 6. Minimum history and Decision eligibility

- [ ] 6.1 RED — Add a Decision behavior test with structurally valid data below the selected Strategy's `minimum_history`, expecting `DATA_FAILED / INSUFFICIENT_HISTORY`, no Strategy evaluation, and no `NEUTRAL` substitute.
- [ ] 6.2 RED — Add a test proving `minimum_history` is an eligibility threshold and does not truncate a larger valid dataset to exactly that many observations; run and verify intended RED failures.
- [ ] 6.3 GREEN — Implement Decision eligibility evaluation against the Strategy's declared minimum history while preserving the full eligible historical view bounded by resolved as-of.
- [ ] 6.4 REFACTOR — Keep minimum-history policy in shared data eligibility behavior so Backtest can reuse it with different WARMUP semantics.
- [ ] 6.5 VERIFY — Run eligibility tests plus full pytest/ruff/mypy checks.

## 7. Decision intraday overlay without formal-state contamination

- [ ] 7.1 RED — Add a Decision behavior test for an incomplete current session where formal StrategyResult uses T-1 completed data and a separate valid snapshot exposes session date, open, latest price, and snapshot time.
- [ ] 7.2 RED — Add tests proving snapshot values cannot change formal market state, entry/exit plans, indicators/model state, or StrategyResult and cannot declare a fill.
- [ ] 7.3 RED — Add tests for deterministic current-price relationships to analytical levels and prove no framework `NEAR` state is inferred without an explicit future tolerance rule.
- [ ] 7.4 RED — Add a test proving open/latest-only snapshot data cannot claim a level was touched earlier in the session.
- [ ] 7.5 RED — Add unavailable/invalid snapshot tests proving a formally valid Decision can still succeed with the overlay omitted or unavailable; run and verify intended RED failures.
- [ ] 7.6 GREEN — Implement optional `IntradaySnapshot`, snapshot validation, and observational overlay construction after formal Decision evaluation.
- [ ] 7.7 REFACTOR — Keep intraday types/builders outside StrategyContext and StrategyResult and remove any path by which snapshot data can enter formal historical indicators.
- [ ] 7.8 VERIFY — Run intraday tests plus full pytest/ruff/mypy checks.

## 8. Decision success, neutral, failure, and artifact contract

- [ ] 8.1 RED — Add a valid `NEUTRAL` Decision test proving `NEUTRAL` is successful only after configuration/data eligibility and Strategy evaluation succeed.
- [ ] 8.2 RED — Add a Strategy evaluation failure test expecting `STRATEGY_FAILED`, machine-readable code, human-readable reason, and no valid market state or plan represented as successful output.
- [ ] 8.3 RED — Add successful artifact traceability tests for instrument, resolved as-of, strategy, parameter set, resolved parameters, Git revision, StrategyResult, and data-quality status.
- [ ] 8.4 RED — Add early configuration-failure artifact tests proving unresolved strategy/parameter metadata is not fabricated.
- [ ] 8.5 RED — Add success and failure artifact tests requiring exactly `僅為個人研究與策略驗證，不構成任何形式之投資建議。`; run and verify intended RED failures.
- [ ] 8.6 GREEN — Implement the shared failure envelope and Decision artifact builder/JSON serialization with optional metadata according to the point of failure.
- [ ] 8.7 REFACTOR — Centralize the exact disclaimer and shared failure serialization so future strategies cannot override or duplicate them.
- [ ] 8.8 VERIFY — Run Decision artifact tests plus full pytest/ruff/mypy checks.

## 9. Analytical Backtest walking skeleton and no-look-ahead

- [ ] 9.1 RED — Add an outside-in analytical Backtest test using deterministic fixtures and a test-only Strategy, expecting chronological StrategyResult replay across multiple eligible trading dates and no execution state.
- [ ] 9.2 RED — Add a cross-application equivalence test proving Decision and Backtest produce equivalent analytical StrategyResults for equivalent strategy/config/code/data/`as_of=T` inputs.
- [ ] 9.3 RED — Add a future-data test where the loaded dataset extends beyond T and prove observations after T cannot affect the StrategyResult evaluated at T; run and verify intended RED failures.
- [ ] 9.4 GREEN — Implement Backtest chronological iteration using bounded historical views and the same common Strategy evaluator used by Decision.
- [ ] 9.5 REFACTOR — Remove any duplicated strategy-evaluation path or Backtest-only simplified strategy logic.
- [ ] 9.6 VERIFY — Run Backtest walking-skeleton/equivalence tests plus full pytest/ruff/mypy checks.

## 10. Backtest ACTIVE and EXPLICIT assignment modes

- [ ] 10.1 RED — Add `ACTIVE` mode tests proving the instrument active strategy+parameter set is used and missing active assignment fails with `CONFIGURATION_FAILED / ACTIVE_STRATEGY_NOT_CONFIGURED` before data loading.
- [ ] 10.2 RED — Add `EXPLICIT` mode tests proving a complete compatible strategy+parameter pair is used without mutating the instrument's active assignment and still works when the configured instrument has no active assignment.
- [ ] 10.3 RED — Add partial explicit-override tests for strategy-only and parameter-set-only requests, expecting `CONFIGURATION_FAILED` and proving active values are not silently borrowed; run and verify intended RED failures.
- [ ] 10.4 GREEN — Implement Backtest assignment-mode request validation and reuse the common resolver for ACTIVE/EXPLICIT resolution.
- [ ] 10.5 REFACTOR — Keep Decision's active-only policy at the Decision boundary rather than adding special cases to Strategy.
- [ ] 10.6 VERIFY — Run assignment-mode tests plus full pytest/ruff/mypy checks.

## 11. Backtest pre-roll, WARMUP, and required-data failure semantics

- [ ] 11.1 RED — Add a pre-roll test proving observations before requested `start_date` may satisfy minimum history but are not emitted as requested evaluation dates.
- [ ] 11.2 RED — Add tests proving early valid-but-insufficient requested dates are `WARMUP`, produce no StrategyResult, and are not `NEUTRAL` or data failures.
- [ ] 11.3 RED — Add a range test where all requested dates are WARMUP, expecting `DATA_FAILED / INSUFFICIENT_HISTORY` and no successful empty timeline.
- [ ] 11.4 RED — Add a mixed range test proving WARMUP dates remain distinguishable while later eligible dates produce StrategyResults and the Backtest may succeed.
- [ ] 11.5 RED — Add invalid required historical-data tests proving the Backtest fails with `DATA_FAILED` rather than silently skipping invalid bars; run and verify intended RED failures.
- [ ] 11.6 GREEN — Implement pre-roll preparation, shared minimum-history eligibility, WARMUP timeline markers, zero-eligible detection, and fail-fast required-data handling.
- [ ] 11.7 REFACTOR — Keep WARMUP as Backtest application semantics layered on shared eligibility rather than adding WARMUP to Strategy MarketState.
- [ ] 11.8 VERIFY — Run pre-roll/WARMUP/data-failure tests plus full pytest/ruff/mypy checks.

## 12. Backtest Strategy failure and no-execution boundary

- [ ] 12.1 RED — Add a test where Strategy evaluation succeeds on earlier eligible dates and fails at T, expecting `STRATEGY_FAILED`, immediate failure semantics, and no partial timeline labeled successful.
- [ ] 12.2 RED — Add a test where a StrategyResult contains an entry plan and prove analytical Backtest records the plan without creating fills, positions, cash balances, PnL, returns, or drawdown.
- [ ] 12.3 RED — Add dependency-boundary tests ensuring analytical Backtest does not import or require an execution simulator; run and verify intended RED failures.
- [ ] 12.4 GREEN — Implement Backtest Strategy-failure propagation and keep output limited to analytical timeline/failure diagnostics.
- [ ] 12.5 REFACTOR — Remove any execution-derived fields or placeholder abstractions that slipped into Backtest domain/application models.
- [ ] 12.6 VERIFY — Run strategy-failure/no-execution tests plus full pytest/ruff/mypy checks.

## 13. Analytical Backtest artifact contract

- [ ] 13.1 RED — Add successful artifact tests for instrument, assignment mode, strategy, parameter set, resolved parameters, Git revision, requested start/end dates, validation status, WARMUP markers where applicable, and eligible StrategyResult timeline.
- [ ] 13.2 RED — Add failed artifact tests requiring top-level failed status, failure category, machine-readable code, human-readable reason, and no partial timeline represented as successful output.
- [ ] 13.3 RED — Add success and failure artifact tests requiring exactly `僅為個人研究與策略驗證，不構成任何形式之投資建議。`; run and verify intended RED failures.
- [ ] 13.4 GREEN — Implement analytical Backtest artifact builder and JSON serialization using the shared failure/disclaimer contracts.
- [ ] 13.5 REFACTOR — Keep artifact schema strategy-neutral and avoid adding trades/equity-curve/execution fields.
- [ ] 13.6 VERIFY — Run Backtest artifact tests plus full pytest/ruff/mypy checks.

## 14. Repository request and GitHub Actions scaffold alignment

- [ ] 14.1 RED — Add schema/parsing tests for the repository Decision request shape (`symbol`, optional `as_of`) and Backtest request shape (`symbol`, `mode`, conditional `strategy`/`parameter_set`, `start_date`, `end_date`).
- [ ] 14.2 RED — Add checks proving Decision rejects research overrides and Backtest rejects partial EXPLICIT assignments through repository request inputs; run and verify intended RED failures.
- [ ] 14.3 GREEN — Update `requests/decision.json` and `requests/backtest.json` examples to the approved request contracts without adding personal portfolio state.
- [ ] 14.4 GREEN — Align `.github/workflows/decision.yml` and `.github/workflows/backtest.yml` inputs/placeholder wording with formal Decision and analytical Backtest semantics; remove the obsolete fill-simulation placeholder and keep workflow YAML free of strategy rules.
- [ ] 14.5 GREEN — Keep live provider/calendar/production-strategy composition explicitly deferred rather than introducing fake production implementations solely to make the scaffolds execute live analysis.
- [ ] 14.6 REFACTOR — Ensure workflow orchestration remains an adapter boundary and generated analytical outputs are intended for Actions Artifacts rather than repository commits.
- [ ] 14.7 VERIFY — Run request parsing tests, workflow static checks if configured, and full pytest/ruff/mypy checks.

## 15. End-to-end framework regression and OpenSpec conformance

- [ ] 15.1 RED — Add/confirm end-to-end application smoke tests covering one successful Decision, one successful analytical Backtest, representative configuration/data/strategy failures, historical as-of replay, and an optional intraday-overlay case using only test adapters.
- [ ] 15.2 RED — Temporarily verify the smoke tests would detect look-ahead, Decision/Backtest strategy divergence, missing disclaimer, execution-state leakage, and a configuration failure that incorrectly loads data.
- [ ] 15.3 GREEN — Make only the minimum integration fixes necessary for all approved capability behaviors to pass together; do not implement deferred production strategies/providers/execution simulation.
- [ ] 15.4 REFACTOR — Remove duplicate orchestration, dead abstractions, and strategy-specific assumptions introduced during vertical-slice implementation while preserving all behavior tests.
- [ ] 15.5 VERIFY — Run the complete test suite and required quality gates: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run mypy src tests`.
- [ ] 15.6 VERIFY — Run OpenSpec validation/status for `establish-strategy-engine` and confirm proposal, specs, design, and tasks remain mutually consistent before implementation is declared complete.
