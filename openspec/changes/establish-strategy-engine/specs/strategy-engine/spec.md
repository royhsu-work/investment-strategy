## Purpose

Define the common observable behavior of strategy evaluation so Decision and analytical Backtest flows can consume different strategy implementations without duplicating strategy logic or introducing hidden state.

## ADDED Requirements

### Requirement: Strategy declares market-data requirements

The system SHALL obtain the selected strategy's declared data frequency, required fields, and minimum history before determining data eligibility or running strategy evaluation.

#### Scenario: Strategy requirements are available before data eligibility

- GIVEN a selected strategy
- WHEN its market-data requirements are requested
- THEN the requirements identify the required frequency
- AND they identify the required fields
- AND they identify the minimum history needed for eligible evaluation

### Requirement: Explicit strategy evaluation inputs

The system SHALL evaluate a strategy using only the selected instrument, the resolved strategy configuration, the evaluation `as_of` date, and market data available for that evaluation.

#### Scenario: Evaluate with explicit inputs

- GIVEN an instrument, a resolved strategy configuration, an `as_of` trading date, and valid market data
- WHEN strategy evaluation is requested
- THEN the evaluation result is derived from those explicit inputs
- AND no real portfolio holding, average cost, account cash, or prior execution state is required

### Requirement: Reproducible analytical evaluation

The system SHALL produce equivalent analytical strategy results when the strategy identity, parameter set, code revision, market data, and `as_of` date are equivalent.

#### Scenario: Repeat the same evaluation

- GIVEN the same strategy identity, parameter set, code revision, market data, and `as_of` date
- WHEN the strategy is evaluated more than once
- THEN the analytical strategy results are equivalent

### Requirement: No future information in strategy evaluation

The system SHALL exclude observations and information that become available after the evaluation `as_of` point from the strategy evaluation.

#### Scenario: Future observations are present in the source dataset

- GIVEN market data containing observations both on or before T and after T
- WHEN the strategy is evaluated with `as_of=T`
- THEN the evaluation uses only information available on or before T
- AND observations after T do not affect the result

### Requirement: Configuration resolution completes before market-data loading

The system SHALL fully resolve and validate the instrument, strategy, parameter set, and strategy parameters before market-data loading or strategy evaluation begins.

#### Scenario: Strategy implementation is not available

- GIVEN a configuration references a strategy that cannot be resolved
- WHEN configuration resolution runs
- THEN the system fails with `CONFIGURATION_FAILED`
- AND the failure code is `STRATEGY_NOT_FOUND`
- AND market-data loading does not run
- AND strategy evaluation does not run

#### Scenario: Parameter set is not available

- GIVEN a configuration references a parameter set that cannot be resolved
- WHEN configuration resolution runs
- THEN the system fails with `CONFIGURATION_FAILED`
- AND the failure code is `PARAMETER_SET_NOT_FOUND`
- AND market-data loading does not run
- AND strategy evaluation does not run

### Requirement: Compatible strategy and parameter-set resolution

The system SHALL resolve a strategy together with a parameter set owned by that strategy before evaluation.

#### Scenario: Compatible strategy and parameter set

- GIVEN a configured strategy and a parameter set declared for that strategy
- WHEN the configuration is resolved
- THEN the system returns a resolved strategy configuration containing the strategy identity and parameter-set identity

#### Scenario: Strategy and parameter set do not match

- GIVEN a selected strategy and a parameter set declared for a different strategy
- WHEN the configuration is resolved
- THEN the system rejects the configuration with `CONFIGURATION_FAILED`
- AND the failure code is `STRATEGY_PARAMETER_MISMATCH`
- AND market-data loading does not run
- AND strategy evaluation does not run

### Requirement: Invalid strategy parameters are rejected before evaluation

The system SHALL reject a parameter set whose values are invalid for the selected strategy before market-data loading or strategy evaluation starts.

#### Scenario: Invalid parameter values

- GIVEN a strategy and a parameter set owned by that strategy
- AND the parameter values violate that strategy's accepted parameter constraints
- WHEN the configuration is resolved
- THEN the system rejects the configuration with `CONFIGURATION_FAILED`
- AND the failure code is `INVALID_STRATEGY_PARAMETERS`
- AND market-data loading does not run
- AND strategy evaluation does not run

### Requirement: Common swing-analysis result

The system SHALL return a common analytical result that identifies the strategy and `as_of` date and exposes market state, entry plan, exit plan, strategy-specific signals, diagnostics, and reasons.

#### Scenario: Strategy returns an accumulation plan

- GIVEN a valid strategy evaluation that identifies an accumulation opportunity
- WHEN the analytical result is produced
- THEN the market state is `ACCUMULATION`
- AND the result can contain entry-plan information
- AND strategy-specific signals and diagnostics can be preserved without changing the common result semantics

### Requirement: Common market-state semantics

The system SHALL represent common swing-stage state using only `NEUTRAL`, `ACCUMULATION`, `TREND`, or `REVERSAL_RISK` at the shared framework level.

#### Scenario: Strategy exposes an implementation-specific regime

- GIVEN a strategy that internally classifies a model-specific regime
- WHEN the common analytical result is produced
- THEN the common market state is one of `NEUTRAL`, `ACCUMULATION`, `TREND`, or `REVERSAL_RISK`
- AND the implementation-specific regime may be preserved in strategy-specific signals or diagnostics

### Requirement: Entry and exit plans remain analytical

The system SHALL treat entry and exit plans as analytical strategy output and SHALL NOT represent them as completed executions, fills, or portfolio state.

#### Scenario: Strategy produces an entry level

- GIVEN a strategy evaluation that produces an entry level
- WHEN the common result is returned
- THEN the entry level is represented as part of the analytical entry plan
- AND the result does not claim that a purchase was executed

### Requirement: Entry and exit plan types are asymmetric

The system SHALL allow an entry plan to contain price levels and conditional triggers while allowing an exit plan to contain dynamic protective levels and conditional triggers without requiring a fixed profit target.

#### Scenario: Trend strategy has no fixed target

- GIVEN a strategy that is in `TREND`
- AND the strategy produces a dynamic protective exit condition without a fixed profit target
- WHEN the analytical result is returned
- THEN the exit plan can represent the dynamic protection and trigger
- AND a fixed profit target is not required
