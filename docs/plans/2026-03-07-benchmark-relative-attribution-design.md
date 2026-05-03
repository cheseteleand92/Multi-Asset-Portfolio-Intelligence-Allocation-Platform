# Benchmark-Relative Backtest Attribution Design

**Date:** 2026-03-07

**Scope:** Extend backtest detail output with benchmark-relative diagnostics derived from the stored strategy run and the benchmark backtest result.

## Problem

The platform can already return strategy NAV, benchmark NAV, turnover, and transaction-cost metrics, but it still does not answer the core PM research question: how did the strategy behave relative to its benchmark? Users need benchmark-relative return diagnostics without manually reconstructing active-return series outside the API.

## Options

### 1. Recommended: enrich backtest detail with relative metrics

- Rebuild the benchmark as a full backtest result, not just NAV.
- Align strategy and benchmark series by date.
- Return a `relative_attribution` block with summary metrics and a date-level series.

Trade-off: this is summary-oriented rather than a full Brinson stack, but it is immediately useful and fits the existing API.

### 2. Full holdings-based Brinson attribution

- Store benchmark holdings and asset-level benchmark returns and compute allocation/selection/interaction effects.

Trade-off: more institutional, but it requires additional data persistence and a larger product surface.

### 3. Summary-only benchmark stats

- Return only information ratio / tracking error style summary numbers.

Trade-off: lower scope, but weaker for debugging and time-series inspection.

## Decision

Implement option 1.

## Architecture

- Add a helper that builds the benchmark as a full `BacktestResult`.
- Add a service helper that aligns portfolio NAV/weights with benchmark NAV/weights and computes:
  - annualized active return
  - tracking error
  - information ratio
  - max relative drawdown
  - average active share
- Return both summary metrics and a `series` payload with per-date active return and active share.

## Validation

- Add API tests that verify the relative attribution block exists when a benchmark is configured.
- Add API tests that verify the block is absent or `None` when benchmark is `none`.
- Run targeted tests, then `python -m pytest -q`, then `ruff check backend tests backtest core examples`.
