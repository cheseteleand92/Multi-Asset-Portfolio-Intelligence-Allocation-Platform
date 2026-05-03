# Covariance Ensemble and Backtest Sweeps Design

**Date:** 2026-03-07

**Scope:** Add configurable covariance estimation to the optimization stack and expose an in-memory backtest sweep endpoint for research comparisons.

## Problem

The current optimization path implicitly uses `window_returns.cov()` everywhere. That makes research brittle because covariance modeling is one of the biggest drivers of allocation stability, but there is no way to compare sample covariance against faster-decay or shrinkage-style alternatives. Separately, the platform can run individual backtests but cannot efficiently compare parameter combinations without manual repetition.

## Options

### 1. Recommended: lightweight covariance methods + stateless sweep API

- Add a reusable covariance estimator with `sample`, `ewma`, `shrinkage`, and `ensemble`.
- Thread `covariance_method` through HRP, ERC, and mean-variance allocators.
- Add `POST /api/backtests/sweep` that runs a cartesian grid in memory and returns summary metrics without writing new database rows.

Trade-off: the sweep results are not persisted automatically, but the implementation is small, testable, and immediately useful.

### 2. Database-backed research experiments

- Create experiment/run tables, persist every grid point, and add history views.

Trade-off: stronger long-term workflow, but much higher schema and product complexity right now.

### 3. Covariance upgrade only

- Improve covariance estimation but keep manual one-off backtests.

Trade-off: lower scope, but it leaves the research loop inefficient.

## Decision

Implement option 1.

## Architecture

- `core/optimization.py` gets a reusable covariance estimator function plus the ensemble method.
- Backtest strategy allocators accept `covariance_method` from params and use the chosen estimator.
- Backtest service adds a sweep helper that expands parameter lists and computes summary metrics such as final NAV, annualized return, annualized vol, max drawdown, average turnover, and total transaction cost.
- Router adds a new backtest sweep endpoint that returns the computed summaries directly.

## Validation

- Core tests must prove the covariance estimators are symmetric, finite, and label-preserving, and that `ensemble` differs from plain sample covariance on non-trivial data.
- API tests must prove `covariance_method` is passed into backtest runs and that the sweep endpoint returns multiple combinations with summary fields.
- Run targeted tests, then `python -m pytest -q`, then `ruff check backend tests backtest examples`.
