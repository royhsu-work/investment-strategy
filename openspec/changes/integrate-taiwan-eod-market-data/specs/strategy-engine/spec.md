## Purpose

Extend the shared Strategy Engine configuration contract with provider-neutral instrument listing-venue identity required for market-data routing.

## ADDED Requirements

### Requirement: Configured instruments identify their listing venue

The system SHALL represent an instrument's listing venue as provider-neutral configuration distinct from the instrument symbol, strategy assignment, parameter set, and any provider-specific market-data identifier.

#### Scenario: Taiwan instrument is configured for market-data acquisition

- GIVEN a configured Taiwan instrument
- WHEN its instrument configuration is resolved for downstream market-data acquisition
- THEN the configuration identifies the canonical instrument symbol
- AND it identifies the instrument's listing venue
- AND the listing venue is not encoded as a provider-specific ticker suffix or provider SDK value

#### Scenario: Two instruments use different Taiwan listing venues

- GIVEN two configured instruments whose canonical symbols belong to different supported Taiwan listing venues
- WHEN their configurations are resolved
- THEN each instrument retains its own listing-venue identity
- AND downstream provider adapters can route or map them without changing the canonical symbols used by Strategy, Decision, or Backtest

### Requirement: Listing venue is independent of strategy assignment

The system SHALL keep instrument listing-venue identity independent of active strategy assignment and research parameter selection.

#### Scenario: Instrument has no active production strategy

- GIVEN a configured instrument with a valid listing venue
- AND the instrument has no active strategy assignment
- WHEN the instrument configuration is read for market-data concerns
- THEN its listing venue remains available
- AND absence of an active strategy does not erase or fabricate market identity
