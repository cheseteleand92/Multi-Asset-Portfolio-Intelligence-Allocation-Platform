# Drift Threshold Rebalancing Design

**Date:** 2026-03-07

**Scope:** Add an optional research-oriented rebalance trigger that skips scheduled trades unless portfolio drift versus target weights breaches a configured threshold.

## Problem

The backtest engine currently trades on every scheduled rebalance date once enough lookback history exists. That is easy to explain, but it overstates turnover, ignores transaction-friction realism, and makes it harder to study whether a strategy's signal is strong enough to justify a trade.

## Decision

Add an optional `rebalance_threshold` parameter to the walk-forward engine and service layer:

- The engine still computes target weights on the first eligible day and applies them immediately.
- On later scheduled rebalance dates, the engine computes the new target weights but only trades if the absolute weight drift versus current weights breaches the threshold.
- If the threshold is omitted or non-positive, behavior stays identical to today's calendar-based rebalancing.
- The threshold is passed through backtest strategy runs and benchmark runs so comparisons use the same execution assumptions.

## Rationale

- Preserves current defaults and avoids silent strategy behavior changes for existing users.
- Adds a useful research control with a low-complexity API surface.
- Improves realism without introducing a larger expected-utility optimizer or regime gate yet.
- Keeps the implementation local to the backtest engine and service boundary.

## Validation

- Add engine tests that show:
  - scheduled rebalance is skipped when target drift stays below threshold
  - scheduled rebalance occurs when target drift breaches threshold
  - default behavior remains unchanged when no threshold is provided
- Add an API regression test to confirm the parameter is accepted and persisted in backtest detail output.
- Run targeted tests, then `python -m pytest -q`, then `ruff check backend tests`.
