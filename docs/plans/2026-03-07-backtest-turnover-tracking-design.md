# Backtest Turnover Tracking Design

**Date:** 2026-03-07

**Scope:** Expose daily turnover and transaction-cost series from the backtest engine through persisted results and the backtest detail API.

## Problem

The engine already computes turnover internally to apply transaction costs, but it discards that information before returning results. That makes the platform weaker for research because users can observe NAV impact only indirectly, cannot diagnose trading intensity, and cannot compare execution assumptions across strategy runs.

## Decision

Extend backtest outputs with explicit trading metrics:

- `BacktestResult` will include daily `turnover` and `transaction_costs` series.
- Each stored backtest result row will persist these values in `metrics_json`.
- The backtest detail API will return a `metrics` time series alongside `nav` and `benchmark`.

## Rationale

- Uses metrics that are already computed, so the implementation cost is low.
- Keeps backward compatibility for existing NAV and weight consumers while adding research observability.
- Makes the new drift-threshold feature measurable; users can see when turnover was actually suppressed.

## Validation

- Add engine tests for turnover on initial allocation, scheduled rebalance, and skipped rebalance paths.
- Add an API test that confirms the detail payload exposes per-date turnover and transaction-cost metrics.
- Run targeted backtest tests, then `python -m pytest -q`, then `ruff check backend tests backtest examples`.
